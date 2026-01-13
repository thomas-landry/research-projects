#!/usr/bin/env python3
"""
Formatting utilities for validation checker.

Formats source text, extracted data, and evidence for LLM prompts.
"""

from typing import List, Dict, Any
from core.parser import DocumentChunk
from core.config import settings


def format_source_text(chunks: List[DocumentChunk], max_chars: int = None) -> str:
    """
    Format source chunks for the checker prompt.
    
    Args:
        chunks: List of document chunks to format
        max_chars: Maximum characters to include (default from settings)
        
    Returns:
        Formatted string with chunk separators and section labels
    """
    if max_chars is None:
        max_chars = settings.MAX_CHUNK_CHARS
    
    text_parts = []
    total_chars = 0
    
    for i, chunk in enumerate(chunks):
        section_label = f"[{chunk.section}]" if chunk.section else ""
        chunk_text = f"--- Chunk {i} {section_label} ---\n{chunk.text}\n"
        
        if total_chars + len(chunk_text) > max_chars:
            break
        
        text_parts.append(chunk_text)
        total_chars += len(chunk_text)
    
    return "\n".join(text_parts)


def format_extracted_data(data: Dict[str, Any]) -> str:
    """
    Format extracted data for display.
    
    Args:
        data: Dictionary of extracted field values
        
    Returns:
        Formatted string with field: value pairs
    """
    lines = []
    for field, value in data.items():
        # Exclude quote fields and private fields
        if not field.endswith("_quote") and not field.startswith("_"):
            lines.append(f"  {field}: {value}")
    return "\n".join(lines)


def format_evidence(evidence: List[Dict[str, Any]]) -> str:
    """
    Format evidence citations for the checker.
    
    Args:
        evidence: List of evidence items with field_name, extracted_value, exact_quote, confidence
        
    Returns:
        Formatted string with evidence details
    """
    if not evidence:
        return "No evidence citations provided."
    
    lines = []
    for evidence_item in evidence:
        field = evidence_item.get("field_name", "unknown")
        value = evidence_item.get("extracted_value", "N/A")
        quote = evidence_item.get("exact_quote", "No quote")
        confidence = evidence_item.get("confidence", 0)
        
        lines.append(f"  {field}:")
        lines.append(f"    Value: {value}")
        lines.append(f"    Quote: \"{quote}\"")
        lines.append(f"    Confidence: {confidence}")
        lines.append("")
    
    return "\n".join(lines)
