"""
Document Cleaner: Remove boilerplate, preserve structure
Handles HTML cleanup, footer/nav removal, and structure preservation
"""

import re
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class DocumentCleaner:
    """Cleans and structures documents from parsed content"""

    def __init__(self):
        # Common boilerplate patterns to remove
        self.boilerplate_patterns = [
            r'(?i)^\s*(home|about|contact|privacy|terms|sitemap)[\s\|/]*',
            r'(?i)©.*?(copyright|all rights reserved)',
            r'(?i)(follow us|share|social media)',
            r'(?i)(loading|please wait|javascript)',
        ]

        # FAQ patterns
        self.faq_patterns = [
            r'^\s*Q:\s*(.+?)(?:\n|$)',
            r'^\s*A:\s*(.+?)(?:\n|$)',
            r'^\s*Question:\s*(.+?)(?:\n|$)',
            r'^\s*Answer:\s*(.+?)(?:\n|$)',
        ]

    def clean(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and structure a document

        Args:
            document: Raw parsed document

        Returns:
            Cleaned document with structure preserved
        """
        cleaned = {
            "source_id": document.get("source_id", ""),
            "url": document.get("url", ""),
            "fetched_at": document.get("fetched_at", ""),
            "content": []
        }

        # Extract text content
        text = document.get("raw_text", "")
        if not text:
            # Try to reconstruct from structured content
            if "content" in document:
                text = self._reconstruct_text(document["content"])
            else:
                logger.warning(f"No text content found in document")
                return cleaned

        # Parse structure
        sections = self._parse_sections(text)
        cleaned["content"] = sections

        # Extract tables if present
        if "tables" in document:
            cleaned["tables"] = document["tables"]

        # Extract FAQ pairs
        faqs = self._extract_faqs(text)
        if faqs:
            cleaned["faqs"] = faqs

        return cleaned

    @staticmethod
    def _reconstruct_text(content: List[Dict[str, Any]]) -> str:
        """Reconstruct text from structured content"""
        lines = []
        for item in content:
            if isinstance(item, dict):
                if "heading" in item:
                    lines.append(item["heading"])
                if "text" in item:
                    lines.append(item["text"])
            elif isinstance(item, str):
                lines.append(item)
        return "\n".join(lines)

    @staticmethod
    def _parse_sections(text: str) -> List[Dict[str, Any]]:
        """Parse text into sections with headings"""
        sections = []
        current_section = {"type": "text", "heading": "", "content": []}

        lines = text.split('\n')
        for line in lines:
            stripped = line.strip()

            # Detect heading (short lines followed by content)
            if DocumentCleaner._is_heading(stripped, lines):
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {
                    "type": "section",
                    "heading": stripped,
                    "content": []
                }
            elif stripped:
                current_section["content"].append(stripped)

        # Add final section
        if current_section["content"]:
            sections.append(current_section)

        return sections

    @staticmethod
    def _is_heading(line: str, context: List[str]) -> bool:
        """Determine if a line is likely a heading"""
        if not line:
            return False

        # Heading heuristics
        is_short = len(line) < 100 and len(line.split()) < 15
        is_uppercase = line.isupper()
        ends_with_colon = line.endswith(':')
        is_number_list = re.match(r'^[\d]+[\.\)]\s+', line)

        return (is_short and (is_uppercase or ends_with_colon or is_number_list)) or len(line.split()) < 5

    @staticmethod
    def _extract_faqs(text: str) -> List[Dict[str, str]]:
        """Extract FAQ pairs from text"""
        faqs = []
        lines = text.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for Q: pattern
            if re.match(r'^\s*Q:\s*', line, re.IGNORECASE):
                question = re.sub(r'^\s*Q:\s*', '', line, flags=re.IGNORECASE)

                # Look for next A: within reasonable distance
                answer = ""
                for j in range(i + 1, min(i + 10, len(lines))):
                    if re.match(r'^\s*A:\s*', lines[j], re.IGNORECASE):
                        answer = re.sub(r'^\s*A:\s*', '', lines[j], flags=re.IGNORECASE)
                        i = j
                        break

                if question and answer:
                    faqs.append({
                        "question": question,
                        "answer": answer
                    })

            i += 1

        return faqs

    @staticmethod
    def _remove_boilerplate(text: str) -> str:
        """Remove common boilerplate text"""
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped and not any(
                re.search(pattern, stripped) for pattern in [
                    r'(?i)^\s*(home|about|contact|privacy|terms|sitemap)',
                    r'(?i)©.*?(copyright|all rights reserved)',
                    r'(?i)follow us|share this',
                ]
            ):
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)
