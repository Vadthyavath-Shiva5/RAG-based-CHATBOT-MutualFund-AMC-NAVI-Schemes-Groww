from __future__ import annotations

from typing import Any, Dict, List, Optional

from pypdf import PdfReader

from phase1.lib.util import iso_now, sha256_bytes


def parse_pdf_document(
    *,
    pdf_bytes: bytes,
    url: str,
    source_id: str,
    label: str,
    parent_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Basic PDF extraction: per-page text plus concatenated full text.
    We keep it generic; scheme-specific numeric extraction can happen in later phases.
    """
    reader = PdfReader.from_bytes(pdf_bytes)
    pages: List[Dict[str, Any]] = []
    texts: List[str] = []

    for i, page in enumerate(reader.pages):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        pages.append({"page_index": i, "text": txt})
        texts.append(txt)

    full_text = "\n\n".join(t.strip() for t in texts if t.strip())

    doc: Dict[str, Any] = {
        "schema": "phase1.document.v1",
        "content_type": "pdf",
        "source_id": source_id,
        "label": label,
        "url": url,
        "parent_url": parent_url,
        "document_id": f"{source_id}:pdf:{sha256_bytes(pdf_bytes)[:16]}",
        "extracted_at": iso_now(),
        "title": "",
        "text": full_text,
        "pages": pages,
        "tables": [],
        "faqs": [],
        "links": {},
    }
    return doc

