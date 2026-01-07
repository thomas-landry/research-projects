#!/usr/bin/env python3
"""
Relevance Classifier for hierarchical extraction.

First-pass LLM call to generate binary relevance masks at chunk level,
efficiently filtering out irrelevant content before detailed extraction.
"""

import os
import json
from typing import List, Dict, Any, Optional, Type
from dataclasses import dataclass
from pydantic import BaseModel, Field

from core import utils
from .parser import DocumentChunk


@dataclass
class RelevanceResult:
    """Result for a single chunk's relevance classification."""
    chunk_index: int
    is_relevant: bool
    confidence: float
    reason: str


class ChunkRelevance(BaseModel):
    """Pydantic model for structured relevance output."""
    index: int
    relevant: int = Field(ge=0, le=1)  # 0 or 1
    reason: str


class RelevanceResponse(BaseModel):
    """Batch response for relevance classification."""
    classifications: List[ChunkRelevance]


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
        batch_size: int = 10,
        preview_chars: int = 500,
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
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        
        if model:
            self.model = model
        elif self.provider == "openrouter":
            self.model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-20250514")
        elif self.provider == "ollama":
            self.model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        else:
            self.model = "gpt-4o"
        
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
    
    def _truncate_chunk(self, chunk: DocumentChunk) -> str:
        """Truncate chunk text for classification preview."""
        text = chunk.text.strip()
        if len(text) <= self.preview_chars:
            return text
        return text[:self.preview_chars] + "..."
    
    def _build_batch_prompt(
        self,
        chunks: List[DocumentChunk],
        start_index: int,
        theme: str,
        schema_fields: List[str],
    ) -> str:
        """Build the user prompt for a batch of chunks."""
        fields_str = ", ".join(schema_fields[:20])  # Limit field list
        
        chunks_str = ""
        for i, chunk in enumerate(chunks):
            idx = start_index + i
            preview = self._truncate_chunk(chunk)
            section_info = f" [Section: {chunk.section}]" if chunk.section else ""
            chunks_str += f"\n[{idx}]{section_info}\n{preview}\n"
        
        return f"""Meta-analysis theme: "{theme}"
Data fields to extract: {fields_str}

Classify each chunk below as relevant (1) or irrelevant (0) to this theme.

Chunks:
{chunks_str}

For each chunk, provide:
- index: the chunk number
- relevant: 1 if it likely contains extractable data, 0 if not
- reason: brief explanation (max 10 words)"""

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
            
            user_prompt = self._build_batch_prompt(
                batch_chunks, batch_start, theme, schema_fields
            )
            
            try:
                response, completion = client.chat.completions.create_with_completion(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_model=RelevanceResponse,
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
            
            user_prompt = self._build_batch_prompt(
                batch_chunks, batch_start, theme, schema_fields
            )
            
            try:
                response, completion = await client.chat.completions.create_with_completion(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_model=RelevanceResponse,
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


if __name__ == "__main__":
    # Test with sample chunks
    test_chunks = [
        DocumentChunk(
            text="We enrolled 42 patients with confirmed DPM. Mean age was 56 years (range 34-78).",
            section="Methods"
        ),
        DocumentChunk(
            text="This study builds on previous work examining rare pulmonary conditions.",
            section="Introduction"
        ),
        DocumentChunk(
            text="Treatment response was observed in 85% of patients (36/42) at 6-month follow-up.",
            section="Results"
        ),
        DocumentChunk(
            text="Future studies should explore the genetic basis of this condition.",
            section="Discussion"
        ),
    ]
    
    theme = "patient demographics and treatment outcomes in diffuse pulmonary meningotheliomatosis"
    fields = ["sample_size", "age", "treatment_response", "follow_up_duration"]
    
    print("Testing relevance classifier...")
    print(f"Theme: {theme}")
    print(f"Fields: {fields}")
    print()
    
    # Note: This will fail without API key - just for structure demonstration
    try:
        classifier = RelevanceClassifier()
        results = classifier.classify_batch(test_chunks, theme, fields)
        
        for chunk, result in zip(test_chunks, results):
            status = "✓ RELEVANT" if result.is_relevant else "✗ IRRELEVANT"
            print(f"{status}: [{chunk.section}] {chunk.text[:50]}...")
            print(f"  Reason: {result.reason}")
    except Exception as e:
        print(f"Test failed (expected if no API key): {e}")
