"""
Deterministic Phase 5 metrics (no LLM-as-judge).

Definitions:
- source_hit@k: at least one retrieved chunk has metadata.source_file in expected_source_files.
- contexts_precision_sources@k: (# chunks whose source_file is in expected set) / k (k = len(contexts)).
- mrr_expected_source: 1/r where r is 1-based index of first chunk from an expected file, else 0.
- context_coverage: every must_appear_in_contexts string occurs in union of top-k context bodies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _norm(s: str) -> str:
    return (s or "").lower()


def _basename(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1].lower()


def contexts_union_text(contexts: Sequence[Dict[str, Any]]) -> str:
    parts = []
    for c in contexts:
        parts.append(str(c.get("content") or ""))
    return _norm(" ".join(parts))


def source_hit_at_k(
    contexts: Sequence[Dict[str, Any]], expected_files: Sequence[str]
) -> bool:
    if not expected_files:
        return True
    exp = {_basename(f) for f in expected_files}
    for c in contexts:
        sf = str((c.get("metadata") or {}).get("source_file") or "")
        if _basename(sf) in exp:
            return True
    return False


def precision_sources_at_k(
    contexts: Sequence[Dict[str, Any]], expected_files: Sequence[str]
) -> Optional[float]:
    """Fraction of top-k chunks whose source_file is in the expected set. None if no expected set."""
    if not expected_files or not contexts:
        return None
    exp = {_basename(f) for f in expected_files}
    hits = 0
    for c in contexts:
        sf = str((c.get("metadata") or {}).get("source_file") or "")
        if _basename(sf) in exp:
            hits += 1
    return hits / max(len(contexts), 1)


def mrr_expected_source(
    contexts: Sequence[Dict[str, Any]], expected_files: Sequence[str]
) -> float:
    if not expected_files or not contexts:
        return 0.0
    exp = {_basename(f) for f in expected_files}
    for rank, c in enumerate(contexts, start=1):
        sf = str((c.get("metadata") or {}).get("source_file") or "")
        if _basename(sf) in exp:
            return 1.0 / rank
    return 0.0


def missing_substrings(text: str, required: Sequence[str], *, case_insensitive: bool = True) -> List[str]:
    hay = _norm(text) if case_insensitive else text
    missing: List[str] = []
    for sub in required:
        needle = _norm(sub) if case_insensitive else sub
        if needle not in hay:
            missing.append(sub)
    return missing


_CITATION_RE = re.compile(r"\[C\d+\]")


def answer_has_citation(answer: str) -> bool:
    return bool(_CITATION_RE.search(answer or ""))


@dataclass
class QuestionEvalResult:
    id: str
    ok: bool
    latency_ms: float
    http_ok: bool
    n_contexts: int
    retrieval_mode: str
    answer_mode: str
    source_hit: bool
    precision_sources_at_k: Optional[float]
    mrr_expected_source: float
    context_coverage_ok: bool
    missing_in_contexts: List[str] = field(default_factory=list)
    missing_in_answer: List[str] = field(default_factory=list)
    citation_ok: bool = True
    api_warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


def evaluate_question_result(
    qid: str,
    latency_ms: float,
    result: Dict[str, Any],
    spec: Dict[str, Any],
) -> QuestionEvalResult:
    contexts = result.get("contexts") or []
    answer = result.get("answer") or ""
    answer_mode = str(result.get("mode") or "")
    rmode = ""
    if contexts:
        rmode = str((contexts[0].get("metadata") or {}).get("retrieval_mode") or "")

    expected_files = spec.get("expected_source_files") or []
    must_ctx = spec.get("must_appear_in_contexts") or []
    must_ans = spec.get("must_appear_in_answer") or []
    req_cite = bool(spec.get("require_citation_in_answer", False))

    union = contexts_union_text(contexts)
    miss_ctx = missing_substrings(union, must_ctx)
    miss_ans = missing_substrings(answer, must_ans) if must_ans else []

    hit = source_hit_at_k(contexts, expected_files)
    p_sk = precision_sources_at_k(contexts, expected_files)
    mrr = mrr_expected_source(contexts, expected_files)

    cite_ok = True
    citation_enforced = req_cite and answer_mode == "llm_grounded"
    if citation_enforced:
        cite_ok = answer_has_citation(answer)

    warnings = [str(w) for w in (result.get("warnings") or [])]

    ok = (
        len(miss_ctx) == 0
        and len(miss_ans) == 0
        and (not expected_files or hit)
        and (not citation_enforced or cite_ok)
    )

    return QuestionEvalResult(
        id=qid,
        ok=ok,
        latency_ms=latency_ms,
        http_ok=True,
        n_contexts=len(contexts),
        retrieval_mode=rmode,
        answer_mode=answer_mode,
        source_hit=hit if expected_files else True,
        precision_sources_at_k=p_sk,
        mrr_expected_source=mrr,
        context_coverage_ok=len(miss_ctx) == 0,
        missing_in_contexts=miss_ctx,
        missing_in_answer=miss_ans,
        citation_ok=cite_ok,
        api_warnings=warnings,
        error=None,
    )
