from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.config import settings


def _infer_section_hint(text: str) -> Optional[str]:
    """
    Prefer Markdown ATX headings near the start of the chunk (RFCs / manuals as .md).
    PDF chunks usually have no leading '#', so hint stays unset and we rely on `page`.
    """
    head = text[:1200]
    for raw in head.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            return title[:240] if title else None
    return None


def _normalize_page(metadata: dict) -> None:
    """Ensure page is an int when PyPDF / loaders provide it (in-place)."""
    if "page" not in metadata or metadata["page"] is None:
        return
    try:
        metadata["page"] = int(metadata["page"])
    except (TypeError, ValueError):
        del metadata["page"]


def _enrich_chunk(doc: Document) -> Document:
    meta = dict(doc.metadata)
    _normalize_page(meta)
    hint = _infer_section_hint(doc.page_content)
    if hint:
        meta["section_hint"] = hint
    return Document(page_content=doc.page_content, metadata=meta)


def split_documents(documents: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n## ", "\n### ", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    return [_enrich_chunk(c) for c in chunks]
