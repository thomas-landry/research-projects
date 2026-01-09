"""
Two-Pass Extractor for hybrid local/cloud extraction.

Implements the local-first extraction strategy:
1. Pass 1: Extract all fields via local model (lenient confidence)
2. Identify low-confidence fields
3. Pass 2: Targeted cloud extraction for failures only

Expected impact: 30-40% reduction in cloud API calls.
"""
import yaml
from enum import IntEnum
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field

from core.utils import get_logger
from core.config import settings

logger = get_logger("TwoPassExtractor")


# Default config path
CONFIG_PATH = Path(__file__).parent.parent / "config" / "field_routing.yaml"


class ExtractionTier(IntEnum):
    """Extraction tier levels, ordered by cost/capability."""
    REGEX = 0
    LOCAL_LIGHTWEIGHT = 1
    LOCAL_STANDARD = 2
    CLOUD_CHEAP = 3
    CLOUD_PREMIUM = 4


class CascadeDecision(IntEnum):
    """Decision from the model cascader."""
    ACCEPT = 0
    ESCALATE = 1
    MANUAL_REVIEW = 2


@dataclass
class TierResult:
    """Result from a single tier extraction attempt."""
    field_name: str
    value: Any
    confidence: float
    tier: ExtractionTier
    supporting_quote: str = ""
    tokens_used: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "value": self.value,
            "confidence": self.confidence,
            "tier": self.tier.name,
            "supporting_quote": self.supporting_quote,
            "tokens_used": self.tokens_used,
        }


@dataclass
class TwoPassResult:
    """Result from two-pass extraction."""
    extracted_fields: Dict[str, TierResult]
    escalated_fields: List[str]
    pass1_only_count: int
    pass2_needed_count: int
    total_tokens_local: int = 0
    total_tokens_cloud: int = 0
    
    @property
    def cloud_savings_ratio(self) -> float:
        """Ratio of fields that didn't need cloud escalation."""
        total = self.pass1_only_count + self.pass2_needed_count
        if total == 0:
            return 1.0
        return self.pass1_only_count / total


class ModelCascader:
    """
    Decides whether to accept, escalate, or send to manual review.
    
    Logic:
    - High confidence (>= threshold) → ACCEPT
    - Low confidence + not at premium tier → ESCALATE
    - Low confidence at premium tier → MANUAL_REVIEW
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with optional config."""
        self.config = self._load_config(config_path or CONFIG_PATH)
        
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load tier configuration from YAML."""
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def get_threshold_for_tier(self, tier: ExtractionTier) -> float:
        """Get confidence threshold for a tier."""
        tier_config = self.config.get(f"tier_{tier.value}", {})
        return tier_config.get("confidence_threshold", 0.85)
    
    def decide(
        self, 
        result: TierResult, 
        threshold: Optional[float] = None
    ) -> CascadeDecision:
        """
        Decide what to do with an extraction result.
        
        Args:
            result: Extraction result to evaluate
            threshold: Confidence threshold (uses tier default if not provided)
            
        Returns:
            CascadeDecision (ACCEPT, ESCALATE, or MANUAL_REVIEW)
        """
        threshold = threshold or self.get_threshold_for_tier(result.tier)
        
        if result.confidence >= threshold:
            return CascadeDecision.ACCEPT
            
        # Can't escalate beyond premium tier
        if result.tier >= ExtractionTier.CLOUD_PREMIUM:
            logger.warning(
                f"Field '{result.field_name}' failed at premium tier "
                f"(conf={result.confidence:.2f}), sending to manual review"
            )
            return CascadeDecision.MANUAL_REVIEW
            
        return CascadeDecision.ESCALATE
    
    def get_next_tier(self, current_tier: ExtractionTier) -> Optional[ExtractionTier]:
        """Get the next tier for escalation."""
        if current_tier >= ExtractionTier.CLOUD_PREMIUM:
            return None
        return ExtractionTier(current_tier.value + 1)


class TwoPassExtractor:
    """
    Implements two-pass extraction strategy.
    
    Pass 1: Local model extracts all fields with lenient confidence
    Pass 2: Cloud model extracts only low-confidence fields
    
    This minimizes cloud API calls while maintaining accuracy.
    """
    
    def __init__(
        self,
        local_model: str = "qwen3:14b",  # Updated per model_evaluation.md
        cloud_model: str = "gpt-4o-mini",
        config_path: Optional[Path] = None,
    ):
        """
        Initialize the two-pass extractor.
        
        Args:
            local_model: Ollama model name for local extraction
            cloud_model: Cloud model name for escalation
            config_path: Path to field routing config
        """
        self.local_model = local_model
        self.cloud_model = cloud_model
        self.cascader = ModelCascader(config_path)
        self.config = self._load_config(config_path or CONFIG_PATH)
        
        # Track extraction statistics
        self._stats = {
            "local_extractions": 0,
            "cloud_extractions": 0,
            "manual_reviews": 0,
        }
        
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load field routing configuration."""
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        logger.warning(f"Config not found at {config_path}")
        return {}
    
    def get_field_tier(self, field_name: str) -> ExtractionTier:
        """Get the default tier for a field from config."""
        # Check each tier config for the field
        for tier_name, tier_config in self.config.items():
            if not tier_name.startswith("tier_"):
                continue
            fields = tier_config.get("fields", [])
            # Fields can be list of strings or list of dicts with 'name' key
            for f in fields:
                if isinstance(f, str) and f == field_name:
                    return self._tier_name_to_enum(tier_name)
                elif isinstance(f, dict) and f.get("name") == field_name:
                    return self._tier_name_to_enum(tier_name)
                    
        # Default to local standard
        return ExtractionTier.LOCAL_STANDARD
    
    def _tier_name_to_enum(self, tier_name: str) -> ExtractionTier:
        """Convert tier config name to enum."""
        mapping = {
            "tier_0_regex": ExtractionTier.REGEX,
            "tier_0_regex_validated": ExtractionTier.REGEX,
            "tier_1_lightweight": ExtractionTier.LOCAL_LIGHTWEIGHT,
            "tier_1_standard": ExtractionTier.LOCAL_STANDARD,
            "tier_2_cloud_cheap": ExtractionTier.CLOUD_CHEAP,
            "tier_3_cloud_premium": ExtractionTier.CLOUD_PREMIUM,
        }
        return mapping.get(tier_name, ExtractionTier.LOCAL_STANDARD)
    
    def _extract_local(
        self, 
        context: str, 
        fields: List[str],
    ) -> Dict[str, TierResult]:
        """
        Pass 1: Extract all fields using local model.
        
        This is a lenient pass - we accept lower confidence initially.
        """
        results = {}
        
        # TODO: Implement actual Ollama extraction
        # For now, this is a placeholder that returns empty results
        # The actual implementation will call self._call_local_model()
        
        for field_name in fields:
            tier = self.get_field_tier(field_name)
            # Placeholder - real implementation extracts via Ollama
            results[field_name] = TierResult(
                field_name=field_name,
                value=None,
                confidence=0.0,
                tier=tier,
            )
            
        self._stats["local_extractions"] += len(fields)
        return results
    
    def _extract_cloud(
        self, 
        context: str, 
        fields: List[str],
    ) -> Dict[str, TierResult]:
        """
        Pass 2: Extract specific fields using cloud model.
        
        Only called for fields that failed local extraction.
        """
        results = {}
        
        # TODO: Implement actual cloud extraction
        # For now, this is a placeholder
        
        for field_name in fields:
            results[field_name] = TierResult(
                field_name=field_name,
                value=None,
                confidence=0.0,
                tier=ExtractionTier.CLOUD_CHEAP,
            )
            
        self._stats["cloud_extractions"] += len(fields)
        return results
    
    def extract(
        self,
        context: str,
        fields: List[str],
        confidence_threshold: float = 0.85,
    ) -> TwoPassResult:
        """
        Perform two-pass extraction.
        
        Args:
            context: Text context to extract from
            fields: List of field names to extract
            confidence_threshold: Minimum confidence to accept
            
        Returns:
            TwoPassResult with all extractions and statistics
        """
        # Pass 1: Local extraction
        logger.info(f"Pass 1: Extracting {len(fields)} fields via local model")
        local_results = self._extract_local(context, fields)
        
        # Identify fields needing escalation
        accepted = {}
        needs_escalation = []
        
        for field_name, result in local_results.items():
            decision = self.cascader.decide(result, confidence_threshold)
            
            if decision == CascadeDecision.ACCEPT:
                accepted[field_name] = result
            elif decision == CascadeDecision.ESCALATE:
                needs_escalation.append(field_name)
            else:  # MANUAL_REVIEW
                accepted[field_name] = result  # Keep result but flag it
                self._stats["manual_reviews"] += 1
        
        # Early exit if no escalation needed
        if not needs_escalation:
            logger.info("Pass 1 complete - all fields accepted, no cloud calls needed!")
            return TwoPassResult(
                extracted_fields=accepted,
                escalated_fields=[],
                pass1_only_count=len(accepted),
                pass2_needed_count=0,
            )
        
        # Pass 2: Cloud extraction for failures
        logger.info(f"Pass 2: Escalating {len(needs_escalation)} low-confidence fields to cloud")
        cloud_results = self._extract_cloud(context, needs_escalation)
        
        # Merge results
        for field_name, result in cloud_results.items():
            accepted[field_name] = result
        
        return TwoPassResult(
            extracted_fields=accepted,
            escalated_fields=needs_escalation,
            pass1_only_count=len(fields) - len(needs_escalation),
            pass2_needed_count=len(needs_escalation),
        )
    
    def get_stats(self) -> Dict[str, int]:
        """Get extraction statistics."""
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Reset extraction statistics."""
        self._stats = {
            "local_extractions": 0,
            "cloud_extractions": 0,
            "manual_reviews": 0,
        }
