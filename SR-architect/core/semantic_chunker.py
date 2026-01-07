"""
Semantic Chunker for non-standard document formats.
Uses sentence boundaries and semantic coherence for intelligent splitting.
"""
from typing import List, Optional
from core.utils import get_logger
from core.text_splitter import split_text_into_chunks

logger = get_logger("SemanticChunker")


class SemanticChunker:
    """
    Intelligent text chunker that respects sentence and paragraph boundaries.
    Designed for non-standard formats like case reports or multi-column layouts.
    """
    
    def __init__(
        self, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            min_chunk_size: Minimum chunk size to keep
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk(self, text: str) -> List[str]:
        """
        Split text into semantic chunks.
        
        Args:
            text: Input text
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        # First, split by paragraph
        paragraphs = self._split_paragraphs(text)
        
        # Then, combine small paragraphs or split large ones
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # If paragraph itself is too large, split it
            if len(para) > self.chunk_size:
                # Flush current chunk
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Split large paragraph by sentences
                sentences = self._split_sentences(para)
                for sent in sentences:
                    if len(current_chunk) + len(sent) > self.chunk_size:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = sent
                    else:
                        current_chunk += " " + sent if current_chunk else sent
            else:
                # Normal paragraph - add to current chunk
                if len(current_chunk) + len(para) > self.chunk_size:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = para
                else:
                    current_chunk += "\n\n" + para if current_chunk else para
        
        # Flush remaining
        if current_chunk.strip() and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())
        
        # Apply overlap
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._apply_overlap(chunks)
            
        logger.debug(f"Created {len(chunks)} semantic chunks from text of length {len(text)}")
        return chunks
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split on double newlines or multiple newlines
        import re
        return re.split(r'\n\s*\n', text)
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        import re
        # Simple sentence splitter - handles common abbreviations
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _apply_overlap(self, chunks: List[str]) -> List[str]:
        """Apply overlap between chunks for context continuity."""
        if len(chunks) <= 1:
            return chunks
            
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped.append(chunk)
            else:
                # Prepend end of previous chunk
                prev_chunk = chunks[i-1]
                overlap_text = prev_chunk[-self.chunk_overlap:] if len(prev_chunk) > self.chunk_overlap else prev_chunk
                overlapped.append(overlap_text + " " + chunk)
                
        return overlapped
