"""
Incremental update helpers for Phase 5.
Current strategy: safe full rebuild of Phase 3 indexes after changed sources.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

from phase0.config import Config
from phase3.index import IndexBuilder

logger = logging.getLogger(__name__)


class IncrementalUpdater:
    """
    Coordinates index updates after source refresh.
    """

    def __init__(self, config: Config):
        self.config = config
        self.data_dir = Path(getattr(config, "data_dir", Path("data")))
        self.phase3_dir = Path("phase3")

    def _remove_if_exists(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def rebuild_indexes(self, changed_source_ids: List[str]) -> Dict[str, int]:
        """
        Rebuild Phase 3 stores.
        Returns summary counters for manifesting.
        """
        if not changed_source_ids:
            return {
                "changed_sources": 0,
                "chunks_regenerated": 0,
                "embeddings_updated": 0,
            }

        logger.info("Rebuilding Phase 3 stores for changed sources: %s", ",".join(changed_source_ids))

        # Remove current index/doc-store artifacts from active data directory.
        self._remove_if_exists(self.data_dir / "vector_store.faiss")
        self._remove_if_exists(self.data_dir / "vector_metadata.json")
        self._remove_if_exists(self.data_dir / "doc_store.db")

        # Backward compatibility cleanup for older builds that wrote into phase3/.
        self._remove_if_exists(self.phase3_dir / "vector_store.faiss")
        self._remove_if_exists(self.phase3_dir / "vector_metadata.json")
        self._remove_if_exists(self.phase3_dir / "doc_store.db")

        builder = IndexBuilder(self.config)
        builder.populate_doc_store()
        builder.embed_chunks()
        stats = builder.get_stats()

        return {
            "changed_sources": len(changed_source_ids),
            "chunks_regenerated": int(stats["doc_store"].get("chunks_count", 0)),
            "embeddings_updated": int(stats["vector_store"].get("total_vectors", 0)),
        }
