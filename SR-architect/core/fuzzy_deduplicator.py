"""
Fuzzy Deduplicator for removing near-duplicate text blocks.
Uses MinHash/RapidFuzz for efficient similarity detection.
"""
import hashlib
from typing import List, Tuple, Set
from core.utils import get_logger

logger = get_logger("FuzzyDeduplicator")

# Try to import rapidfuzz, fall back to difflib if not available
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    from difflib import SequenceMatcher
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not installed, using difflib (slower)")


class FuzzyDeduplicator:
    """
    Remove near-duplicate text blocks from a list of chunks.
    Uses fuzzy string matching to identify >90% similar blocks.
    """
    
    def __init__(self, similarity_threshold: float = 0.90):
        """
        Initialize deduplicator.
        
        Args:
            similarity_threshold: Minimum similarity (0.0-1.0) to consider duplicates
        """
        self.threshold = similarity_threshold
        self._seen_hashes: Set[str] = set()
    
    def _quick_hash(self, text: str) -> str:
        """Generate a quick hash for exact duplicate detection."""
        normalized = text.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        if RAPIDFUZZ_AVAILABLE:
            return fuzz.ratio(text1, text2) / 100.0
        else:
            return SequenceMatcher(None, text1, text2).ratio()
    
    def deduplicate(self, chunks: List[str]) -> List[str]:
        """
        Remove near-duplicate chunks.
        
        Args:
            chunks: List of text strings
            
        Returns:
            Deduplicated list of text strings
        """
        if not chunks:
            return []
            
        unique_chunks: List[str] = []
        self._seen_hashes = set()
        
        for chunk in chunks:
            # Skip empty chunks
            if not chunk.strip():
                continue
                
            # Quick exact duplicate check
            chunk_hash = self._quick_hash(chunk)
            if chunk_hash in self._seen_hashes:
                logger.debug(f"Skipping exact duplicate (hash: {chunk_hash[:8]})")
                continue
            
            # Fuzzy duplicate check against existing unique chunks
            is_duplicate = False
            for existing in unique_chunks:
                sim = self._similarity(chunk.strip().lower(), existing.strip().lower())
                if sim >= self.threshold:
                    logger.debug(f"Skipping fuzzy duplicate (similarity: {sim:.2f})")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_chunks.append(chunk)
                self._seen_hashes.add(chunk_hash)
                
        removed = len(chunks) - len(unique_chunks)
        if removed > 0:
            logger.info(f"Deduplicated: removed {removed} similar blocks ({len(unique_chunks)} remaining)")
            
        return unique_chunks
    
    def deduplicate_with_indices(self, chunks: List[str]) -> Tuple[List[str], List[int]]:
        """
        Remove duplicates and return original indices of kept chunks.
        
        Returns:
            Tuple of (deduplicated chunks, original indices)
        """
        if not chunks:
            return [], []
            
        unique_chunks: List[str] = []
        kept_indices: List[int] = []
        self._seen_hashes = set()
        
        for idx, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
                
            chunk_hash = self._quick_hash(chunk)
            if chunk_hash in self._seen_hashes:
                continue
            
            is_duplicate = False
            for existing in unique_chunks:
                sim = self._similarity(chunk.strip().lower(), existing.strip().lower())
                if sim >= self.threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_chunks.append(chunk)
                kept_indices.append(idx)
                self._seen_hashes.add(chunk_hash)
                
        return unique_chunks, kept_indices
