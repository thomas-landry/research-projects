#!/usr/bin/env python3
"""
Section Locator Agent - Identifies specific sections within a document.

This agent acts as a "Librarian" who knows exactly where to look for specific information,
preventing the extractor from searching the whole document and hallucinating.
"""

import sys
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.parser import ParsedDocument, DocumentChunk

class SectionLocation(BaseModel):
    """Location of a specific topic within the document."""
    section_name: str = Field(description="Name of the section containing the info")
    relevant_text: str = Field(description="The exact text or paragraph containing the info")
    confidence: float = Field(description="Confidence that this is the right section (0-1)")
    page_number: int = Field(description="Page number where this section starts")

class SectionLocatorAgent:
    """
    Finds the exact section containing target information.
    """
    
    LOCATOR_PROMPT = """You are a navigation assistant for academic papers.
    
    Your goal is to find WHERE in the document specific information is located.
    Do not extract the final data, just find the relevant section and text.
    
    QUERY: {query}
    
    DOCUMENT STRUCTURE:
    {structure}
    
    Return the best matching section.
    """
    
    def __init__(self, provider: str = "openrouter", model: Optional[str] = None):
        self.provider = provider
        self.model = model or "gpt-4o-mini" # Fast model is sufficient for locating
        self._client = None
        
        from core.utils import get_logger
        self.logger = get_logger("SectionLocatorAgent")
        
    @property
    def client(self):
        if self._client is not None:
            return self._client
        from core.utils import get_llm_client
        self._client = get_llm_client(self.provider)
        return self._client

    def locate_section(self, doc: ParsedDocument, query: str) -> SectionLocation:
        """
        Find the section containing information about 'query'.
        """
        # Create a condensed structure map
        structure = []
        for chunk in doc.chunks:
            if chunk.section and chunk.section not in [s['section'] for s in structure]:
                structure.append({
                    "section": chunk.section,
                    "preview": chunk.text[:100] + "..."
                })
                
        structure_str = "\n".join([f"- {s['section']}: {s['preview']}" for s in structure])
        
        prompt = self.LOCATOR_PROMPT.format(query=query, structure=structure_str)
        
        try:
            result = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_model=SectionLocation,
            )
            return result
        except Exception as e:
            self.logger.error(f"Failed to locate section: {e}")
            # Fallback
            return SectionLocation(
                section_name="Full Text", 
                relevant_text=doc.full_text[:500],
                confidence=0.0,
                page_number=0
            )
