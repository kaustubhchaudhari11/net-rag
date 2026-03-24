#!/usr/bin/env python3
"""
Phase 5 — smoke eval: POST /query for each question in docs/eval_questions.json.

Usage (API running):
  .venv\\Scripts\\python.exe scripts/run_eval.py
  .venv\\Scripts\\python.exe scripts/run_eval.py --retrieval-mode hybrid
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


def _load_questions(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    qs = data.get("questions", [])
    if not qs:
        raise ValueError("No questions in eval file.")
    return qs


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Net-RAG /query eval runner")
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
    args = parser.parse_args()

    try:
        questions = _load_questions(args.questions)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Failed to load questions: {exc}", file=sys.stderr)
        return 1

    url = f"{args.base_url.rstrip('/')}/query"
    failures = 0
    latencies: List[float] = []
    substring_misses = 0

    print(f"Running {len(questions)} questions against {url}\n")

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
            print(f"[{qid}] REQUEST ERROR: {exc}")
            failures += 1
            continue
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed)

        if not resp.ok:
            print(f"[{qid}] HTTP {resp.status_code}: {resp.text[:500]}")
            failures += 1
            continue

        body = resp.json()
        result = body.get("result", {})
        n_ctx = len(result.get("contexts") or [])
        mode = result.get("mode", "")
        rpath = ""
        if result.get("contexts"):
            rpath = (result["contexts"][0].get("metadata") or {}).get("retrieval_mode", "")

        print(f"[{qid}] {elapsed:.0f} ms | contexts={n_ctx} | answer_mode={mode} | retrieval={rpath}")

        subs: List[str] = q.get("expected_substrings") or []
        blob = (result.get("answer") or "").lower()
        blob += " ".join(
            (c.get("content") or "").lower() for c in (result.get("contexts") or [])
        )
        for sub in subs:
            if sub.lower() not in blob:
                print(f"    ! substring miss: expected '{sub}' in answer+contexts")
                substring_misses += 1

    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"\nAvg latency: {avg:.0f} ms | failures: {failures} | substring misses: {substring_misses}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
