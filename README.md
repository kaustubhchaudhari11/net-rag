# Net-RAG: Network Protocol & Architecture Assistant

Net-RAG is a Level-1 Retrieval-Augmented Generation project focused on networking and distributed systems documentation (RFCs, protocol manuals, architecture notes).

It ingests technical docs, chunks them by structure, embeds them locally, and retrieves the most relevant context for user questions through a Streamlit app.

**Living roadmap + tasks:** see [`docs/PROJECT_MEMORY.md`](docs/PROJECT_MEMORY.md) (objective, progress, upcoming phases).

## 1) Why this project stands out

- Domain is highly technical (network protocols + architecture).
- Shows practical AI + systems engineering.
- Built with service boundaries (UI + API + vector layer) so it is distributed-system ready.
- Runs locally with low cost and can scale to cloud later.

## Features

- Ingests PDF, Markdown, and text files from RFCs and network manuals.
- Chunks technical documents with structure-aware splitting.
- Builds local semantic vector index with FAISS.
- Exposes retrieval pipeline through FastAPI endpoints.
- **Phase 3:** Async ingestion jobs (`POST /ingest/job` + status polling) with a serialized worker queue (swap backend to Redis/RQ later — see `docs/architecture.md`).
- **Phase 4:** **BM25 + dense** retrieval fused with **RRF**; cached lexical index **invalidated on ingest**; optional `retrieval_mode` on `/query` and in Streamlit.
- **Phase 5:** `docs/eval_questions.json` + `scripts/run_eval.py` for smoke checks against a running API.
- Provides interactive Q/A experience with Streamlit.
- Includes Docker Compose for multi-service local deployment.

## 2) Tech stack

- **Backend API:** FastAPI
- **RAG pipeline:** LangChain + FAISS
- **Embeddings:** Sentence Transformers (`all-MiniLM-L6-v2`)
- **UI:** Streamlit
- **Docs parsing:** PyPDF + text/markdown loader
- **Lexical:** `rank-bm25` (BM25 over all chunks in the FAISS docstore)

## 3) Project structure

```text
net-rag/
  app/
    api.py
    ui.py
    config.py
    rag/
      chunker.py
      embedder.py
      vector_store.py
      hybrid_retrieval.py
    services/
      ingestion_service.py
      ingest_job_manager.py
      query_service.py
  scripts/
    ingest.py
    run_eval.py
    run_local.ps1
    run_ui.ps1
    setup_local.bat
    run_api.bat
    run_ui.bat
  docs/
    architecture.md
    WINDOWS_SETUP.md
    PROJECT_MEMORY.md
    eval_questions.json
  sample_docs/
```

## 4) Setup

### Windows (recommended if `Activate.ps1` is blocked)

Use **Command Prompt** (`cmd`). Full steps: [`docs/WINDOWS_SETUP.md`](docs/WINDOWS_SETUP.md).

1. One-time: `scripts\setup_local.bat` (creates `.venv`, installs deps, copies `.env` if missing).
2. Put RFC/manual files inside `sample_docs/` (or another folder you ingest from).

### All platforms — PowerShell / manual

1. Create and activate virtual environment:

```powershell
cd C:\Users\kaust\Documents\net-rag
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks scripts: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create `.env` from template:

```powershell
copy .env.example .env
```

4. Put RFC/manual files inside `sample_docs/`.

## 5) Run locally (two terminals)

### Windows — Command Prompt (no activation)

**Window 1 — API:** `scripts\run_api.bat`  
**Window 2 — UI:** `scripts\run_ui.bat`  

(From repo root, or `cd /d C:\Users\kaust\Documents\net-rag` first.)

### PowerShell — with venv activated

**Terminal 1 — API**

```powershell
.\scripts\run_local.ps1
```

**Terminal 2 — UI**

```powershell
.\scripts\run_ui.ps1
```

### Any shell — without activating

```bat
.venv\Scripts\python.exe -m uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
```

```bat
.venv\Scripts\python.exe -m streamlit run app/ui.py
```

- API health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Streamlit: [http://localhost:8501](http://localhost:8501)

Use the sidebar in Streamlit to ingest documents (**background job** recommended), then ask protocol/architecture questions.

### API quick reference (OpenAPI: `/docs`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness; `?detailed=true` includes ingest worker / queue depth |
| POST | `/ingest` | Sync ingest (blocks until done) |
| POST | `/ingest/job` | Queue background ingest → `{ job_id, status_url }` |
| GET | `/ingest/status/{job_id}` | `queued` / `running` / `succeeded` / `failed` + progress |
| GET | `/ingest/jobs?limit=20` | Recent jobs (ephemeral, in-memory) |
| POST | `/query` | Body: `query`, optional `top_k`, optional `retrieval_mode` (`dense` \| `hybrid`) |

**Scaling note:** Use **one uvicorn worker** per API instance for the default in-memory job store, or externalize jobs to Redis/workers (see `docs/architecture.md`).

**Docker:** Paths must exist **on the API container** (e.g. `/app/sample_docs` when using compose volumes).

### Run with Docker (distributed-style local setup)

```powershell
docker compose up --build
```

- UI: `http://localhost:8501`
- API: `http://localhost:8000/health`

## 6) Example questions

- "Explain the TCP 3-way handshake and state transitions."
- "How does BGP update propagation differ from OSPF flooding?"
- "Summarize IPv6 header changes compared to IPv4."
- "What are failure risks in this architecture and recommended mitigations?"

## 7) Resume bullets (customized)

- Built a domain-specific RAG platform to analyze networking RFCs and infrastructure architecture manuals.
- Designed a distributed-ready architecture with decoupled FastAPI retrieval service and Streamlit client.
- Implemented local vector retrieval using LangChain + FAISS with CPU-optimized sentence-transformer embeddings.
- Shipped **async ingestion jobs** with a **stable job/status API** and documented path to **Redis/RQ** for scale-out.
- Added **hybrid BM25 + dense (RRF)** retrieval with **ingest-time cache invalidation** and a **small eval harness** for regression smoke tests.
- Reduced operational cost by running fully local inference while maintaining fast semantic search over technical corpora.

## 8) Next upgrades to make it exceptional

- ~~Add LLM answer synthesis with grounded citations.~~ **Phase 2 / 2.1 done** (see below).
- ~~Add async ingestion workers and progress/status API.~~ **Phase 3 done** — job API + queue; evolve to Redis/RQ for multi-replica.
- ~~Baseline eval questions + `run_eval.py`.~~ **Phase 5 baseline done** — extend with precision / groundedness metrics.
- Deploy API + UI as separate cloud services (**Phase 6**).

## License

MIT (you can replace this with your preferred license).

## Phase 2: Grounded LLM Answers

The query pipeline now supports optional grounded LLM synthesis on top of retrieved chunks.

1. Configure `.env`:

```powershell
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT_SEC=60
```

2. Behavior:

- If `LLM_MODEL` + `LLM_API_KEY` are set, `/query` returns an LLM-generated answer constrained to retrieved contexts with inline citations (`[C1]`, `[C2]`, ...).
- If not set (or LLM call fails), Net-RAG falls back to retrieval-only mode and still returns cited contexts.

### Phase 2.1 (complete): trust, metrics, chunk metadata

- **Chunk metadata:** PDF **page** (from loaders) is normalized and stored; **section_hint** is inferred from Markdown headings (`# …`) at the start of each chunk. **Re-run ingestion** after upgrading so existing FAISS indexes pick up `section_hint`.
- **`/query` response:** always includes **`latency_ms`** (end-to-end). When `INCLUDE_DEV_METRICS=true` (default in `.env.example`), also **`retrieval_ms`**, **`llm_ms`** (if an LLM call was attempted), and **`llm_usage`** (`prompt_tokens`, `completion_tokens`, `total_tokens`) when the provider returns them.
- **UI:** shows timing captions, token line when present, and context expanders include page / section when available.
Set `INCLUDE_DEV_METRICS=false` to hide breakdown and token counts (total `latency_ms` is still returned).

## Phase 4: Hybrid retrieval (BM25 + dense + RRF)

1. Install deps (`rank-bm25` is in `requirements.txt`):

```powershell
pip install -r requirements.txt
```

2. Configure `.env` (see `.env.example`):

- `HYBRID_ENABLED` — default on; set `false` for dense-only unless the client sends `retrieval_mode: hybrid`.
- `HYBRID_CANDIDATE_MULTIPLIER` — pool size per channel before fusion (e.g. `4` × `top_k`).
- `HYBRID_DENSE_WEIGHT` / `HYBRID_KEYWORD_WEIGHT` — RRF weights (should sum to `1.0` for interpretability).
- `HYBRID_RRF_K` — RRF rank constant (commonly `60`).

3. **Per-request override:** `POST /query` JSON may include `"retrieval_mode": "dense"` or `"hybrid"`.

4. **Cache:** BM25 is rebuilt when the vector index changes (invalidated automatically after ingest).

## Phase 5: quick eval script

Run a lightweight evaluation set against `/query`:

```powershell
.venv\Scripts\python.exe scripts/run_eval.py
.venv\Scripts\python.exe scripts/run_eval.py --retrieval-mode hybrid
```

The script prints per-question latency, context count, answer mode, retrieval path, and optional **expected substring** misses from `docs/eval_questions.json`.
