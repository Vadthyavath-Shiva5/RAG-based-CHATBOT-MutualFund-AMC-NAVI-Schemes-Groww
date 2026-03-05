"""
Document store implementation using SQLite for Phase 3 indexing.
Stores canonical documents, chunks, typed facts, and evidence spans.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentStore:
    """SQLite-based document store for canonical docs, chunks, and typed facts."""

    def __init__(self, db_path: str):
        """
        Initialize document store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Documents table - canonical source documents
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    fetched_at TEXT NOT NULL,
                    source_type TEXT,
                    metadata TEXT,  -- JSON metadata
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Chunks table - processed text chunks
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_type TEXT NOT NULL,  -- narrative, faq, table_row, typed_fact
                    text TEXT NOT NULL,
                    section_path TEXT,
                    fields_present TEXT,  -- JSON array of field names
                    token_count INTEGER,
                    embedding BLOB,  -- Optional: store embedding here too
                    metadata TEXT,  -- JSON metadata
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                )
            ''')

            # Typed facts table - normalized structured facts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS typed_facts (
                    id TEXT PRIMARY KEY,
                    scheme_name TEXT,
                    field_name TEXT NOT NULL,
                    field_value TEXT,
                    value_type TEXT,  -- string, number, date, boolean
                    confidence REAL DEFAULT 1.0,
                    source_chunk_id TEXT,
                    as_of_date TEXT,
                    metadata TEXT,  -- JSON metadata
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_chunk_id) REFERENCES chunks(id)
                )
            ''')

            # Evidence spans table - fact to source text mappings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS evidence_spans (
                    id TEXT PRIMARY KEY,
                    typed_fact_id TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    span_text TEXT NOT NULL,
                    start_offset INTEGER,
                    end_offset INTEGER,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (typed_fact_id) REFERENCES typed_facts(id),
                    FOREIGN KEY (chunk_id) REFERENCES chunks(id)
                )
            ''')

            # Indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks(chunk_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_typed_facts_scheme ON typed_facts(scheme_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_typed_facts_field ON typed_facts(field_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_evidence_fact ON evidence_spans(typed_fact_id)')

            conn.commit()
            logger.info("Database schema initialized")

    def add_document(self, doc_id: str, url: str, title: str = None, content: str = None,
                    fetched_at: str = None, source_type: str = None, metadata: Dict[str, Any] = None):
        """
        Add or update a document.

        Args:
            doc_id: Unique document identifier
            url: Source URL
            title: Document title
            content: Full document content
            fetched_at: ISO timestamp when fetched
            source_type: Type of source (html, pdf, etc.)
            metadata: Additional metadata as dict
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO documents
                (id, url, title, content, fetched_at, source_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc_id, url, title, content, fetched_at, source_type,
                json.dumps(metadata) if metadata else None
            ))

            conn.commit()
            logger.debug(f"Added document: {doc_id}")

    def add_chunk(self, chunk_id: str, document_id: str, chunk_type: str, text: str,
                 section_path: str = None, fields_present: List[str] = None,
                 token_count: int = None, metadata: Dict[str, Any] = None):
        """
        Add a text chunk.

        Args:
            chunk_id: Unique chunk identifier
            document_id: Parent document ID
            chunk_type: Type of chunk (narrative, faq, table_row, typed_fact)
            text: Chunk text content
            section_path: Document section path
            fields_present: List of field names present in chunk
            token_count: Approximate token count
            metadata: Additional metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO chunks
                (id, document_id, chunk_type, text, section_path, fields_present,
                 token_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                chunk_id, document_id, chunk_type, text, section_path,
                json.dumps(fields_present) if fields_present else None,
                token_count, json.dumps(metadata) if metadata else None
            ))

            conn.commit()
            logger.debug(f"Added chunk: {chunk_id}")

    def add_typed_fact(self, fact_id: str, scheme_name: str, field_name: str,
                      field_value: Any, value_type: str, confidence: float = 1.0,
                      source_chunk_id: str = None, as_of_date: str = None,
                      metadata: Dict[str, Any] = None):
        """
        Add a typed fact.

        Args:
            fact_id: Unique fact identifier
            scheme_name: Scheme name (if applicable)
            field_name: Field name (nav_value, expense_ratio, etc.)
            field_value: Field value
            value_type: Value type (string, number, date, boolean)
            confidence: Confidence score 0-1
            source_chunk_id: Source chunk ID
            as_of_date: Date this fact is valid as of
            metadata: Additional metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO typed_facts
                (id, scheme_name, field_name, field_value, value_type, confidence,
                 source_chunk_id, as_of_date, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fact_id, scheme_name, field_name, str(field_value), value_type,
                confidence, source_chunk_id, as_of_date,
                json.dumps(metadata) if metadata else None
            ))

            conn.commit()
            logger.debug(f"Added typed fact: {fact_id}")

    def get_chunks_by_type(self, chunk_type: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get chunks by type.

        Args:
            chunk_type: Chunk type to filter by
            limit: Maximum number of chunks to return

        Returns:
            List of chunk dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            query = '''
                SELECT id, document_id, chunk_type, text, section_path,
                       fields_present, token_count, metadata, created_at
                FROM chunks WHERE chunk_type = ?
                ORDER BY created_at DESC
            '''

            if limit:
                query += f' LIMIT {limit}'

            cursor.execute(query, (chunk_type,))
            rows = cursor.fetchall()

            chunks = []
            for row in rows:
                chunk = {
                    'id': row[0],
                    'document_id': row[1],
                    'chunk_type': row[2],
                    'text': row[3],
                    'section_path': row[4],
                    'fields_present': json.loads(row[5]) if row[5] else None,
                    'token_count': row[6],
                    'metadata': json.loads(row[7]) if row[7] else None,
                    'created_at': row[8]
                }
                chunks.append(chunk)

            return chunks

    def get_typed_facts(self, scheme_name: str = None, field_name: str = None) -> List[Dict[str, Any]]:
        """
        Get typed facts with optional filtering.

        Args:
            scheme_name: Filter by scheme name
            field_name: Filter by field name

        Returns:
            List of typed fact dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            conditions = []
            params = []

            if scheme_name:
                conditions.append("scheme_name = ?")
                params.append(scheme_name)

            if field_name:
                conditions.append("field_name = ?")
                params.append(field_name)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            cursor.execute(f'''
                SELECT id, scheme_name, field_name, field_value, value_type,
                       confidence, source_chunk_id, as_of_date, metadata, created_at
                FROM typed_facts
                WHERE {where_clause}
                ORDER BY confidence DESC, created_at DESC
            ''', params)

            rows = cursor.fetchall()

            facts = []
            for row in rows:
                fact = {
                    'id': row[0],
                    'scheme_name': row[1],
                    'field_name': row[2],
                    'field_value': row[3],
                    'value_type': row[4],
                    'confidence': row[5],
                    'source_chunk_id': row[6],
                    'as_of_date': row[7],
                    'metadata': json.loads(row[8]) if row[8] else None,
                    'created_at': row[9]
                }
                facts.append(fact)

            return facts

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            stats = {}

            # Count records in each table
            for table in ['documents', 'chunks', 'typed_facts', 'evidence_spans']:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats[f'{table}_count'] = cursor.fetchone()[0]

            # Chunk type distribution
            cursor.execute('SELECT chunk_type, COUNT(*) FROM chunks GROUP BY chunk_type')
            stats['chunk_types'] = dict(cursor.fetchall())

            # Field distribution
            cursor.execute('SELECT field_name, COUNT(*) FROM typed_facts GROUP BY field_name')
            stats['field_types'] = dict(cursor.fetchall())

            return stats