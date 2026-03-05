"""
Lightweight lexical retriever fallback for Phase 4.
Used when vector retrieval is unavailable/uninitialized.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


_STOPWORDS = {
    "the", "is", "are", "a", "an", "of", "to", "in", "on", "for", "and",
    "or", "with", "what", "which", "how", "about", "me", "tell", "please",
}


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9%]+", (text or "").lower())
    return [t for t in tokens if len(t) > 2 and t not in _STOPWORDS]


class LocalChunkRetriever:
    """Keyword-overlap retriever on `data/chunks/*/chunks.jsonl`."""

    def __init__(self, chunks_root: Path):
        self.chunks_root = chunks_root
        self._rows: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not self.chunks_root.exists():
            logger.warning("Local retriever chunks path not found: %s", self.chunks_root)
            return

        decoder = json.JSONDecoder()
        loaded = 0
        for chunks_file in self.chunks_root.glob("*/chunks.jsonl"):
            try:
                raw = chunks_file.read_text(encoding="utf-8")
                idx = 0
                length = len(raw)
                while idx < length:
                    while idx < length and raw[idx].isspace():
                        idx += 1
                    if idx >= length:
                        break
                    row, next_idx = decoder.raw_decode(raw, idx)
                    idx = next_idx

                    if not isinstance(row, dict):
                        continue

                    content = row.get("content") or row.get("text") or ""
                    if not content.strip():
                        continue

                    metadata = row.get("metadata") or {}
                    self._rows.append(
                        {
                            "chunk_id": row.get("id") or row.get("chunk_id") or "",
                            "source_id": row.get("source_id") or "",
                            "text": content,
                            "url": metadata.get("url") or row.get("url") or "",
                            "fetched_at": metadata.get("fetched_at") or row.get("fetched_at") or "",
                        }
                    )
                    loaded += 1
            except Exception as exc:
                logger.warning("Failed to load chunks from %s: %s", chunks_file, exc)

        logger.info("Local retriever loaded %s chunks", loaded)

    def _score(self, query_tokens: List[str], text: str) -> float:
        text_lower = text.lower()
        score = 0.0

        for tok in query_tokens:
            if tok in text_lower:
                score += 1.0

        # Domain-aware boosts
        if "aum" in query_tokens and "aum" in text_lower:
            score += 3.0
        if "nav" in query_tokens and "nav" in text_lower:
            score += 2.0
        if "expense" in query_tokens and "expense ratio" in text_lower:
            score += 2.0
        if "navi" in query_tokens and "navi mutual fund" in text_lower:
            score += 1.5

        return score

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        tokens = _tokenize(query)
        if not tokens:
            return []

        scored: List[Dict[str, Any]] = []
        for row in self._rows:
            score = self._score(tokens, row["text"])
            if score <= 0:
                continue
            scored.append(
                {
                    "type": "local_lexical",
                    "content": row["text"],
                    "metadata": {
                        "chunk_id": row["chunk_id"],
                        "source_id": row["source_id"],
                        "url": row["url"],
                        "fetched_at": row["fetched_at"],
                    },
                    "score": score,
                    "source": "local_chunks",
                }
            )

        scored.sort(key=lambda r: r.get("score", 0.0), reverse=True)
        return scored[:top_k]
