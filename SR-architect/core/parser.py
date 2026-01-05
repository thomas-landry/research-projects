#!/usr/bin/env python3
"""
PDF Parser using IBM Docling for academic document parsing.

Handles multi-column layouts, table extraction, and hierarchical chunking.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


@dataclass
class DocumentChunk:
    """Represents a chunk of parsed document text with metadata."""
    text: str
    section: str = ""
    subsection: str = ""
    chunk_type: str = "text"  # text, table, figure
    page_number: int = 0
    source_file: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "section": self.section,
            "subsection": self.subsection,
            "chunk_type": self.chunk_type,
            "page_number": self.page_number,
            "source_file": self.source_file,
        }


@dataclass 
class ParsedDocument:
    """Represents a fully parsed academic document."""
    filename: str
    chunks: List[DocumentChunk] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    full_text: str = ""
    
    @property
    def abstract(self) -> str:
        """Extract abstract text."""
        for chunk in self.chunks:
            # Guard against None section or text
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
    
    def get_extraction_context(self, max_chars: int = 15000) -> str:
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
    
    def __init__(self, use_ocr: bool = False):
        """
        Initialize the parser.
        
        Args:
            use_ocr: Whether to use OCR for scanned documents
        """
        self.use_ocr = use_ocr
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
                raise ImportError(
                    "Docling not installed. Install with: pip install docling\n"
                    "Note: Docling requires Python 3.10+ and may need additional dependencies."
                )
    
    def parse_pdf(self, pdf_path: str) -> ParsedDocument:
        """
        Parse a single PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            ParsedDocument with chunks and metadata
        """
        self._ensure_docling()
        
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Convert PDF
        result = self._converter.convert(str(path))
        doc = result.document
        
        # Extract full text
        full_text = doc.export_to_markdown()
        
        # Create hierarchical chunks
        chunks = []
        try:
            docling_chunks = list(self._chunker.chunk(doc))
            
            for i, chunk in enumerate(docling_chunks):
                # Extract section info from chunk metadata
                section = ""
                subsection = ""
                
                if hasattr(chunk, 'meta') and chunk.meta:
                    headings = chunk.meta.get('headings', [])
                    # Safely access headings with explicit bounds checking
                    section = headings[0] if isinstance(headings, list) and len(headings) > 0 else ""
                    subsection = headings[1] if isinstance(headings, list) and len(headings) > 1 else ""
                
                # Determine chunk type
                chunk_type = "text"
                text = chunk.text if hasattr(chunk, 'text') else str(chunk)
                
                if "|" in text and "---" in text:
                    chunk_type = "table"
                
                chunks.append(DocumentChunk(
                    text=text,
                    section=section,
                    subsection=subsection,
                    chunk_type=chunk_type,
                    page_number=getattr(chunk, 'page', 0),
                    source_file=path.name,
                ))
        except Exception as e:
            # Fallback: simple text splitting
            print(f"Warning: Hierarchical chunking failed, using simple splitting: {e}")
            chunks = self._simple_chunk(full_text, path.name)
        
        return ParsedDocument(
            filename=path.name,
            chunks=chunks,
            full_text=full_text,
            metadata={
                "path": str(path),
                "num_chunks": len(chunks),
            }
        )
    
    def _simple_chunk(self, text: str, filename: str, chunk_size: int = 1000) -> List[DocumentChunk]:
        """Simple fallback chunking by paragraphs."""
        chunks = []
        paragraphs = text.split("\n\n")
        
        current_chunk = ""
        current_section = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Detect section headers (simple heuristic)
            if para.isupper() or (len(para) < 50 and para.endswith(":")):
                current_section = para
                continue
            
            if len(current_chunk) + len(para) > chunk_size:
                if current_chunk:
                    chunks.append(DocumentChunk(
                        text=current_chunk,
                        section=current_section,
                        source_file=filename,
                    ))
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(DocumentChunk(
                text=current_chunk,
                section=current_section,
                source_file=filename,
            ))
        
        return chunks
    
    def parse_file(self, file_path: str) -> ParsedDocument:
        """
        Parse a file based on its extension.
        
        Supported: .pdf, .html, .htm, .md, .markdown, .txt
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        ext = path.suffix.lower()
        
        if ext == ".pdf":
            return self.parse_pdf(file_path)
        elif ext in [".html", ".htm"]:
            return self.parse_html(file_path)
        elif ext in [".md", ".markdown"]:
            return self.parse_markdown(file_path)
        elif ext == ".txt":
            return self.parse_text(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    def parse_html(self, html_path: str) -> ParsedDocument:
        """Parse an HTML file, extracting sections from headers."""
        if BeautifulSoup is None:
            raise ImportError("BeautifulSoup4 not installed. Run: pip install beautifulsoup4")
            
        path = Path(html_path)
        with open(path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
            
        # Remove scripts and styles
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        chunks = []
        current_section = "Introduction"
        current_subsection = ""
        
        # Iterate over elements to build chunks
        # This is a simplified heuristic: H1/H2 start sections, P adds text
        elements = soup.find_all(['h1', 'h2', 'h3', 'p', 'table'])
        
        for el in elements:
            text = el.get_text(separator=" ", strip=True)
            if not text:
                continue
                
            if el.name in ['h1', 'h2']:
                current_section = text
                current_subsection = ""
            elif el.name == 'h3':
                current_subsection = text
            elif el.name == 'table':
                # Basic table text extraction
                chunks.append(DocumentChunk(
                    text=text,
                    section=current_section,
                    subsection=current_subsection,
                    chunk_type="table",
                    source_file=path.name
                ))
            else: # p
                # paragraphs
                chunks.append(DocumentChunk(
                    text=text,
                    section=current_section,
                    subsection=current_subsection,
                    source_file=path.name
                ))
                
        # Consolidate tiny chunks? (Optional optimization)
        
        full_text = soup.get_text(separator="\n\n")
        
        return ParsedDocument(
            filename=path.name,
            chunks=chunks,
            full_text=full_text,
            metadata={"source": "html"}
        )

    def parse_markdown(self, md_path: str) -> ParsedDocument:
        """Parse a Markdown file using header structure."""
        import re
        path = Path(md_path)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
            
        lines = text.split('\n')
        chunks = []
        current_section = "Introduction"
        current_subsection = ""
        current_text = []
        
        for line in lines:
            # Check for headers
            if line.startswith('# '):
                # Save previous chunk if exists
                if current_text:
                    chunks.append(DocumentChunk(
                        text="\n".join(current_text).strip(),
                        section=current_section,
                        subsection=current_subsection,
                        source_file=path.name
                    ))
                    current_text = []
                current_section = line[2:].strip()
                current_subsection = ""
                
            elif line.startswith('## '):
                if current_text:
                    chunks.append(DocumentChunk(
                        text="\n".join(current_text).strip(),
                        section=current_section,
                        subsection=current_subsection,
                        source_file=path.name
                    ))
                    current_text = []
                current_subsection = line[3:].strip()
                
            elif line.strip():
                current_text.append(line)
        
        # Last chunk
        if current_text:
             chunks.append(DocumentChunk(
                text="\n".join(current_text).strip(),
                section=current_section,
                subsection=current_subsection,
                source_file=path.name
            ))
            
        return ParsedDocument(
            filename=path.name,
            chunks=chunks,
            full_text=text,
            metadata={"source": "markdown"}
        )

    def parse_text(self, txt_path: str) -> ParsedDocument:
        """Parse a plain text file."""
        path = Path(txt_path)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
            
        chunks = self._simple_chunk(text, path.name)
        
        return ParsedDocument(
            filename=path.name,
            chunks=chunks,
            full_text=text,
            metadata={"source": "text"}
        )

    def parse_folder(self, folder_path: str, extensions: List[str] = None) -> List[ParsedDocument]:
        """
        Parse all supported files in a folder.
        
        Args:
            folder_path: Path to folder
            extensions: List of extensions to include (e.g. ['.pdf', '.html'])
                        Default: all supported
            
        Returns:
            List of ParsedDocument objects
        """
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
            
        if extensions is None:
            extensions = [".pdf", ".html", ".htm", ".md", ".markdown", ".txt"]
            
        documents = []
        
        for file_path in folder.iterdir():
            if file_path.suffix.lower() in extensions:
                try:
                    doc = self.parse_file(str(file_path))
                    documents.append(doc)
                except Exception as e:
                    print(f"Error parsing {file_path.name}: {e}")
        
        return documents


if __name__ == "__main__":
    # Test parsing
    import sys
    
    if len(sys.argv) > 1:
        parser = DocumentParser()
        doc = parser.parse_pdf(sys.argv[1])
        
        print(f"Parsed: {doc.filename}")
        print(f"Chunks: {len(doc.chunks)}")
        print(f"Abstract length: {len(doc.abstract)}")
        print(f"\nExtraction context preview:")
        print(doc.get_extraction_context()[:500])
