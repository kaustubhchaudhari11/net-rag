from typing import Any, Dict, List

import requests

from app.config import settings
from app.rag.vector_store import load_index


def search_context(query: str, top_k: int | None = None) -> List[Dict[str, Any]]:
    k = top_k or settings.top_k
    store = load_index()
    docs = store.similarity_search(query=query, k=k)

    items: List[Dict[str, Any]] = []
    for doc in docs:
        items.append(
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
        )
    return items


def _contexts_with_citation_ids(contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    numbered: List[Dict[str, Any]] = []
    for idx, item in enumerate(contexts, start=1):
        metadata = dict(item.get("metadata", {}))
        metadata["citation_id"] = f"C{idx}"
        numbered.append({"content": item.get("content", ""), "metadata": metadata})
    return numbered


def _fallback_answer(query: str, contexts: List[Dict[str, Any]]) -> str:
    if not contexts:
        return "No context found. Please ingest documents first."
    return (
        "Retrieved relevant protocol documentation snippets for your query. "
        "Set LLM_MODEL and LLM_API_KEY in .env to enable grounded synthesized answers with citations."
    )


def _llm_enabled() -> bool:
    return bool(settings.llm_model and settings.llm_api_key)


def _build_prompt(query: str, contexts: List[Dict[str, Any]]) -> str:
    joined_context = []
    for item in contexts:
        citation_id = item["metadata"].get("citation_id", "C?")
        source_file = item["metadata"].get("source_file", "unknown")
        chunk = item["content"]
        joined_context.append(f"[{citation_id}] Source: {source_file}\n{chunk}")

    context_block = "\n\n".join(joined_context)
    return (
        "You are a networking and distributed-systems documentation assistant.\n"
        "Answer ONLY using the provided context snippets. Do not invent facts.\n"
        "When making claims, include inline citations like [C1], [C2].\n"
        "If context is insufficient, explicitly say what is missing.\n\n"
        f"User question:\n{query}\n\n"
        f"Context snippets:\n{context_block}\n"
    )


def _generate_grounded_answer(query: str, contexts: List[Dict[str, Any]]) -> str:
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": "Provide concise, grounded technical answers."},
            {"role": "user", "content": _build_prompt(query, contexts)},
        ],
    }
    response = requests.post(url, headers=headers, json=payload, timeout=settings.llm_timeout_sec)
    response.raise_for_status()
    body = response.json()
    return body["choices"][0]["message"]["content"].strip()


def build_answer(query: str, top_k: int | None = None) -> Dict[str, Any]:
    raw_contexts = search_context(query, top_k)
    if not raw_contexts:
        return {"answer": "No context found. Please ingest documents first.", "contexts": []}
    contexts = _contexts_with_citation_ids(raw_contexts)

    sources = []
    for c in contexts:
        source_file = c["metadata"].get("source_file", "unknown")
        if source_file not in sources:
            sources.append(source_file)

    if _llm_enabled():
        try:
            answer = _generate_grounded_answer(query, contexts)
            mode = "llm_grounded"
        except Exception:
            answer = _fallback_answer(query, contexts)
            mode = "retrieval_fallback"
    else:
        answer = _fallback_answer(query, contexts)
        mode = "retrieval_only"

    return {
        "answer": answer,
        "mode": mode,
        "sources": sources,
        "contexts": contexts,
    }
