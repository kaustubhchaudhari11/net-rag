#!/usr/bin/env bash
# Entrypoint for Hugging Face Spaces: start the API, ingest a demo corpus,
# then start the Streamlit UI on port 7860 (the port HF Spaces exposes).
set -uo pipefail

VECTOR_DB_DIR="${VECTOR_DB_DIR:-/tmp/netrag/vector_db}"
INGEST_DIR="${INGEST_DIR:-./docs/eval_corpus}"
mkdir -p "$VECTOR_DB_DIR"

echo "[hf-start] launching API (uvicorn, single worker)..."
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000 --workers 1 &

echo "[hf-start] waiting for API health..."
for _ in $(seq 1 90); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "[hf-start] API is up"
    break
  fi
  sleep 2
done

echo "[hf-start] ingesting demo corpus from ${INGEST_DIR} ..."
curl -sf -X POST http://127.0.0.1:8000/ingest \
  -H 'Content-Type: application/json' \
  -d "{\"input_dir\": \"${INGEST_DIR}\"}" \
  && echo "[hf-start] ingestion complete" \
  || echo "[hf-start] ingestion skipped/failed (UI will still start)"

echo "[hf-start] launching Streamlit UI on :7860 ..."
exec streamlit run app/ui.py \
  --server.port=7860 --server.address=0.0.0.0 \
  --server.headless=true --browser.gatherUsageStats=false
