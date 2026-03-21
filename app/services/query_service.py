import re
from typing import Any, Dict, List

import requests

from app.config import settings
from app.rag.vector_store import load_index

_CITATION_PATTERN = re.compile(r"\[C(\d+)\]")

SYSTEM_MESSAGE = (
    "You are a senior networking and distributed-systems engineer answering from "
    "retrieved documentation only. Be precise: protocols, states, headers, and "
    "routing behavior must match the snippets. Prefer short numbered steps for "
    "processes (e.g. handshakes). Never fabricate RFC numbers or packet fields."
)


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
        "Rules:\n"
        "1) Use ONLY the context snippets below. If they do not contain enough "
        "information, start your answer with exactly: "
        '"Insufficient context in retrieved snippets:" then briefly list what is missing.\n'
        "2) Every technical claim (definitions, steps, field names, timers, states) "
        "must include at least one inline citation like [C1], [C2] drawn from those snippets.\n"
        "3) Do not cite snippet IDs that are not in the context list.\n"
        "4) If the question is ambiguous, state assumptions and still cite supporting snippets.\n\n"
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
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": _build_prompt(query, contexts)},
        ],
    }
    response = requests.post(url, headers=headers, json=payload, timeout=settings.llm_timeout_sec)
    response.raise_for_status()
    body = response.json()
    return body["choices"][0]["message"]["content"].strip()


def _extract_citations_used(answer: str, num_contexts: int) -> List[str]:
    """Unique [C#] ids appearing in the answer, in order of first appearance."""
    seen: List[str] = []
    for m in _CITATION_PATTERN.finditer(answer):
        n = int(m.group(1))
        if 1 <= n <= num_contexts:
            cid = f"C{n}"
            if cid not in seen:
                seen.append(cid)
    return seen


def _citation_warnings(answer: str, num_contexts: int) -> List[str]:
    warnings: List[str] = []
    if num_contexts == 0:
        return warnings
    if _CITATION_PATTERN.search(answer) is None and "Insufficient context" not in answer:
        warnings.append(
            "The answer contains no [C#] citations; verify it against the retrieved snippets."
        )
    # Flag citations that do not exist in this retrieval set
    for m in _CITATION_PATTERN.finditer(answer):
        n = int(m.group(1))
        if n < 1 or n > num_contexts:
            warnings.append(
                f"Answer cites [C{n}] but only C1–C{num_contexts} exist for this query."
            )
    return warnings


def build_answer(query: str, top_k: int | None = None) -> Dict[str, Any]:
    raw_contexts = search_context(query, top_k)
    if not raw_contexts:
        return {
            "answer": "No context found. Please ingest documents first.",
            "mode": "no_context",
            "sources": [],
            "contexts": [],
            "warnings": [
                "No chunks matched. Run ingestion on a folder that contains your RFCs/manuals, "
                "or try a different query."
            ],
            "citations_used": [],
        }

    contexts = _contexts_with_citation_ids(raw_contexts)
    n_ctx = len(contexts)

    sources = []
    for c in contexts:
        source_file = c["metadata"].get("source_file", "unknown")
        if source_file not in sources:
            sources.append(source_file)

    warnings: List[str] = []
    citations_used: List[str] = []

    if _llm_enabled():
        try:
            answer = _generate_grounded_answer(query, contexts)
            mode = "llm_grounded"
            citations_used = _extract_citations_used(answer, n_ctx)
            warnings.extend(_citation_warnings(answer, n_ctx))
        except Exception as exc:
            detail = str(exc).strip()
            if len(detail) > 240:
                detail = detail[:237] + "..."
            warnings.append(f"LLM request failed ({type(exc).__name__}): {detail}")
            answer = _fallback_answer(query, contexts)
            mode = "retrieval_fallback"
    else:
        answer = _fallback_answer(query, contexts)
        mode = "retrieval_only"
        warnings.append(
            "LLM synthesis disabled: set LLM_MODEL and LLM_API_KEY in .env for grounded answers."
        )

    return {
        "answer": answer,
        "mode": mode,
        "sources": sources,
        "contexts": contexts,
        "warnings": warnings,
        "citations_used": citations_used,
    }
