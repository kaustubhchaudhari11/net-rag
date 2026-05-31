"""
Hybrid retrieval: dense (FAISS) + lexical (BM25) with Reciprocal Rank Fusion.

BM25 excels at exact tokens (RFC numbers, acronyms, field names); dense embeddings
catch paraphrases. RRF merges ranked lists without score calibration.

Cache: BM25 index is rebuilt when the vector store changes (explicit invalidation
after ingest + fingerprint fallback).
"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.config import settings
from app.rag.vector_store import load_index

_lock = threading.Lock()
_cached_bm25: Optional[BM25Retriever] = None
_cache_fingerprint: Optional[str] = None


def invalidate_bm25_cache() -> None:
    """Call after ingest completes so the next query rebuilds BM25 from the new docstore."""
    global _cached_bm25, _cache_fingerprint
    with _lock:
        _cached_bm25 = None
        _cache_fingerprint = None


def _vector_dir_fingerprint() -> str:
    """Cheap signal that FAISS files changed (mtime of index.faiss if present)."""
    base = Path(settings.vector_db_dir)
    idx = base / "index.faiss"
    if not idx.is_file():
        return "missing"
    return f"{idx.stat().st_mtime_ns}:{idx.stat().st_size}"


def doc_fingerprint(doc: Document) -> str:
    """Stable key for the same chunk across retrievers."""
    meta = doc.metadata or {}
    content = doc.page_content or ""
    digest = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
    page = meta.get("page", "")
    src = meta.get("source_file", "?")
    return f"{src}|{page}|{digest}"


def _all_documents_from_faiss(store: FAISS) -> List[Document]:
    """All chunks in the FAISS docstore (order is arbitrary but stable enough for BM25)."""
    out: List[Document] = []
    seen: set[str] = set()
    for doc_id in store.index_to_docstore_id.values():
        if doc_id in seen:
            continue
        seen.add(doc_id)
        doc = store.docstore.search(doc_id)
        if doc is not None:
            out.append(doc)
    return out


def _get_bm25_retriever(store: FAISS) -> Optional[BM25Retriever]:
    global _cached_bm25, _cache_fingerprint
    fp = _vector_dir_fingerprint()
    with _lock:
        if fp == _cache_fingerprint and _cached_bm25 is not None:
            return _cached_bm25
        docs = _all_documents_from_faiss(store)
        if not docs:
            _cached_bm25 = None
            _cache_fingerprint = fp
            return None
        retriever = BM25Retriever.from_documents(docs)
        _cached_bm25 = retriever
        _cache_fingerprint = fp
        return retriever


def _bm25_get_documents(retriever: BM25Retriever, query: str, k: int) -> List[Document]:
    retriever.k = k
    if hasattr(retriever, "invoke"):
        return list(retriever.invoke(query))
    return list(retriever.get_relevant_documents(query))


def hybrid_search_rrf(
    query: str,
    k: int,
    *,
    candidate_k: int,
    dense_weight: float,
    bm25_weight: float,
    rrf_k: int,
) -> List[Dict[str, Any]]:
    """
    Dense + BM25, then RRF over the union of ranked lists.

    Returns context dicts compatible with ``query_service`` (content + metadata).
    """
    store = load_index()
    candidate_k = max(k, candidate_k)

    dense_docs = store.similarity_search(query=query, k=candidate_k)
    bm25_retriever = _get_bm25_retriever(store)

    if not dense_docs:
        return []

    if bm25_retriever is None:
        out: List[Dict[str, Any]] = []
        for i, doc in enumerate(dense_docs[:k], start=1):
            meta = dict(doc.metadata or {})
            meta["dense_rank"] = i
            meta["bm25_rank"] = None
            meta["hybrid_rrf_score"] = None
            meta["retrieval_mode"] = "dense_fallback_no_bm25"
            out.append({"content": doc.page_content, "metadata": meta})
        return out

    bm25_docs = _bm25_get_documents(bm25_retriever, query, candidate_k)

    dense_ranks: Dict[str, int] = {}
    for rank, doc in enumerate(dense_docs, start=1):
        dense_ranks[doc_fingerprint(doc)] = rank

    bm25_ranks: Dict[str, int] = {}
    for rank, doc in enumerate(bm25_docs, start=1):
        bm25_ranks.setdefault(doc_fingerprint(doc), rank)

    key_to_doc: Dict[str, Document] = {}
    for doc in dense_docs:
        key_to_doc.setdefault(doc_fingerprint(doc), doc)
    for doc in bm25_docs:
        key_to_doc.setdefault(doc_fingerprint(doc), doc)

    all_keys = set(dense_ranks.keys()) | set(bm25_ranks.keys())
    sentinel = 10_000
    scored: List[Tuple[float, str]] = []
    for key in all_keys:
        dr = dense_ranks.get(key, sentinel)
        br = bm25_ranks.get(key, sentinel)
        score = (dense_weight / (rrf_k + dr)) + (bm25_weight / (rrf_k + br))
        scored.append((score, key))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_keys = [key for _, key in scored[:k]]

    out = []
    for hybrid_rank, key in enumerate(top_keys, start=1):
        doc = key_to_doc[key]
        dr = dense_ranks.get(key, sentinel)
        br = bm25_ranks.get(key, sentinel)
        fused = (dense_weight / (rrf_k + dr)) + (bm25_weight / (rrf_k + br))
        meta = dict(doc.metadata or {})
        meta["dense_rank"] = dense_ranks.get(key)
        meta["bm25_rank"] = bm25_ranks.get(key)
        meta["hybrid_rrf_score"] = round(fused, 6)
        meta["hybrid_rank"] = hybrid_rank
        meta["retrieval_mode"] = "hybrid_bm25_dense_rrf"
        out.append({"content": doc.page_content, "metadata": meta})
    return out
