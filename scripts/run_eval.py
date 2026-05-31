#!/usr/bin/env python3
"""
Evaluation: gold questions + deterministic retrieval metrics.

Prerequisite: ingest docs/eval_corpus (path as seen by API), then run with API up.

Examples:
  .venv\\Scripts\\python.exe scripts/run_eval.py
  .venv\\Scripts\\python.exe scripts/run_eval.py --retrieval-mode hybrid --json-output eval_report.json
  .venv\\Scripts\\python.exe scripts/run_eval.py --lenient
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

import requests

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from eval_lib import QuestionEvalResult, evaluate_question_result


def _load_questions(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    qs = data.get("questions", [])
    if not qs:
        raise ValueError("No questions in eval file.")
    return data


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Net-RAG evaluation (gold retrieval metrics)")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--questions",
        type=Path,
        default=root / "docs" / "eval_questions.json",
    )
    parser.add_argument(
        "--retrieval-mode",
        choices=["dense", "hybrid"],
        default=None,
        help="Override retrieval; default follows HYBRID_ENABLED on the API",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--tier",
        choices=["gold", "all"],
        default="gold",
        help="Only run questions with tier==gold (recommended)",
    )
    parser.add_argument(
        "--lenient",
        action="store_true",
        help="Exit 0 even when gold checks fail (still prints FAIL lines)",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Write full report JSON (per-question rows + aggregates)",
    )
    args = parser.parse_args()

    try:
        bundle = _load_questions(args.questions)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Failed to load questions: {exc}", file=sys.stderr)
        return 1

    questions: List[Dict[str, Any]] = bundle.get("questions", [])
    if args.tier == "gold":
        questions = [q for q in questions if q.get("tier") == "gold"]

    url = f"{args.base_url.rstrip('/')}/query"
    results: List[QuestionEvalResult] = []

    print(f"Eval dataset: {bundle.get('dataset_version', '?')} | {len(questions)} question(s) | {url}\n")
    if bundle.get("prerequisites"):
        print(f"Note: {bundle['prerequisites']}\n")

    for q in questions:
        qid = q.get("id", "?")
        text = q.get("text", "")
        payload: Dict[str, Any] = {"query": text, "top_k": args.top_k}
        if args.retrieval_mode:
            payload["retrieval_mode"] = args.retrieval_mode

        t0 = time.perf_counter()
        try:
            resp = requests.post(url, json=payload, timeout=180)
        except requests.RequestException as exc:
            results.append(
                QuestionEvalResult(
                    id=qid,
                    ok=False,
                    latency_ms=0.0,
                    http_ok=False,
                    n_contexts=0,
                    retrieval_mode="",
                    answer_mode="",
                    source_hit=False,
                    precision_sources_at_k=None,
                    mrr_expected_source=0.0,
                    context_coverage_ok=False,
                    error=str(exc),
                )
            )
            print(f"[{qid}] REQUEST ERROR: {exc}")
            continue

        elapsed = (time.perf_counter() - t0) * 1000
        if not resp.ok:
            results.append(
                QuestionEvalResult(
                    id=qid,
                    ok=False,
                    latency_ms=elapsed,
                    http_ok=False,
                    n_contexts=0,
                    retrieval_mode="",
                    answer_mode="",
                    source_hit=False,
                    precision_sources_at_k=None,
                    mrr_expected_source=0.0,
                    context_coverage_ok=False,
                    error=f"HTTP {resp.status_code}: {resp.text[:300]}",
                )
            )
            print(f"[{qid}] HTTP {resp.status_code}")
            continue

        body = resp.json()
        result = body.get("result", {})
        ev = evaluate_question_result(qid, elapsed, result, q)
        results.append(ev)

        status = "PASS" if ev.ok else "FAIL"
        p_sk = ev.precision_sources_at_k
        p_sk_s = f"{p_sk:.2f}" if p_sk is not None else "n/a"
        print(
            f"[{qid}] {status} | {elapsed:.0f}ms | ctx={ev.n_contexts} | "
            f"src_hit={ev.source_hit} | P_src@k={p_sk_s} | MRR={ev.mrr_expected_source:.3f} | "
            f"ctx_cov={ev.context_coverage_ok} | {ev.retrieval_mode}"
        )
        if ev.missing_in_contexts:
            print(f"    missing in contexts: {ev.missing_in_contexts}")
        if ev.missing_in_answer:
            print(f"    missing in answer: {ev.missing_in_answer}")
        if not ev.citation_ok:
            print("    citation check failed (LLM mode)")
        if ev.api_warnings:
            for w in ev.api_warnings[:3]:
                print(f"    api warning: {w[:120]}")
        if ev.error:
            print(f"    error: {ev.error}")

    latencies = [r.latency_ms for r in results if r.http_ok]
    precs = [r.precision_sources_at_k for r in results if r.precision_sources_at_k is not None]
    mrrs = [r.mrr_expected_source for r in results if r.http_ok]
    passed = sum(1 for r in results if r.ok)

    summary = {
        "dataset_version": bundle.get("dataset_version"),
        "questions_run": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "http_failures": sum(1 for r in results if not r.http_ok),
        "mean_latency_ms": sum(latencies) / len(latencies) if latencies else None,
        "mean_precision_sources_at_k": sum(precs) / len(precs) if precs else None,
        "mean_mrr_expected_source": sum(mrrs) / len(mrrs) if mrrs else None,
    }

    print(
        f"\n=== Summary ===\n"
        f"pass {passed}/{len(results)} | "
        f"mean_latency_ms={summary['mean_latency_ms'] or 0:.0f} | "
        f"mean_P_src@k={summary['mean_precision_sources_at_k'] or 0:.3f} | "
        f"mean_MRR={summary['mean_mrr_expected_source'] or 0:.3f}"
    )

    if args.json_output:
        report = {"summary": summary, "questions": [asdict(r) for r in results]}
        args.json_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json_output}")

    any_http_fail = any(not r.http_ok for r in results)
    any_eval_fail = any(r.http_ok and not r.ok for r in results)
    if any_http_fail:
        return 1
    if args.lenient:
        return 0
    return 1 if any_eval_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
