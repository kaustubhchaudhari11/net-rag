# Hugging Face Spaces (Docker SDK) image — runs API + UI in one container.
# HF Spaces expects the app on port 7860. For local multi-service runs use
# docker-compose.yml (Dockerfile.api + Dockerfile.ui) instead.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/tmp/hfcache \
    VECTOR_DB_DIR=/tmp/netrag/vector_db \
    NETRAG_API_BASE=http://127.0.0.1:8000 \
    NETRAG_PUBLIC_MODE=1 \
    INGEST_DIR=./docs/eval_corpus

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# /tmp is always writable regardless of the runtime user HF assigns.
RUN mkdir -p /tmp/netrag/vector_db /tmp/hfcache \
    && chmod -R 777 /tmp/netrag /tmp/hfcache \
    && chmod +x scripts/hf_spaces_start.sh

EXPOSE 7860

CMD ["bash", "scripts/hf_spaces_start.sh"]
