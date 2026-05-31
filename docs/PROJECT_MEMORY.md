# Net-RAG — project memory (living doc)

Use this file so assistants and future you can resume with the same **objective**, **progress**, and **next tasks**. Update it when a phase ships or priorities change.

---

## Objective (what we are building)

**Net-RAG** is a **network protocol & architecture assistant**: a RAG system that ingests **highly technical** sources (RFCs, router/switch manuals, architecture guidelines) — not generic docs — so users can ask things like:

- “What is the handshake / state machine for this protocol?”
- “Summarize routing table updates in this scenario.”

**Why it stands out:** bridges **software engineering** and **computer networks / internet infrastructure**, with AI grounded in real protocol and ops documentation.

**Core flow:** upload or point at PDF/MD/TXT → **chunk** (structure-aware) → **embed locally** → **FAISS** retrieval → **Streamlit** (and FastAPI) for Q&A. Optional **LLM** layer synthesizes answers **only** from retrieved chunks with **citations**.

---

## Tech snapshot

| Layer        | Choice |
|-------------|--------|
| API         | FastAPI: ingest (sync + job), `/query` with optional `retrieval_mode`, `/health` |
| RAG         | LangChain + FAISS; **Phase 4:** BM25 over docstore + **RRF** fusion with dense |
| Embeddings  | Sentence Transformers (e.g. `all-MiniLM-L6-v2`) |
| Lexical     | `rank-bm25` + LangChain `BM25Retriever`; cache cleared on ingest |
| UI          | Streamlit (async ingest + retrieval override) |
| LLM (opt.)  | OpenAI-compatible API via `.env` |
| Eval        | `docs/eval_questions.json` + `scripts/run_eval.py` |
| Deploy path | Docker Compose (API + UI); API **workers=1** for in-memory jobs |

---

## Progress (as of last update)

| Phase | Status | Notes |
|-------|--------|--------|
| **Phase 0** — Scaffold | Done | Modular pipeline, services, sample docs, Docker, README |
| **Phase 1** — Retrieval MVP | Done | Ingest, chunk, FAISS, `/query` contexts |
| **Phase 2** — Grounded LLM | Done | Optional synthesis + `[C#]` citations + fallbacks |
| **Phase 2.1** — Quality & trust | Done | Metrics, `warnings`, chunk `page` / `section_hint`, Windows `.bat` |
| **Phase 3** — Ingestion at scale | Done | `/ingest/job`, `/ingest/status`, queue + worker; sync `/ingest` kept |
| **Phase 4** — Retrieval quality | Done | **BM25 + dense + RRF** (`app/rag/hybrid_retrieval.py`); `HYBRID_*` env; per-query override |
| **Phase 5** — Evaluation | Done | Gold `docs/eval_corpus/*.md`, labeled `eval_questions.json`, metrics in `scripts/eval_lib.py` |
| **Phase 6** — Production deploy | **Done** | Healthchecked Docker Compose, env substitution, named volume, `.dockerignore`, polished demo UI, `docs/DEPLOYMENT.md` + `docs/PITCH.md` |

**All planned phases (0–6) are complete.** Project is demo-ready and deployable.

---

## Current focus (session memory)

- **Done today:** Phase 6 — production Compose (healthchecks, `depends_on: service_healthy`, named `netrag-data` volume, env-var substitution), demo-grade Streamlit UI (health badge, example chips, metric chips, retrieval-path display), `docs/DEPLOYMENT.md`, `docs/PITCH.md` (LinkedIn kit), API `v1.0.0`.
- **Launch:** record 45–75s captioned demo video (see `docs/PITCH.md`); push to GitHub; post on LinkedIn.
- **Ops:** `uvicorn --workers 1` (Docker default) for in-memory ingest jobs; re-ingest after corpus changes (BM25 cache auto-invalidates).

---

## Upcoming phases (roadmap)

### Stretch (post-1.0)

- Ingest: Redis-backed jobs, cancel, incremental index updates.
- Retrieval: filter by `source_file`, cross-encoder re-rank, separate lexical service at scale.

---

## Active task list (edit when you pick work)

- [x] Phase 3 — job API + worker + UI poll
- [x] Phase 4 — BM25 + dense RRF + ingest invalidation + `retrieval_mode` on `/query`
- [x] Phase 5 — eval corpus + metrics (`eval_lib.py`, `run_eval.py`)
- [x] Phase 6 — Docker Compose deploy (healthchecks, volume, env), demo UI, deployment + pitch docs
- [ ] Launch: record demo video + LinkedIn post (`docs/PITCH.md`)
- [ ] Stretch: Redis-backed jobs, query filter by source, managed vector DB, cross-encoder re-rank

---

## For Cursor / assistants

When starting a session, read this file plus `README.md` and `docs/architecture.md`. After shipping a slice, update **Progress** and check off **Active task list** items.
