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
| API         | FastAPI: `/ingest`, `/ingest/job`, `/ingest/status/{id}`, `/ingest/jobs`, `/query`, `/health` |
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
| **Phase 2** — Grounded LLM | **Done** | Optional synthesis with `[C#]` citations, fallback, citation sanity warnings |
| **Phase 2.1** — Quality & trust | **Done** | Stricter prompts; `warnings` / `citations_used`; **`latency_ms`** + dev breakdown + **`llm_usage`**; chunk **`page`** + **`section_hint`**; Windows `.bat` run |
| **GitHub** | Done | Empty repo created; `main` pushed with Phase 2 commit |
| **Windows local run** | Done (approved) | `scripts/*.bat` + `docs/WINDOWS_SETUP.md` — no `Activate.ps1` required |
| **Phase 3** — Ingestion at scale | **Done** | `POST /ingest/job`, `GET /ingest/status/{id}`, `GET /ingest/jobs`; threaded queue; sync `/ingest` kept |

---

## Current focus (session memory)

- **Phases 0 → 3 are complete** in code: job-based ingest + polling UI; **distributed evolution** documented in `docs/architecture.md` (Redis/RQ, multi-replica notes).
- **Next:** **Phase 4** — hybrid retrieval (BM25 + dense); then eval suite (Phase 5).
- **Reminder:** Re-ingest once after 2.1 if you need **`section_hint`** on old indexes.
- **Ops:** Run API with **`uvicorn --workers 1`** (or Docker image default) so in-memory jobs stay coherent; scale ingest via external queue later.

---

## Upcoming phases (roadmap)

### Phase 3 — Ingestion at scale *(shipped)*

- Implemented: **`POST /ingest/job`**, **`GET /ingest/status/{job_id}`**, **`GET /ingest/jobs`**, progress in `ingestion_service`, Streamlit async mode.
- Stretch: incremental re-ingest; cancel job; Redis-backed store.

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
- [x] Phase 2.1: structured `/query` fields (`warnings`, `citations_used`, metrics, `llm_usage`)
- [x] Phase 2.1: chunk metadata (`page`, `section_hint`) + prompt/UI surfacing
- [x] Phase 3: `POST /ingest/job` + `GET /ingest/status/{job_id}` + in-memory job registry + threaded worker; Streamlit poll UI; sync `POST /ingest` retained
- [ ] Phase 4: spike hybrid retrieval (keyword + vector)
- [ ] Phase 5: add 5–10 eval questions and a simple script to run them

---

## For Cursor / assistants

When starting a session, read this file plus `README.md` and `docs/architecture.md`. After shipping a slice, update **Progress** and check off **Active task list** items.
