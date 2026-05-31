# Net-RAG — Deployment (Phase 6)

Three ways to run, from easiest demo to cloud.

---

## A) One command (Docker Compose) — recommended for the demo

Prereq: Docker Desktop.

```bash
docker compose up --build
```

- UI:  http://localhost:8501
- API: http://localhost:8000/health  (Swagger docs at http://localhost:8000/docs)

The UI waits for the API healthcheck before starting. First build is slow (downloads
`sentence-transformers` / `torch`); later builds are cached.

**Optional grounded LLM answers:** create `.env` from `.env.example` and set:

```
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...
```

Compose auto-loads `.env`. Without it, Net-RAG runs in retrieval-only mode (still cited).

**Ingest from the UI sidebar** using a path the **API container** can see:
- `/app/sample_docs` (mounted)
- `/app/docs/eval_corpus` (mounted, for the eval suite)

Stop: `docker compose down`  (add `-v` to also wipe the `netrag-data` index volume).

---

## B) Local Python (no Docker)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1            # or use scripts\setup_local.bat on Windows
pip install -r requirements.txt
copy .env.example .env

# Terminal 1
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --workers 1
# Terminal 2
streamlit run app/ui.py
```

Windows without `Activate.ps1`: see `docs/WINDOWS_SETUP.md` (`scripts\run_api.bat`, `scripts\run_ui.bat`).

---

## C) Cloud (split API + UI)

The two services are already decoupled, so any container host works. General recipe:

1. **Build & push images** (or let the platform build from the Dockerfiles):
   - API: `Dockerfile.api` → exposes `8000`
   - UI:  `Dockerfile.ui`  → exposes `8501`
2. **Deploy the API** as its own service. Set env (`LLM_*`, `HYBRID_*`, `INCLUDE_DEV_METRICS`).
   Attach a **persistent volume** at `/app/app/data` so the FAISS index survives restarts.
   Keep it **single instance** (in-memory ingest jobs) until you externalize the queue.
3. **Deploy the UI** as a second service with `NETRAG_API_BASE=https://<your-api-host>`.
4. **Health checks:** API `GET /health`, UI `GET /_stcore/health`.

Platform notes:
- **Render / Railway / Fly.io:** point each service at the repo + its Dockerfile; add the
  persistent disk to the API service; set env vars in the dashboard.
- **Single VM:** clone repo, install Docker, `docker compose up -d`, put Nginx/Caddy in
  front for TLS on 8501 (UI) and optionally 8000 (API).
- **Streamlit Community Cloud:** can host the **UI only**; it must point `NETRAG_API_BASE`
  at a publicly reachable API (deploy the API on Render/Fly first).

---

## Scale-out checklist (when traffic grows)

| Bottleneck | Move to |
|------------|---------|
| Ingest jobs (in-memory, single process) | Redis + RQ/Celery workers; API becomes stateless and replicable |
| FAISS on local disk | Managed vector DB (Qdrant / Weaviate / pgvector) behind the same retrieval interface |
| BM25 rebuilt in-process | Dedicated lexical service (OpenSearch/Elasticsearch); keep RRF fusion contract |
| Secrets in `.env` | Platform secret manager |

See `docs/architecture.md` for the full distributed design.
