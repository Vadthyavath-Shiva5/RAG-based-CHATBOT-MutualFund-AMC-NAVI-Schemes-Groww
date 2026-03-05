"""
Table Handler: Extract tables as markdown + JSON
Handles conversion of tables to dual format for LLM + direct answers
"""

import json
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class TableHandler:
    """Handles table extraction and conversion"""

    def extract_table_chunks(
        self,
        source_id: str,
        tables: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract chunks from tables (one row per chunk or whole table)

        Args:
            source_id: Source identifier
            tables: List of table objects
            metadata: Document metadata

        Returns:
            List of table chunks
        """
        chunks = []

        for table_idx, table in enumerate(tables):
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            caption = table.get("caption", "")

            if not rows:
                continue

            # For scheme comparison tables, create one chunk per row
            if self._is_scheme_table(headers):
                for row_idx, row in enumerate(rows):
                    chunk = self._create_row_chunk(
                        source_id=source_id,
                        table_idx=table_idx,
                        row_idx=row_idx,
                        headers=headers,
                        row=row,
                        caption=caption,
                        metadata=metadata
                    )
                    chunks.append(chunk)
            else:
                # For smaller tables, create one chunk for whole table
                chunk = self._create_table_chunk(
                    source_id=source_id,
                    table_idx=table_idx,
                    headers=headers,
                    rows=rows,
                    caption=caption,
                    metadata=metadata
                )
                chunks.append(chunk)

        return chunks

    @staticmethod
    def _is_scheme_table(headers: List[str]) -> bool:
        """Detect if table contains scheme data"""
        scheme_keywords = ["scheme", "fund", "nav", "sip", "expense", "rating"]
        headers_lower = [h.lower() for h in headers]
        matches = sum(1 for h in headers_lower for kw in scheme_keywords if kw in h)
        return matches >= 2

    @staticmethod
    def _create_row_chunk(
        source_id: str,
        table_idx: int,
        row_idx: int,
        headers: List[str],
        row: List[str],
        caption: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create chunk for single table row"""
        # Build markdown representation
        markdown_lines = []
        if caption:
            markdown_lines.append(f"**{caption}**")

        markdown_lines.append("")
        markdown_lines.append("| " + " | ".join(headers) + " |")
        markdown_lines.append("|" + "|".join(["---"] * len(headers)) + "|")
        markdown_lines.append("| " + " | ".join(str(v) for v in row) + " |")

        # Build JSON representation
        json_data = dict(zip(headers, row))

        text = "\n".join(markdown_lines)

        # Detect fields from headers
        fields = []
        field_keywords = {
            "nav": ["nav", "price"],
            "expense_ratio": ["expense", "ratio", "ter", "cost"],
            "min_sip": ["min", "sip", "minimum"],
            "exit_load": ["exit", "load", "redemption"],
        }

        headers_lower = [h.lower() for h in headers]
        for field, keywords in field_keywords.items():
            if any(kw in h for h in headers_lower for kw in keywords):
                fields.append(field)

        return {
            "chunk_id": f"{source_id}_table_{table_idx}_row_{row_idx}",
            "source_id": source_id,
            "source_url": metadata.get("url", ""),
            "doc_version": metadata.get("fetched_at", ""),
            "fetched_at": metadata.get("fetched_at", ""),
            "chunk_type": "table_row",
            "section_path": f"Table: {caption}",
            "text": text,
            "json_data": json_data,
            "fields_present": fields,
            "character_count": len(text),
            "token_estimate": len(text) // 4
        }

    @staticmethod
    def _create_table_chunk(
        source_id: str,
        table_idx: int,
        headers: List[str],
        rows: List[List[str]],
        caption: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create chunk for entire table"""
        # Build markdown
        markdown_lines = []
        if caption:
            markdown_lines.append(f"**{caption}**")

        markdown_lines.append("")
        markdown_lines.append("| " + " | ".join(headers) + " |")
        markdown_lines.append("|" + "|".join(["---"] * len(headers)) + "|")

        for row in rows:
            markdown_lines.append("| " + " | ".join(str(v) for v in row) + " |")

        text = "\n".join(markdown_lines)

        # Detect fields
        fields = []
        field_keywords = {
            "nav": ["nav", "price"],
            "expense_ratio": ["expense", "ratio", "ter"],
            "min_sip": ["min", "sip"],
        }

        headers_lower = [h.lower() for h in headers]
        for field, keywords in field_keywords.items():
            if any(kw in h for h in headers_lower for kw in keywords):
                fields.append(field)

        return {
            "chunk_id": f"{source_id}_table_{table_idx}",
            "source_id": source_id,
            "source_url": metadata.get("url", ""),
            "doc_version": metadata.get("fetched_at", ""),
            "fetched_at": metadata.get("fetched_at", ""),
            "chunk_type": "table",
            "section_path": f"Table: {caption}",
            "text": text,
            "json_data": {
                "headers": headers,
                "rows": rows,
                "row_count": len(rows)
            },
            "fields_present": fields,
            "character_count": len(text),
            "token_estimate": len(text) // 4
        }

    @staticmethod
    def convert_html_table(html_table: str) -> Dict[str, Any]:
        """Convert HTML table to structured format"""
        try:
            from html.parser import HTMLParser

            class TableParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.headers = []
                    self.rows = []
                    self.current_row = []
                    self.in_header = False
                    self.in_row = False

                def handle_starttag(self, tag, attrs):
                    if tag == "th":
                        self.in_header = True
                    elif tag == "td":
                        self.in_row = True
                    elif tag == "tr":
                        self.current_row = []

                def handle_endtag(self, tag):
                    if tag == "th":
                        self.in_header = False
                    elif tag == "td":
                        self.in_row = False
                    elif tag == "tr" and self.current_row:
                        if self.in_header:
                            self.headers = self.current_row
                        else:
                            self.rows.append(self.current_row)
                        self.current_row = []

                def handle_data(self, data):
                    data = data.strip()
                    if data and (self.in_header or self.in_row):
                        self.current_row.append(data)

            parser = TableParser()
            parser.feed(html_table)

            return {
                "headers": parser.headers,
                "rows": parser.rows
            }

        except Exception as e:
            logger.error(f"Error parsing HTML table: {str(e)}")
            return {"headers": [], "rows": []}
