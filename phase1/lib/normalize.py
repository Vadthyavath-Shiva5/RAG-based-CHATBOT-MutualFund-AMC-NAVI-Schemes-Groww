from __future__ import annotations

from typing import Any, Dict


def normalize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Light-weight normalizer for Phase-1.

    - Ensures required top-level keys exist.
    - Normalizes empty fields to sane defaults.
    - Leaves detailed numeric interpretation (NAV, expense ratio, etc.) to later phases.
    """
    out = dict(doc)

    out.setdefault("schema", "phase1.document.v1")
    out.setdefault("content_type", "unknown")
    out.setdefault("title", "")
    out.setdefault("text", "")
    out.setdefault("tables", [])
    out.setdefault("faqs", [])
    out.setdefault("links", {})

    # Basic metadata container where later phases can add
    # normalized fields like nav, expense_ratio, risk_o_meter, etc.
    out.setdefault("meta", {})

    # Optionally store simple text length metadata
    text = out.get("text") or ""
    out["meta"]["text_chars"] = len(text)
    out["meta"]["has_tables"] = bool(out.get("tables"))
    out["meta"]["has_faqs"] = bool(out.get("faqs"))

    return out

