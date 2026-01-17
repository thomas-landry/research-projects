"""
Baseline Measurement for Extraction Accuracy.

Implements per-field and per-tier accuracy measurement against gold standard.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


def calculate_field_accuracy(
    predictions: List[Dict[str, Any]],
    gold_standard: List[Dict[str, Any]],
    field: str
) -> float:
    """
    Calculate accuracy for a single field.
    
    Args:
        predictions: List of prediction dictionaries
        gold_standard: List of gold standard dictionaries
        field: Field name to calculate accuracy for
    
    Returns:
        Accuracy as float between 0.0 and 1.0
    """
    if len(predictions) != len(gold_standard):
        raise ValueError("Predictions and gold standard must have same length")
    
    if len(predictions) == 0:
        return 0.0
    
    correct = 0
    total = len(predictions)
    
    for pred, gold in zip(predictions, gold_standard):
        pred_value = pred.get(field)
        gold_value = gold.get(field)
        
        # Check for FindingReport-like objects (duck typing)
        # For binary accuracy, we only care if the status matches
        if hasattr(pred_value, 'status') and hasattr(gold_value, 'status'):
            if pred_value.status == gold_value.status:
                correct += 1
        elif pred_value == gold_value:
            # Fallback for standard types (bool, str, int, None)
            correct += 1
    
    return correct / total


def calculate_tier_accuracy(
    field_accuracies: Dict[str, float],
    tier_config: Dict[int, List[str]],
    tier: int
) -> float:
    """
    Calculate aggregate accuracy for a tier.
    
    Args:
        field_accuracies: Dictionary of field -> accuracy
        tier_config: Dictionary of tier -> list of fields
        tier: Tier number to calculate accuracy for
    
    Returns:
        Average accuracy of fields in the tier
    """
    fields_in_tier = tier_config.get(tier, [])
    
    if not fields_in_tier:
        return 0.0
    
    accuracies = [
        field_accuracies.get(field, 0.0)
        for field in fields_in_tier
    ]
    
    return sum(accuracies) / len(accuracies)


def calculate_null_rate(
    data: List[Dict[str, Any]],
    field: str
) -> float:
    """
    Calculate NULL rate for a field.
    
    Args:
        data: List of data dictionaries
        field: Field name to calculate NULL rate for
    
    Returns:
        NULL rate as float between 0.0 and 1.0
    """
    if len(data) == 0:
        return 0.0
    
    null_count = sum(1 for row in data if row.get(field) is None)
    
    return null_count / len(data)


@dataclass
class BaselineMeasurement:
    """
    Calculate baseline accuracy metrics against gold standard.
    
    Provides per-field accuracy, per-tier accuracy, NULL rates,
    and identifies worst-performing fields.
    """
    tier_config: Dict[int, List[str]]
    
    def __init__(self, tier_config: Dict[int, List[str]]):
        """
        Initialize baseline measurement with tier configuration.
        
        Args:
            tier_config: Dictionary mapping tier number to list of fields
        """
        self.tier_config = tier_config
    
    def generate_report(
        self,
        predictions: List[Dict[str, Any]],
        gold_standard: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive baseline accuracy report.
        
        Args:
            predictions: List of prediction dictionaries
            gold_standard: List of gold standard dictionaries
        
        Returns:
            Report dictionary with:
            - field_accuracies: Per-field accuracy scores
            - tier_accuracies: Per-tier aggregate accuracy
            - null_rates: Per-field NULL rates
            - worst_performing_fields: Fields with lowest accuracy
        """
        # Get all fields from tier config
        all_fields = []
        for fields in self.tier_config.values():
            all_fields.extend(fields)
        
        # Calculate per-field accuracy
        field_accuracies = {}
        for field in all_fields:
            field_accuracies[field] = calculate_field_accuracy(
                predictions, gold_standard, field
            )
        
        # Calculate per-tier accuracy
        tier_accuracies = {}
        for tier in self.tier_config.keys():
            tier_accuracies[tier] = calculate_tier_accuracy(
                field_accuracies, self.tier_config, tier
            )
        
        # Calculate NULL rates
        null_rates = {}
        for field in all_fields:
            null_rates[field] = calculate_null_rate(predictions, field)
        
        # Identify worst-performing fields (lowest accuracy)
        sorted_fields = sorted(
            field_accuracies.items(),
            key=lambda x: x[1]
        )
        worst_performing_fields = [
            {"field": field, "accuracy": acc}
            for field, acc in sorted_fields[:10]  # Top 10 worst
        ]
        
        return {
            "field_accuracies": field_accuracies,
            "tier_accuracies": tier_accuracies,
            "null_rates": null_rates,
            "worst_performing_fields": worst_performing_fields,
            "overall_accuracy": sum(field_accuracies.values()) / len(field_accuracies) if field_accuracies else 0.0,
        }
