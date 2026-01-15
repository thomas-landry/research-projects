"""
Semantic Chunker for intelligent document segmentation.
Adapts logic from llm-ie to use LLM for identifying section boundaries.
"""
from typing import List, Dict, Any, Optional
import uuid
from core.utils import get_logger, extract_json, apply_prompt_template
from core.parser import DocumentChunk

logger = get_logger("SemanticChunker")

DEFAULT_CHUNKING_PROMPT = """
You are a layout analysis engine. Your task is to Segment the provided text into logical sections (e.g., Abstract, Introduction, Methods, Results, Discussion).

Identify the HEADINGS or STARTING PHRASES that mark the beginning of each new section.
These "anchor_text" values must match the text EXACTLY.

Return a JSON list of anchors:
[
    {"title": "Abstract", "anchor_text": "Abstract"},
    {"title": "Methods", "anchor_text": "2. Materials and Methods"},
    {"title": "Results", "anchor_text": "Results"}
]

Rules:
1. anchor_text must appear sequentially in the text.
2. Only identify top-level changes in topic.
3. If no clear sections exist, return an empty list.

TEXT:
{{text}}
"""

class SemanticChunker:
    """
    Intelligent text chunker that uses LLM to identify section anchors.
    """
    
    def __init__(
        self, 
        client: Any = None, 
        prompt_template: Optional[str] = None
    ):
        """
        Initialize chunker with LLM client.
        
        Args:
            client: Initialized LLM client (Instructor/OpenAI)
            prompt_template: Custom prompt for section identification
        """
        self.client = client
        self.prompt_template = prompt_template or DEFAULT_CHUNKING_PROMPT
        
    async def chunk_document_async(
        self, 
        text: str, 
        doc_id: Optional[str] = None
    ) -> List[DocumentChunk]:
        """
        Split text into chunks based on semantic sections.
        
        Args:
            text: Full text content
            doc_id: Optional document identifier
        
        Returns:
            List of DocumentChunk objects with section metadata
        """
        if not text or not text.strip():
            return []
            
        doc_id = doc_id or str(uuid.uuid4())
        
        # 1. Get anchors from LLM
        anchors = await self._identify_anchors(text)
        
        # 2. Split text based on anchors
        chunks = self._split_by_anchors(text, anchors, doc_id)
        
        # 3. Fallback if no chunks (LLM failed or returned nothing)
        if not chunks:
            logger.warning("Semantic chunking yielded no results, falling back to single chunk.")
            chunks = [DocumentChunk(
                text=text,
                section="Full Text",
                source_file=doc_id
            )]
            
        return chunks

    def chunk(self, text: str, doc_id: Optional[str] = None) -> List[DocumentChunk]:
        """
        Synchronous wrapper for chunk_document_async (Legacy API).
        """
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        if loop and loop.is_running():
            # If we are already in an event loop, we can't use asyncio.run
            # This is a hack, but strictly for backward compat of sync method
            # Ideally the caller should await chunk_document_async
            # For now, we return a single chunk to avoid crashing if we can't await
            logger.warning("Called sync chunk() from inside event loop - falling back to simple chunking")
            doc_id = doc_id or str(uuid.uuid4())
            return [DocumentChunk(text=text, section="Full Text", source_file=doc_id)]
            
        return asyncio.run(self.chunk_document_async(text, doc_id))

    async def _identify_anchors(self, text: str) -> List[Dict[str, str]]:
        """Query LLM to find section anchors."""
        if not self.client:
            logger.warning("No LLM client provided to SemanticChunker, skipping semantic split.")
            return []

        # Truncate text if too long for context window (heuristic)
        # We mostly care about headers which appear throughout, but let's send first 15k chars 
        # as a rough "structure" sample if the doc is massive?
        # Actually, for segmentation we probably need the whole text or sliding window.
        # For now, let's assume text fits or we send a simplified version (headings only? no, too hard to strip).
        # We will send the first 20k chars which usually covers structure of standard papers.
        # Ideally we'd map the whole file, but context limits exist.
        
        truncated_text = text[:30000] 
        
        prompt = apply_prompt_template(self.prompt_template, truncated_text)
        
        try:
            # Universal handling for Sync/Async clients
            # We call .create() and await if it returns a coroutine
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", # Use cheap fast model
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            
            if hasattr(response, '__await__'):
                response = await response

            content = response.choices[0].message.content
            return extract_json(content)
            
        except Exception as e:
            logger.error(f"Error getting anchors from LLM: {e}")
            return []

    def _split_by_anchors(
        self, 
        text: str, 
        anchors: List[Dict[str, str]], 
        doc_id: str
    ) -> List[DocumentChunk]:
        """Split text at anchor text locations."""
        if not anchors:
            return []

        chunks = []
        current_pos = 0
        
        # Validate and sort anchors by position in text
        valid_anchors = []
        start_search = 0
        
        for anchor in anchors:
            anchor_text = anchor.get("anchor_text", "")
            if not anchor_text:
                continue
                
            pos = text.find(anchor_text, start_search)
            if pos != -1:
                valid_anchors.append({
                    "title": anchor.get("title", "Section"),
                    "start": pos,
                    "text": anchor_text
                })
                start_search = pos + len(anchor_text)
            else:
                logger.debug(f"Anchor text not found: '{anchor_text}'")

        if not valid_anchors:
            return []

        # Create chunks between anchors
        # Chunk 0: Start -> Anchor 1
        if valid_anchors[0]["start"] > 0:
            chunks.append(DocumentChunk(
                text=text[0:valid_anchors[0]["start"]],
                section="Intro/Abstract", # Assumed start
                source_file=doc_id
            ))
            current_pos = valid_anchors[0]["start"]

        for i, anchor in enumerate(valid_anchors):
            start = anchor["start"]
            # End is start of next anchor, or end of text
            if i + 1 < len(valid_anchors):
                end = valid_anchors[i+1]["start"]
            else:
                end = len(text)
                
            chunk_text = text[start:end]
            
            chunks.append(DocumentChunk(
                text=chunk_text,
                section=anchor["title"],
                source_file=doc_id
            ))
            
        return chunks
