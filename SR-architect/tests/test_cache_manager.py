
"""
Tests for CacheManager logic before and after refactoring.
"""
import pytest
import tempfile
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from core.cache_manager import CacheManager

@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        path = Path(tmp.name)
        yield path
    # Cleanup happens automatically by tempfile closure, but path persistence varies.
    # NamedTemporaryFile deletes on close by default.
    if path.exists():
        path.unlink()

@pytest.fixture
def cache_manager(temp_db_path):
    cm = CacheManager(db_path=temp_db_path)
    yield cm
    cm.close()

def test_init_creates_db(cache_manager, temp_db_path):
    assert temp_db_path.exists()
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    assert "document_cache" in tables
    assert "extraction_cache" in tables
    assert "embedding_cache" in tables
    conn.close()

def test_document_cache(cache_manager):
    doc_hash = "test_hash_123"
    text = "Sample text"
    meta = {"source": "test.pdf"}
    
    # Test Set
    cache_manager.set_document(doc_hash, text, meta)
    
    # Test Get
    cached = cache_manager.get_document(doc_hash)
    assert cached is not None
    assert cached["parsed_text"] == text
    assert cached["metadata"] == meta
    assert cached["parser_version"] == cache_manager.parser_version

def test_field_cache(cache_manager):
    doc_hash = "test_hash_123"
    field = "patient_age"
    result = {"value": 45, "unit": "years"}
    schema_ver = 1
    
    # Test Set
    cache_manager.set_field(
        doc_hash, field, result, schema_ver,
        tier_used=1, confidence=0.95
    )
    
    # Test Get
    cached = cache_manager.get_field(doc_hash, field, schema_ver)
    assert cached is not None
    assert cached["result"] == result
    assert cached["confidence"] == 0.95
    
    # Test Miss (wrong version)
    miss = cache_manager.get_field(doc_hash, field, schema_ver + 1)
    assert miss is None

def test_invalidation(cache_manager):
    doc_hash = "doc_to_invalidate"
    cache_manager.set_document(doc_hash, "text", {})
    
    assert cache_manager.get_document(doc_hash) is not None
    
    cache_manager.invalidate_document(doc_hash)
    assert cache_manager.get_document(doc_hash) is None

def test_stats(cache_manager):
    stats = cache_manager.get_stats()
    assert stats["hits"] == 0
    assert stats["cached_documents"] == 0
    
    doc_hash = "stat_test"
    cache_manager.set_document(doc_hash, "text", {})
    cache_manager.get_document(doc_hash)
    
    updated_stats = cache_manager.get_stats()
    assert updated_stats["hits"] == 1
    assert updated_stats["sets"] == 1
    assert updated_stats["cached_documents"] == 1
