"""
Phase 2: Document Processing & Chunking
Main orchestrator that processes parsed documents and creates RAG-ready chunks.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase0.config import config
from phase2.lib.cleaner import DocumentCleaner
from phase2.lib.chunker import ChunkBuilder
from phase2.lib.table_handler import TableHandler


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Orchestrates document processing pipeline"""

    def __init__(self):
        self.parsed_dir = config.data_dir / "parsed"
        self.chunks_dir = config.data_dir / "chunks"
        self.cleaner = DocumentCleaner()
        self.chunk_builder = ChunkBuilder()
        self.table_handler = TableHandler()

        # Ensure output directory exists
        self.chunks_dir.mkdir(parents=True, exist_ok=True)

    def process_all(self) -> Dict[str, Any]:
        """Process all parsed documents"""
        logger.info("Starting document processing pipeline")

        results = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_sources": 0,
            "total_chunks": 0,
            "sources_processed": [],
            "errors": []
        }

        # Find all source directories in parsed folder
        if not self.parsed_dir.exists():
            logger.warning(f"Parsed directory not found: {self.parsed_dir}")
            return results

        source_dirs = [d for d in self.parsed_dir.iterdir() if d.is_dir()]
        logger.info(f"Found {len(source_dirs)} sources to process")

        for source_dir in sorted(source_dirs):
            try:
                source_result = self.process_source(source_dir)
                results["sources_processed"].append(source_result)
                results["total_sources"] += 1
                results["total_chunks"] += source_result["chunk_count"]
            except Exception as e:
                logger.error(f"Error processing {source_dir.name}: {str(e)}")
                results["errors"].append({
                    "source": source_dir.name,
                    "error": str(e)
                })

        logger.info(f"Processing complete. Total chunks: {results['total_chunks']}")
        return results

    def process_source(self, source_dir: Path) -> Dict[str, Any]:
        """Process a single source directory"""
        source_id = source_dir.name
        logger.info(f"Processing source: {source_id}")

        # Load document metadata
        meta_path = source_dir / "meta.json"
        if not meta_path.exists():
            logger.warning(f"No meta.json found for {source_id}")
            meta = {}
        else:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)

        # Load document content
        doc_path = source_dir / "document.json"
        text_path = source_dir / "text.txt"

        document = {}
        if doc_path.exists():
            with open(doc_path, 'r', encoding='utf-8') as f:
                document = json.load(f)
        elif text_path.exists():
            with open(text_path, 'r', encoding='utf-8') as f:
                document = {"raw_text": f.read()}

        if not document:
            logger.warning(f"No document content found for {source_id}")
            return {"source_id": source_id, "chunk_count": 0}

        # Clean document
        cleaned = self.cleaner.clean(document)

        # Build chunks
        chunks = self.chunk_builder.build_chunks(
            source_id=source_id,
            document=cleaned,
            metadata=meta
        )

        # Handle tables if present
        if "tables" in cleaned:
            table_chunks = self.table_handler.extract_table_chunks(
                source_id=source_id,
                tables=cleaned["tables"],
                metadata=meta
            )
            chunks.extend(table_chunks)

        # Save chunks to JSONL
        output_file = self.chunks_dir / f"{source_id}.jsonl"
        self._save_chunks(chunks, output_file)

        logger.info(f"✓ {source_id}: Generated {len(chunks)} chunks")

        return {
            "source_id": source_id,
            "source_url": meta.get("url", ""),
            "chunk_count": len(chunks),
            "output_file": str(output_file)
        }

    @staticmethod
    def _save_chunks(chunks: List[Dict[str, Any]], output_file: Path) -> None:
        """Save chunks to JSONL file (one JSON per line)"""
        with open(output_file, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 2: Document Processing & Chunking")
    parser.add_argument('--source', type=str, help='Process specific source (optional)')
    parser.add_argument('--verify', action='store_true', help='Verify output after processing')

    args = parser.parse_args()

    processor = DocumentProcessor()

    # Process documents
    if args.source:
        source_dir = processor.parsed_dir / args.source
        if source_dir.exists():
            result = processor.process_source(source_dir)
            print(f"\n✓ Processed {args.source}: {result['chunk_count']} chunks")
        else:
            print(f"✗ Source directory not found: {source_dir}")
    else:
        results = processor.process_all()

        # Print summary
        print("\n" + "="*60)
        print("DOCUMENT PROCESSING SUMMARY")
        print("="*60)
        print(f"Timestamp: {results['timestamp']}")
        print(f"Total sources: {results['total_sources']}")
        print(f"Total chunks: {results['total_chunks']}")

        if results['errors']:
            print(f"\nErrors ({len(results['errors'])}):")
            for error in results['errors']:
                print(f"  - {error['source']}: {error['error']}")

        print("\nProcessed sources:")
        for source in results['sources_processed']:
            print(f"  - {source['source_id']}: {source['chunk_count']} chunks")

        print("="*60)

        # Save manifest
        manifest_path = config.data_dir / "manifests" / f"processing_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Manifest saved: {manifest_path}")

        # Verification
        if args.verify:
            print("\n✓ Verifying output...")
            chunk_count = 0
            for chunk_file in processor.chunks_dir.glob("*.jsonl"):
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk_count += sum(1 for _ in f)
            print(f"✓ Verified: {chunk_count} total chunks in JSONL files")


if __name__ == "__main__":
    main()
