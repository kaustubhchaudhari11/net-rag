from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

from app.rag.chunker import split_documents
from app.rag.vector_store import save_documents_to_index


def _load_file(path: Path) -> List[Document]:
    if path.suffix.lower() == ".pdf":
        return PyPDFLoader(str(path)).load()
    if path.suffix.lower() in {".txt", ".md"}:
        return TextLoader(str(path), encoding="utf-8").load()
    raise ValueError(f"Unsupported file format: {path.name}")


def ingest_documents(input_dir: str) -> dict:
    source_dir = Path(input_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {source_dir}")

    docs: List[Document] = []
    for path in source_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".pdf", ".txt", ".md"}:
            loaded = _load_file(path)
            for doc in loaded:
                doc.metadata["source_file"] = path.name
            docs.extend(loaded)

    if not docs:
        return {"files": 0, "documents": 0, "chunks": 0}

    chunks = split_documents(docs)
    count = save_documents_to_index(chunks)
    unique_files = {d.metadata.get("source_file", "unknown") for d in docs}
    return {"files": len(unique_files), "documents": len(docs), "chunks": count}
