"""
Diff helpers for Phase 5 refresh pipeline.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _json_hash(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return _sha256_text(canonical)


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Snapshot:
    source_id: str
    fetch_hash: Optional[str]
    doc_hash: Optional[str]


@dataclass(frozen=True)
class DiffResult:
    source_id: str
    changed: bool
    reason: str
    before: Snapshot
    after: Snapshot


class SourceDiffer:
    """Compares persisted source outputs before vs after refresh."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def snapshot(self, source_id: str) -> Snapshot:
        raw_meta_path = self.data_dir / "raw" / source_id / "fetch.json"
        parsed_doc_path = self.data_dir / "parsed" / source_id / "document.json"

        raw_meta = _read_json(raw_meta_path)
        parsed_doc = _read_json(parsed_doc_path)

        fetch_hash = _json_hash(raw_meta) if raw_meta else None
        doc_hash = _json_hash(parsed_doc) if parsed_doc else None
        return Snapshot(source_id=source_id, fetch_hash=fetch_hash, doc_hash=doc_hash)

    def diff(self, before: Snapshot, after: Snapshot) -> DiffResult:
        if before.fetch_hash is None and after.fetch_hash is not None:
            return DiffResult(
                source_id=before.source_id,
                changed=True,
                reason="new_source_materialized",
                before=before,
                after=after,
            )

        if before.fetch_hash != after.fetch_hash:
            return DiffResult(
                source_id=before.source_id,
                changed=True,
                reason="raw_snapshot_changed",
                before=before,
                after=after,
            )

        if before.doc_hash != after.doc_hash:
            return DiffResult(
                source_id=before.source_id,
                changed=True,
                reason="normalized_document_changed",
                before=before,
                after=after,
            )

        return DiffResult(
            source_id=before.source_id,
            changed=False,
            reason="no_change",
            before=before,
            after=after,
        )

