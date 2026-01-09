#!/usr/bin/env python3
"""
Schema Chunking Module for Cost Optimization.

Splits large schemas into smaller chunks to work around grammar complexity
limits in models like Gemini Flash Lite, enabling cost-effective extraction
of 80+ field schemas.
"""

from typing import List, Dict, Any
from dataclasses import dataclass

from core.schema_builder import FieldDefinition


def chunk_schema(
    fields: List[FieldDefinition],
    max_fields_per_chunk: int = 25
) -> List[List[FieldDefinition]]:
    """
    Split a large schema into smaller chunks for incremental extraction.
    
    Each field with `include_quote=True` is treated as a unit (field + quote).
    Metadata fields are added to each chunk automatically.
    
    Args:
        fields: List of field definitions to chunk
        max_fields_per_chunk: Maximum number of field units per chunk
        
    Returns:
        List of field definition chunks
        
    Example:
        >>> fields = [FieldDefinition("age", ...), FieldDefinition("gender", ...)]
        >>> chunks = chunk_schema(fields, max_fields_per_chunk=25)
        >>> len(chunks)  # e.g., 4 chunks for 80 fields
        4
    """
    if not fields:
        return []
    
    # Separate metadata fields (filename, extraction_confidence, etc.)
    # These will be added to every chunk
    metadata_fields = [
        f for f in fields 
        if f.name in ('filename', 'extraction_confidence', 'extraction_notes')
    ]
    
    # Data fields (excluding metadata)
    data_fields = [
        f for f in fields 
        if f.name not in ('filename', 'extraction_confidence', 'extraction_notes')
    ]
    
    # Create chunks
    chunks = []
    current_chunk = []
    
    for field in data_fields:
        current_chunk.append(field)
        
        # Check if we've hit the limit
        # Note: Each field with include_quote counts as 1 unit
        # (the quote field is added automatically by build_extraction_model)
        if len(current_chunk) >= max_fields_per_chunk:
            chunks.append(current_chunk)
            current_chunk = []
    
    # Add remaining fields
    if current_chunk:
        chunks.append(current_chunk)
    
    # Add metadata fields to each chunk
    # (These are needed for merging and tracking)
    for chunk in chunks:
        chunk.extend(metadata_fields)
    
    return chunks


def merge_extraction_results(
    chunk_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Merge multiple extraction results from chunked schemas into a single record.
    
    Metadata fields (filename, extraction_confidence) are taken from the first chunk.
    Data fields are merged by key.
    
    Args:
        chunk_results: List of extraction dictionaries from each chunk
        
    Returns:
        Merged extraction dictionary
        
    Example:
        >>> chunk1 = {"age": 45, "age_quote": "45 years", "filename": "doc.pdf"}
        >>> chunk2 = {"gender": "M", "gender_quote": "male", "filename": "doc.pdf"}
        >>> merged = merge_extraction_results([chunk1, chunk2])
        >>> merged
        {"age": 45, "age_quote": "45 years", "gender": "M", "gender_quote": "male", "filename": "doc.pdf"}
    """
    if not chunk_results:
        return {}
    
    if len(chunk_results) == 1:
        return chunk_results[0]
    
    # Start with first chunk as base
    merged = dict(chunk_results[0])
    
    # Merge subsequent chunks
    for chunk_result in chunk_results[1:]:
        for key, value in chunk_result.items():
            # Skip metadata fields (already in merged from first chunk)
            if key in ('filename', 'extraction_confidence', 'extraction_notes'):
                continue
            
            # Add data fields
            merged[key] = value
    
    # Recalculate extraction_confidence as average
    confidences = [
        r.get('extraction_confidence') 
        for r in chunk_results 
        if r.get('extraction_confidence') is not None
    ]
    
    if confidences:
        merged['extraction_confidence'] = sum(confidences) / len(confidences)
    
    return merged


def should_chunk_schema(fields: List[FieldDefinition]) -> bool:
    """
    Determine if a schema should be chunked based on size.
    
    Args:
        fields: List of field definitions
        
    Returns:
        True if schema should be chunked (>30 fields)
    """
    # Count data fields (excluding metadata)
    data_field_count = sum(
        1 for f in fields 
        if f.name not in ('filename', 'extraction_confidence', 'extraction_notes')
    )
    
    # Gemini Flash Lite reliably handles ~30 fields
    return data_field_count > 30
