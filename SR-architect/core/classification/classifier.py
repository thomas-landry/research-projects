#!/usr/bin/env python3
"""
Relevance Classifier for hierarchical extraction.

First-pass LLM call to generate binary relevance masks at chunk level,
efficiently filtering out irrelevant content before detailed extraction.
"""

from typing import List, Dict, Any, Optional
from core import utils
from core import constants
from core.parser import DocumentChunk
from .models import RelevanceResult, RelevanceResponse
from .helpers import truncate_chunk, build_batch_prompt


class RelevanceClassifier:
    """Classifies chunks as relevant (1) or irrelevant (0) to the extraction theme."""
    
    SYSTEM_PROMPT = """You are a systematic review assistant performing relevance screening.

Your task is to classify document chunks as RELEVANT or IRRELEVANT to the given meta-analysis theme.

A chunk is RELEVANT (1) if it likely contains extractable data for ANY of the specified fields.
A chunk is IRRELEVANT (0) if it contains:
- General discussion or background without specific data
- Methodology rationale without specific numbers
- Limitations or future directions
- Administrative content

Be INCLUSIVE rather than exclusive - when in doubt, mark as relevant.
It's better to include slightly irrelevant content than to miss important data."""

    def __init__(
        self,
        provider: str = "openrouter",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        batch_size: int = None,
        preview_chars: int = None,
        token_tracker: Optional["TokenTracker"] = None,
    ):
        """
        Initialize the relevance classifier.
        
        Args:
            provider: LLM provider ("openrouter" or "ollama")
            model: Model name
            api_key: API key
            batch_size: Number of chunks to classify per API call
            preview_chars: Characters per chunk for classification context
        """
        utils.load_env()
        
        self.provider = provider.lower()
        from core.config import settings
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        
        if model:
            self.model = model
        elif self.provider == "openrouter":
            self.model = settings.OPENROUTER_MODEL
        elif self.provider == "ollama":
            self.model = settings.OLLAMA_MODEL
        else:
            self.model = "gpt-4o"
        
        if batch_size is None:
            batch_size = constants.RELEVANCE_BATCH_SIZE
        if preview_chars is None:
            preview_chars = constants.RELEVANCE_PREVIEW_CHARS
        self.batch_size = batch_size
        self.preview_chars = preview_chars
        self.token_tracker = token_tracker
        self._client = None
        self._instructor_client = None
        self._async_instructor_client = None
        self.logger = utils.get_logger("RelevanceClassifier")
    
    def _get_client(self):
        """Initialize the Instructor-patched client (Sync)."""
        if self._instructor_client is not None:
            return self._instructor_client
        
        self._instructor_client = utils.get_llm_client(
            provider=self.provider,
            api_key=self.api_key
        )
        return self._instructor_client

    def _get_async_client(self):
        """Initialize the Instructor-patched client (Async)."""
        if self._async_instructor_client is not None:
            return self._async_instructor_client
        
        self._async_instructor_client = utils.get_async_llm_client(
            provider=self.provider,
            api_key=self.api_key
        )
        return self._async_instructor_client

    def classify_batch(
        self,
        chunks: List[DocumentChunk],
        theme: str,
        schema_fields: List[str],
    ) -> List[RelevanceResult]:
        """
        Classify all chunks for relevance to the extraction theme.
        
        Args:
            chunks: List of document chunks to classify
            theme: Meta-analysis theme description
            schema_fields: List of field names we're extracting
            
        Returns:
            List of RelevanceResult for each chunk
        """
        if not chunks:
            return []
        
        client = self._get_client()
        all_results: List[RelevanceResult] = []
        
        # Process in batches
        for batch_start in range(0, len(chunks), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(chunks))
            batch_chunks = chunks[batch_start:batch_end]
            
            user_prompt = build_batch_prompt(
                batch_chunks, batch_start, theme, schema_fields, self.preview_chars
            )
            
            try:
                response, completion = client.chat.completions.create_with_completion(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_model=RelevanceResponse,
                    extra_body={"usage": {"include": True}}
                )
                
                # Record usage
                if self.token_tracker and hasattr(completion, 'usage') and completion.usage:
                    self.token_tracker.record_usage(
                        usage={
                            "prompt_tokens": completion.usage.prompt_tokens,
                            "completion_tokens": completion.usage.completion_tokens,
                            "total_tokens": completion.usage.total_tokens
                        },
                        model=self.model,
                        operation="relevance_classification"
                    )
                
                # Map response to results
                for classification in response.classifications:
                    all_results.append(RelevanceResult(
                        chunk_index=classification.index,
                        is_relevant=classification.relevant == 1,
                        # Use more distinctive confidence values
                        # Relevant chunks: high confidence (0.85+)
                        # Irrelevant chunks: lower confidence (0.5-0.7)
                        confidence=0.9 if classification.relevant == 1 else 0.5,
                        reason=classification.reason,
                    ))
                    
            except Exception as e:
                # On error, mark all chunks in batch as relevant (safe default)
                self.logger.warning(f"Relevance classification failed for batch {batch_start}-{batch_end}: {e}")
                for i in range(batch_start, batch_end):
                    all_results.append(RelevanceResult(
                        chunk_index=i,
                        is_relevant=True,
                        confidence=0.5,
                        reason="Classification failed - defaulting to relevant",
                    ))
        
        # Sort by chunk index and fill any gaps
        results_by_index = {r.chunk_index: r for r in all_results}
        final_results = []
        
        for i in range(len(chunks)):
            if i in results_by_index:
                final_results.append(results_by_index[i])
            else:
                # Missing result - default to relevant
                final_results.append(RelevanceResult(
                    chunk_index=i,
                    is_relevant=True,
                    confidence=0.5,
                    reason="Not classified - defaulting to relevant",
                ))
        
        return final_results

    async def classify_batch_async(
        self,
        chunks: List[DocumentChunk],
        theme: str,
        schema_fields: List[str],
    ) -> List[RelevanceResult]:
        """
        Classify all chunks for relevance (Async).
        """
        if not chunks:
            return []
        
        client = self._get_async_client()
        all_results: List[RelevanceResult] = []
        
        # Process in batches
        for batch_start in range(0, len(chunks), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(chunks))
            batch_chunks = chunks[batch_start:batch_end]
            
            user_prompt = build_batch_prompt(
                batch_chunks, batch_start, theme, schema_fields, self.preview_chars
            )
            
            try:
                response, completion = await client.chat.completions.create_with_completion(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_model=RelevanceResponse,
                    extra_body={"usage": {"include": True}}
                )
                
                # Record usage
                if self.token_tracker and hasattr(completion, 'usage') and completion.usage:
                    self.token_tracker.record_usage(
                        usage={
                            "prompt_tokens": completion.usage.prompt_tokens,
                            "completion_tokens": completion.usage.completion_tokens,
                            "total_tokens": completion.usage.total_tokens
                        },
                        model=self.model,
                        operation="relevance_classification"
                    )
                
                for classification in response.classifications:
                    all_results.append(RelevanceResult(
                        chunk_index=classification.index,
                        is_relevant=classification.relevant == 1,
                        confidence=0.9 if classification.relevant == 1 else 0.5,
                        reason=classification.reason,
                    ))
                    
            except Exception as e:
                self.logger.warning(f"Async Relevance classification failed for batch {batch_start}-{batch_end}: {e}")
                for i in range(batch_start, batch_end):
                    all_results.append(RelevanceResult(
                        chunk_index=i,
                        is_relevant=True,
                        confidence=0.5,
                        reason="Classification failed - defaulting to relevant",
                    ))
        
        # Sorting and filling gaps
        results_by_index = {r.chunk_index: r for r in all_results}
        final_results = []
        for i in range(len(chunks)):
            if i in results_by_index:
                final_results.append(results_by_index[i])
            else:
                final_results.append(RelevanceResult(
                    chunk_index=i,
                    is_relevant=True,
                    confidence=0.5,
                    reason="Not classified - defaulting to relevant",
                ))
        return final_results

    
    def get_relevant_chunks(
        self,
        chunks: List[DocumentChunk],
        theme: str,
        schema_fields: List[str],
    ) -> tuple[List[DocumentChunk], List[RelevanceResult]]:
        """
        Filter chunks to only those classified as relevant.
        
        Args:
            chunks: All document chunks
            theme: Meta-analysis theme
            schema_fields: Fields to extract
            
        Returns:
            Tuple of (relevant_chunks, all_classification_results)
        """
        results = self.classify_batch(chunks, theme, schema_fields)
        
        relevant_chunks = [
            chunk for chunk, result in zip(chunks, results)
            if result.is_relevant
        ]
        
        return relevant_chunks, results

    async def get_relevant_chunks_async(
        self,
        chunks: List[DocumentChunk],
        theme: str,
        schema_fields: List[str],
    ) -> tuple[List[DocumentChunk], List[RelevanceResult]]:
        """
        Filter chunks to only those classified as relevant (Async).
        """
        results = await self.classify_batch_async(chunks, theme, schema_fields)
        
        relevant_chunks = [
            chunk for chunk, result in zip(chunks, results)
            if result.is_relevant
        ]
        
        return relevant_chunks, results

    
    def get_classification_summary(self, results: List[RelevanceResult]) -> Dict[str, Any]:
        """Generate summary statistics for classification results."""
        if not results:
            return {
                "total_chunks": 0,
                "relevant_chunks": 0,
                "irrelevant_chunks": 0,
                "relevance_rate": 0.0,
                "avg_confidence": 0.0,
            }
        
        total = len(results)
        relevant = sum(1 for r in results if r.is_relevant)
        irrelevant = total - relevant
        
        # Safely calculate average confidence, filtering None values
        valid_confidences = [r.confidence for r in results if r.confidence is not None]
        avg_conf = sum(valid_confidences) / len(valid_confidences) if valid_confidences else 0.0
        
        return {
            "total_chunks": total,
            "relevant_chunks": relevant,
            "irrelevant_chunks": irrelevant,
            "relevance_rate": round(relevant / total * 100, 1),
            "avg_confidence": round(avg_conf, 2),
        }
