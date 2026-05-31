import re
from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.config import settings

_MD_HEADING_RE = re.compile(r"(?m)^(#{1,6}\s+.+)$")


def _looks_like_markdown(doc: Document) -> bool:
    meta = doc.metadata or {}
    source = str(meta.get("source") or meta.get("source_file") or "").lower()
    return source.endswith(".md")


def _split_markdown_by_headings(doc: Document) -> List[Document]:
    """
    Keep short Markdown sections from being merged into unrelated chunks.

    The recursive splitter is still used afterward for long sections, but this
    first pass keeps headings like "MPLS" and "longest-prefix match" separate.
    """
    text = doc.page_content or ""
    matches = list(_MD_HEADING_RE.finditer(text))
    if len(matches) <= 1:
        return [doc]

    out: List[Document] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        if section_text:
            out.append(Document(page_content=section_text, metadata=dict(doc.metadata)))
    return out or [doc]


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
    structured_docs: List[Document] = []
    for doc in documents:
        if _looks_like_markdown(doc):
            structured_docs.extend(_split_markdown_by_headings(doc))
        else:
            structured_docs.append(doc)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n## ", "\n### ", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(structured_docs)
    return [_enrich_chunk(c) for c in chunks]
