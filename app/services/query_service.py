from typing import Any, Dict, List

from app.config import settings
from app.rag.vector_store import load_index


def search_context(query: str, top_k: int | None = None) -> List[Dict[str, Any]]:
    k = top_k or settings.top_k
    store = load_index()
    docs = store.similarity_search(query=query, k=k)

    items: List[Dict[str, Any]] = []
    for doc in docs:
        items.append(
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
        )
    return items


def build_answer(query: str, top_k: int | None = None) -> Dict[str, Any]:
    contexts = search_context(query, top_k)
    if not contexts:
        return {"answer": "No context found. Please ingest documents first.", "contexts": []}

    sources = []
    for c in contexts:
        source_file = c["metadata"].get("source_file", "unknown")
        if source_file not in sources:
            sources.append(source_file)

    answer = (
        "Retrieved relevant protocol documentation snippets for your query. "
        "Use the contexts below for grounded analysis."
    )
    return {
        "answer": answer,
        "sources": sources,
        "contexts": contexts,
    }
