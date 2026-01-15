"""
Base models and types for document parsing.
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from ..config import settings


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
