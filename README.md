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
- Provides interactive Q/A experience with Streamlit.
- Includes Docker Compose for multi-service local deployment.

## 2) Tech stack

- **Backend API:** FastAPI
- **RAG pipeline:** LangChain + FAISS
- **Embeddings:** Sentence Transformers (`all-MiniLM-L6-v2`)
- **UI:** Streamlit
- **Docs parsing:** PyPDF + text/markdown loader

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
    services/
      ingestion_service.py
      query_service.py
  scripts/
    ingest.py
    run_local.ps1
    run_ui.ps1
    setup_local.bat
    run_api.bat
    run_ui.bat
  docs/
    architecture.md
    WINDOWS_SETUP.md
    PROJECT_MEMORY.md
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

Use the sidebar in Streamlit to ingest documents, then ask protocol/architecture questions.

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
- Reduced operational cost by running fully local inference while maintaining fast semantic search over technical corpora.

## 8) Next upgrades to make it exceptional

- ~~Add LLM answer synthesis with grounded citations.~~ **Phase 2 / 2.1 done** (see below).
- Add async ingestion workers and progress/status API.
- Add evaluation suite (retrieval precision, latency, groundedness checks).
- Deploy API + UI as separate cloud services.

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
