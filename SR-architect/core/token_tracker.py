#!/usr/bin/env python3
"""
Token usage tracking and cost estimation for OpenRouter API.

Provides:
- Token counting from API responses
- Price lookups from OpenRouter models API
- Pre-flight cost estimation
- Session-level cost aggregation
- Standardized cost reports
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pydantic import BaseModel

from core.config import settings
from core.utils import get_logger

logger = get_logger("TokenTracker")


@dataclass
class UsageRecord:
    """Single API call usage record."""
    timestamp: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    filename: Optional[str] = None
    operation: str = "extraction"
    tier: Optional[str] = None
    field: Optional[str] = None


@dataclass
class CostEstimate:
    """Pre-flight cost estimation result."""
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_total_tokens: int
    estimated_cost_usd: float
    model: str
    num_documents: int
    tokens_per_document: int
    confidence: str  # "low", "medium", "high"


class TokenTracker:
    """
    Track token usage and estimate costs for OpenRouter API calls.
    
    Usage:
        tracker = TokenTracker()
        
        # Before extraction - get estimate
        estimate = tracker.estimate_extraction_cost(
            documents=["doc1.pdf", "doc2.pdf"],
            avg_tokens_per_doc=10000
        )
        tracker.display_cost_report(estimate)
        
        # After each API call - record usage
        tracker.record_usage(response.usage, model="claude-3.5-sonnet", filename="doc1.pdf")
        
        # At end - get summary
        summary = tracker.get_session_summary()
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        log_file: Optional[Path] = None,
    ):
        """
        Initialize token tracker.
        
        Args:
            api_key: OpenRouter API key for fetching live pricing
            log_file: Optional file to persist usage logs
        """
        from core.config import settings
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.log_file = log_file
        
        # Session tracking
        self.session_start = datetime.now()
        self.records: List[UsageRecord] = []
        
        # Cache model pricing
        self._pricing_cache: Dict[str, Dict[str, float]] = {}
        
    def estimate_tokens(self, text: str, model: str = "gpt-4o") -> int:
        """
        Estimate token count using tiktoken if available.
        Falls back to character-based estimation if tiktoken is unavailable.
        
        Args:
            text: Text to estimate tokens for
            model: Model name for tiktoken encoding selection
            
        Returns:
            Estimated token count
        """
        try:
            import tiktoken
            # Map openrouter models to tiktoken encodings
            if "claude" in model:
                # Claude doesn't have public tiktoken, use cl100k_base approximation
                encoding = tiktoken.get_encoding("cl100k_base")
            else:
                try:
                    encoding = tiktoken.encoding_for_model(model)
                except KeyError:
                    encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            logger.debug("tiktoken not available, using character-based estimation")
            return len(text) // settings.CHARS_PER_TOKEN_ESTIMATE
        except Exception as e:
            logger.warning(f"Token estimation failed: {e}, using fallback")
            return len(text) // settings.CHARS_PER_TOKEN_ESTIMATE

    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """
        Get pricing for a model (per 1M tokens).
        
        Args:
            model: Model identifier (e.g., "anthropic/claude-3.5-sonnet")
            
        Returns:
            Dict with 'prompt' and 'completion' prices in USD per 1M tokens
        """
        if model is None:
            model = "anthropic/claude-3.5-sonnet"
            
        # Check cache first
        if model in self._pricing_cache:
            return self._pricing_cache[model]
        
        # Try to fetch from OpenRouter API (ALWAYS try API first)
        try:
            if self.api_key:
                response = requests.get(
                    settings.OPENROUTER_MODELS_API,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=5
                )
                if response.status_code == 200:
                    models_data = response.json().get("data", [])
                    for model_data in models_data:
                        if model_data.get("id") == model:
                            pricing = model_data.get("pricing", {})
                            result = {
                                "prompt": float(pricing.get("prompt", 0)) * settings.TOKENS_PER_MILLION,
                                "completion": float(pricing.get("completion", 0)) * settings.TOKENS_PER_MILLION,
                            }
                            self._pricing_cache[model] = result
                            logger.debug(f"Fetched pricing for {model} from OpenRouter API")
                            return result
        except requests.Timeout as e:
            logger.warning(f"OpenRouter API timeout while fetching pricing: {e}")
        except requests.RequestException as e:
            logger.warning(f"OpenRouter API request failed: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error fetching model pricing: {e}", exc_info=True)
        
        # Use fallback pricing (only if API failed)
        if model in settings.FALLBACK_PRICING:
            logger.debug(f"Using fallback pricing for {model}")
            return settings.FALLBACK_PRICING[model]
        
        # Try partial match
        for key, value in settings.FALLBACK_PRICING.items():
            if key in model or model in key:
                logger.debug(f"Using partial match fallback pricing: {key} for {model}")
                return value
        
        # Ultimate fallback - use default model pricing
        logger.warning(f"No pricing found for {model}, using default model pricing")
        return settings.FALLBACK_PRICING[settings.OPENROUTER_MODEL]
    
    def calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
    ) -> float:
        """
        Calculate cost for a given token usage.
        
        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            model: Model identifier
            
        Returns:
            Cost in USD
        """
        pricing = self.get_model_pricing(model)
        
        prompt_cost = (prompt_tokens / settings.TOKENS_PER_MILLION) * pricing["prompt"]
        completion_cost = (completion_tokens / settings.TOKENS_PER_MILLION) * pricing["completion"]
        
        return prompt_cost + completion_cost
    
    def record_usage(
        self,
        usage: Dict[str, Any],
        model: str,
        filename: Optional[str] = None,
        operation: str = "extraction",
        tier: Optional[str] = None,
        field: Optional[str] = None,
    ) -> UsageRecord:
        """
        Record token usage from an API response (Sync).
        """
        record = self._create_record(usage, model, filename, operation, tier, field)
        self.records.append(record)
        
        if self.log_file:
            self._append_to_log(record)
        
        return record

    async def record_usage_async(
        self,
        usage: Dict[str, Any],
        model: str,
        filename: Optional[str] = None,
        operation: str = "extraction",
        tier: Optional[str] = None,
        field: Optional[str] = None,
    ) -> UsageRecord:
        """
        Record token usage from an API response (Async).
        Offloads file I/O to executor to prevent blocking the loop.
        """
        record = self._create_record(usage, model, filename, operation, tier, field)
        self.records.append(record)
        
        if self.log_file:
            import asyncio
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: self._append_to_log(record))
        
        return record

    def _create_record(
        self,
        usage: Dict[str, Any],
        model: str,
        filename: Optional[str],
        operation: str,
        tier: Optional[str],
        field: Optional[str]
    ) -> UsageRecord:
        """Helper to create UsageRecord object."""
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        
        # Check for direct cost
        if "cost" in usage:
            cost = float(usage["cost"])
        elif "cost_usd" in usage:
            cost = float(usage["cost_usd"])
        else:
            cost = self.calculate_cost(prompt_tokens, completion_tokens, model)
        
        return UsageRecord(
            timestamp=datetime.now().isoformat(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            filename=filename,
            operation=operation,
            tier=tier,
            field=field,
        )
    
    def _append_to_log(self, record: UsageRecord):
        """Append record to log file."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record.__dict__) + "\n")
    
    def estimate_extraction_cost(
        self,
        num_documents: int,
        avg_tokens_per_doc: int = None,
        avg_output_tokens: int = None,
        model: str = None,
        num_passes: int = 1,
    ) -> CostEstimate:
        """
        Estimate cost for an extraction run.
        
        Args:
            num_documents: Number of PDFs to process
            avg_tokens_per_doc: Average input tokens per document
            avg_output_tokens: Average output tokens per extraction
            model: Model to use
            num_passes: Number of extraction passes (for multi-schema approach)
            
        Returns:
            CostEstimate with breakdown
        """
        # Use config defaults if not provided
        if avg_tokens_per_doc is None:
            avg_tokens_per_doc = settings.DEFAULT_TOKENS_PER_DOCUMENT
        if avg_output_tokens is None:
            avg_output_tokens = settings.DEFAULT_OUTPUT_TOKENS
        if model is None:
            model = settings.OPENROUTER_MODEL
        
        total_input = num_documents * avg_tokens_per_doc * num_passes
        total_output = num_documents * avg_output_tokens * num_passes
        total_tokens = total_input + total_output
        
        cost = self.calculate_cost(total_input, total_output, model)
        
        # Confidence based on estimation quality
        if avg_tokens_per_doc == settings.DEFAULT_TOKENS_PER_DOCUMENT:  # Using default
            confidence = "medium"
        else:
            confidence = "high"
        
        return CostEstimate(
            estimated_input_tokens=total_input,
            estimated_output_tokens=total_output,
            estimated_total_tokens=total_tokens,
            estimated_cost_usd=cost,
            model=model,
            num_documents=num_documents,
            tokens_per_document=avg_tokens_per_doc,
            confidence=confidence,
        )
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session usage."""
        if not self.records:
            return {
                "total_records": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "session_duration_seconds": 0,
            }
        
        total_prompt = sum(r.prompt_tokens for r in self.records)
        total_completion = sum(r.completion_tokens for r in self.records)
        total_tokens = sum(r.total_tokens for r in self.records)
        total_cost = sum(r.cost_usd for r in self.records)
        
        duration = (datetime.now() - self.session_start).total_seconds()
        
        # By model breakdown
        by_model: Dict[str, Dict[str, Any]] = {}
        for r in self.records:
            if r.model not in by_model:
                by_model[r.model] = {"calls": 0, "tokens": 0, "cost": 0.0}
            by_model[r.model]["calls"] += 1
            by_model[r.model]["tokens"] += r.total_tokens
            by_model[r.model]["cost"] += r.cost_usd
        
        return {
            "total_records": len(self.records),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "session_duration_seconds": round(duration, 1),
            "by_model": by_model,
        }
    
    def display_cost_report(self, estimate: CostEstimate) -> str:
        """
        Generate a standardized cost report for user approval.
        
        Args:
            estimate: Pre-flight cost estimate
            
        Returns:
            Formatted report string
        """
        pricing = self.get_model_pricing(estimate.model)
        
        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    EXTRACTION COST ESTIMATE                       ║
╠══════════════════════════════════════════════════════════════════╣
║ Model: {estimate.model:<55} ║
║ Documents: {estimate.num_documents:<52} ║
║ Tokens/doc: ~{estimate.tokens_per_document:,}<49 ║
╠══════════════════════════════════════════════════════════════════╣
║ ESTIMATED USAGE:                                                  ║
║   Input tokens:  {estimate.estimated_input_tokens:>12,}                                  ║
║   Output tokens: {estimate.estimated_output_tokens:>12,}                                  ║
║   Total tokens:  {estimate.estimated_total_tokens:>12,}                                  ║
╠══════════════════════════════════════════════════════════════════╣
║ PRICING (per 1M tokens):                                          ║
║   Input:  ${pricing['prompt']:.2f}                                             ║
║   Output: ${pricing['completion']:.2f}                                            ║
╠══════════════════════════════════════════════════════════════════╣
║ ESTIMATED COST: ${estimate.estimated_cost_usd:>8.4f} USD                                ║
║ Confidence: {estimate.confidence:<54} ║
╚══════════════════════════════════════════════════════════════════╝
"""
        return report
    
    def display_session_summary(self) -> str:
        """Generate formatted session summary."""
        summary = self.get_session_summary()
        
        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    SESSION USAGE SUMMARY                          ║
╠══════════════════════════════════════════════════════════════════╣
║ API Calls: {summary['total_records']:<55} ║
║ Duration: {summary['session_duration_seconds']:.1f}s<53 ║
╠══════════════════════════════════════════════════════════════════╣
║ TOKEN USAGE:                                                      ║
║   Prompt tokens:     {summary['total_prompt_tokens']:>12,}                              ║
║   Completion tokens: {summary['total_completion_tokens']:>12,}                              ║
║   Total tokens:      {summary['total_tokens']:>12,}                              ║
╠══════════════════════════════════════════════════════════════════╣
║ ACTUAL COST: ${summary['total_cost_usd']:>8.4f} USD                                   ║
╚══════════════════════════════════════════════════════════════════╝
"""
        return report


def estimate_document_tokens(text: str) -> int:
    """
    Estimate token count for a document using approximate tokenization.
    
    Uses character-based estimation as a rough estimate for English text.
    For more accuracy, use tiktoken library via TokenTracker.estimate_tokens().
    
    Args:
        text: Document text
        
    Returns:
        Estimated token count
    """
    # Simple approximation using config constant
    return len(text) // settings.CHARS_PER_TOKEN_ESTIMATE


if __name__ == "__main__":
    # Demo usage
    tracker = TokenTracker()
    
    # Pre-flight estimate
    estimate = tracker.estimate_extraction_cost(
        num_documents=80,
        avg_tokens_per_doc=10000,
        avg_output_tokens=2000,
        model="anthropic/claude-sonnet-4-20250514",
    )
    
    print(tracker.display_cost_report(estimate))
    
    # Simulate some usage
    tracker.record_usage(
        usage={"prompt_tokens": 10500, "completion_tokens": 1800},
        model="anthropic/claude-sonnet-4-20250514",
        filename="paper1.pdf",
    )
    
    tracker.record_usage(
        usage={"prompt_tokens": 8200, "completion_tokens": 2100},
        model="anthropic/claude-sonnet-4-20250514",
        filename="paper2.pdf",
    )
    
    print(tracker.display_session_summary())
