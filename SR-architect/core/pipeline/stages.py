"""
Pure functions for pipeline stages.

These functions have no side effects and are fully testable.
They handle context building, filtering, classification, and extraction preparation.
"""
from typing import Dict, Any, List, Type, TypeVar, Optional, Callable, Tuple
from pydantic import BaseModel
from core.parser import ParsedDocument, DocumentChunk
from core.config import settings
from core import constants

T = TypeVar('T', bound=BaseModel)


def build_context(chunks: List[DocumentChunk], max_chars: int = None) -> str:
    """
    Pure function: Build extraction context from chunks.
    
    Args:
        chunks: List of document chunks
        max_chars: Maximum characters to include
        
    Returns:
        Concatenated context string
    """
    if max_chars is None:
        max_chars = settings.MAX_CONTEXT_CHARS
    
    context_parts = []
    total_chars = 0
    
    for chunk in chunks:
        chunk_text = chunk.text
        if total_chars + len(chunk_text) > max_chars:
            break
        context_parts.append(chunk_text)
        total_chars += len(chunk_text)
    
    return "\n\n".join(context_parts)


def prepare_extraction_context(
    document: ParsedDocument,
    schema: Type[T],
    theme: str,
    compute_fingerprint: Callable[[str], str],
    check_duplicate: Callable[[str], Optional[Any]],
    filter_and_classify_fn: Callable,
    build_context_fn: Callable,
) -> Dict[str, Any]:
    """
    Pure function: Prepare extraction context (no I/O, no side effects).
    
    This function orchestrates the preparation phase by calling injected
    dependencies. It's pure because all I/O is delegated to the injected functions.
    
    Args:
        document: Parsed document
        schema: Extraction schema
        theme: Extraction theme
        compute_fingerprint: Function to compute doc fingerprint
        check_duplicate: Function to check cache
        filter_and_classify_fn: Function to filter/classify chunks
        build_context_fn: Function to build context string
    
    Returns:
        Dict with extraction context data including:
        - cached: Cached result if duplicate (or None)
        - fingerprint: Document fingerprint
        - relevant_chunks: Filtered and classified chunks
        - context: Built context string
        - schema_fields: List of schema field names
        - filter_stats: Filtering statistics
        - relevance_stats: Classification statistics
        - warnings: List of warning messages
    """
    # Check for duplicates
    fingerprint = compute_fingerprint(document.full_text)
    cached = check_duplicate(fingerprint)
    if cached:
        return {"cached": cached, "fingerprint": fingerprint}
    
    # Extract schema fields
    schema_fields = list(schema.model_fields.keys()) if hasattr(schema, 'model_fields') else []
    
    # Stage 1 & 2: Filter and classify
    relevant_chunks, filter_stats, relevance_stats, warnings = \
        filter_and_classify_fn(document, theme, schema_fields)
    
    # Build context
    context = build_context_fn(relevant_chunks)
    
    return {
        "relevant_chunks": relevant_chunks,
        "context": context,
        "schema_fields": schema_fields,
        "filter_stats": filter_stats,
        "relevance_stats": relevance_stats,
        "warnings": warnings,
        "fingerprint": fingerprint,
        "cached": None
    }


def apply_regex_extraction(
    context: str,
    schema_fields: List[str],
    regex_extractor,
    confidence_threshold: float,
    logger
) -> Dict[str, Any]:
    """
    Pure function: Extract fields using regex patterns.
    
    Args:
        context: Text context to extract from
        schema_fields: List of schema field names
        regex_extractor: Regex extractor instance
        confidence_threshold: Minimum confidence for acceptance
        logger: Logger instance for info messages
        
    Returns:
        Dict of pre-filled fields from regex extraction
    """
    regex_results = regex_extractor.extract_all(context)
    pre_filled = {}
    
    for field_name, result in regex_results.items():
        if result.confidence >= confidence_threshold:
            pre_filled[field_name] = result.value
            logger.info(
                f"  Regex extracted {field_name}: {result.value} "
                f"(conf={result.confidence:.2f})"
            )
    
    return pre_filled


def build_revision_prompts(checker_result, checker) -> List[str]:
    """
    Pure function: Build revision prompts from checker feedback.
    
    Args:
        checker_result: CheckerResult with suggestions
        checker: Checker instance with format_revision_prompt method
        
    Returns:
        List of revision prompt strings
    """
    if not checker_result.suggestions:
        return []
    
    revision_prompt = checker.format_revision_prompt(checker_result)
    return [revision_prompt]
