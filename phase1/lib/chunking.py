from __future__ import annotations

from typing import Any, Dict, Iterable, List

from phase1.lib.util import sha256_text


def _text_chunks(text: str, *, max_chars: int = 1200, overlap: int = 200) -> List[str]:
    text = text or ""
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + max_chars)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert a normalized document into RAG-ready chunks.

    Each chunk has:
    - id
    - source_id, document_id
    - content (text)
    - chunk_index, chunk_type
    - small metadata fragment (title, url, etc.)
    """
    source_id = doc.get("source_id", "unknown")
    document_id = doc.get("document_id", sha256_text(source_id))
    title = doc.get("title") or ""
    url = doc.get("url") or ""
    content_type = doc.get("content_type") or "unknown"

    chunks: List[Dict[str, Any]] = []

    # 1) Main text chunks
    main_text = doc.get("text") or ""
    text_parts = _text_chunks(main_text)
    for idx, part in enumerate(text_parts):
        chunk_id = f"{document_id}:text:{idx}"
        chunks.append(
            {
                "id": chunk_id,
                "chunk_index": idx,
                "chunk_type": "text",
                "source_id": source_id,
                "document_id": document_id,
                "content": part,
                "metadata": {
                    "title": title,
                    "url": url,
                    "content_type": content_type,
                },
            }
        )

    # 2) Table chunks (serialize simple text view)
    for t_idx, table in enumerate(doc.get("tables") or []):
        rows = table.get("rows") or []
        lines = [" | ".join(r) for r in rows if any(cell for cell in r)]
        if not lines:
            continue
        text_table = "\n".join(lines)
        chunk_id = f"{document_id}:table:{t_idx}"
        chunks.append(
            {
                "id": chunk_id,
                "chunk_index": len(chunks),
                "chunk_type": "table",
                "source_id": source_id,
                "document_id": document_id,
                "content": text_table,
                "metadata": {
                    "title": title,
                    "url": url,
                    "content_type": content_type,
                    "table_index": t_idx,
                },
            }
        )

    # 3) FAQ chunks
    for f_idx, faq in enumerate(doc.get("faqs") or []):
        q = faq.get("question") or ""
        a = faq.get("answer") or ""
        text_faq = f"Q: {q}\nA: {a}".strip()
        if not text_faq:
            continue
        chunk_id = f"{document_id}:faq:{f_idx}"
        chunks.append(
            {
                "id": chunk_id,
                "chunk_index": len(chunks),
                "chunk_type": "faq",
                "source_id": source_id,
                "document_id": document_id,
                "content": text_faq,
                "metadata": {
                    "title": title,
                    "url": url,
                    "content_type": content_type,
                    "faq_index": f_idx,
                },
            }
        )

    return chunks

