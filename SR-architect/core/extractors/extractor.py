#!/usr/bin/env python3
"""
LLM-based structured extraction using Instructor and Pydantic.

Extracts data from parsed documents into structured schemas with evidence support.
"""

import os
from typing import Type, TypeVar, Optional, Dict, Any, List
from pydantic import BaseModel
from core import utils
from core.parser import ParsedDocument
from core import constants
from .models import EvidenceItem, ExtractionWithEvidence, EvidenceResponse

T = TypeVar('T', bound=BaseModel)

# Evidence extraction constants
EVIDENCE_CONTEXT_MAX_CHARS = 12000  # Max characters for evidence extraction to avoid token limits


class StructuredExtractor:
    """Extract structured data from text using LLMs with Instructor."""
    
    SYSTEM_PROMPT_TEMPLATE = """You are a systematic review auditor aimed at extracting structured data from scientific texts.

Your task is to extract specific data points from academic papers with HIGH PRECISION.

CRITICAL RULES:
1. Extract ONLY information that is EXPLICITLY stated in the text
2. If a value is not clearly stated, use "Not reported" or null
3. For every field, also extract the EXACT QUOTE from the text that supports your answer
4. Do not infer or assume values that are not directly stated
5. Be precise with numbers - extract them exactly as written
6. For patient demographics, extract all available details
7. STANDARDIZATION RULES:
   - Expand abbreviations to full terms (e.g., "Minute Pulmonary Meningothelial-like Nodules" instead of "MPMN")
   - If findings are "incidental" and no symptoms are reported, set presenting_symptoms to "Asymptomatic"
   - Use "Observation" for treatment if only follow-up/monitoring is mentioned
   - Use "Not reported" exactly if information is missing
   - For transplant cases, extract RECIPIENT demographics
   - Use standard medical terminology whenever possible

You will receive text from an academic paper (typically Abstract, Methods, Results sections).
Extract the requested fields according to the provided schema."""

    def __init__(
        self,
        provider: str = "openrouter",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        examples: Optional[str] = None,
        token_tracker: Optional["TokenTracker"] = None,
        max_retries: Optional[int] = None,
    ):
        """
        Initialize the extractor logic.
        
        Args:
            provider: LLM provider
            model: Model name
            api_key: API key
            base_url: Base URL
            examples: Few-shot examples string to append to prompt
            token_tracker: Optional token usage tracker
            max_retries: Maximum number of retries for failed extractions
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.examples = examples
        self.token_tracker = token_tracker
        self.max_retries = max_retries if max_retries is not None else constants.MAX_LLM_RETRIES
        
        # Lazy-initialized clients
        self._instructor_client = None
        self._async_instructor_client = None
        
        # Usage tracking
        self.call_count = 0
        self.success_count = 0
        self.failure_count = 0
        
        from core.utils import get_logger
        self.logger = get_logger("StructuredExtractor")

    @property
    def client(self):
        """Initialize and return the Instructor-patched client."""
        if self._instructor_client is not None:
            return self._instructor_client
        
        from core.utils import get_llm_client
        
        self._instructor_client = get_llm_client(
            provider=self.provider,
            api_key=self.api_key,
            base_url=self.base_url
        )
        return self._instructor_client

    @property
    def async_client(self):
        """Initialize and return the Instructor-patched async client."""
        if self._async_instructor_client is not None:
            return self._async_instructor_client
        
        from core.utils import get_async_llm_client
        
        self._async_instructor_client = get_async_llm_client(
            provider=self.provider,
            api_key=self.api_key,
            base_url=self.base_url
        )
        return self._async_instructor_client
    
    def _track_usage(self, model: str, success: bool = True, usage: Optional[Dict[str, int]] = None, filename: Optional[str] = None):
        """Track call statistics and token usage."""
        self.call_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        if self.token_tracker and usage:
            self.token_tracker.record_usage(
                usage=usage,
                model=model,
                operation="extraction",
                filename=filename
            )
    
    async def _track_usage_async(self, model: str, success: bool = True, usage: Optional[Dict[str, int]] = None, filename: Optional[str] = None):
        """Track call statistics and token usage (Async)."""
        self.call_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        if self.token_tracker and usage:
            await self.token_tracker.record_usage_async(
                usage=usage,
                model=model,
                operation="extraction",
                filename=filename
            )
    
    def extract(
        self,
        text: str,
        schema: Type[T],
        filename: Optional[str] = None,
    ) -> T:
        """
        Extract structured data from text.
        
        Args:
            text: Document text to extract from
            schema: Pydantic model class defining extraction schema
            filename: Source filename to include in output
            
        Returns:
            Instance of schema class with extracted data
        """
        client = self.client
        
        # Build prompt
        system_prompt = self.SYSTEM_PROMPT_TEMPLATE
        if self.examples:
            system_prompt += f"\n\n{self.examples}"
        
        user_prompt = f"Extract the following data from this text:\n\n{text}"
        
        try:
            # Call LLM with Instructor
            result, completion = client.chat.completions.create_with_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_model=schema,
                max_retries=self.max_retries,
                extra_body={"usage": {"include": True}}
            )
            
            # Track usage
            usage = None
            if hasattr(completion, 'usage') and completion.usage:
                usage = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens
                }
            
            self._track_usage(self.model, success=True, usage=usage, filename=filename)
            return result
            
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            self._track_usage(self.model, success=False, filename=filename)
            raise
    
    async def extract_async(
        self,
        text: str,
        schema: Type[T],
        filename: Optional[str] = None,
    ) -> T:
        """
        Extract structured data from text (Async).
        """
        client = self.async_client
        
        # Build prompt
        system_prompt = self.SYSTEM_PROMPT_TEMPLATE
        if self.examples:
            system_prompt += f"\n\n{self.examples}"
        
        user_prompt = f"Extract the following data from this text:\n\n{text}"
        
        try:
            # Call LLM with Instructor
            result, completion = await client.chat.completions.create_with_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_model=schema,
                max_retries=self.max_retries,
                extra_body={"usage": {"include": True}}
            )
            
            # Track usage
            usage = None
            if hasattr(completion, 'usage') and completion.usage:
                usage = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens
                }
            
            await self._track_usage_async(self.model, success=True, usage=usage, filename=filename)
            return result
            
        except Exception as e:
            self.logger.error(f"Async extraction failed: {e}")
            await self._track_usage_async(self.model, success=False, filename=filename)
            raise

    def extract_document(
        self,
        document: ParsedDocument,
        schema: Type[T],
        theme: str = "",
    ) -> T:
        """
        Batch-compatible extraction method.
        Matches HierarchicalExtractionPipeline.extract_document signature.
        """
        # Use full text for extraction
        text = document.full_text
        return self.extract(text, schema, filename=document.filename)

    def extract_with_retry(
        self,
        text: str,
        schema: Type[T],
        filename: Optional[str] = None,
        max_retries: int = None,
    ) -> T:
        """Sync with retry."""
        if max_retries is None:
            max_retries = self.max_retries
        
        # max_retries is number of retries AFTER initial attempt
        # So total attempts = 1 + max_retries
        for attempt in range(max_retries + 1):
            try:
                return self.extract(text, schema, filename)
            except Exception as e:
                if attempt == max_retries:
                    raise
                self.logger.warning(f"Extraction attempt {attempt + 1} failed: {e}")
    
    async def extract_with_retry_async(
        self,
        text: str,
        schema: Type[T],
        filename: Optional[str] = None,
        max_retries: int = None,
    ) -> T:
        """
        Extract with automatic retry on failure (Async).
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        # max_retries is number of retries AFTER initial attempt
        # So total attempts = 1 + max_retries
        for attempt in range(max_retries + 1):
            try:
                return await self.extract_async(text, schema, filename)
            except Exception as e:
                if attempt == max_retries:
                    raise
                self.logger.warning(f"Async extraction attempt {attempt + 1} failed: {e}")

    def get_usage_stats(self) -> Dict[str, int]:
        """Get usage statistics."""
        return {
            "total_calls": self.call_count,
            "call_count": self.call_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count
        }

    def _build_evidence_messages(
        self,
        text: str,
        extracted_data: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Build messages for evidence extraction call.
        
        Args:
            text: Source text to extract evidence from
            extracted_data: Already-extracted field values
            
        Returns:
            List of message dicts for LLM call
        """
        # Truncate text if needed
        if len(text) > EVIDENCE_CONTEXT_MAX_CHARS:
            text = text[:EVIDENCE_CONTEXT_MAX_CHARS] + "... [truncated]"
        
        # Format extracted data
        data_str = "\n".join([f"  {k}: {v}" for k, v in extracted_data.items()])
        
        user_prompt = f"""For each extracted field below, find the EXACT QUOTE from the source text that supports it.

EXTRACTED DATA:
{data_str}

SOURCE TEXT:
{text}

For each field, provide:
1. The exact quote from the source text
2. Confidence in the match (0.0-1.0)

If you cannot find a supporting quote, use an empty string for exact_quote."""
        
        return [
            {"role": "system", "content": "You are a citation auditor. Find exact quotes supporting extracted values."},
            {"role": "user", "content": user_prompt}
        ]

    def extract_with_evidence(
        self,
        text: str,
        schema: Type[T],
        filename: Optional[str] = None,
        revision_prompts: Optional[List[str]] = None,
        pre_filled_fields: Optional[Dict[str, Any]] = None,
    ) -> ExtractionWithEvidence:
        """
        Extract with evidence citations (self-proving extraction).
        
        Args:
            text: Source text
            schema: Pydantic schema
            filename: Optional filename
            revision_prompts: Optional list of revision instructions from previous iterations
            pre_filled_fields: Optional dict of pre-filled field values
            
        Returns:
            ExtractionWithEvidence with data and evidence
        """
        client = self.client
        
        # Build extraction prompt
        system_prompt = self.SYSTEM_PROMPT_TEMPLATE
        if self.examples:
            system_prompt += f"\n\n{self.examples}"
        
        # Add revision prompts if provided
        user_prompt = f"Extract the following data from this text:\n\n{text}"
        
        if revision_prompts:
            revision_text = "\n".join([f"- {prompt}" for prompt in revision_prompts])
            user_prompt += f"\n\nREVISION INSTRUCTIONS:\n{revision_text}"
        
        # Add pre-filled fields to prompt if provided
        if pre_filled_fields:
            prefilled_str = "\n".join([f"  {k}: {v}" for k, v in pre_filled_fields.items()])
            user_prompt += f"\n\nPRE-EXTRACTED FIELDS (use these values):\n{prefilled_str}"
        
        try:
            # Step 1: Extract data
            result, completion = client.chat.completions.create_with_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_model=schema,
                max_retries=self.max_retries,
                extra_body={"usage": {"include": True}}
            )
            
            # Track usage for extraction
            if hasattr(completion, 'usage') and completion.usage:
                self._track_usage(
                    self.model,
                    success=True,
                    usage={
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens
                    },
                    filename=filename
                )
            
            # Convert to dict
            if hasattr(result, 'model_dump'):
                data_dict = result.model_dump()
            elif hasattr(result, 'dict'):
                data_dict = result.dict()
            else:
                data_dict = dict(result)
            
            # Merge pre-filled fields into result
            if pre_filled_fields:
                for key, value in pre_filled_fields.items():
                    if key in data_dict and (data_dict[key] is None or data_dict[key] == ""):
                        data_dict[key] = value
            
            # Step 2: Extract evidence
            evidence_messages = self._build_evidence_messages(text, data_dict)
            
            evidence_result, evidence_completion = client.chat.completions.create_with_completion(
                model=self.model,
                messages=evidence_messages,
                response_model=EvidenceResponse,
                max_retries=self.max_retries,
                extra_body={"usage": {"include": True}}
            )
            
            # Track usage for evidence
            if hasattr(evidence_completion, 'usage') and evidence_completion.usage:
                self._track_usage(
                    self.model,
                    success=True,
                    usage={
                        "prompt_tokens": evidence_completion.usage.prompt_tokens,
                        "completion_tokens": evidence_completion.usage.completion_tokens,
                        "total_tokens": evidence_completion.usage.total_tokens
                    },
                    filename=filename
                )
            
            return ExtractionWithEvidence(
                data=data_dict,
                evidence=evidence_result.evidence,
                extraction_metadata={"model": self.model, "filename": filename}
            )
            
        except Exception as e:
            self.logger.error(f"Evidence extraction failed: {e}")
            self._track_usage(self.model, success=False, filename=filename)
            raise

    async def extract_with_evidence_async(
        self,
        text: str,
        schema: Type[T],
        filename: Optional[str] = None,
        revision_prompts: Optional[List[str]] = None,
        pre_filled_fields: Optional[Dict[str, Any]] = None,
    ) -> ExtractionWithEvidence:
        """
        Extract with evidence citations (self-proving extraction) - Async.
        
        Args:
            text: Source text
            schema: Pydantic schema
            filename: Optional filename
            revision_prompts: Optional list of revision instructions from previous iterations
            pre_filled_fields: Optional dict of pre-filled field values
            
        Returns:
            ExtractionWithEvidence with data and evidence
        """
        client = self.async_client
        
        # Build extraction prompt
        system_prompt = self.SYSTEM_PROMPT_TEMPLATE
        if self.examples:
            system_prompt += f"\n\n{self.examples}"
        
        # Add revision prompts if provided
        user_prompt = f"Extract the following data from this text:\n\n{text}"
        
        if revision_prompts:
            revision_text = "\n".join([f"- {prompt}" for prompt in revision_prompts])
            user_prompt += f"\n\nREVISION INSTRUCTIONS:\n{revision_text}"
        
        # Add pre-filled fields to prompt if provided
        if pre_filled_fields:
            prefilled_str = "\n".join([f"  {k}: {v}" for k, v in pre_filled_fields.items()])
            user_prompt += f"\n\nPRE-EXTRACTED FIELDS (use these values):\n{prefilled_str}"
        
        try:
            # Step 1: Extract data
            result, completion = await client.chat.completions.create_with_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_model=schema,
                max_retries=self.max_retries,
                extra_body={"usage": {"include": True}}
            )
            
            # Track usage for extraction
            if hasattr(completion, 'usage') and completion.usage:
                await self._track_usage_async(
                    self.model,
                    success=True,
                    usage={
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens
                    },
                    filename=filename
                )
            
            # Convert to dict
            if hasattr(result, 'model_dump'):
                data_dict = result.model_dump()
            elif hasattr(result, 'dict'):
                data_dict = result.dict()
            else:
                data_dict = dict(result)
            
            # Merge pre-filled fields into result
            if pre_filled_fields:
                for key, value in pre_filled_fields.items():
                    if key in data_dict and (data_dict[key] is None or data_dict[key] == ""):
                        data_dict[key] = value
            
            # Step 2: Extract evidence
            evidence_messages = self._build_evidence_messages(text, data_dict)
            
            evidence_result, evidence_completion = await client.chat.completions.create_with_completion(
                model=self.model,
                messages=evidence_messages,
                response_model=EvidenceResponse,
                max_retries=self.max_retries,
                extra_body={"usage": {"include": True}}
            )
            
            # Track usage for evidence
            if hasattr(evidence_completion, 'usage') and evidence_completion.usage:
                await self._track_usage_async(
                    self.model,
                    success=True,
                    usage={
                        "prompt_tokens": evidence_completion.usage.prompt_tokens,
                        "completion_tokens": evidence_completion.usage.completion_tokens,
                        "total_tokens": evidence_completion.usage.total_tokens
                    },
                    filename=filename
                )
            
            return ExtractionWithEvidence(
                data=data_dict,
                evidence=evidence_result.evidence,
                extraction_metadata={"model": self.model, "filename": filename}
            )
            
        except Exception as e:
            self.logger.error(f"Async evidence extraction failed: {e}")
            await self._track_usage_async(self.model, success=False, filename=filename)
            raise
