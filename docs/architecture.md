# Net-RAG Distributed System Architecture

## Logical Services

1. **UI Service (Streamlit)**
   - Handles user interaction.
   - Sends ingestion and query requests to API service.
   - **Phase 3:** Polls `GET /ingest/status/{job_id}` after `POST /ingest/job` for non-blocking ingest UX.

2. **API Service (FastAPI)**
   - Exposes `/ingest` (sync), **`/ingest/job`** (async queue), **`/ingest/status/{id}`**, **`/ingest/jobs`**, `/query`, `/health`.
   - Coordinates ingestion and retrieval workflows.
   - **Single-writer rule:** FAISS index save replaces the on-disk store; ingestion jobs are **serialized** per API process (one background worker thread draining a queue).

3. **Embedding + Vector Service (FAISS Local)**
   - Generates embeddings via local sentence-transformer model.
   - Stores vector index on disk for fast similarity search.

4. **Document Store (Filesystem / object store in future)**
   - Holds RFC/manual source files.

## Phase 3 — Ingestion jobs (implemented)

| Concern | Current (MVP) | Scale-out direction |
|--------|----------------|---------------------|
| Job state | In-memory dict + `threading` queue | **Redis** + **RQ** / **Celery** / **Temporal** |
| API replicas | One uvicorn worker recommended | Sticky sessions or shared job store; **dedicated ingest workers** |
| Progress | Callbacks from `ingestion_service` | Same contract; worker publishes to Redis |
| Durability | Lost on process restart | Persist job rows + object store for corpus |

**Stable API contract:** `POST /ingest/job` → `{ job_id, status_url }`; `GET /ingest/status/{job_id}` → `state`, `progress_percent`, `stage`, `message`, `result` / `error`. UI and clients do not need to change when you swap the backend.

## Why this is "Distributed-Ready"

- Services are separated by clear API boundaries (UI and API already decoupled).
- API can be containerized and deployed independently from UI.
- FAISS layer can later be swapped with managed vector DB (Qdrant/Pinecone/Weaviate) with minimal API changes.
- **Ingestion is already modeled as asynchronous work** (job id + status), matching how real systems offload heavy I/O and embedding to workers.

## Evolution Path for Resume Impact

- **V2:** LLM-grounded answers + citations *(done)*.
- **V3:** Background ingestion queue and status tracking *(done — in-memory; externalize next)*.
- **V4:** Add hybrid retrieval (BM25 + dense vectors).
- **V5:** Add multi-tenant project spaces and auth.
- **Differentiators:** job-based ingest, explicit single-writer semantics, documented path to Redis/workers, health `?detailed=1` for ops.
