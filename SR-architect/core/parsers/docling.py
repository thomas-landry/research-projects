"""
Docling parser implementation for handling PDF to markdown conversion and hierarchical chunking.
"""
from pathlib import Path
from typing import List, Optional

from ..config import settings
from ..utils import get_logger
from ..text_splitter import split_text_into_chunks
from .base import ParsedDocument, DocumentChunk

logger = get_logger("DoclingParser")

class DoclingParser:
    """Handles parsing using IBM Docling."""
    
    def __init__(self):
        self._converter = None
        self._chunker = None
        
    def _ensure_docling(self):
        """Lazy-load Docling to avoid import errors if not installed."""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
                from docling.chunking import HierarchicalChunker
                
                self._converter = DocumentConverter()
                self._chunker = HierarchicalChunker()
            except ImportError:
                logger.warning("Docling not installed.")
                raise ImportError(
                    "Docling not installed. Install with: pip install docling"
                )

    def _simple_chunk(self, text: str, filename: str, chunk_size: Optional[int] = None) -> List[DocumentChunk]:
        """Simple fallback chunking."""
        if not text:
            return []
            
        if chunk_size is None:
            chunk_size = settings.PARSER_CHUNK_SIZE

        text_chunks = split_text_into_chunks(text, chunk_size=chunk_size, chunk_overlap=settings.PARSER_CHUNK_OVERLAP)
        chunks = []
        
        for i, chunk_text in enumerate(text_chunks):
            chunks.append(DocumentChunk(
                text=chunk_text,
                section=f"Chunk {i+1}",
                source_file=filename,
            ))
        
        return chunks

    def parse(self, path: Path) -> ParsedDocument:
        """Parse a PDF file using Docling."""
        self._ensure_docling()
        
        # Convert PDF
        logger.info(f"Parsing {path.name} using Docling...")
        result = self._converter.convert(str(path))
        doc = result.document
        
        # Extract full text
        full_text = doc.export_to_markdown()
        
        # Create hierarchical chunks
        chunks = []
        try:
            docling_chunks = list(self._chunker.chunk(doc))
            for chunk in docling_chunks:
                section = ""
                subsection = ""
                
                if hasattr(chunk, 'meta') and chunk.meta:
                    headings = getattr(chunk.meta, 'headings', None) or []
                    section = headings[0] if isinstance(headings, list) and len(headings) > 0 else ""
                    subsection = headings[1] if isinstance(headings, list) and len(headings) > 1 else ""
                
                text = chunk.text if hasattr(chunk, 'text') else str(chunk)
                chunk_type = "table" if "|" in text and "---" in text else "text"
                
                chunks.append(DocumentChunk(
                    text=text,
                    section=section,
                    subsection=subsection,
                    chunk_type=chunk_type,
                    page_number=getattr(chunk, 'page', 0),
                    source_file=path.name,
                ))
        except Exception as e:
            logger.warning(f"Hierarchical chunking failed, using simple splitting: {e}")
            chunks = self._simple_chunk(full_text, path.name)
        
        return ParsedDocument(
            filename=path.name,
            chunks=chunks,
            full_text=full_text,
            metadata={
                "path": str(path),
                "num_chunks": len(chunks),
                "parser": "docling"
            }
        )
