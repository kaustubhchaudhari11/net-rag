import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.config import settings
from app.rag.hybrid_retrieval import hybrid_search_rrf
from app.rag.vector_store import load_index

_CITATION_PATTERN = re.compile(r"\[C(\d+)\]")

SYSTEM_MESSAGE = (
    "You are a senior networking and distributed-systems engineer answering from "
    "retrieved documentation only. Be precise: protocols, states, headers, and "
    "routing behavior must match the snippets. Prefer short numbered steps for "
    "processes (e.g. handshakes). Never fabricate RFC numbers or packet fields."
)


def _search_context_dense_only(query: str, k: int) -> List[Dict[str, Any]]:
    store = load_index()
    docs = store.similarity_search(query=query, k=k)
    out: List[Dict[str, Any]] = []
    for i, doc in enumerate(docs, start=1):
        meta = dict(doc.metadata or {})
        meta["dense_rank"] = i
        meta["retrieval_mode"] = "dense"
        out.append({"content": doc.page_content, "metadata": meta})
    return out


def search_context(
    query: str,
    top_k: int | None = None,
    *,
    retrieval_mode: str | None = None,
) -> List[Dict[str, Any]]:
    """
    retrieval_mode: None → follow ``HYBRID_ENABLED``; ``dense`` / ``hybrid`` force path.
    """
    k = top_k or settings.top_k
    use_hybrid = settings.hybrid_enabled
    if retrieval_mode == "dense":
        use_hybrid = False
    elif retrieval_mode == "hybrid":
        use_hybrid = True

    if use_hybrid:
        candidate_k = max(k, k * settings.hybrid_candidate_multiplier)
        return hybrid_search_rrf(
            query,
            k,
            candidate_k=candidate_k,
            dense_weight=settings.hybrid_dense_weight,
            bm25_weight=settings.hybrid_keyword_weight,
            rrf_k=settings.hybrid_rrf_k,
        )
    return _search_context_dense_only(query, k)


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
    lines: List[str] = [
        "**Retrieval-only answer** — excerpts from your top retrieved snippets (no LLM). "
        "Set **LLM_MODEL** and **LLM_API_KEY** in `.env` for one synthesized reply with `[C#]` citations.",
        "",
    ]
    max_per_chunk = 900
    max_chunks = 4
    for item in contexts[:max_chunks]:
        meta = item.get("metadata") or {}
        cid = meta.get("citation_id", "?")
        src = meta.get("source_file", "unknown")
        text = (item.get("content") or "").strip()
        if not text:
            continue
        excerpt = text if len(text) <= max_per_chunk else text[: max_per_chunk - 1] + "…"
        lines.append(f"**[{cid}] {src}**\n\n{excerpt}\n")
    lines.append(
        "\n---\n*Expand “Retrieved Context” below for full chunks, or ingest RFC 793 for deeper TCP state detail.*"
    )
    return "\n".join(lines)


def _llm_enabled() -> bool:
    return bool(settings.llm_model and settings.llm_api_key)


def _build_prompt(query: str, contexts: List[Dict[str, Any]]) -> str:
    joined_context = []
    for item in contexts:
        citation_id = item["metadata"].get("citation_id", "C?")
        source_file = item["metadata"].get("source_file", "unknown")
        page = item["metadata"].get("page")
        section = item["metadata"].get("section_hint")
        chunk = item["content"]
        header = f"[{citation_id}] Source: {source_file}"
        if page is not None:
            header += f" | Page: {page}"
        if section:
            header += f" | Section: {section}"
        joined_context.append(f"{header}\n{chunk}")

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


def _parse_llm_usage(body: Dict[str, Any]) -> Optional[Dict[str, int]]:
    raw = body.get("usage")
    if not isinstance(raw, dict):
        return None
    out: Dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        val = raw.get(key)
        if val is not None:
            try:
                out[key] = int(val)
            except (TypeError, ValueError):
                pass
    return out or None


def _generate_grounded_answer(
    query: str, contexts: List[Dict[str, Any]]
) -> Tuple[str, Optional[Dict[str, int]]]:
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
    answer = body["choices"][0]["message"]["content"].strip()
    usage = _parse_llm_usage(body)
    return answer, usage


def _attach_metrics(
    result: Dict[str, Any],
    *,
    t0: float,
    retrieval_ms: float,
    llm_ms: Optional[float],
    llm_usage: Optional[Dict[str, int]],
) -> Dict[str, Any]:
    total_ms = round((time.perf_counter() - t0) * 1000, 2)
    result["latency_ms"] = total_ms
    if settings.include_dev_metrics:
        result["retrieval_ms"] = round(retrieval_ms, 2)
        result["llm_ms"] = round(llm_ms, 2) if llm_ms is not None else None
        result["llm_usage"] = llm_usage
    return result


def _extract_citations_used(answer: str, num_contexts: int) -> List[str]:
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
    for m in _CITATION_PATTERN.finditer(answer):
        n = int(m.group(1))
        if n < 1 or n > num_contexts:
            warnings.append(
                f"Answer cites [C{n}] but only C1–C{num_contexts} exist for this query."
            )
    return warnings


def build_answer(
    query: str,
    top_k: int | None = None,
    *,
    retrieval_mode: str | None = None,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    t_search0 = time.perf_counter()
    raw_contexts = search_context(query, top_k, retrieval_mode=retrieval_mode)
    retrieval_ms = (time.perf_counter() - t_search0) * 1000

    if not raw_contexts:
        result = {
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
        return _attach_metrics(
            result, t0=t0, retrieval_ms=retrieval_ms, llm_ms=None, llm_usage=None
        )

    contexts = _contexts_with_citation_ids(raw_contexts)
    n_ctx = len(contexts)

    sources = []
    for c in contexts:
        source_file = c["metadata"].get("source_file", "unknown")
        if source_file not in sources:
            sources.append(source_file)

    warnings: List[str] = []
    citations_used: List[str] = []
    llm_ms: Optional[float] = None
    llm_usage: Optional[Dict[str, int]] = None

    if _llm_enabled():
        t_llm0 = time.perf_counter()
        try:
            answer, llm_usage = _generate_grounded_answer(query, contexts)
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
            llm_usage = None
        finally:
            llm_ms = (time.perf_counter() - t_llm0) * 1000
    else:
        answer = _fallback_answer(query, contexts)
        mode = "retrieval_only"
        warnings.append(
            "LLM synthesis disabled: set LLM_MODEL and LLM_API_KEY in .env for grounded answers."
        )

    result = {
        "answer": answer,
        "mode": mode,
        "sources": sources,
        "contexts": contexts,
        "warnings": warnings,
        "citations_used": citations_used,
    }
    return _attach_metrics(
        result,
        t0=t0,
        retrieval_ms=retrieval_ms,
        llm_ms=llm_ms,
        llm_usage=llm_usage,
    )
