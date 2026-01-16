"""
Rule Coverage Audit for Binary Extraction.

Identifies gaps between schema binary fields and existing derivation rules.
"""

from typing import Dict, List, Set, Any, Type
from pydantic import BaseModel
from dataclasses import dataclass


def get_binary_fields(schema_class: Type[BaseModel]) -> List[str]:
    """
    Extract all binary (boolean) fields from a Pydantic schema.
    
    Args:
        schema_class: Pydantic model class to inspect
    
    Returns:
        List of field names that are boolean type
    """
    binary_fields = []
    
    for field_name, field_info in schema_class.model_fields.items():
        # Get the annotation (type hint)
        annotation = field_info.annotation
        
        # Handle Optional types
        if hasattr(annotation, '__origin__'):
            # For Optional[bool], check the args
            if hasattr(annotation, '__args__'):
                for arg in annotation.__args__:
                    if arg is bool:
                        binary_fields.append(field_name)
                        break
        elif annotation is bool:
            binary_fields.append(field_name)
    
    return binary_fields


def audit_rule_coverage(rules: List[Any]) -> Dict[str, Dict[str, Any]]:
    """
    Map existing derivation rules to their target fields.
    
    Args:
        rules: List of DerivationRule objects
    
    Returns:
        Dictionary mapping field_name to rule metadata
    """
    coverage = {}
    
    for rule in rules:
        field_name = rule.field_name
        coverage[field_name] = {
            "has_rule": True,
            "source_narrative": rule.source_narrative,
            "pattern_count": len(rule.positive_patterns),
            "has_negative_patterns": bool(rule.negative_patterns),
        }
    
    return coverage


def identify_gaps(
    schema_class: Type[BaseModel],
    rules: List[Any]
) -> List[str]:
    """
    Identify binary fields without derivation rules.
    
    Args:
        schema_class: Pydantic schema with binary fields
        rules: List of existing derivation rules
    
    Returns:
        List of field names without rules (gaps)
    """
    # Get all binary fields from schema
    binary_fields = get_binary_fields(schema_class)
    
    # Get fields covered by rules
    covered_fields = {rule.field_name for rule in rules}
    
    # Find gaps
    gaps = [
        field for field in binary_fields
        if field not in covered_fields
    ]
    
    return gaps


def generate_coverage_report(
    schema_class: Type[BaseModel],
    rules: List[Any]
) -> str:
    """
    Generate markdown report of rule coverage.
    
    Args:
        schema_class: Pydantic schema to analyze
        rules: List of existing derivation rules
    
    Returns:
        Markdown formatted coverage report
    """
    binary_fields = get_binary_fields(schema_class)
    coverage = audit_rule_coverage(rules)
    gaps = identify_gaps(schema_class, rules)
    
    covered_count = len([f for f in binary_fields if f in coverage])
    total_count = len(binary_fields)
    coverage_pct = covered_count / total_count * 100 if total_count > 0 else 0
    
    # Group gaps by domain (based on prefix)
    domain_gaps = {}
    for gap in gaps:
        prefix = gap.split("_")[0] if "_" in gap else "other"
        if prefix not in domain_gaps:
            domain_gaps[prefix] = []
        domain_gaps[prefix].append(gap)
    
    report = f"""# Binary Field Rule Coverage Report

## Summary

- **Total binary fields:** {total_count}
- **Fields with rules:** {covered_count}
- **Fields without rules:** {len(gaps)}
- **Coverage:** {coverage_pct:.1f}%

## Gaps by Domain

"""
    
    for domain, fields in sorted(domain_gaps.items()):
        report += f"### {domain.title()} ({len(fields)} uncovered)\n\n"
        for field in fields:
            report += f"- `{field}`\n"
        report += "\n"
    
    report += """## Covered Fields

| Field | Source Narrative | Patterns |
|-------|------------------|----------|
"""
    
    for field, info in sorted(coverage.items()):
        report += f"| `{field}` | {info['source_narrative']} | {info['pattern_count']} |\n"
    
    return report


if __name__ == "__main__":
    # Generate coverage report
    from schemas.dpm_gold_standard import DPMGoldStandardSchema
    from core.binary.rules import ALL_RULES
    
    report = generate_coverage_report(DPMGoldStandardSchema, ALL_RULES)
    print(report)
