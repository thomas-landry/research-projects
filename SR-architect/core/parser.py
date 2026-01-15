#!/usr/bin/env python3
"""
PDF Parser using IBM Docling for academic document parsing.

Handles multi-column layouts, table extraction, and hierarchical chunking.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

from .config import settings
from .text_splitter import split_text_into_chunks
from .utils import get_logger


try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


class DocumentChunk(BaseModel):
    """Represents a chunk of parsed document text with metadata."""
    text: str
    section: str = ""
    subsection: str = ""
    chunk_type: str = "text"  # text, table, figure
    page_number: int = 0
    source_file: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ParsedDocument(BaseModel):
    """Represents a fully parsed academic document."""
    filename: str
    chunks: List[DocumentChunk] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    full_text: str = ""
    tables: List[Dict[str, Any]] = Field(default_factory=list)  # Extracted tables
    
    @property
    def abstract(self) -> str:
        """Extract abstract text."""
        for chunk in self.chunks:
            section = chunk.section or ""
            if "abstract" in section.lower():
                return chunk.text or ""
        return ""
    
    @property
    def methods_text(self) -> str:
        """Extract methods section text."""
        method_chunks = []
        for chunk in self.chunks:
            section_lower = (chunk.section or "").lower()
            if any(term in section_lower for term in ["method", "material", "patient", "study design"]):
                method_chunks.append(chunk.text or "")
        return "\n\n".join(method_chunks)
    
    @property
    def results_text(self) -> str:
        """Extract results section text."""
        result_chunks = []
        for chunk in self.chunks:
            section_lower = (chunk.section or "").lower()
            if "result" in section_lower or "finding" in section_lower:
                result_chunks.append(chunk.text or "")
        return "\n\n".join(result_chunks)
    
    def get_extraction_context(self, max_chars: int = settings.PARSER_EXTRACTION_CONTEXT_MAX_CHARS) -> str:
        """Get the most relevant text for extraction (Abstract + Methods + Results)."""
        context_parts = []
        
        if self.abstract:
            context_parts.append(f"ABSTRACT:\n{self.abstract}")
        
        methods = self.methods_text
        if methods:
            context_parts.append(f"METHODS:\n{methods[:5000]}")
        
        results = self.results_text
        if results:
            context_parts.append(f"RESULTS:\n{results[:5000]}")
        
        context = "\n\n".join(context_parts)
        
        # Fallback to full text if sections not found
        if len(context) < 500:
            context = self.full_text[:max_chars]
        
        return context[:max_chars]


class DocumentParser:
    """Parse academic PDFs using Docling with hierarchical chunking."""
    
    # Simplified parser chain per plan.md: Docling → PyMuPDF only
    # pdfplumber removed as Docling+PyMuPDF handles >95% of cases
    PARSER_CHAIN = ["docling", "pymupdf"]
    
    def __init__(
        self, 
        use_ocr: bool = False, 
        cache_dir: str = ".cache/parsed_docs",
        use_imrad: bool = False,
        extract_tables: bool = True,
        max_cache_size: int = None,
    ):
        """
        Initialize the parser.
        
        Args:
            use_ocr: Whether to use OCR for scanned documents
            cache_dir: Directory to store parsed document objects
            use_imrad: Whether to apply IMRAD section parsing
            extract_tables: Whether to extract tables separately
            max_cache_size: Maximum number of cached parsed documents (LRU eviction)
        """
        self.use_ocr = use_ocr
        self.cache_dir = Path(cache_dir)
        self.use_imrad = use_imrad
        self.extract_tables = extract_tables
        if max_cache_size is None:
            max_cache_size = settings.PARSER_CACHE_MAX_SIZE
        self.max_cache_size = max_cache_size
        self.logger = get_logger("DocumentParser")
        self._converter = None
        self._chunker = None
        self._imrad_parser = None
        
        # Ensure cache directory exists
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Evict old cache entries if over limit
        self._evict_cache_if_needed()
        
        # Lazy-load IMRAD parser if enabled
        if self.use_imrad:
            try:
                from core.imrad_parser import IMRADParser
                self._imrad_parser = IMRADParser()
            except ImportError:
                self.logger.warning("IMRADParser not available")
    
    def _evict_cache_if_needed(self):
        """
        Evict oldest cache entries if over max_cache_size limit.
        Uses LRU eviction based on file modification time.
        (MEM-001 fix)
        """
        if not self.cache_dir.exists():
            return
            
        cache_files = list(self.cache_dir.glob("*.json"))
        if len(cache_files) <= self.max_cache_size:
            return
            
        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda f: f.stat().st_mtime)
        
        # Evict oldest entries
        to_evict = len(cache_files) - self.max_cache_size
        for cache_file in cache_files[:to_evict]:
            try:
                cache_file.unlink()
                self.logger.debug(f"Evicted cache entry: {cache_file.name}")
            except Exception as e:
                self.logger.warning(f"Failed to evict cache {cache_file}: {e}")
    
    def _get_cache_path(self, file_path: Path) -> Path:
        """Generate a unique cache path based on file content hash."""
        # Use file path + modification time as cache key
        stat = file_path.stat()
        key = f"{str(file_path)}_{stat.st_mtime}_{stat.st_size}"
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.json"
        
    def _load_cached(self, file_path: Path) -> Optional[ParsedDocument]:
        """Try to load parsed document from cache (JSON)."""
        cache_path = self._get_cache_path(file_path)
        if cache_path.exists():
            try:
                self.logger.debug(f"Loading cached parse for {file_path.name}")
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return ParsedDocument(**data)
            except Exception as e:
                self.logger.warning(f"Cache load failed for {file_path}: {e}")
        return None
        
    def _save_to_cache(self, doc: ParsedDocument, file_path: Path):
        """Save parsed document to cache as JSON."""
        try:
            cache_path = self._get_cache_path(file_path)
            # Use atomic write via temp file
            temp_path = cache_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(doc.model_dump(), f, indent=2)
            temp_path.replace(cache_path)
            self.logger.debug(f"Saved parse for {file_path.name} to cache")
        except Exception as e:
            self.logger.error(f"Cache save failed for {file_path}: {e}")

    def _ensure_docling(self):
        """Lazy-load Docling to avoid import errors if not installed."""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
                from docling.chunking import HierarchicalChunker
                
                self._converter = DocumentConverter()
                self._chunker = HierarchicalChunker()
            except ImportError:
                self.logger.warning("Docling not installed. Falling back to PyMuPDF.")
                raise ImportError(
                    "Docling not installed. Install with: pip install docling"
                )
    
    def parse_pdf(self, pdf_path: str) -> ParsedDocument:
        """Parse a single PDF file."""
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
        # Check cache first
        cached_doc = self._load_cached(path)
        if cached_doc:
            return cached_doc
        
        parsed_doc = None
        try:
            # Try Docling first
            self._ensure_docling()
            
            # Convert PDF
            self.logger.info(f"Parsing {path.name} using Docling...")
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
                self.logger.warning(f"Hierarchical chunking failed, using simple splitting: {e}")
                chunks = self._simple_chunk(full_text, path.name)
            
            parsed_doc = ParsedDocument(
                filename=path.name,
                chunks=chunks,
                full_text=full_text,
                metadata={
                    "path": str(path),
                    "num_chunks": len(chunks),
                    "parser": "docling"
                }
            )
            
        except (ImportError, Exception) as e:
            self.logger.warning(f"Docling parsing failed or unavailable: {e}. Falling back to PyMuPDF.")
            try:
                parsed_doc = self._parse_pdf_pymupdf(path)
                self.logger.info(f"Successfully parsed {path.name} using PyMuPDF fallback")
            except (ImportError, Exception) as e2:
                # NOTE: Simplified fallback chain per plan.md (Docling → PyMuPDF only)
                # pdfplumber fallback removed as Docling+PyMuPDF handles >95% of cases
                self.logger.error(f"All parsers failed for {path.name}: Docling={e}, PyMuPDF={e2}")
                raise RuntimeError(f"Failed to parse {pdf_path}: no available parser succeeded")
        
        # Post-processing: IMRAD parsing
        if parsed_doc and self._imrad_parser and self.use_imrad:
            try:
                imrad_sections = self._imrad_parser.parse(parsed_doc.full_text)
                parsed_doc.metadata["imrad_sections"] = imrad_sections
                self.logger.debug("Applied IMRAD section parsing")
            except Exception as e:
                self.logger.warning(f"IMRAD parsing failed: {e}")
            
        # Save to cache
        if parsed_doc:
            self._save_to_cache(parsed_doc, path)
        return parsed_doc
    
    def _parse_pdf_pdfplumber(self, path: Path) -> ParsedDocument:
        """Tertiary fallback parser using pdfplumber."""
        if pdfplumber is None:
            raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")
            
        self.logger.info(f"Parsing {path.name} using pdfplumber (tertiary fallback)...")
        
        full_text = ""
        chunks = []
        tables = []
        
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Extract text
                text = page.extract_text() or ""
                full_text += text + "\n\n"
                
                # Chunk the page text
                page_chunks = split_text_into_chunks(text, chunk_size=settings.PARSER_CHUNK_SIZE, chunk_overlap=settings.PARSER_CHUNK_OVERLAP)
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
                            table_text = self._table_to_markdown(table)
                            if table_text:
                                chunks.append(DocumentChunk(
                                    text=table_text,
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
                "page_count": len(pdf.pages) if 'pdf' in dir() else 0,
            }
        )
    
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

    def _parse_pdf_pymupdf(self, path: Path) -> ParsedDocument:
        """Fallback PDF parser using PyMuPDF (fitz)."""
        if fitz is None:
            self.logger.error("PyMuPDF not installed")
            raise ImportError("PyMuPDF not installed. Run: pip install pymupdf")
            
        self.logger.info(f"Parsing {path.name} using PyMuPDF (fallback)...")
        pdf_document = fitz.open(path)
        full_text = ""
        chunks = []
        
        for i, page in enumerate(pdf_document):
            text = page.get_text()
            full_text += text + "\n\n"
            
            # Robust chunking for each page
            page_chunks = split_text_into_chunks(text, chunk_size=settings.PARSER_CHUNK_SIZE, chunk_overlap=settings.PARSER_CHUNK_OVERLAP)
            
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
                "page_count": len(doc)
            }
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
    
    def parse_file(self, file_path: str) -> ParsedDocument:
        """Parse a file based on its extension."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        ext = path.suffix.lower()
        
        if ext == ".pdf":
            return self.parse_pdf(file_path)
        elif ext == ".txt":
            return self._parse_txt(path)
            
        raise ValueError(f"Unsupported file extension: {ext}")

    def _parse_txt(self, path: Path) -> ParsedDocument:
        """Parse a simple text file."""
        self.logger.info(f"Parsing text file: {path.name}")
        full_text = path.read_text(encoding="utf-8")
        chunks = self._simple_chunk(full_text, path.name)
        
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


if __name__ == "__main__":
    # Test block
    from core.utils import setup_logging
    setup_logging()
    
    parser = DocumentParser()
    print("Parser initialized. NO PICKLE enforced.")
