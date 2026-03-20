from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.services.ingestion_service import ingest_documents
from app.services.query_service import build_answer

app = FastAPI(title="Net-RAG API", version="0.1.0")


class IngestRequest(BaseModel):
    input_dir: str = Field(..., description="Directory path with PDF/TXT/MD files")


class QueryRequest(BaseModel):
    query: str
    top_k: int | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest")
def ingest(payload: IngestRequest) -> dict:
    try:
        result = ingest_documents(payload.input_dir)
        return {"ok": True, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/query")
def query(payload: QueryRequest) -> dict:
    try:
        result = build_answer(payload.query, payload.top_k)
        return {"ok": True, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
