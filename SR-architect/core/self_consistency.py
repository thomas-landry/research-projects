"""
Self-Consistency Voting for critical numeric fields.

Runs multiple extractions with temperature variation and accepts
values only if they agree within a tolerance threshold. This
reduces hallucination for important numeric fields.

Per plan.md: Apply to sample_size, mean_age, mortality_rate.
"""
import statistics
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from collections import Counter

from core.utils import get_logger

logger = get_logger("SelfConsistency")

# Default fields that require self-consistency voting
CRITICAL_NUMERIC_FIELDS = [
    "sample_size",
    "case_count",
    "mean_age",
    "median_age",
    "mortality_rate",
    "survival_rate",
    "response_rate",
]

# Tolerance thresholds per field type
DEFAULT_TOLERANCE = 0.05  # 5%


@dataclass
class VoteResult:
    """Result of self-consistency voting."""
    field_name: str
    values: List[Any]
    consensus_value: Any
    accepted: bool
    needs_escalation: bool = False
    variance: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    
    
class SelfConsistencyVoter:
    """
    Self-consistency voting for extraction reliability.
    
    Runs N extractions and accepts only if:
    - Numeric fields: all values within tolerance %
    - String fields: majority vote (2/3+ agreement)
    """
    
    def __init__(
        self,
        num_votes: int = 3,
        temperature: float = 0.3,
        tolerance: float = DEFAULT_TOLERANCE,
        critical_fields: Optional[List[str]] = None,
    ):
        """
        Initialize self-consistency voter.
        
        Args:
            num_votes: Number of extraction attempts (default 3)
            temperature: LLM temperature for variation (default 0.3)
            tolerance: Numeric variance tolerance (default 5%)
            critical_fields: Fields requiring voting
        """
        self.num_votes = num_votes
        self.temperature = temperature
        self.tolerance = tolerance
        self.critical_fields = critical_fields or CRITICAL_NUMERIC_FIELDS
        
        # Statistics tracking
        self._stats = {
            "total_votes": 0,
            "accepted": 0,
            "escalated": 0,
        }
    
    def vote(
        self,
        field_name: str,
        values: List[Any],
    ) -> VoteResult:
        """
        Vote on a set of extracted values.
        
        Args:
            field_name: Name of the field
            values: List of extracted values from multiple runs
            
        Returns:
            VoteResult with consensus decision
        """
        self._stats["total_votes"] += 1
        
        if not values:
            return VoteResult(
                field_name=field_name,
                values=[],
                consensus_value=None,
                accepted=False,
                needs_escalation=True,
                reason="No values to vote on",
            )
        
        # Check if numeric or string voting
        if self._is_numeric_field(field_name, values):
            return self._vote_numeric(field_name, values)
        else:
            return self._vote_string(field_name, values)
    
    def _is_numeric_field(self, field_name: str, values: List[Any]) -> bool:
        """Check if field should use numeric voting."""
        # Check by field name first
        numeric_keywords = ["size", "count", "age", "rate", "ratio", "number"]
        if any(kw in field_name.lower() for kw in numeric_keywords):
            return True
        
        # Check by value type
        try:
            [float(v) for v in values if v is not None]
            return True
        except (ValueError, TypeError):
            return False
    
    def _vote_numeric(
        self,
        field_name: str,
        values: List[Any],
    ) -> VoteResult:
        """Numeric voting: check if all values within tolerance."""
        # Convert to floats
        try:
            numeric_values = [float(v) for v in values if v is not None]
        except (ValueError, TypeError) as e:
            return VoteResult(
                field_name=field_name,
                values=values,
                consensus_value=None,
                accepted=False,
                needs_escalation=True,
                reason=f"Cannot convert to numeric: {e}",
            )
        
        if not numeric_values:
            return VoteResult(
                field_name=field_name,
                values=values,
                consensus_value=None,
                accepted=False,
                needs_escalation=True,
                reason="No valid numeric values",
            )
        
        # Calculate statistics
        mean_val = statistics.mean(numeric_values)
        variance = 0.0
        
        if len(numeric_values) > 1:
            # Calculate max deviation from mean as percentage
            max_deviation = max(abs(v - mean_val) for v in numeric_values)
            if mean_val != 0:
                variance = max_deviation / abs(mean_val)
            else:
                variance = max_deviation
        
        # Check tolerance
        accepted = variance <= self.tolerance
        
        if accepted:
            self._stats["accepted"] += 1
            consensus = round(mean_val, 2) if "rate" in field_name.lower() else int(round(mean_val))
            confidence = 1.0 - variance
            logger.debug(f"Vote accepted for {field_name}: {consensus} (variance={variance:.2%})")
        else:
            self._stats["escalated"] += 1
            consensus = mean_val
            confidence = max(0.5, 1.0 - variance)
            logger.info(f"Vote failed for {field_name}: variance {variance:.2%} exceeds {self.tolerance:.0%}")
        
        return VoteResult(
            field_name=field_name,
            values=values,
            consensus_value=consensus,
            accepted=accepted,
            needs_escalation=not accepted,
            variance=variance,
            confidence=confidence,
            reason="" if accepted else f"Variance {variance:.2%} exceeds tolerance {self.tolerance:.0%}",
        )
    
    def _vote_string(
        self,
        field_name: str,
        values: List[Any],
    ) -> VoteResult:
        """String voting: majority vote (2/3+ agreement)."""
        # Count occurrences
        counts = Counter(str(v) for v in values if v is not None)
        
        if not counts:
            return VoteResult(
                field_name=field_name,
                values=values,
                consensus_value=None,
                accepted=False,
                needs_escalation=True,
                reason="No valid string values",
            )
        
        # Get most common
        most_common, count = counts.most_common(1)[0]
        total = sum(counts.values())
        agreement_ratio = count / total
        
        # Require 2/3 majority for strings
        threshold = 2 / 3
        accepted = agreement_ratio >= threshold
        
        if accepted:
            self._stats["accepted"] += 1
            confidence = agreement_ratio
            logger.debug(f"Vote accepted for {field_name}: '{most_common}' ({count}/{total})")
        else:
            self._stats["escalated"] += 1
            confidence = agreement_ratio
            logger.info(f"Vote failed for {field_name}: no majority ({count}/{total})")
        
        return VoteResult(
            field_name=field_name,
            values=values,
            consensus_value=most_common,
            accepted=accepted,
            needs_escalation=not accepted,
            variance=1.0 - agreement_ratio,
            confidence=confidence,
            reason="" if accepted else f"No majority: {count}/{total} ({agreement_ratio:.0%})",
        )
    
    def extract_with_voting(
        self,
        extract_fn: Callable[..., Dict[str, Any]],
        field_name: str,
        context: str,
        **kwargs,
    ) -> VoteResult:
        """
        Convenience method to extract a field with voting.
        
        Args:
            extract_fn: Function that performs extraction
            field_name: Field to extract
            context: Text context
            **kwargs: Additional args for extract_fn
            
        Returns:
            VoteResult with consensus
        """
        values = []
        
        for i in range(self.num_votes):
            try:
                result = extract_fn(context=context, temperature=self.temperature, **kwargs)
                if field_name in result:
                    values.append(result[field_name])
            except Exception as e:
                logger.warning(f"Extraction attempt {i+1} failed: {e}")
        
        return self.vote(field_name, values)
    
    def should_use_voting(self, field_name: str) -> bool:
        """Check if a field requires self-consistency voting."""
        return field_name in self.critical_fields
    
    def get_stats(self) -> Dict[str, Any]:
        """Get voting statistics."""
        total = self._stats["total_votes"]
        return {
            **self._stats,
            "acceptance_rate": self._stats["accepted"] / total if total > 0 else 0,
        }
