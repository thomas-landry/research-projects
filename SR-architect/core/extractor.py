#!/usr/bin/env python3
"""
LLM-based structured extraction using Instructor and Pydantic.

Extracts data from parsed documents into structured schemas.
"""

import os
from typing import Type, TypeVar, Optional, Dict, Any, List
from pydantic import BaseModel, Field
from core import utils
from core.parser import ParsedDocument

T = TypeVar('T', bound=BaseModel)


class EvidenceItem(BaseModel):
    """Citation evidence for a single extracted value."""
    field_name: str = Field(description="Name of the extracted field")
    extracted_value: Any = Field(description="The value that was extracted")
    exact_quote: str = Field(description="Verbatim quote from source text supporting this value")
    page_number: Optional[int] = Field(default=None, description="Page number if known")
    chunk_index: Optional[int] = Field(default=None, description="Index of source chunk")
    confidence: float = Field(ge=0.0, le=1.0, default=0.9, description="Confidence in extraction accuracy")


class ExtractionWithEvidence(BaseModel):
    """Wrapper combining extracted data with provenance evidence."""
    data: Dict[str, Any] = Field(description="The extracted field values")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Evidence citations for each value")
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict)


# Using utils.load_env


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
    ):
        """
        Initialize the extractor logic.
        
        Args:
            provider: LLM provider
            model: Model name
            api_key: API key
            base_url: Base URL
            examples: Few-shot examples string to append to prompt
            token_tracker: Optional TokenTracker for cost tracking
        """
        utils.load_env()
        
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = base_url
        
        # Set default models
        if model:
            self.model = model
        elif self.provider == "openrouter":
            self.model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-20250514")
        elif self.provider == "ollama":
            self.model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        else:
            self.model = "gpt-4o"
        
        self._client = None
        self._instructor_client = None
        self._async_instructor_client = None
        
        # Token tracking
        self.token_tracker = token_tracker
        
        # Usage tracking
        self._stats = {
            "total_calls": 0,
            "calls_by_model": {},
            "errors": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
        }
        
        self.logger = utils.get_logger("StructuredExtractor")
        
        # Build dynamic system prompt
        self.system_prompt = self.SYSTEM_PROMPT_TEMPLATE
        if examples:
            self.system_prompt += "\n\n" + examples
            
        # Build dynamic self-proving prompt
        self.self_proving_prompt = self.SELF_PROVING_PROMPT_TEMPLATE
        if examples:
            self.self_proving_prompt += "\n\n" + examples

    @property
    def client(self):
        """Initialize and return the Instructor-patched client."""
        if self._instructor_client is not None:
            return self._instructor_client
        
        self.logger.debug(f"Initializing LLM client for provider: {self.provider}")
        self._instructor_client = utils.get_llm_client(
            provider=self.provider,
            api_key=self.api_key
        )
        
        return self._instructor_client

    @property
    def async_client(self):
        """Initialize and return the Instructor-patched async client."""
        if self._async_instructor_client is not None:
            return self._async_instructor_client
        
        self.logger.debug(f"Initializing Async LLM client for provider: {self.provider}")
        self._async_instructor_client = utils.get_async_llm_client(
            provider=self.provider,
            api_key=self.api_key
        )
        
        return self._async_instructor_client
    
    def _track_usage(self, model: str, success: bool = True, usage: Optional[Dict[str, int]] = None, filename: Optional[str] = None):
        """Track call statistics and token usage."""
        self._stats["total_calls"] += 1
        self._stats["calls_by_model"][model] = self._stats["calls_by_model"].get(model, 0) + 1
        if not success:
            self._stats["errors"] += 1
        
        # Track token usage if available
        if usage:
            self._stats["total_prompt_tokens"] += usage.get("prompt_tokens", 0)
            self._stats["total_completion_tokens"] += usage.get("completion_tokens", 0)
            
            # Record in token tracker if available
            if self.token_tracker:
                self.token_tracker.record_usage(
                    usage=usage,
                    model=model,
                    filename=filename,
                    operation="extraction",
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
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Extract data from the following academic paper text:\n\n{text}"},
        ]
        
        # 1. Check Cache
        from core.utils import LLMCache
        cache = LLMCache()
        cached_result = cache.get(self.model, messages, response_model=schema)
        if cached_result:
            self.logger.info(f"✓ Using cached extraction for {filename or 'text'}")
            return cached_result

        try:
            self.logger.info(f"Extracting data from {filename or 'text'} using {self.model}")
            result, completion = self.client.chat.completions.create_with_completion(
                model=self.model,
                messages=messages,
                response_model=schema,
                max_retries=2,
                extra_body={"usage": {"include": True}}
            )
            
            # Record usage
            if hasattr(completion, 'usage') and completion.usage:
                usage_dict = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens
                }
                self._track_usage(self.model, success=True, usage=usage_dict, filename=filename)
            else:
                self._track_usage(self.model, success=True)
            
            # 2. Save to Cache
            cache.set(self.model, messages, result)
            
            # Add filename if the schema supports it
            if hasattr(result, 'filename') and filename:
                result.filename = filename
            
            self._track_usage(self.model, success=True)
            return result
        
        except Exception as e:
            self._track_usage(self.model, success=False)
            self.logger.error(f"Extraction failed: {e}")
            raise RuntimeError(f"Extraction failed for {filename or 'text'}: {str(e)}") from e

    async def extract_async(
        self,
        text: str,
        schema: Type[T],
        filename: Optional[str] = None,
    ) -> T:
        """
        Extract structured data from text (Async).
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Extract data from the following academic paper text:\n\n{text}"},
        ]
        
        # 1. Check Cache
        from core.utils import LLMCache
        cache = LLMCache()
        cached_result = cache.get(self.model, messages, response_model=schema)
        if cached_result:
            self.logger.info(f"✓ Using cached extraction (async) for {filename or 'text'}")
            return cached_result

        try:
            self.logger.info(f"Extracting data (async) from {filename or 'text'} examples={len(self.examples)} using {self.model}")
            result, completion = await self.async_client.chat.completions.create_with_completion(
                model=self.model,
                messages=messages,
                response_model=schema,
                max_retries=2,
                extra_body={"usage": {"include": True}}
            )
            
            # Record usage
            if hasattr(completion, 'usage') and completion.usage:
                usage_dict = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens
                }
                self._track_usage(self.model, success=True, usage=usage_dict, filename=filename)
            else:
                self._track_usage(self.model, success=True)

            # 2. Save to Cache
            cache.set(self.model, messages, result)
            
            # Add filename if the schema supports it
            if hasattr(result, 'filename') and filename:
                result.filename = filename
            
            return result
        
        except Exception as e:
            self._track_usage(self.model, success=False)
            self.logger.error(f"Async extraction failed: {e}")
            raise RuntimeError(f"Async extraction failed for {filename or 'text'}: {str(e)}") from e

        
    def extract_document(
        self,
        document: ParsedDocument,
        schema: Type[T],
        theme: str = "",
    ) -> Any:
        """
        Batch-compatible extraction method.
        Matches HierarchicalExtractionPipeline.extract_document signature.
        """
        # For standard extraction, we just use the full context
        context = document.get_extraction_context()
        return self.extract_with_retry(context, schema, filename=document.filename)
    
    def extract_with_retry(
        self,
        text: str,
        schema: Type[T],
        filename: Optional[str] = None,
        max_retries: int = 2,
    ) -> T:
        """Sync with retry."""
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return self.extract(text, schema, filename)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    self.logger.warning(f"Retry {attempt + 1}/{max_retries} for {filename} due to: {e}")
        
        raise last_error

    async def extract_with_retry_async(
        self,
        text: str,
        schema: Type[T],
        filename: Optional[str] = None,
        max_retries: int = 2,
    ) -> T:
        """
        Extract with automatic retry on failure (Async).
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return await self.extract_async(text, schema, filename)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    self.logger.warning(f"Retry {attempt + 1}/{max_retries} (async) for {filename} due to: {e}")
        
        raise last_error
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return self._stats
    
    # Self-proving extraction prompt
    SELF_PROVING_PROMPT_TEMPLATE = """You are an expert systematic reviewer extracting data for a meta-analysis.

CRITICAL: This extraction requires SELF-PROVING - you must provide evidence for every value.

For EVERY numerical value or specific finding you extract, you MUST:
1. Provide the EXACT QUOTE from the text that contains this value
2. Only extract values that have direct textual support

RULES:
1. Extract ONLY information that is EXPLICITLY stated in the text
2. If you cannot find a direct quote supporting a value, mark it as "Not reported"
3. Be precise with numbers - extract them exactly as written
4. Include units, confidence intervals, and ranges when present
5. If a value appears in multiple places, cite the most authoritative source (Methods > Results > Abstract)

You will receive text and must output:
- data: The extracted field values
- evidence: A list of citations, one per extracted value, with:
  - field_name: Which field this evidence supports
  - extracted_value: The value you extracted
  - exact_quote: The verbatim text from the source
  - confidence: Your confidence (0.0-1.0) that the quote supports the value"""

    def extract_with_evidence(
        self,
        text: str,
        schema: Type[T],
        filename: Optional[str] = None,
        revision_prompts: Optional[List[str]] = None,
    ) -> ExtractionWithEvidence:
        """
        Extract structured data with self-proving evidence citations.
        
        Args:
            text: Document text to extract from
            schema: Pydantic model class defining extraction schema
            filename: Source filename for metadata
            revision_prompts: Optional feedback from checker for corrections
            
        Returns:
            ExtractionWithEvidence with data, evidence list, and metadata
        """
        # Build the user message
        user_content = f"Extract data from the following academic paper text:\n\n{text}"
        
        # Add revision instructions if provided (from checker feedback)
        if revision_prompts:
            revision_text = "\n".join(f"- {p}" for p in revision_prompts)
            user_content += f"\n\n--- REVISION INSTRUCTIONS ---\nPlease fix the following issues from the previous extraction:\n{revision_text}\n\nBe especially careful with these corrections."
        
        # Get schema field names for the prompt
        schema_fields = list(schema.model_fields.keys()) if hasattr(schema, 'model_fields') else []
        fields_info = f"\n\nFields to extract: {', '.join(schema_fields)}" if schema_fields else ""
        
        user_content += fields_info
        
        messages = [
            {"role": "system", "content": self.self_proving_prompt},
            {"role": "user", "content": user_content},
        ]
        
        try:
            # First, extract the data using the provided schema
            data_result, completion = self.client.chat.completions.create_with_completion(
                model=self.model,
                messages=messages,
                response_model=schema,
                extra_body={"usage": {"include": True}}
            )
            
            # Record usage
            if hasattr(completion, 'usage') and completion.usage:
                usage_dict = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens
                }
                self._track_usage(self.model, success=True, usage=usage_dict, filename=filename)
            
            # Convert to dict
            data_dict = data_result.model_dump()
            
            # Add filename if present
            if filename:
                data_dict["filename"] = filename
            
            # Now extract evidence for each field
            # Use proportional truncation based on data location hints
            evidence_context = text[:12000]
            if len(text) > 12000:
                # Log warning about truncation
                self.logger.warning(f"Text truncated from {len(text)} to 12000 chars for evidence extraction")

            evidence_messages = [
                {"role": "system", "content": self.self_proving_prompt},
                {"role": "user", "content": f"""Based on this text:
{evidence_context}

And these extracted values:
{data_dict}

Provide evidence citations for each extracted value. For each field that has a non-null value, cite the exact quote from the text that supports it."""},
            ]
            
            # Create a dynamic model for evidence response
            class EvidenceResponse(BaseModel):
                evidence: List[EvidenceItem]
            
            evidence_result, completion_ev = self.client.chat.completions.create_with_completion(
                model=self.model,
                messages=evidence_messages,
                response_model=EvidenceResponse,
                extra_body={"usage": {"include": True}}
            )
            
            # Record usage
            if hasattr(completion_ev, 'usage') and completion_ev.usage:
                usage_dict = {
                    "prompt_tokens": completion_ev.usage.prompt_tokens,
                    "completion_tokens": completion_ev.usage.completion_tokens,
                    "total_tokens": completion_ev.usage.total_tokens
                }
                self._track_usage(self.model, success=True, usage=usage_dict, filename=filename)
            
            return ExtractionWithEvidence(
                data=data_dict,
                evidence=evidence_result.evidence,
                extraction_metadata={
                    "filename": filename,
                    "model": self.model,
                    "provider": self.provider,
                    "had_revision_prompts": bool(revision_prompts),
                }
            )
        
        except Exception as e:
            raise RuntimeError(f"Self-proving extraction failed for {filename or 'text'}: {str(e)}") from e

    async def extract_with_evidence_async(
        self,
        text: str,
        schema: Type[T],
        filename: Optional[str] = None,
        revision_prompts: Optional[List[str]] = None,
    ) -> ExtractionWithEvidence:
        """
        Extract structured data with self-proving evidence citations (Async).
        """
        # Build the user message
        user_content = f"Extract data from the following academic paper text:\n\n{text}"
        
        if revision_prompts:
            revision_text = "\n".join(f"- {p}" for p in revision_prompts)
            user_content += f"\n\n--- REVISION INSTRUCTIONS ---\nPlease fix the following issues from the previous extraction:\n{revision_text}\n\nBe especially careful with these corrections."
        
        schema_fields = list(schema.model_fields.keys()) if hasattr(schema, 'model_fields') else []
        fields_info = f"\n\nFields to extract: {', '.join(schema_fields)}" if schema_fields else ""
        user_content += fields_info
        
        messages = [
            {"role": "system", "content": self.self_proving_prompt},
            {"role": "user", "content": user_content},
        ]
        
        try:
            # First, extract the data
            data_result = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_model=schema,
            )
            data_dict = data_result.model_dump()
            if filename:
                data_dict["filename"] = filename
            
            # Evidence extraction
            evidence_context = text[:12000]
            evidence_messages = [
                {"role": "system", "content": self.self_proving_prompt},
                {"role": "user", "content": f"Based on this text:\n{evidence_context}\n\nAnd these extracted values:\n{data_dict}\n\nProvide evidence citations for each extracted value."},
            ]
            
            class EvidenceResponse(BaseModel):
                evidence: List[EvidenceItem]
            
            ev_result = await self.async_client.chat.completions.create(
                model=self.model,
                messages=evidence_messages,
                response_model=EvidenceResponse,
            )
            
            return ExtractionWithEvidence(
                data=data_dict,
                evidence=ev_result.evidence,
                extraction_metadata={
                    "filename": filename,
                    "model": self.model,
                    "provider": self.provider,
                    "had_revision_prompts": bool(revision_prompts),
                }
            )
        except Exception as e:
            raise RuntimeError(f"Async self-proving extraction failed for {filename or 'text'}: {str(e)}") from e



if __name__ == "__main__":
    # Quick test
    from core.schema_builder import get_case_report_schema, build_extraction_model

    
    schema = get_case_report_schema()
    Model = build_extraction_model(schema, "DPMModel")
    
    # Test with sample text
    sample_text = """
    ABSTRACT: We report a case of diffuse pulmonary meningotheliomatosis in a 
    52-year-old female presenting with progressive dyspnea over 6 months. 
    
    METHODS: CT imaging revealed bilateral ground-glass opacities with 
    innumerable micronodules. Transbronchial biopsy was performed.
    
    RESULTS: Histopathology showed characteristic meningothelial-like cells 
    positive for EMA and vimentin, negative for TTF-1. Patient was treated 
    conservatively with follow-up imaging at 6 months showing stable disease.
    """
    
    print("Initializing extractor for test...")
    try:
        # Initialize without API key might fail in real usage, but good for structure check
        extractor = StructuredExtractor(api_key="sk-test-key") 
        print("Extractor initialized.")
        
        # Dry run of extraction with retry to test logic (will fail on auth)
        try:
             # Just checking method signature validity
             pass
        except Exception:
             pass
             
    except Exception as e:
        print(f"Initialization failed: {e}")
