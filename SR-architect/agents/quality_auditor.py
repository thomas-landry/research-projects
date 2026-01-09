#!/usr/bin/env python3
"""
Quality Auditor Agent - Verifies extraction quality against source text.

This agent checks if the extracted values are actually supported by the quotes provided.
It acts as a second pair of eyes to hallucination-check the Extractor.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class FieldAudit(BaseModel):
    """Audit result for a single field."""
    field_name: str
    is_correct: bool = Field(description="Does the quote support the value?")
    confidence: float = Field(description="Confidence in this judgment (0-1)")
    explanation: str = Field(description="Why it is correct or incorrect")
    severity: str = Field(description="low, medium, high (if incorrect)")

class AuditReport(BaseModel):
    """Complete audit report for an extraction."""
    audits: List[FieldAudit]
    overall_score: float = Field(description="0-1 score representing overall quality")
    critical_errors: int = Field(description="Count of high severity errors")
    passed: bool = Field(description="Whether the extraction passes the audit")

class QualityAuditorAgent:
    """
    Audits extraction quality by verifying values against source quotes.
    """
    
    AUDIT_PROMPT = """You are a QA Auditor for a scientific data extraction pipeline.
    
    Your job is to verify that the extracted VALUE is supported by the QUOTE from the text.
    
    FIELD: {field}
    EXTRACTED VALUE: {value}
    SOURCE QUOTE: "{quote}"
    
    Task:
    1. Check if the Value is logically derived from the Quote.
    2. Check if the Quote actually exists in the Source Text (if provided).
    3. Flag specific issues (hallucinations, wrong units, misinterpretation).
    """
    
    def __init__(self, provider: str = "openrouter", model: Optional[str] = None, token_tracker: Optional["TokenTracker"] = None):
        self.provider = provider
        self.model = model or "gpt-4o" # Verification needs a strong model
        self.token_tracker = token_tracker
        self._client = None
        
        from core.utils import get_logger
        self.logger = get_logger("QualityAuditorAgent")
        
    @property
    def client(self):
        """Initialize and return the Instructor-patched client (Sync)."""
        if self._client is not None:
            return self._client
        from core.utils import get_llm_client
        self._client = get_llm_client(self.provider)
        return self._client

    @property
    def async_client(self):
        """Initialize and return the Instructor-patched client (Async)."""
        if hasattr(self, "_async_client") and self._async_client is not None:
            return self._async_client
        from core.utils import get_async_llm_client
        self._async_client = get_async_llm_client(self.provider)
        return self._async_client

    def audit_extraction(self, data: Dict[str, Any], evidence: List[Dict[str, Any]], source_text: Optional[str] = None) -> AuditReport:
        """
        Audit a full extraction result.
        
        Args:
            data: The extracted dictionary
            evidence: List of evidence items (field, value, quote, confidence)
            source_text: The full text of the document/chunk to verify quotes against
        """
        from core.text_utils import find_best_substring_match
        
        audits = []
        
        # We process each field that has evidence
        for item in evidence:
            field_name = item.get("field_name", "")
            value = item.get("extracted_value", "")
            quote = item.get("exact_quote", "")
            
            # Skip if no quote (can't audit)
            if not quote:
                continue

            # 1. Verify Quote Existence (Deterministically)
            quote_status = "verified"
            if source_text:
                matched_text, score, span = find_best_substring_match(source_text, quote, threshold=0.8)
                if matched_text:
                    if score < 1.0:
                        quote = matched_text  # Auto-correct to exact text
                        quote_status = f"fuzzy_matched (score={score:.2f})"
                else:
                    # Quote not found in text
                    audits.append(FieldAudit(
                        field_name=field_name,
                        is_correct=False,
                        confidence=1.0,
                        explanation=f"Quote not found in source text (best match score < 0.8). This is a hallucination.",
                        severity="high"
                    ))
                    continue
                
            # 2. Verify Logic (LLM)
            prompt = self.AUDIT_PROMPT.format(
                field=field_name,
                value=str(value),
                quote=quote
            )
            
            try:
                result, completion = self.client.chat.completions.create_with_completion(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_model=FieldAudit,
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
                        operation="quality_audit"
                    )
                
                # Check consistency: result.field_name should match
                result.field_name = field_name 
                if quote_status.startswith("fuzzy"):
                     result.explanation = f"{result.explanation} [Note: Quote was fuzzy matched]"
                audits.append(result)
                
            except Exception as e:
                self.logger.error(f"Audit failed for {field_name}: {e}")
        
        # Calculate summary metrics
        if not audits:
            return AuditReport(audits=[], overall_score=1.0, critical_errors=0, passed=True)
            
        critical_errors = sum(1 for a in audits if not a.is_correct and a.severity == "high")
        correct_count = sum(1 for a in audits if a.is_correct)
        score = correct_count / len(audits)
        
        return AuditReport(
            audits=audits,
            overall_score=score,
            critical_errors=critical_errors,
            passed=score >= 0.8 and critical_errors == 0
        )

    async def audit_extraction_async(self, data: Dict[str, Any], evidence: List[Dict[str, Any]], source_text: Optional[str] = None) -> AuditReport:
        """
        Audit a full extraction result (Async).
        
        Args:
            data: The extracted dictionary
            evidence: List of evidence items
            source_text: The full text of the document/chunk to verify quotes against
        """
        import asyncio
        from core.text_utils import find_best_substring_match
        
        # Helper for a single field audit
        async def audit_field(item):
            field_name = item.get("field_name", "")
            value = item.get("extracted_value", "")
            quote = item.get("exact_quote", "")
            
            if not quote:
                return None
            
            # 1. Verify Quote Existence (Deterministically)
            quote_status = "verified"
            if source_text:
                matched_text, score, span = find_best_substring_match(source_text, quote, threshold=0.8)
                if matched_text:
                    if score < 1.0:
                        quote = matched_text  # Auto-correct to exact text
                        quote_status = f"fuzzy_matched (score={score:.2f})"
                else:
                    # Quote not found in text
                    return FieldAudit(
                        field_name=field_name,
                        is_correct=False,
                        confidence=1.0,
                        explanation=f"Quote not found in source text (best match score < 0.8). This is a hallucination.",
                        severity="high"
                    )

            # 2. Verify Logic (LLM)
            prompt = self.AUDIT_PROMPT.format(
                field=field_name,
                value=str(value),
                quote=quote
            )
            
            try:
                result, completion = await self.async_client.chat.completions.create_with_completion(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_model=FieldAudit,
                    max_retries=2,
                    extra_body={"usage": {"include": True}}
                )
                
                # Record usage
                if self.token_tracker and hasattr(completion, 'usage') and completion.usage:
                    await self.token_tracker.record_usage_async(
                        usage={
                            "prompt_tokens": completion.usage.prompt_tokens,
                            "completion_tokens": completion.usage.completion_tokens,
                            "total_tokens": completion.usage.total_tokens
                        },
                        model=self.model,
                        operation="quality_audit_async"
                    )
                result.field_name = field_name
                if quote_status.startswith("fuzzy"):
                     result.explanation = f"{result.explanation} [Note: Quote was fuzzy matched]"
                return result
            except Exception as e:
                self.logger.error(f"Async Audit failed for {field_name}: {e}")
                return None

        # Run audits in parallel
        audit_tasks = [audit_field(item) for item in evidence]
        results = await asyncio.gather(*audit_tasks)
        
        audits = [r for r in results if r is not None]
        
        if not audits:
            return AuditReport(audits=[], overall_score=1.0, critical_errors=0, passed=True)
            
        critical_errors = sum(1 for a in audits if not a.is_correct and a.severity == "high")
        correct_count = sum(1 for a in audits if a.is_correct)
        score = correct_count / len(audits)
        
        return AuditReport(
            audits=audits,
            overall_score=score,
            critical_errors=critical_errors,
            passed=score >= 0.8 and critical_errors == 0
        )

