# Net-RAG Distributed System Architecture

## Logical Services

1. **UI Service (Streamlit)**
   - Handles user interaction.
   - Sends ingestion and query requests to API service.

2. **API Service (FastAPI)**
   - Exposes `/ingest` and `/query`.
   - Coordinates ingestion and retrieval workflows.

3. **Embedding + Vector Service (FAISS Local)**
   - Generates embeddings via local sentence-transformer model.
   - Stores vector index on disk for fast similarity search.

4. **Document Store (Filesystem / object store in future)**
   - Holds RFC/manual source files.

## Why this is "Distributed-Ready"

- Services are separated by clear API boundaries (UI and API already decoupled).
- API can be containerized and deployed independently from UI.
- FAISS layer can later be swapped with managed vector DB (Qdrant/Pinecone/Weaviate) with minimal API changes.
- Ingestion can be moved to async workers (Celery/RQ) once dataset grows.

## Evolution Path for Resume Impact

- **V2:** Replace static response with LLM-generated grounded answer + citation formatting.
- **V3:** Add background ingestion queue and status tracking.
- **V4:** Add hybrid retrieval (BM25 + dense vectors).
- **V5:** Add multi-tenant project spaces and auth.
