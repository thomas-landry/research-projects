"""
Unit tests for schema chunking module.

Tests the chunking and merging logic for large schemas.
"""

import pytest
from core.schema_chunker import (
    chunk_schema,
    merge_extraction_results,
    should_chunk_schema,
)
from core.schema_builder import FieldDefinition, FieldType


def test_chunk_schema_preserves_quote_pairs():
    """Test that chunking keeps field + quote pairs together."""
    fields = [
        FieldDefinition("age", "Patient age", FieldType.INTEGER, required=True, include_quote=True),
        FieldDefinition("gender", "Patient gender", FieldType.TEXT, required=True, include_quote=True),
        FieldDefinition("diagnosis", "Primary diagnosis", FieldType.TEXT, required=True, include_quote=True),
    ]
    
    chunks = chunk_schema(fields, max_fields_per_chunk=2)
    
    # Should create 2 chunks (3 fields / 2 per chunk = 2 chunks)
    assert len(chunks) == 2
    
    # Each chunk should have data fields + metadata
    assert len(chunks[0]) >= 2  # 2 data fields + metadata
    assert len(chunks[1]) >= 1  # 1 data field + metadata


def test_chunk_schema_respects_max_size():
    """Test that chunks don't exceed max_fields_per_chunk."""
    fields = [
        FieldDefinition(f"field_{i}", f"Field {i}", FieldType.TEXT, required=True, include_quote=True)
        for i in range(50)
    ]
    
    chunks = chunk_schema(fields, max_fields_per_chunk=25)
    
    # Should create 2 chunks (50 / 25 = 2)
    assert len(chunks) == 2
    
    # Each chunk should have at most 25 data fields (excluding metadata)
    for chunk in chunks:
        data_fields = [f for f in chunk if f.name not in ('filename', 'extraction_confidence', 'extraction_notes')]
        assert len(data_fields) <= 25


def test_chunk_schema_includes_metadata():
    """Test that metadata fields are added to every chunk."""
    fields = [
        FieldDefinition("age", "Patient age", FieldType.INTEGER, required=True, include_quote=True),
        FieldDefinition("gender", "Patient gender", FieldType.TEXT, required=True, include_quote=True),
        FieldDefinition("filename", "Source file", FieldType.TEXT, required=False, include_quote=False),
        FieldDefinition("extraction_confidence", "Confidence", FieldType.TEXT, required=False, include_quote=False),
    ]
    
    chunks = chunk_schema(fields, max_fields_per_chunk=1)
    
    # Each chunk should have metadata fields
    for chunk in chunks:
        field_names = [f.name for f in chunk]
        assert "filename" in field_names
        assert "extraction_confidence" in field_names


def test_merge_extraction_results():
    """Test merging multiple extraction results."""
    chunk1 = {
        "age": 45,
        "age_quote": "45 years old",
        "filename": "doc.pdf",
        "extraction_confidence": 0.9,
    }
    
    chunk2 = {
        "gender": "M",
        "gender_quote": "male patient",
        "filename": "doc.pdf",
        "extraction_confidence": 0.85,
    }
    
    merged = merge_extraction_results([chunk1, chunk2])
    
    # Should have all fields
    assert merged["age"] == 45
    assert merged["age_quote"] == "45 years old"
    assert merged["gender"] == "M"
    assert merged["gender_quote"] == "male patient"
    
    # Metadata from first chunk
    assert merged["filename"] == "doc.pdf"
    
    # Confidence should be averaged
    assert merged["extraction_confidence"] == pytest.approx(0.875)


def test_merge_extraction_results_single_chunk():
    """Test that merging a single chunk returns it unchanged."""
    chunk = {"age": 45, "filename": "doc.pdf"}
    
    merged = merge_extraction_results([chunk])
    
    assert merged == chunk


def test_merge_extraction_results_empty():
    """Test that merging empty list returns empty dict."""
    merged = merge_extraction_results([])
    
    assert merged == {}


def test_should_chunk_schema():
    """Test schema chunking detection."""
    # Small schema (should not chunk)
    small_fields = [
        FieldDefinition(f"field_{i}", f"Field {i}", FieldType.TEXT, required=True, include_quote=True)
        for i in range(20)
    ]
    assert should_chunk_schema(small_fields) is False
    
    # Large schema (should chunk)
    large_fields = [
        FieldDefinition(f"field_{i}", f"Field {i}", FieldType.TEXT, required=True, include_quote=True)
        for i in range(50)
    ]
    assert should_chunk_schema(large_fields) is True


def test_chunk_schema_with_metadata_only():
    """Test chunking with only metadata fields."""
    fields = [
        FieldDefinition("filename", "Source file", FieldType.TEXT, required=False, include_quote=False),
        FieldDefinition("extraction_confidence", "Confidence", FieldType.TEXT, required=False, include_quote=False),
    ]
    
    chunks = chunk_schema(fields, max_fields_per_chunk=25)
    
    # Should return empty list (no data fields to chunk)
    assert len(chunks) == 0
