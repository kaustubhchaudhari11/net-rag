# Net-RAG — Pitch & Launch Kit

## One-liner

**Net-RAG is a grounded Q&A engine for the documents that run the internet** — RFCs,
router/switch manuals, and architecture guides — answering protocol questions with
**verifiable citations** instead of hallucinations.

## The problem

Network/SRE/security engineers lose hours digging through dense RFCs and 800-page
vendor manuals. General chatbots **hallucinate protocol details** — wrong timers, made-up
RFC numbers, invented header fields — which is unsafe in infrastructure work.

## The solution

Upload RFCs/manuals → structure-aware chunking → **hybrid retrieval (BM25 + dense, RRF)**
→ answers constrained to retrieved text with **inline citations** (`[C1]`, `[C2]`), page /
section hints, and "insufficient context" honesty when the corpus doesn't cover it.

## Why it's different from a typical RAG demo

| | Typical RAG demo | **Net-RAG** |
|---|---|---|
| Domain | Generic PDFs | Networking / internet infrastructure |
| Retrieval | Dense only | **BM25 + dense fused with RRF** (exact RFC numbers & field names) |
| Trust | "Trust the LLM" | Citations + citation-sanity **warnings** + insufficient-context behavior |
| Ingestion | Blocking call | **Async job API** + status polling + progress (single-writer FAISS) |
| Observability | None | `latency_ms`, retrieval/LLM breakdown, token usage, retrieval path |
| Evaluation | "Looks good" | **Gold corpus + metrics**: `source_hit@k`, `P_src@k`, **MRR**, context coverage |
| Architecture | One script | Decoupled UI/API/vector + Docker + documented Redis/managed-DB path |

## What to demo (the "wow" moments)

1. **Citations:** ask "Explain the TCP three-way handshake" → answer cites `[C1]`, expand
   the context card showing the exact source file + page/section.
2. **Hybrid wins:** ask something with an exact term (e.g. an RFC number / "MPLS") and
   toggle **Dense only** vs **Hybrid BM25 + dense** — show the retrieval path chip change.
3. **Async ingest at scale:** queue an ingestion job and show the **live progress bar** +
   `/ingest/status` — "this is how real systems offload heavy embedding work."
4. **Honesty:** ask something outside the corpus → it says *insufficient context* instead
   of fabricating.
5. **Evaluation:** run `scripts/run_eval.py` → show `MRR` / `P_src@k` — "I can prove
   retrieval quality, not just claim it."

---

## LinkedIn launch

### Video vs photo — recommendation
**Post a short screen-recording (45–75s) as the primary asset**, plus 1–2 still images
in the carousel. Reasons:
- Video shows the *grounding + citations + live ingest progress* — the parts that make it
  credible. A static screenshot can't show "it didn't hallucinate."
- LinkedIn favors native video dwell-time; a captioned demo outperforms a single image.
- Add a **carousel/PDF** (architecture diagram + metrics screenshot) for people who skim
  without sound.

**Ideal format:** 45–75s MP4, captioned (most people watch muted), 1080p, show the browser
URL bar so it's clearly a real running app. End on the GitHub URL.

### Suggested storyboard (60s)
1. (0–8s) Title card: "Net-RAG — ask the internet's manuals, get cited answers."
2. (8–25s) Type the TCP handshake question → answer appears with `[C1]` citations → expand
   the source card.
3. (25–40s) Toggle Dense vs Hybrid on an exact-term query; point at the retrieval-path chip.
4. (40–52s) Queue an ingestion job; show the progress bar reaching 100%.
5. (52–60s) Flash the eval output (MRR / P_src@k) + GitHub link.

### Draft post

> 🛰️ I built **Net-RAG** — a Retrieval-Augmented Generation assistant for the documents
> that actually run the internet: RFCs, router/switch manuals, and architecture guides.
>
> Most RAG demos answer questions about generic PDFs. Networking is different: get an RFC
> number or a header field wrong and the answer is worse than useless. So Net-RAG focuses
> on **trust and precision**:
>
> 🔹 **Hybrid retrieval** — BM25 + dense embeddings fused with Reciprocal Rank Fusion, so
>    exact terms (RFC numbers, field names) and paraphrases both land.
> 🔹 **Grounded answers with citations** — every answer is constrained to retrieved chunks
>    with inline `[C1]` references and page/section hints; it says *"insufficient context"*
>    instead of hallucinating.
> 🔹 **Built like a system, not a script** — async ingestion jobs with live progress, a
>    decoupled FastAPI + Streamlit architecture, Docker Compose, and a documented path to
>    Redis workers + a managed vector DB.
> 🔹 **Measured, not vibes** — a gold eval set with retrieval metrics (MRR, precision@k).
>
> Bridging AI with core computer networks taught me as much about distributed-systems
> design as about LLMs. Code + architecture notes on GitHub 👇
>
> github.com/kaustubhchaudhari11/net-rag
>
> #RAG #LLM #ComputerNetworks #AI #MachineLearning #SoftwareEngineering #Python #FastAPI

### Tips
- Put the **GitHub link in the first comment** too (some feeds suppress link-in-post reach).
- Pin the repo on your profile; make sure the README top section + a screenshot render well.
- Reply to early comments quickly (first hour drives reach).
