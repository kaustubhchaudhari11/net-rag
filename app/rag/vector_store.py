import os
from typing import List

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.config import settings
from app.rag.embedder import get_embeddings


def _ensure_vector_dir() -> None:
    os.makedirs(settings.vector_db_dir, exist_ok=True)


def index_exists() -> bool:
    return os.path.isfile(
        os.path.join(settings.vector_db_dir, "index.faiss")
    ) and os.path.isfile(
        os.path.join(settings.vector_db_dir, "index.pkl")
    )


def save_documents_to_index(chunks: List[Document]) -> int:
    _ensure_vector_dir()
    if not chunks:
        return 0
    embeddings = get_embeddings()
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(settings.vector_db_dir)
    return len(chunks)


def load_index() -> FAISS:
    _ensure_vector_dir()
    embeddings = get_embeddings()
    return FAISS.load_local(
        settings.vector_db_dir,
        embeddings=embeddings,
        allow_dangerous_deserialization=True,
    )
