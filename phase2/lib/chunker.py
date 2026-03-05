"""
Chunk Builder: Create hybrid chunks (narrative, FAQ, typed-fact, table rows)
Handles conversion of documents into RAG-ready chunks with rich metadata
"""

import re
from typing import Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ChunkBuilder:
    """Builds hybrid chunks from cleaned documents"""

    def __init__(self):
        self.chunk_id_counter = {}

    def build_chunks(
        self,
        source_id: str,
        document: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Build all types of chunks from a document

        Args:
            source_id: Source identifier
            document: Cleaned document
            metadata: Document metadata (url, fetched_at, etc)

        Returns:
            List of chunks with metadata
        """
        chunks = []

        # 1. Generate narrative chunks from sections
        narrative_chunks = self._build_narrative_chunks(source_id, document, metadata)
        chunks.extend(narrative_chunks)

        # 2. Generate FAQ chunks
        if "faqs" in document:
            faq_chunks = self._build_faq_chunks(source_id, document["faqs"], metadata)
            chunks.extend(faq_chunks)

        # 3. Generate typed-fact chunks
        if "typed_facts" in document:
            fact_chunks = self._build_fact_chunks(source_id, document["typed_facts"], metadata)
            chunks.extend(fact_chunks)

        logger.info(f"Built {len(chunks)} chunks for {source_id}")
        return chunks

    def _build_narrative_chunks(
        self,
        source_id: str,
        document: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build narrative chunks (300-800 tokens)"""
        chunks = []
        content = document.get("content", [])
        section_path = []

        for section in content:
            heading = section.get("heading", "")
            section_content = section.get("content", [])

            if heading:
                section_path.append(heading)

            # Combine content into chunk
            text_lines = section_content
            combined_text = "\n".join(text_lines).strip()

            if combined_text:
                # Estimate tokens (rough: 1 token ≈ 4 chars)
                token_count = len(combined_text) // 4

                # Only create chunk if reasonable size
                if 50 < token_count < 2000:
                    chunk = {
                        "chunk_id": self._next_chunk_id(source_id),
                        "source_id": source_id,
                        "source_url": metadata.get("url", ""),
                        "doc_version": metadata.get("fetched_at", ""),
                        "fetched_at": metadata.get("fetched_at", datetime.utcnow().isoformat() + "Z"),
                        "chunk_type": "narrative",
                        "section_path": " / ".join(section_path[-3:]),  # Last 3 levels
                        "text": combined_text,
                        "fields_present": self._detect_fields(combined_text),
                        "character_count": len(combined_text),
                        "token_estimate": token_count
                    }
                    chunks.append(chunk)

        return chunks

    def _build_faq_chunks(
        self,
        source_id: str,
        faqs: List[Dict[str, str]],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build FAQ chunks (one Q+A per chunk)"""
        chunks = []

        for faq in faqs:
            question = faq.get("question", "").strip()
            answer = faq.get("answer", "").strip()

            if question and answer:
                text = f"Q: {question}\nA: {answer}"
                token_count = len(text) // 4

                chunk = {
                    "chunk_id": self._next_chunk_id(source_id),
                    "source_id": source_id,
                    "source_url": metadata.get("url", ""),
                    "doc_version": metadata.get("fetched_at", ""),
                    "fetched_at": metadata.get("fetched_at", datetime.utcnow().isoformat() + "Z"),
                    "chunk_type": "faq",
                    "section_path": "FAQ",
                    "text": text,
                    "fields_present": self._detect_fields(text),
                    "character_count": len(text),
                    "token_estimate": token_count
                }
                chunks.append(chunk)

        return chunks

    def _build_fact_chunks(
        self,
        source_id: str,
        facts: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build typed-fact chunks (small, high-precision)"""
        chunks = []

        for fact in facts:
            field_name = fact.get("field_name", "")
            field_value = fact.get("field_value", "")
            scheme_id = fact.get("scheme_id", "")

            if field_name and field_value:
                text = f"{field_name}: {field_value}"
                if scheme_id:
                    text = f"{scheme_id}: {text}"

                chunk = {
                    "chunk_id": self._next_chunk_id(source_id),
                    "source_id": source_id,
                    "source_url": metadata.get("url", ""),
                    "doc_version": metadata.get("fetched_at", ""),
                    "fetched_at": metadata.get("fetched_at", datetime.utcnow().isoformat() + "Z"),
                    "chunk_type": "typed_fact",
                    "section_path": f"Facts / {field_name}",
                    "text": text,
                    "fields_present": [field_name],
                    "character_count": len(text),
                    "token_estimate": len(text) // 4,
                    "confidence": fact.get("confidence", 0.95)
                }
                chunks.append(chunk)

        return chunks

    @staticmethod
    def _detect_fields(text: str) -> List[str]:
        """Detect which typed fields are present in text"""
        fields = []
        field_patterns = {
            "nav": r"(?i)\bNAV\b|net asset value",
            "expense_ratio": r"(?i)expense ratio|TER|costs",
            "min_sip": r"(?i)minimum SIP|min.*?SIP|minimum SIP",
            "min_lumpsum": r"(?i)minimum lumpsum|min.*?lumpsum",
            "exit_load": r"(?i)exit load|redemption fee",
            "lock_in": r"(?i)lock-in|lock in|locked for",
            "risk_label": r"(?i)risk.*?(low|medium|high)|volatility",
            "aum": r"(?i)AUM|fund size|assets under management",
            "holdings": r"(?i)holdings?|portfolio",
            "performance": r"(?i)return|performance|gain",
        }

        for field, pattern in field_patterns.items():
            if re.search(pattern, text):
                fields.append(field)

        return fields

    def _next_chunk_id(self, source_id: str) -> str:
        """Generate next chunk ID for a source"""
        if source_id not in self.chunk_id_counter:
            self.chunk_id_counter[source_id] = 0

        self.chunk_id_counter[source_id] += 1
        return f"{source_id}_chunk_{self.chunk_id_counter[source_id]:03d}"
