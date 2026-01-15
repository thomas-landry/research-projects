"""
Fallback parser implementations using PyMuPDF and PDFPlumber.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

from ..config import settings
from ..utils import get_logger
from ..text_splitter import split_text_into_chunks
from .base import ParsedDocument, DocumentChunk

logger = get_logger("FallbackParsers")


def chunk_text(text: str) -> List[str]:
    """Split text into chunks using configured size and overlap."""
    return split_text_into_chunks(
        text, 
        chunk_size=settings.PARSER_CHUNK_SIZE, 
        chunk_overlap=settings.PARSER_CHUNK_OVERLAP
    )


def simple_chunk(text: str, filename: str, chunk_size: Optional[int] = None) -> List[DocumentChunk]:
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


class PyMuPDFParser:
    """Fallback PDF parser using PyMuPDF (fitz)."""
    
    def parse(self, path: Path) -> ParsedDocument:
        if fitz is None:
            logger.error("PyMuPDF not installed")
            raise ImportError("PyMuPDF not installed. Run: pip install pymupdf")
            
        logger.info(f"Parsing {path.name} using PyMuPDF (fallback)...")
        pdf_document = fitz.open(path)
        full_text = ""
        chunks = []
        
        for i, page in enumerate(pdf_document):
            text = page.get_text()
            full_text += text + "\n\n"
            
            # Robust chunking for each page
            page_chunks = chunk_text(text)
            
            for chunk in page_chunks:
                chunks.append(DocumentChunk(
                    text=chunk,
                    section="",
                    chunk_type="text",
                    page_number=i + 1,
                    source_file=path.name,
                ))
        
        pdf_document.close()
        return ParsedDocument(
            filename=path.name,
            chunks=chunks,
            full_text=full_text,
            metadata={
                "path": str(path),
                "num_chunks": len(chunks),
                "parser": "pymupdf",
                # "page_count": len(pdf_document) # pdf_document is closed
            }
        )


class PDFPlumberParser:
    """Tertiary fallback parser using pdfplumber."""
    
    def __init__(self, extract_tables: bool = True):
        self.extract_tables = extract_tables
        
    def _table_to_markdown(self, table: List[List]) -> str:
        """Convert pdfplumber table to markdown format."""
        if not table or not table[0]:
            return ""
        
        lines = []
        # Header row
        header = [str(cell) if cell else "" for cell in table[0]]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        
        # Data rows
        for row in table[1:]:
            cells = [str(cell) if cell else "" for cell in row]
            # Pad if needed
            while len(cells) < len(header):
                cells.append("")
            lines.append("| " + " | ".join(cells[:len(header)]) + " |")
        
        return "\n".join(lines)

    def parse(self, path: Path) -> ParsedDocument:
        if pdfplumber is None:
            raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")
            
        logger.info(f"Parsing {path.name} using pdfplumber (tertiary fallback)...")
        
        full_text = ""
        chunks = []
        tables = []
        
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Extract text
                text = page.extract_text() or ""
                full_text += text + "\n\n"
                
                # Chunk the page text
                page_chunks = chunk_text(text)
                for chunk_text in page_chunks:
                    chunks.append(DocumentChunk(
                        text=chunk_text,
                        section=f"Page {i+1}",
                        page_number=i+1,
                        source_file=path.name
                    ))
                
                # Extract tables if enabled
                if self.extract_tables:
                    page_tables = page.extract_tables()
                    for j, table in enumerate(page_tables or []):
                        if table:
                            tables.append({
                                "page": i + 1,
                                "table_index": j,
                                "data": table,
                            })
                            # Also add table as chunk
                            table_markdown = self._table_to_markdown(table)
                            if table_markdown:
                                chunks.append(DocumentChunk(
                                    text=table_markdown,
                                    section=f"Table {len(tables)}",
                                    chunk_type="table",
                                    page_number=i+1,
                                    source_file=path.name
                                ))
        
        return ParsedDocument(
            filename=path.name,
            chunks=chunks,
            full_text=full_text,
            tables=tables,
            metadata={
                "path": str(path),
                "num_chunks": len(chunks),
                "num_tables": len(tables),
                "parser": "pdfplumber",
            }
        )


class TextParser:
    """Parser for simple text files."""
    
    def parse(self, path: Path) -> ParsedDocument:
        logger.info(f"Parsing text file: {path.name}")
        try:
            full_text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback for other encodings if needed
            full_text = path.read_text(encoding="latin-1")
            
        chunks = simple_chunk(full_text, path.name)
        
        return ParsedDocument(
            filename=path.name,
            chunks=chunks,
            full_text=full_text,
            metadata={
                "path": str(path),
                "num_chunks": len(chunks),
                "parser": "text"
            }
        )
