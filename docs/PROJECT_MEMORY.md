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

| Layer        | Choice                                      |
|-------------|----------------------------------------------|
| API         | FastAPI (`/ingest`, `/query`, `/health`)     |
| RAG         | LangChain + FAISS (local index on disk)      |
| Embeddings  | Sentence Transformers (e.g. `all-MiniLM-L6-v2`) |
| UI          | Streamlit                                    |
| LLM (opt.)  | OpenAI-compatible API via `.env`           |
| Deploy path | Docker Compose (API + UI separated)          |

---

## Progress (as of last update)

| Phase | Status | Notes |
|-------|--------|--------|
| **Phase 0** — Scaffold | Done | Modular pipeline, services, sample docs, Docker, README |
| **Phase 1** — Retrieval MVP | Done | Ingest, chunk, FAISS, query returns contexts + sources |
| **Phase 2** — Grounded LLM | **In progress** | Optional synthesis with `[C1]`-style citations; fallback if no key / API error |
| **Phase 2.1** — Quality & trust | **In progress** | Stricter prompts; `warnings` + `citations_used` on `/query`; local run scripts |
| **GitHub** | Done | Empty repo created; `main` pushed with Phase 2 commit |
| **Windows local run** | Done (approved) | `scripts/*.bat` + `docs/WINDOWS_SETUP.md` — no `Activate.ps1` required |

---

## Upcoming phases (roadmap)

### Phase 2.1 — Quality & trust (near-term)

- Stricter prompting: every factual claim cites `[C#]`; explicit “insufficient context” behavior.
- Richer API/UI: show `mode`, optional `warnings`, token/latency in dev.
- Better chunk metadata (page number, section hints where PDF allows).

### Phase 3 — Ingestion at scale

- Async or background ingestion; **job id + status** endpoint (or polling).
- Progress UI in Streamlit; idempotent re-ingest / incremental updates (stretch).

### Phase 4 — Retrieval quality

- **Hybrid search** (BM25 + dense) for exact terms (RFC numbers, field names).
- Re-ranking optional; configurable `top_k` and filters (by source file).

### Phase 5 — Evaluation & demos

- Small **eval set** (questions + expected sources); latency and groundedness checks.
- Curated `sample_docs` + golden questions for portfolio demo.

### Phase 6 — Production-style deploy

- Separate cloud deploy for API vs UI; secrets via env/secret manager; optional managed vector DB later (Qdrant, etc.) — aligned with `docs/architecture.md`.

---

## Active task list (edit when you pick work)

- [x] Phase 2.1: tighten LLM prompt + citation rules
- [x] Phase 2.1: optional structured fields on `/query` response (`warnings`, `citations_used`)
- [ ] Phase 3: design `POST /ingest/job` + `GET /ingest/status/{id}` (or equivalent)
- [ ] Phase 4: spike hybrid retrieval (keyword + vector)
- [ ] Phase 5: add 5–10 eval questions and a simple script to run them

---

## For Cursor / assistants

When starting a session, read this file plus `README.md` and `docs/architecture.md`. After shipping a slice, update **Progress** and check off **Active task list** items.
