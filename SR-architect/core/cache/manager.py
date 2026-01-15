import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading

from core.utils import get_logger
from core.config import settings
from .constants import DEFAULT_CACHE_PATH
from .models import CacheEntry

logger = get_logger("CacheManager")

class CacheManager:
    """
    SQLite-based cache manager for extraction pipeline.
    
    Provides document-level and field-level caching with
    clear invalidation policies.
    """
    
    # Schema version - increment when changing table structure
    SCHEMA_VERSION = 1
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        parser_version: str = "1.0.0",
    ):
        """
        Initialize cache manager.
        
        Args:
            db_path: Path to SQLite database
            parser_version: Current parser version for invalidation
        """
        self.db_path = db_path or DEFAULT_CACHE_PATH
        self.parser_version = parser_version
        self._local = threading.local()
        
        # Statistics tracking
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
        }
        
        # Ensure cache directory exists
        if hasattr(self.db_path, 'parent'):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Document-level cache (skip re-parsing)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_cache (
                doc_hash TEXT PRIMARY KEY,
                parsed_text TEXT,
                sections TEXT,
                metadata TEXT,
                parser_version TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Field-level cache (skip re-extraction)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extraction_cache (
                doc_hash TEXT,
                field_name TEXT,
                schema_version INTEGER,
                result TEXT,
                confidence REAL,
                tier_used INTEGER,
                tokens_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (doc_hash, field_name, schema_version)
            )
        """)
        
        # Embedding cache (skip re-embedding)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embedding_cache (
                chunk_hash TEXT PRIMARY KEY,
                embedding BLOB,
                model_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_extraction_doc 
            ON extraction_cache(doc_hash)
        """)
        
        conn.commit()
        # logger.info(f"Cache database initialized at {self.db_path}") 
        # Reduced log verbosity
    
    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
    
    # =========================================================================
    # Document Cache
    # =========================================================================
    
    def set_document(
        self,
        doc_hash: str,
        parsed_text: str,
        metadata: Dict[str, Any],
        sections: Optional[List[Dict]] = None,
    ) -> None:
        """
        Cache parsed document.
        
        Args:
            doc_hash: SHA256 hash of document
            parsed_text: Parsed text content
            metadata: Document metadata
            sections: Optional list of sections
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO document_cache 
            (doc_hash, parsed_text, sections, metadata, parser_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            doc_hash,
            parsed_text,
            json.dumps(sections or []),
            json.dumps(metadata),
            self.parser_version,
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        self._stats["sets"] += 1
        logger.debug(f"Cached document: {doc_hash[:8]}...")
    
    def get_document(self, doc_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached document.
        
        Args:
            doc_hash: SHA256 hash of document
            
        Returns:
            Cached document data or None if not found/invalidated
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT parsed_text, sections, metadata, parser_version, created_at
            FROM document_cache
            WHERE doc_hash = ? AND parser_version = ?
        """, (doc_hash, self.parser_version))
        
        row = cursor.fetchone()
        
        if row is None:
            self._stats["misses"] += 1
            return None
        
        self._stats["hits"] += 1
        return {
            "parsed_text": row["parsed_text"],
            "sections": json.loads(row["sections"]),
            "metadata": json.loads(row["metadata"]),
            "parser_version": row["parser_version"],
            "created_at": row["created_at"],
        }
    
    # =========================================================================
    # Field Extraction Cache
    # =========================================================================
    
    def set_field(
        self,
        doc_hash: str,
        field_name: str,
        result: Dict[str, Any],
        schema_version: int,
        tier_used: int,
        confidence: float = 0.0,
        tokens_used: int = 0,
    ) -> None:
        """
        Cache field extraction result.
        
        Args:
            doc_hash: Document hash
            field_name: Name of extracted field
            result: Extraction result
            schema_version: Schema version for invalidation
            tier_used: Extraction tier
            confidence: Extraction confidence score
            tokens_used: Tokens consumed for this extraction
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO extraction_cache
            (doc_hash, field_name, schema_version, result, confidence, tier_used, tokens_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_hash,
            field_name,
            schema_version,
            json.dumps(result),
            confidence,
            tier_used,
            tokens_used,
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        self._stats["sets"] += 1
    
    def get_field(
        self,
        doc_hash: str,
        field_name: str,
        schema_version: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached field extraction.
        
        Args:
            doc_hash: Document hash
            field_name: Name of field
            schema_version: Schema version (must match for hit)
            
        Returns:
            Cached extraction result or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT result, confidence, tier_used, tokens_used, created_at
            FROM extraction_cache
            WHERE doc_hash = ? AND field_name = ? AND schema_version = ?
        """, (doc_hash, field_name, schema_version))
        
        row = cursor.fetchone()
        
        if row is None:
            self._stats["misses"] += 1
            return None
        
        self._stats["hits"] += 1
        return {
            "result": json.loads(row["result"]),
            "confidence": row["confidence"],
            "tier_used": row["tier_used"],
            "tokens_used": row["tokens_used"],
            "created_at": row["created_at"],
        }
    
    def get_all_fields_for_doc(
        self,
        doc_hash: str,
        schema_version: int,
    ) -> Dict[str, Dict[str, Any]]:
        """Get all cached fields for a document."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT field_name, result, confidence, tier_used
            FROM extraction_cache
            WHERE doc_hash = ? AND schema_version = ?
        """, (doc_hash, schema_version))
        
        results = {}
        for row in cursor.fetchall():
            results[row["field_name"]] = {
                "result": json.loads(row["result"]),
                "confidence": row["confidence"],
                "tier_used": row["tier_used"],
            }
        
        return results
    
    # =========================================================================
    # Invalidation
    # =========================================================================
    
    def invalidate_document(self, doc_hash: str) -> int:
        """Invalidate all cache entries for a document."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM document_cache WHERE doc_hash = ?", (doc_hash,))
        cursor.execute("DELETE FROM extraction_cache WHERE doc_hash = ?", (doc_hash,))
        
        total = cursor.rowcount
        conn.commit()
        self._stats["invalidations"] += total
        
        logger.info(f"Invalidated {total} cache entries for document {doc_hash[:8]}...")
        return total
    
    def invalidate_field_by_schema(self, schema_version: int) -> int:
        """Invalidate all field caches for a schema version."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM extraction_cache WHERE schema_version < ?",
            (schema_version,)
        )
        
        total = cursor.rowcount
        conn.commit()
        self._stats["invalidations"] += total
        
        logger.info(f"Invalidated {total} field cache entries for schema < v{schema_version}")
        return total
    
    def clear_all(self) -> None:
        """Clear all caches (use with caution)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM document_cache")
        cursor.execute("DELETE FROM extraction_cache")
        cursor.execute("DELETE FROM embedding_cache")
        
        conn.commit()
        logger.warning("All caches cleared")
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM document_cache")
        doc_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM extraction_cache")
        field_count = cursor.fetchone()[0]
        
        hit_rate = 0.0
        total_access = self._stats["hits"] + self._stats["misses"]
        if total_access > 0:
            hit_rate = self._stats["hits"] / total_access
        
        return {
            **self._stats,
            "cached_documents": doc_count,
            "cached_fields": field_count,
            "hit_rate": hit_rate,
        }
    
    @staticmethod
    def compute_doc_hash(text: str, max_chars: int = None) -> str:
        """Compute SHA256 hash of document text for cache key."""
        if max_chars is None:
            max_chars = settings.CACHE_HASH_CHARS
        sample = text[:max_chars].encode('utf-8')
        return hashlib.sha256(sample).hexdigest()
