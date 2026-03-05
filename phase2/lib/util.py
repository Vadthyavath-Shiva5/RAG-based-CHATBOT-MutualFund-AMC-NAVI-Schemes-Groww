"""
Utility functions for Phase 2
Helper functions for chunking, text analysis, and data processing
"""

import re
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class TokenEstimator:
    """Estimate token count for text"""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count (rough approximation)
        Based on: 1 token ≈ 4 characters on average
        """
        if not text:
            return 0
        return len(text) // 4

    @staticmethod
    def word_count(text: str) -> int:
        """Count words in text"""
        return len(text.split())

    @staticmethod
    def sentence_count(text: str) -> int:
        """Count sentences in text"""
        sentences = re.split(r'[.!?]+', text)
        return sum(1 for s in sentences if s.strip())


class TextCleaner:
    """Text cleaning utilities"""

    @staticmethod
    def remove_extra_whitespace(text: str) -> str:
        """Remove extra whitespace and normalize"""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove trailing/leading whitespace
        return text.strip()

    @staticmethod
    def remove_special_characters(text: str, keep_punctuation: bool = True) -> str:
        """Remove special characters"""
        if keep_punctuation:
            # Keep alphanumeric, spaces, and basic punctuation
            text = re.sub(r'[^a-zA-Z0-9\s.,!?;:\'"()-]', '', text)
        else:
            text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        return text

    @staticmethod
    def normalize_numbers(text: str) -> str:
        """Normalize numeric values (e.g., currency formatting)"""
        # Normalize Indian rupee values
        text = re.sub(r'₹\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', r'₹\1', text)
        # Remove comma spacing in large numbers
        text = re.sub(r'(\d+),(\d{3})', r'\1\2', text)
        return text

    @staticmethod
    def extract_numbers(text: str) -> List[str]:
        """Extract all numbers from text"""
        return re.findall(r'\d+(?:\.\d+)?', text)

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = r'https?://[^\s]+'
        return re.findall(url_pattern, text)

    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract email addresses from text"""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(email_pattern, text)


class FieldExtractor:
    """Extract typed fields from text"""

    # Field detection patterns
    FIELD_PATTERNS = {
        "expense_ratio": {
            "patterns": [
                r"expense\s+ratio[:\s]+([0-9.]+%?)",
                r"TER[:\s]+([0-9.]+%?)",
                r"total\s+expense\s+ratio[:\s]+([0-9.]+%?)",
            ],
            "keywords": ["expense", "ratio", "ter", "costs", "fee"]
        },
        "nav": {
            "patterns": [
                r"NAV[:\s]+₹?([0-9.]+)",
                r"net\s+asset\s+value[:\s]+₹?([0-9.]+)",
            ],
            "keywords": ["nav", "price", "net asset value", "per unit"]
        },
        "min_sip": {
            "patterns": [
                r"minimum\s+SIP[:\s]+₹?([0-9,]+)",
                r"min\s+SIP[:\s]+₹?([0-9,]+)",
            ],
            "keywords": ["minimum sip", "min sip", "sip amount"]
        },
        "min_lumpsum": {
            "patterns": [
                r"minimum\s+lumpsum[:\s]+₹?([0-9,]+)",
                r"min\s+investment[:\s]+₹?([0-9,]+)",
            ],
            "keywords": ["minimum lumpsum", "lumpsum amount"]
        },
        "exit_load": {
            "patterns": [
                r"exit\s+load[:\s]+([0-9.%]+)?",
                r"redemption\s+fee[:\s]+([0-9.%]+)?",
            ],
            "keywords": ["exit load", "redemption fee"]
        },
        "aum": {
            "patterns": [
                r"AUM[:\s]+₹?([0-9.,]+\s+(?:Cr|Crore))",
                r"fund\s+size[:\s]+₹?([0-9.,]+)",
            ],
            "keywords": ["aum", "assets under management", "fund size"]
        },
        "lock_in": {
            "patterns": [
                r"lock-?in\s+(?:period[:\s]+)?([0-9]+\s+(?:year|month))",
                r"locked\s+for[:\s]+([0-9]+\s+(?:year|month))",
            ],
            "keywords": ["lock in", "lock-in", "locked"]
        },
        "risk_label": {
            "patterns": [
                r"risk\s+(?:label|rating)[:\s]+(low|medium|high|very\s+high)",
            ],
            "keywords": ["risk", "volatility", "rating"]
        }
    }

    @classmethod
    def extract_fields(cls, text: str) -> dict:
        """Extract all detected fields from text"""
        fields = {}

        for field_name, field_config in cls.FIELD_PATTERNS.items():
            # Try patterns
            for pattern in field_config.get("patterns", []):
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    fields[field_name] = {
                        "value": matches[0],
                        "method": "pattern"
                    }
                    break

            # If no match, check keywords
            if field_name not in fields:
                keywords = field_config.get("keywords", [])
                if any(kw in text.lower() for kw in keywords):
                    fields[field_name] = {
                        "method": "keyword",
                        "detected": True
                    }

        return fields

    @classmethod
    def extract_field_value(cls, field_name: str, text: str) -> str:
        """Extract specific field value from text"""
        if field_name not in cls.FIELD_PATTERNS:
            return ""

        patterns = cls.FIELD_PATTERNS[field_name].get("patterns", [])
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0) if match.lastindex is None else match.group(1)

        return ""


class SectionParser:
    """Parse document sections and create section paths"""

    HEADING_LEVELS = {
        "h1": 1,
        "h2": 2,
        "h3": 3,
        "h4": 4,
    }

    @staticmethod
    def build_section_path(headings: List[Tuple[int, str]]) -> str:
        """
        Build section path from heading hierarchy

        Args:
            headings: List of (level, text) tuples

        Returns:
            Section path like "Section1 / Subsection1 / Subsubsection"
        """
        if not headings:
            return ""

        # Get only the most recent headings
        path_parts = []
        current_level = 0

        for level, text in reversed(headings):
            if level <= current_level or len(path_parts) < 3:
                path_parts.insert(0, text)
                current_level = level

        return " / ".join(path_parts)

    @staticmethod
    def detect_section_type(heading: str) -> str:
        """Detect section type from heading text"""
        heading_lower = heading.lower()

        if "faq" in heading_lower or "question" in heading_lower:
            return "faq"
        elif "fact" in heading_lower:
            return "fact"
        elif "table" in heading_lower or "comparison" in heading_lower:
            return "table"
        elif any(word in heading_lower for word in ["overview", "introduction", "about"]):
            return "overview"
        elif any(word in heading_lower for word in ["risk", "performance", "return"]):
            return "analysis"
        else:
            return "general"


class ChunkValidator:
    """Validate chunks for quality"""

    @staticmethod
    def validate_chunk(chunk: dict) -> Tuple[bool, List[str]]:
        """
        Validate chunk structure and content

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Required fields
        required_fields = [
            "chunk_id", "source_id", "chunk_type", "text",
            "fetched_at", "source_url"
        ]

        for field in required_fields:
            if field not in chunk:
                errors.append(f"Missing required field: {field}")

        # Validate types
        if "text" in chunk and not isinstance(chunk["text"], str):
            errors.append("'text' field must be string")

        if "token_estimate" in chunk and chunk["token_estimate"] < 10:
            errors.append("Chunk too small (< 10 tokens)")

        if "token_estimate" in chunk and chunk["token_estimate"] > 5000:
            errors.append("Chunk too large (> 5000 tokens)")

        # Validate chunk_id format
        if "chunk_id" in chunk:
            if not re.match(r'^[a-z0-9_-]+$', chunk["chunk_id"]):
                errors.append("Invalid chunk_id format")

        return len(errors) == 0, errors

    @staticmethod
    def validate_chunks_batch(chunks: List[dict]) -> dict:
        """Validate batch of chunks"""
        results = {
            "total": len(chunks),
            "valid": 0,
            "invalid": 0,
            "errors": []
        }

        for chunk in chunks:
            is_valid, errors = ChunkValidator.validate_chunk(chunk)
            if is_valid:
                results["valid"] += 1
            else:
                results["invalid"] += 1
                results["errors"].append({
                    "chunk_id": chunk.get("chunk_id", "unknown"),
                    "errors": errors
                })

        return results
