"""
Background ingestion jobs — Phase 3.

Design goals for scalability / distributed evolution:
- **API contract** (`POST /ingest/job`, `GET /ingest/status/{id}`) stays stable when you swap the backend.
- **Single writer** to the FAISS index: one worker thread processes jobs sequentially (today:
  in-memory queue + threading). Replace this module with Redis + RQ/Celery workers later; keep
  one writer per vector store partition or use mergeable indices.
- **State is ephemeral** in RAM today; move to Redis/Postgres for multi-instance API replicas.

See docs/architecture.md → "Phase 3 ingestion jobs".
"""

from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

from app.services.ingestion_service import ingest_documents


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class IngestJob:
    job_id: str
    input_dir: str
    state: JobState = JobState.QUEUED
    created_at: str = ""
    updated_at: str = ""
    progress_percent: float = 0.0
    stage: str = "queued"
    message: str = "Waiting in queue"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    current_file: Optional[str] = None
    files_total: Optional[int] = None
    files_done: Optional[int] = None


class IngestJobManager:
    """
    In-process job queue + one background worker.
    Serializes writes to the vector index (FAISS save replaces the whole store).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._jobs: Dict[str, IngestJob] = {}
        self._queue: Deque[str] = deque()
        self._worker: Optional[threading.Thread] = None
        self._shutdown = False

    def start_worker(self) -> None:
        with self._lock:
            if self._worker is not None and self._worker.is_alive():
                return
            self._shutdown = False
            self._worker = threading.Thread(
                target=self._worker_loop,
                name="netrag-ingest-worker",
                daemon=True,
            )
            self._worker.start()

    def stop_worker(self) -> None:
        with self._cv:
            self._shutdown = True
            self._cv.notify_all()
        if self._worker is not None:
            self._worker.join(timeout=8.0)

    def submit(self, input_dir: str) -> str:
        job_id = str(uuid.uuid4())
        now = _utc_now_iso()
        job = IngestJob(
            job_id=job_id,
            input_dir=input_dir,
            state=JobState.QUEUED,
            created_at=now,
            updated_at=now,
            progress_percent=0.0,
            stage="queued",
            message="Queued for ingestion",
        )
        with self._lock:
            self._jobs[job_id] = job
            self._queue.append(job_id)
        with self._cv:
            self._cv.notify()
        return job_id

    def get(self, job_id: str) -> Optional[IngestJob]:
        with self._lock:
            j = self._jobs.get(job_id)
            if j is None:
                return None
            return self._copy_job(j)

    def list_recent(self, limit: int = 20) -> List[IngestJob]:
        with self._lock:
            items = sorted(
                self._jobs.values(),
                key=lambda x: x.created_at,
                reverse=True,
            )[:limit]
            return [self._copy_job(j) for j in items]

    def queue_depth(self) -> int:
        with self._lock:
            return len(self._queue)

    def worker_alive(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    @staticmethod
    def _copy_job(j: IngestJob) -> IngestJob:
        return IngestJob(
            job_id=j.job_id,
            input_dir=j.input_dir,
            state=j.state,
            created_at=j.created_at,
            updated_at=j.updated_at,
            progress_percent=j.progress_percent,
            stage=j.stage,
            message=j.message,
            result=dict(j.result) if j.result else None,
            error=j.error,
            current_file=j.current_file,
            files_total=j.files_total,
            files_done=j.files_done,
        )

    def _patch_job(self, job_id: str, **kwargs: Any) -> None:
        j = self._jobs[job_id]
        for k, v in kwargs.items():
            if hasattr(j, k):
                setattr(j, k, v)
        j.updated_at = _utc_now_iso()

    def _worker_loop(self) -> None:
        while True:
            job_id: Optional[str] = None
            with self._cv:
                while not self._shutdown and not self._queue:
                    self._cv.wait(timeout=0.5)
                if self._shutdown and not self._queue:
                    break
                if self._queue:
                    job_id = self._queue.popleft()
            if job_id:
                self._run_job(job_id)

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            if job_id not in self._jobs:
                return

        def on_progress(ev: Dict[str, Any]) -> None:
            with self._lock:
                if job_id not in self._jobs:
                    return
                self._patch_job(
                    job_id,
                    progress_percent=float(ev.get("percent", 0)),
                    stage=str(ev.get("stage", "")),
                    message=str(ev.get("message", "")),
                    current_file=ev.get("file"),
                    files_total=ev.get("files_total"),
                    files_done=ev.get("files_done"),
                )

        with self._lock:
            self._patch_job(
                job_id,
                state=JobState.RUNNING,
                stage="starting",
                message="Starting ingestion",
                progress_percent=0.0,
            )

        try:
            with self._lock:
                input_dir = self._jobs[job_id].input_dir
            result = ingest_documents(input_dir, progress=on_progress)
            with self._lock:
                if job_id not in self._jobs:
                    return
                self._patch_job(
                    job_id,
                    state=JobState.SUCCEEDED,
                    stage="done",
                    message="Ingestion complete",
                    progress_percent=100.0,
                    result=result,
                    error=None,
                    current_file=None,
                )
        except Exception as exc:  # noqa: BLE001
            err = str(exc).strip()
            with self._lock:
                if job_id not in self._jobs:
                    return
                self._patch_job(
                    job_id,
                    state=JobState.FAILED,
                    stage="failed",
                    message="Ingestion failed",
                    error=err,
                    result=None,
                )


_manager: Optional[IngestJobManager] = None
_manager_lock = threading.Lock()


def get_ingest_job_manager() -> IngestJobManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = IngestJobManager()
        return _manager
