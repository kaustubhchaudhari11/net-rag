from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

from app.rag.chunker import split_documents
from app.rag.hybrid_retrieval import invalidate_bm25_cache
from app.rag.vector_store import save_documents_to_index

ProgressCallback = Optional[Callable[[Dict[str, Any]], None]]


def _supported_paths(source_dir: Path) -> List[Path]:
    exts = {".pdf", ".txt", ".md"}
    return sorted(
        p
        for p in source_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in exts
    )


def _load_file(path: Path) -> List[Document]:
    if path.suffix.lower() == ".pdf":
        return PyPDFLoader(str(path)).load()
    if path.suffix.lower() in {".txt", ".md"}:
        return TextLoader(str(path), encoding="utf-8").load()
    raise ValueError(f"Unsupported file format: {path.name}")


def _emit(
    progress: ProgressCallback,
    *,
    stage: str,
    percent: float,
    message: str,
    **extra: Any,
) -> None:
    if progress is None:
        return
    payload: Dict[str, Any] = {
        "stage": stage,
        "percent": max(0.0, min(100.0, percent)),
        "message": message,
    }
    payload.update(extra)
    progress(payload)


def ingest_documents(input_dir: str, *, progress: ProgressCallback = None) -> dict:
    """
    Load all supported files under input_dir, chunk, and rebuild the FAISS index.

    Optional ``progress`` receives dicts: stage, percent, message, and optionally
    file, files_total, files_done.
    """
    source_dir = Path(input_dir).expanduser().resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {source_dir}")

    paths = _supported_paths(source_dir)
    n_files = len(paths)
    _emit(
        progress,
        stage="listing",
        percent=1.0,
        message=f"Found {n_files} file(s) to ingest",
        files_total=n_files,
        files_done=0,
    )

    if not paths:
        _emit(
            progress,
            stage="done",
            percent=100.0,
            message="No matching files; index unchanged",
            files_total=0,
            files_done=0,
        )
        return {"files": 0, "documents": 0, "chunks": 0}

    docs: List[Document] = []
    for i, path in enumerate(paths):
        pct = 5.0 + (50.0 * (i + 1) / max(n_files, 1))
        _emit(
            progress,
            stage="loading",
            percent=pct,
            message=f"Loading {path.name}",
            file=path.name,
            files_total=n_files,
            files_done=i,
        )
        loaded = _load_file(path)
        for doc in loaded:
            doc.metadata["source_file"] = path.name
        docs.extend(loaded)

    _emit(
        progress,
        stage="chunking",
        percent=58.0,
        message="Chunking documents",
        files_total=n_files,
        files_done=n_files,
    )
    chunks = split_documents(docs)

    _emit(
        progress,
        stage="indexing",
        percent=72.0,
        message="Embedding and writing FAISS index",
        files_total=n_files,
        files_done=n_files,
    )
    count = save_documents_to_index(chunks)
    invalidate_bm25_cache()

    unique_files = {d.metadata.get("source_file", "unknown") for d in docs}
    _emit(
        progress,
        stage="done",
        percent=100.0,
        message="Ingestion complete",
        files_total=n_files,
        files_done=n_files,
    )
    return {"files": len(unique_files), "documents": len(docs), "chunks": count}
