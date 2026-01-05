#!/usr/bin/env python3
"""
Content Filter for token optimization.

Removes non-essential sections (affiliations, references, acknowledgments)
from parsed documents to reduce token usage during extraction.
"""

import re
from typing import List, Dict, Any, Set
from dataclasses import dataclass

# Import from sibling module
from .parser import DocumentChunk


@dataclass
class FilterResult:
    """Result of content filtering operation."""
    filtered_chunks: List[DocumentChunk]
    removed_chunks: List[DocumentChunk]
    token_stats: Dict[str, Any]


class ContentFilter:
    """Filters out affiliations, references, and other token-heavy sections."""
    
    # Section patterns to exclude (case-insensitive)
    DEFAULT_EXCLUDE_PATTERNS = [
        r"^affiliations?$",
        r"^author\s*affiliations?$",
        r"^author\s*contributions?$",
        r"^authors?\s*contributions?$",
        r"^references?$",
        r"^bibliography$",
        r"^acknowledgm?ents?$",
        r"^declarations?$",
        r"^funding$",
        r"^funding\s*(statement|information|sources?)?$",
        r"^conflicts?\s*of\s*interests?$",
        r"^competing\s*interests?$",
        r"^disclosure$",
        r"^disclosures?$",
        r"^ethics\s*(statement|approval|declarations?)?$",
        r"^data\s*availability$",
        r"^supplementary\s*(materials?|information)?$",
        r"^supporting\s*information$",
        r"^abbreviations?$",
    ]
    
    # Content patterns that indicate non-essential text
    CONTENT_EXCLUDE_PATTERNS = [
        r"^\d+\.\s*[A-Z][^.]+\.\s*[A-Z]",  # Reference format: "1. Author Name. Title..."
        r"^https?://",  # URLs
        r"^\[\d+\]",  # Citation markers at start of line
    ]
    
    def __init__(
        self,
        exclude_patterns: List[str] = None,
        content_patterns: List[str] = None,
        chars_per_token: float = 4.0,  # Approximate chars per token
    ):
        """
        Initialize the content filter.
        
        Args:
            exclude_patterns: Section header patterns to exclude (regex)
            content_patterns: Content patterns indicating exclusion (regex)
            chars_per_token: Approximate characters per token for estimation
        """
        self.exclude_patterns = [
            re.compile(p, re.IGNORECASE) 
            for p in (exclude_patterns or self.DEFAULT_EXCLUDE_PATTERNS)
        ]
        self.content_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (content_patterns or self.CONTENT_EXCLUDE_PATTERNS)
        ]
        self.chars_per_token = chars_per_token
    
    def _should_exclude_section(self, section: str) -> bool:
        """Check if a section header matches exclusion patterns."""
        if not section:
            return False
        
        section_clean = section.strip()
        for pattern in self.exclude_patterns:
            if pattern.match(section_clean):
                return True
        return False
    
    def _is_reference_content(self, text: str) -> bool:
        """Detect if text content looks like references/citations."""
        lines = text.strip().split('\n')
        if not lines:
            return False
        
        # Check if multiple lines match reference patterns
        ref_like_lines = 0
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if not line:
                continue
            for pattern in self.content_patterns:
                if pattern.match(line):
                    ref_like_lines += 1
                    break
        
        # If more than 50% of checked lines look like references
        return ref_like_lines > len(lines) * 0.5 if lines else False
    
    def _estimate_tokens(self, char_count: int) -> int:
        """Estimate token count from character count."""
        return int(char_count / self.chars_per_token)
    
    def filter_chunks(self, chunks: List[DocumentChunk]) -> FilterResult:
        """
        Remove chunks belonging to excluded sections.
        
        Args:
            chunks: List of document chunks to filter
            
        Returns:
            FilterResult with filtered chunks, removed chunks, and stats
        """
        filtered = []
        removed = []
        
        # Track which sections we're currently in
        in_excluded_section = False
        current_excluded_section = ""
        
        for chunk in chunks:
            # Check if this chunk starts a new section
            if chunk.section:
                if self._should_exclude_section(chunk.section):
                    in_excluded_section = True
                    current_excluded_section = chunk.section
                elif chunk.section.strip():  # Non-empty section that's not excluded
                    in_excluded_section = False
                    current_excluded_section = ""
            
            # Also check subsection
            if chunk.subsection and self._should_exclude_section(chunk.subsection):
                in_excluded_section = True
                current_excluded_section = chunk.subsection
            
            # Check content patterns for reference-like content
            is_reference_content = self._is_reference_content(chunk.text)
            
            if in_excluded_section or is_reference_content:
                removed.append(chunk)
            else:
                filtered.append(chunk)
        
        # Calculate token statistics
        original_chars = sum(len(c.text) for c in chunks)
        filtered_chars = sum(len(c.text) for c in filtered)
        removed_chars = sum(len(c.text) for c in removed)
        
        token_stats = {
            "original_chunks": len(chunks),
            "filtered_chunks": len(filtered),
            "removed_chunks": len(removed),
            "original_chars": original_chars,
            "filtered_chars": filtered_chars,
            "removed_chars": removed_chars,
            "estimated_original_tokens": self._estimate_tokens(original_chars),
            "estimated_filtered_tokens": self._estimate_tokens(filtered_chars),
            "estimated_tokens_saved": self._estimate_tokens(removed_chars),
            "reduction_percentage": round(removed_chars / original_chars * 100, 1) if original_chars > 0 else 0,
        }
        
        return FilterResult(
            filtered_chunks=filtered,
            removed_chunks=removed,
            token_stats=token_stats,
        )
    
    def filter_text(self, full_text: str) -> tuple[str, Dict[str, Any]]:
        """
        Filter raw text by removing excluded sections.
        
        Useful when chunks aren't available but full markdown text is.
        
        Args:
            full_text: Full document text (typically markdown)
            
        Returns:
            Tuple of (filtered_text, stats_dict)
        """
        lines = full_text.split('\n')
        filtered_lines = []
        removed_lines = []
        
        in_excluded_section = False
        
        for line in lines:
            # Check for section headers (markdown format)
            header_match = re.match(r'^#{1,6}\s+(.+)$', line)
            if header_match:
                header_text = header_match.group(1)
                if self._should_exclude_section(header_text):
                    in_excluded_section = True
                else:
                    in_excluded_section = False
            
            if in_excluded_section:
                removed_lines.append(line)
            else:
                filtered_lines.append(line)
        
        filtered_text = '\n'.join(filtered_lines)
        
        stats = {
            "original_lines": len(lines),
            "filtered_lines": len(filtered_lines),
            "removed_lines": len(removed_lines),
            "original_chars": len(full_text),
            "filtered_chars": len(filtered_text),
            "reduction_percentage": round((len(full_text) - len(filtered_text)) / len(full_text) * 100, 1) if full_text else 0,
        }
        
        return filtered_text, stats


if __name__ == "__main__":
    # Test with sample chunks
    test_chunks = [
        DocumentChunk(text="Background: This study investigates...", section="Abstract"),
        DocumentChunk(text="We enrolled 42 patients...", section="Methods"),
        DocumentChunk(text="Dr. Smith is affiliated with...", section="Author Affiliations"),
        DocumentChunk(text="1. Smith J, et al. J Med. 2020;...", section="References"),
        DocumentChunk(text="The treatment showed 85% efficacy...", section="Results"),
    ]
    
    filter = ContentFilter()
    result = filter.filter_chunks(test_chunks)
    
    print(f"Original: {result.token_stats['original_chunks']} chunks")
    print(f"Filtered: {result.token_stats['filtered_chunks']} chunks")
    print(f"Removed: {result.token_stats['removed_chunks']} chunks")
    print(f"Token savings: ~{result.token_stats['estimated_tokens_saved']} tokens ({result.token_stats['reduction_percentage']}%)")
