#!/usr/bin/env python3
"""
LLM-based structured extraction using Instructor and Pydantic.

Extracts data from parsed documents into structured schemas.
"""

import os
from typing import Type, TypeVar, Optional, Dict, Any
from pydantic import BaseModel
from pathlib import Path

T = TypeVar('T', bound=BaseModel)


def load_env():
    """Load environment variables from .env file."""
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent / ".env",
        Path.home() / "Projects" / ".env",
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip("'\"")
                        if key and value:
                            os.environ.setdefault(key, value)
            break


class StructuredExtractor:
    """Extract structured data from text using LLMs with Instructor."""
    
    SYSTEM_PROMPT = """You are an expert systematic reviewer extracting data for a meta-analysis.

Your task is to extract specific data points from academic papers with HIGH PRECISION.

CRITICAL RULES:
1. Extract ONLY information that is EXPLICITLY stated in the text
2. If a value is not clearly stated, use "Not reported" or null
3. For every field, also extract the EXACT QUOTE from the text that supports your answer
4. Do not infer or assume values that are not directly stated
5. Be precise with numbers - extract them exactly as written
6. For patient demographics, extract all available details

You will receive text from an academic paper (typically Abstract, Methods, Results sections).
Extract the requested fields according to the provided schema."""

    def __init__(
        self,
        provider: str = "openrouter",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize the extractor.
        
        Args:
            provider: LLM provider ("openrouter" or "ollama")
            model: Model name (defaults based on provider)
            api_key: API key (or loaded from env)
        """
        load_env()
        
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        
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
    
    def _get_client(self):
        """Initialize the Instructor-patched client."""
        if self._instructor_client is not None:
            return self._instructor_client
        
        try:
            import instructor
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "Required packages not installed. Run:\n"
                "pip install instructor openai"
            )
        
        if self.provider == "openrouter":
            if not self.api_key:
                raise ValueError(
                    "OPENROUTER_API_KEY not set. Add it to your .env file."
                )
            
            self._client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
            )
        
        elif self.provider == "ollama":
            ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            self._client = OpenAI(
                base_url=f"{ollama_host}/v1",
                api_key="ollama",  # Ollama doesn't need a real key
            )
        
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
        
        # Patch with Instructor for structured outputs
        self._instructor_client = instructor.from_openai(self._client)
        
        return self._instructor_client
    
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
        client = self._get_client()
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract data from the following academic paper text:\n\n{text}"},
        ]
        
        try:
            result = client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_model=schema,
            )
            
            # Add filename if the schema supports it
            if hasattr(result, 'filename') and filename:
                result.filename = filename
            
            return result
        
        except Exception as e:
            raise RuntimeError(f"Extraction failed: {e}")
    
    def extract_with_retry(
        self,
        text: str,
        schema: Type[T],
        filename: Optional[str] = None,
        max_retries: int = 2,
    ) -> T:
        """
        Extract with automatic retry on failure.
        
        Args:
            text: Document text
            schema: Pydantic schema
            filename: Source filename
            max_retries: Maximum retry attempts
            
        Returns:
            Extracted data
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return self.extract(text, schema, filename)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    print(f"Retry {attempt + 1}/{max_retries}: {e}")
        
        raise last_error
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get token usage statistics (if available)."""
        # TODO: Track usage across calls
        return {"note": "Usage tracking not yet implemented"}


if __name__ == "__main__":
    # Quick test
    from schema_builder import get_case_report_schema, build_extraction_model
    
    schema = get_case_report_schema()
    Model = build_extraction_model(schema, "DPMModel")
    
    extractor = StructuredExtractor()
    
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
    
    try:
        result = extractor.extract(sample_text, Model, filename="test.pdf")
        print("Extraction successful!")
        print(result.model_dump_json(indent=2))
    except Exception as e:
        print(f"Test failed (expected if no API key): {e}")
