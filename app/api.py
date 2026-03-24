from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.services.ingest_job_manager import IngestJob, get_ingest_job_manager
from app.services.ingestion_service import ingest_documents
from app.services.query_service import build_answer


def _job_to_dict(j: IngestJob) -> dict[str, Any]:
    return {
        "job_id": j.job_id,
        "input_dir": j.input_dir,
        "state": j.state.value,
        "created_at": j.created_at,
        "updated_at": j.updated_at,
        "progress_percent": j.progress_percent,
        "stage": j.stage,
        "message": j.message,
        "result": j.result,
        "error": j.error,
        "current_file": j.current_file,
        "files_total": j.files_total,
        "files_done": j.files_done,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background ingest worker; stop gracefully on shutdown."""
    mgr = get_ingest_job_manager()
    mgr.start_worker()
    yield
    mgr.stop_worker()


app = FastAPI(
    title="Net-RAG API",
    version="0.3.0",
    lifespan=lifespan,
    description="Network protocol RAG: sync/async ingestion, grounded query. "
    "Run API with a single uvicorn worker if using in-memory ingest jobs, "
    "or externalize jobs (Redis/RQ) for horizontal scale.",
)


class IngestRequest(BaseModel):
    input_dir: str = Field(..., description="Directory path with PDF/TXT/MD files")


class QueryRequest(BaseModel):
    query: str
    top_k: int | None = None


class IngestJobSubmitResponse(BaseModel):
    job_id: str
    status_url: str


@app.get("/health")
def health(detailed: bool = False) -> dict:
    out: dict = {"status": "ok", "service": "net-rag-api"}
    if detailed:
        mgr = get_ingest_job_manager()
        out["ingest_jobs"] = {
            "worker_alive": mgr.worker_alive(),
            "queue_depth": mgr.queue_depth(),
            "backend": "in_memory_thread_queue",
            "note": "Replace with Redis/RQ for multi-replica API + durable jobs.",
        }
    return out


@app.post("/ingest")
def ingest(payload: IngestRequest) -> dict:
    """Synchronous ingestion (blocks until complete). Prefer /ingest/job for large corpora."""
    try:
        result = ingest_documents(payload.input_dir)
        return {"ok": True, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/ingest/job", response_model=IngestJobSubmitResponse)
def ingest_job_submit(payload: IngestRequest) -> IngestJobSubmitResponse:
    """
    Queue a background ingestion job. Poll ``GET /ingest/status/{job_id}`` until
    ``succeeded`` or ``failed``. Jobs run **one at a time** per API process so FAISS
    writes stay consistent.
    """
    p = Path(payload.input_dir).expanduser().resolve()
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"Input directory not found: {p}")
    if not p.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {p}")

    mgr = get_ingest_job_manager()
    job_id = mgr.submit(str(p))
    return IngestJobSubmitResponse(
        job_id=job_id,
        status_url=f"/ingest/status/{job_id}",
    )


@app.get("/ingest/status/{job_id}")
def ingest_job_status(job_id: str) -> dict:
    mgr = get_ingest_job_manager()
    job = mgr.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return {"ok": True, "job": _job_to_dict(job)}


@app.get("/ingest/jobs")
def ingest_jobs_list(limit: int = 20) -> dict:
    """Recent jobs (newest first). Ephemeral unless you add a durable store."""
    mgr = get_ingest_job_manager()
    jobs: List[IngestJob] = mgr.list_recent(limit=min(max(limit, 1), 100))
    return {"ok": True, "jobs": [_job_to_dict(j) for j in jobs]}


@app.post("/query")
def query(payload: QueryRequest) -> dict:
    try:
        result = build_answer(
            payload.query,
            payload.top_k,
            retrieval_mode=payload.retrieval_mode,
        )
        return {"ok": True, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
