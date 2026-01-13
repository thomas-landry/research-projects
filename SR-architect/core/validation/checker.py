#!/usr/bin/env python3
"""
Extraction checker for validating extraction accuracy and consistency.

Main ExtractionChecker class that coordinates validation using LLMs.
"""

from typing import List, Dict, Any, Optional
from core.parser import DocumentChunk
from core.config import settings
from core import constants
from .models import CheckerResponse, CheckerResult, Issue
from .formatters import format_source_text, format_extracted_data, format_evidence


class ExtractionChecker:
    """Validates extraction accuracy and consistency, provides revision feedback."""
    
    SYSTEM_PROMPT = """You are a systematic review auditor verifying data extraction accuracy.

Your task is to validate extracted data against source text and evidence citations.

For each extracted field, verify:
1. ACCURACY: Does the extracted value EXACTLY match what the supporting quote says?
   - Numbers must match precisely
   - Units must be consistent
   - Ranges and confidence intervals must be complete
   
2. CONSISTENCY: Does the field semantically match the extraction theme requirements?
   - Is this the right type of data for this field?
   - Does it answer what the schema intends to capture?
   - Are there any misinterpretations?

SCORING:
- accuracy_score: Proportion of fields where extracted value matches cited quote
- consistency_score: Proportion of fields that semantically match theme requirements

OUTPUT FORMAT:
- List specific issues found with field name, type, and detail
- Provide actionable suggestions for the extractor to fix problems
- Be specific: instead of "check the value", say "The quote says 42, not 43"

If no issues are found, return high scores and empty issues/suggestions lists."""

    def __init__(
        self,
        provider: str = "openrouter",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        accuracy_weight: float = None,
        consistency_weight: float = None,
        token_tracker: Optional["TokenTracker"] = None,
    ):
        """
        Initialize the extraction checker.
        
        Args:
            provider: LLM provider
            model: Model name
            api_key: API key
            accuracy_weight: Weight for accuracy in overall score
            consistency_weight: Weight for consistency in overall score
            token_tracker: Optional token usage tracker
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model or "gpt-4o"  # Default fallback
        
        self.accuracy_weight = accuracy_weight if accuracy_weight is not None else constants.VALIDATION_WEIGHT_COMPLETENESS
        self.consistency_weight = consistency_weight if consistency_weight is not None else constants.VALIDATION_WEIGHT_ACCURACY
        self.token_tracker = token_tracker
        self._instructor_client = None
        self._async_instructor_client = None
        
        from core.utils import get_logger
        self.logger = get_logger("ExtractionChecker")

    @property
    def client(self):
        """Initialize and return the Instructor-patched client (Sync)."""
        if self._instructor_client is not None:
            return self._instructor_client
        
        from core.utils import get_llm_client
        
        self._instructor_client = get_llm_client(
            provider=self.provider,
            api_key=self.api_key
        )
        return self._instructor_client

    @property
    def async_client(self):
        """Initialize and return the Instructor-patched client (Async)."""
        if self._async_instructor_client is not None:
            return self._async_instructor_client
        
        from core.utils import get_async_llm_client
        
        self._async_instructor_client = get_async_llm_client(
            provider=self.provider,
            api_key=self.api_key
        )
        return self._async_instructor_client
    
    def check(
        self,
        source_chunks: List[DocumentChunk],
        extracted_data: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        theme: str,
        threshold: float = None,
    ) -> CheckerResult:
        """
        Validate extraction accuracy and consistency.
        
        Args:
            source_chunks: Original document chunks
            extracted_data: The extracted field values
            evidence: List of evidence items with quotes
            theme: The meta-analysis theme for consistency checking
            threshold: Score threshold to pass validation
            
        Returns:
            CheckerResult with scores, issues, and suggestions
        """
        if threshold is None:
            threshold = settings.EXTRACTION_MIN_CONFIDENCE
        client = self.client
        
        source_text = format_source_text(source_chunks)
        data_text = format_extracted_data(extracted_data)
        evidence_text = format_evidence(evidence)
        
        user_prompt = f"""Verify the following extraction for the meta-analysis theme: "{theme}"

=== ORIGINAL SOURCE TEXT ===
{source_text}

=== EXTRACTED DATA ===
{data_text}

=== EVIDENCE CITATIONS ===
{evidence_text}

Validate each extracted field:
1. Does the value match the cited quote exactly?
2. Does the field match the theme requirements?

Provide scores, issues, and specific revision suggestions."""

        try:
            response, completion = client.chat.completions.create_with_completion(
                model=self.model,
                messages=[{"role": "user", "content": user_prompt}],
                response_model=CheckerResponse,
                max_retries=constants.MAX_LLM_RETRIES_ASYNC,
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
                    operation="extraction_check"
                )
            
            # Calculate overall score
            overall_score = (
                response.accuracy_score * self.accuracy_weight +
                response.consistency_score * self.consistency_weight
            )
            
            return CheckerResult(
                accuracy_score=response.accuracy_score,
                consistency_score=response.consistency_score,
                overall_score=overall_score,
                issues=response.issues,
                suggestions=response.suggestions,
                passed=overall_score >= threshold,
            )
            
        except Exception as e:
            # On error, return a failed result that triggers re-extraction
            return CheckerResult(
                accuracy_score=0.0,
                consistency_score=0.0,
                overall_score=0.0,
                issues=[Issue(
                    field="*",
                    issue_type="error",
                    severity="high",
                    detail=f"Checker failed: {str(e)}",
                )],
                suggestions=["Re-extract all fields due to validation error"],
                passed=False,
            )

    async def check_async(
        self,
        source_chunks: List[DocumentChunk],
        extracted_data: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        theme: str,
        threshold: float = None,
    ) -> CheckerResult:
        """
        Validate extraction accuracy and consistency (Async).
        
        Args:
            source_chunks: Original document chunks
            extracted_data: The extracted field values
            evidence: List of evidence items with quotes
            theme: The meta-analysis theme for consistency checking
            threshold: Score threshold to pass validation
            
        Returns:
            CheckerResult with scores, issues, and suggestions
        """
        if threshold is None:
            threshold = settings.EXTRACTION_MIN_CONFIDENCE
        client = self.async_client
        
        source_text = format_source_text(source_chunks)
        data_text = format_extracted_data(extracted_data)
        evidence_text = format_evidence(evidence)
        
        user_prompt = f"""Verify the following extraction for the meta-analysis theme: "{theme}"

=== ORIGINAL SOURCE TEXT ===
{source_text}

=== EXTRACTED DATA ===
{data_text}

=== EVIDENCE CITATIONS ===
{evidence_text}

Validate each extracted field:
1. Does the value match the cited quote exactly?
2. Does the field match the theme requirements?

Provide scores, issues, and specific revision suggestions."""

        try:
            response, completion = await client.chat.completions.create_with_completion(
                model=self.model,
                messages=[{"role": "user", "content": user_prompt}],
                response_model=CheckerResponse,
                max_retries=constants.MAX_LLM_RETRIES_ASYNC,
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
                    operation="extraction_validation"
                )
            
            # Calculate overall score
            overall_score = (
                response.accuracy_score * self.accuracy_weight +
                response.consistency_score * self.consistency_weight
            )
            
            return CheckerResult(
                accuracy_score=response.accuracy_score,
                consistency_score=response.consistency_score,
                overall_score=overall_score,
                issues=response.issues,
                suggestions=response.suggestions,
                passed=overall_score >= threshold,
            )
            
        except Exception as e:
            # On error, return a failed result
            self.logger.error(f"Async Checker failed: {e}")
            return CheckerResult(
                accuracy_score=0.0,
                consistency_score=0.0,
                overall_score=0.0,
                issues=[Issue(
                    field="*",
                    issue_type="error",
                    severity="high",
                    detail=f"Async Checker failed: {str(e)}",
                )],
                suggestions=["Re-extract all fields due to validation error"],
                passed=False,
            )

    
    def format_revision_prompt(self, result: CheckerResult) -> str:
        """
        Format checker feedback as revision instructions for the extractor.
        
        Args:
            result: The CheckerResult from validation
            
        Returns:
            Formatted string to include in extraction prompt
        """
        if result.passed or not result.suggestions:
            return ""
        
        lines = [
            "\n--- REVISION INSTRUCTIONS ---",
            "The previous extraction had issues. Please fix the following:",
            "",
        ]
        
        # Add specific issues
        for issue in result.issues:
            lines.append(f"• [{issue.field}] {issue.issue_type}: {issue.detail}")
            if issue.suggested_fix:
                lines.append(f"  → Fix: {issue.suggested_fix}")
        
        lines.append("")
        
        # Add general suggestions
        if result.suggestions:
            lines.append("Specific corrections needed:")
            for suggestion in result.suggestions:
                lines.append(f"  - {suggestion}")
        
        lines.append("\nBe especially careful with numerical values and ensure quotes match exactly.")
        
        return "\n".join(lines)
