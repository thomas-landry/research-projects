"""
Unit-Context Sentence Extractor.

Implements the "Sentence Frame Extraction" pattern from LLM-IE:
1. Split document into sentences
2. Process each sentence with ±N sentences of context
3. Use async concurrency to maintain speed
4. Aggregate frame outputs

This approach solves the "needle in haystack" problem for complex fields.
"""

import asyncio
import json
import re
import logging
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel

from core.parser import DocumentChunk
from core.utils import get_async_llm_client, get_logger
from core.data_types import EvidenceFrame
from core import constants

logger = get_logger("SentenceExtractor")

class SentenceExtractor:
    """
    Extracts structured data by processing text one sentence at a time
    with surrounding context.
    """
    
    SYSTEM_PROMPT = """You are a precise clinical information extractor.
Your task is to extract specific entities from a single focus sentence, using the provided context for disambiguation.

Output validation:
- Return ONLY a JSON array of objects.
- Each object must have "entity_text" (exact quote) and "attr" (attributes).
- If no relevant entities are in the focus sentence, return [].
"""

    def __init__(
        self,
        provider: str = "openrouter",
        model: str = "google/gemini-2.5-flash-lite", 
        context_window_size: int = None,
        concurrency_limit: int = None,
        token_tracker: Optional[Any] = None
    ):
        """
        Args:
            provider: LLM provider (e.g., 'ollama', 'openrouter')
            model: Model name to use
            context_window_size: Number of sentences before/after to include
            concurrency_limit: Max concurrent LLM requests
            token_tracker: Optional tracker for cost monitoring
        """
        self.provider = provider
        self.model = model
        if context_window_size is None:
            context_window_size = constants.SENTENCE_CONTEXT_WINDOW
        if concurrency_limit is None:
            concurrency_limit = constants.SENTENCE_CONCURRENCY_LIMIT
        self.context_window_size = context_window_size
        self.concurrency_limit = concurrency_limit
        self.token_tracker = token_tracker
        self.client = None # Lazy init
        
        # Initialize semaphore for concurrency control
        self.sem = asyncio.Semaphore(concurrency_limit)
        
        # Try importing nltk, fallback to simple split
        try:
            import nltk
            try:
                # Check for required data
                try:
                    nltk.data.find('tokenizers/punkt')
                except LookupError:
                    nltk.download('punkt', quiet=True)
                
                try:
                    nltk.data.find('tokenizers/punkt_tab')
                except LookupError:
                    nltk.download('punkt_tab', quiet=True)
                    
            except Exception as e:
                logger.warning(f"Failed to download NLTK data: {e}")
            
            # Wrap nltk.sent_tokenize to handle runtime lookup errors
            def robust_sent_tokenize(text):
                try:
                    return nltk.sent_tokenize(text)
                except LookupError:
                    logger.warning("NLTK data missing at runtime, using regex fallback.")
                    return self._simple_sent_tokenize(text)
                    
            self._sent_tokenize = robust_sent_tokenize
            
        except ImportError:
            logger.warning("NLTK not found. Using simple regex sentence splitter.")
            self._sent_tokenize = self._simple_sent_tokenize

    def _get_client(self):
        if self.client is None:
            self.client = get_async_llm_client(self.provider)
        return self.client

    def _simple_sent_tokenize(self, text: str) -> List[str]:
        """Fallback sentence tokenizer using regex."""
        # Split on (.?! ) but keep delimiters
        # Simple approximation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _tokenize_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        return self._sent_tokenize(text)

    def _get_context(self, sentences: List[str], index: int) -> str:
        """
        Get context window for a specific sentence index.
        Returns concatenated string of Pre + Focus + Post sentences.
        """
        start = max(0, index - self.context_window_size)
        end = min(len(sentences), index + self.context_window_size + 1)
        
        # Mark the focus sentence? LLM-IE style separates them in prompt.
        # But this method creates the raw context string.
        return " ".join(sentences[start:end])

    def _merge_results(self, all_frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate and merge extracted frames.
        Deduping based on (entity_text, entity_type).
        """
        unique_frames = {}
        
        for frame in all_frames:
            # Normalize for deduping
            text = frame.get("entity_text", "").strip()
            attr = frame.get("attr", {})
            etype = attr.get("entity_type", "unknown")
            
            key = (text.lower(), etype)
            
            if key not in unique_frames:
                unique_frames[key] = frame
        
        return list(unique_frames.values())

    async def _extract_single_sentence(
        self, 
        focus_sentence: str, 
        context: str,
        prompt_template: str,
        sentence_start_index: int,
        doc_id: str
    ) -> List[EvidenceFrame]:
        """
        Process a single sentence with the LLM.
        """
        client = self._get_client()
        
        user_content = f"""
Context:
"{context}"

Focus Sentence:
"{focus_sentence}"

Extract fields from the Focus Sentence only.
"""
        full_prompt = f"{prompt_template}\n\n{user_content}"
        
        async with self.sem: 
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": full_prompt}
                    ],
                    temperature=0.0,
                    extra_body={"usage": {"include": True}}
                )
                
                content = response.choices[0].message.content
                
                # Usage tracking
                if self.token_tracker and hasattr(response, 'usage') and response.usage:
                     await self.token_tracker.record_usage_async(
                        usage={
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        },
                        model=self.model,
                        operation="sentence_extraction"
                    )

                # Parse JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[0].strip()
                
                result = json.loads(content)
                
                if not isinstance(result, list):
                    logger.warning(f"Expected list from LLM, got {type(result)}")
                    return []
                
                # Convert dicts to EvidenceFrames
                frames = []
                for item in result:
                    entity_text = item.get("entity_text", "").strip()
                    attr = item.get("attr", {})
                    
                    if not entity_text:
                        continue
                        
                    # Find offset in sentence
                    # Strategy: Use exact match first.
                    try:
                        start_in_sent = focus_sentence.index(entity_text)
                    except ValueError:
                        # Fallback: simple fuzzy or just skipping
                        # For now, strict.
                        if entity_text in focus_sentence: # Should be caught by index
                             pass
                        logger.debug(f"Entity '{entity_text}' not found in sentence: '{focus_sentence}'")
                        continue
                        
                    abs_start = sentence_start_index + start_in_sent
                    abs_end = abs_start + len(entity_text)
                    
                    frames.append(EvidenceFrame(
                        text=entity_text,
                        doc_id=doc_id,
                        start_char=abs_start,
                        end_char=abs_end,
                        section="Unknown", # Could be passed in if known
                        content=attr
                    ))
                    
                return frames

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON for sentence: {focus_sentence[:30]}...")
                return []
            except Exception as e:
                logger.error(f"LLM request failed: {e}")
                return []

    async def extract(
        self, 
        chunks: List[DocumentChunk], 
        prompt_template: str = ""
    ) -> List[EvidenceFrame]:
        """
        Main extraction method.
        """
        # Combine text to form full document flow
        full_text = " ".join([c.text for c in chunks])
        sentences = self._tokenize_sentences(full_text)
        
        if not sentences:
            return []
            
        doc_id = chunks[0].source_file if chunks else "unknown"
            
        tasks = []
        current_pos = 0
        
        for i, sentence in enumerate(sentences):
            # Calculate absolute start index of this sentence in full_text
            # We must find the sentence starting from current_pos
            start_index = full_text.find(sentence, current_pos)
            if start_index == -1:
                # Should not happen if sentences come from text
                logger.warning(f"Could not find sentence in text: {sentence[:20]}...")
                continue
            
            # Update current_pos to end of this sentence
            current_pos = start_index + len(sentence)
            
            context = self._get_context(sentences, i)
            tasks.append(
                self._extract_single_sentence(
                    sentence, 
                    context, 
                    prompt_template,
                    sentence_start_index=start_index,
                    doc_id=doc_id
                )
            )
            
        logger.info(f"Processing {len(tasks)} sentences with concurrency {self.concurrency_limit}...")
        
        # Run all tasks
        results_list = await asyncio.gather(*tasks)
        
        # Flatten
        all_frames = []
        for res in results_list:
            all_frames.extend(res)
            
        # Dedupe based on text + type (content type)
        unique_frames = {}
        for frame in all_frames:
            # Use tuple key: (text, type)
            etype = frame.content.get("entity_type", "unknown")
            key = (frame.text.lower(), etype)
            
            if key not in unique_frames:
                unique_frames[key] = frame
        
        logger.info(f"Extracted {len(unique_frames)} unique entities from {len(sentences)} sentences.")
        return list(unique_frames.values())
