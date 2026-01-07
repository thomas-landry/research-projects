#!/usr/bin/env python3
"""
Extraction Checker with Feedback Mechanism.

Validates extraction accuracy and consistency, provides revision feedback
for the extractor to iterate until quality thresholds are met.
"""

import os
from typing import List, Dict, Any, Optional, Type
from dataclasses import dataclass
from pydantic import BaseModel, Field

from .parser import DocumentChunk


class Issue(BaseModel):
    """A specific issue found during validation."""
    field: str
    issue_type: str  # "mismatch", "missing_quote", "semantic_error", "inconsistent"
    severity: str = "medium"  # "low", "medium", "high"
    detail: str
    suggested_fix: Optional[str] = None


class CheckerResponse(BaseModel):
    """Structured response from the checker LLM."""
    accuracy_score: float = Field(ge=0.0, le=1.0, description="Do values match their cited quotes?")
    consistency_score: float = Field(ge=0.0, le=1.0, description="Do semantics align with theme?")
    issues: List[Issue] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list, description="Revision prompts for extractor")


@dataclass
class CheckerResult:
    """Result of extraction validation."""
    accuracy_score: float
    consistency_score: float
    overall_score: float
    issues: List[Issue]
    suggestions: List[str]
    passed: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "accuracy_score": self.accuracy_score,
            "consistency_score": self.consistency_score,
            "overall_score": self.overall_score,
            "issues": [i.model_dump() for i in self.issues],
            "suggestions": self.suggestions,
            "passed": self.passed,
        }


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
        accuracy_weight: float = 0.6,
        consistency_weight: float = 0.4,
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
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model or "gpt-4o"  # Default fallback, specific defaults handled in utils or env
        
        self.accuracy_weight = accuracy_weight
        self.consistency_weight = consistency_weight
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
    
    def _format_source_text(self, chunks: List[DocumentChunk], max_chars: int = 8000) -> str:
        """Format source chunks for the checker prompt."""
        text_parts = []
        total_chars = 0
        
        for i, chunk in enumerate(chunks):
            section_label = f"[{chunk.section}]" if chunk.section else ""
            chunk_text = f"--- Chunk {i} {section_label} ---\n{chunk.text}\n"
            
            if total_chars + len(chunk_text) > max_chars:
                break
            
            text_parts.append(chunk_text)
            total_chars += len(chunk_text)
        
        return "\n".join(text_parts)
    
    def _format_extracted_data(self, data: Dict[str, Any]) -> str:
        """Format extracted data for display."""
        lines = []
        for field, value in data.items():
            if not field.endswith("_quote") and not field.startswith("_"):
                lines.append(f"  {field}: {value}")
        return "\n".join(lines)
    
    def _format_evidence(self, evidence: List[Dict[str, Any]]) -> str:
        """Format evidence citations for the checker."""
        if not evidence:
            return "No evidence citations provided."
        
        lines = []
        for item in evidence:
            field = item.get("field_name", "unknown")
            value = item.get("extracted_value", "N/A")
            quote = item.get("exact_quote", "No quote")
            conf = item.get("confidence", 0)
            
            lines.append(f"  {field}:")
            lines.append(f"    Value: {value}")
            lines.append(f"    Quote: \"{quote}\"")
            lines.append(f"    Confidence: {conf}")
            lines.append("")
        
        return "\n".join(lines)
    
    def check(
        self,
        source_chunks: List[DocumentChunk],
        extracted_data: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        theme: str,
        threshold: float = 0.9,
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
        client = self.client
        
        source_text = self._format_source_text(source_chunks)
        data_text = self._format_extracted_data(extracted_data)
        evidence_text = self._format_evidence(evidence)
        
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
                max_retries=2,
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
        threshold: float = 0.9,
    ) -> CheckerResult:
        """
        Validate extraction accuracy and consistency (Async).
        """
        client = self.async_client
        
        source_text = self._format_source_text(source_chunks)
        data_text = self._format_extracted_data(extracted_data)
        evidence_text = self._format_evidence(evidence)
        
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


if __name__ == "__main__":
    # Test with sample data
    sample_chunks = [
        DocumentChunk(
            text="We enrolled 42 patients with confirmed DPM. Mean age was 56 years.",
            section="Methods"
        ),
        DocumentChunk(
            text="Treatment response was observed in 85% (36/42) of patients.",
            section="Results"
        ),
    ]
    
    sample_data = {
        "sample_size": 43,  # Intentional error
        "mean_age": 56,
        "response_rate": "85%",
    }
    
    sample_evidence = [
        {
            "field_name": "sample_size",
            "extracted_value": 43,
            "exact_quote": "We enrolled 42 patients",
            "confidence": 0.9,
        },
        {
            "field_name": "mean_age",
            "extracted_value": 56,
            "exact_quote": "Mean age was 56 years",
            "confidence": 0.95,
        },
    ]
    
    theme = "patient demographics and treatment outcomes"
    
    print("Testing extraction checker...")
    
    try:
        checker = ExtractionChecker()
        result = checker.check(sample_chunks, sample_data, sample_evidence, theme)
        
        print(f"Accuracy: {result.accuracy_score:.2f}")
        print(f"Consistency: {result.consistency_score:.2f}")
        print(f"Overall: {result.overall_score:.2f}")
        print(f"Passed: {result.passed}")
        
        if result.issues:
            print("\nIssues found:")
            for issue in result.issues:
                print(f"  [{issue.field}] {issue.detail}")
        
        if result.suggestions:
            print("\nSuggestions:")
            for s in result.suggestions:
                print(f"  - {s}")
                
    except Exception as e:
        print(f"Test failed (expected if no API key): {e}")
