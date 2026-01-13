#!/usr/bin/env python3
"""
Classification helper functions.

Pure helper functions for chunk truncation and prompt building.
"""

from typing import List
from core.parser import DocumentChunk


def truncate_chunk(chunk: DocumentChunk, preview_chars: int) -> str:
    """
    Truncate chunk text for classification preview.
    
    Args:
        chunk: Document chunk to truncate
        preview_chars: Maximum characters to include
        
    Returns:
        Truncated text with ellipsis if needed
    """
    text = chunk.text.strip()
    if len(text) <= preview_chars:
        return text
    return text[:preview_chars] + "..."


def build_batch_prompt(
    chunks: List[DocumentChunk],
    start_index: int,
    theme: str,
    schema_fields: List[str],
    preview_chars: int,
) -> str:
    """
    Build the user prompt for a batch of chunks.
    
    Args:
        chunks: List of chunks to classify
        start_index: Starting index for chunk numbering
        theme: Meta-analysis theme
        schema_fields: List of field names to extract
        preview_chars: Maximum characters per chunk preview
        
    Returns:
        Formatted prompt string
    """
    fields_str = ", ".join(schema_fields)  # Include all fields for context
    
    chunks_str = ""
    for i, chunk in enumerate(chunks):
        idx = start_index + i
        preview = truncate_chunk(chunk, preview_chars)
        section_info = f" [Section: {chunk.section}]" if chunk.section else ""
        chunks_str += f"\n[{idx}]{section_info}\n{preview}\n"
    
    return f"""Meta-analysis theme: "{theme}"
Data fields to extract: {fields_str}

Classify each chunk below as relevant (1) or irrelevant (0) to this theme.

Chunks:
{chunks_str}

For each chunk, provide:
- index: the chunk number
- relevant: 1 if it likely contains extractable data, 0 if not
- reason: brief explanation (max 10 words)"""
