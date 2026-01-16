"""
Field Tier Configuration for Tiered Extraction.

Manages field classification into accuracy tiers and confidence thresholds.
"""

import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path


def load_tier_config(path: str) -> Dict[str, Any]:
    """
    Load field tier configuration from YAML file.
    
    Args:
        path: Path to the YAML configuration file
    
    Returns:
        Configuration dictionary with tiers
    """
    config_path = Path(path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Tier configuration not found: {path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def get_field_tier(field: str, config: Dict[str, Any]) -> Optional[int]:
    """
    Get tier number for a specific field.
    
    Args:
        field: Field name to look up
        config: Tier configuration dictionary
    
    Returns:
        Tier number (1-5) or None if field not found
    """
    for tier_num, tier_data in config.get("tiers", {}).items():
        if field in tier_data.get("fields", []):
            return tier_num
    
    return None


def get_confidence_threshold(tier: int, config: Dict[str, Any]) -> float:
    """
    Get confidence threshold for a tier.
    
    Args:
        tier: Tier number (1-5)
        config: Tier configuration dictionary
    
    Returns:
        Confidence threshold (0.0 - 1.0)
    """
    tier_data = config.get("tiers", {}).get(tier, {})
    return tier_data.get("confidence_threshold", 0.5)


def get_fields_by_tier(tier: int, config: Dict[str, Any]) -> List[str]:
    """
    Get all fields in a specific tier.
    
    Args:
        tier: Tier number (1-5)
        config: Tier configuration dictionary
    
    Returns:
        List of field names in the tier
    """
    tier_data = config.get("tiers", {}).get(tier, {})
    return tier_data.get("fields", [])


def create_default_tier_config() -> Dict[str, Any]:
    """
    Create default tier configuration based on field analysis.
    
    Returns:
        Default tier configuration dictionary
    """
    return {
        "tiers": {
            1: {
                "confidence_threshold": 0.90,
                "description": "Keyword-based (92-95% target)",
                "fields": [
                    # Symptoms - simple keywords
                    "symptom_fever",
                    "symptom_dyspnea",
                    "symptom_wheezing",
                    # Biopsy types - acronyms
                    "biopsy_tblb",
                    "biopsy_surgical",
                    "biopsy_cryobiopsy",
                    "biopsy_autopsy",
                    # Exposures - simple keywords
                    "exposure_birds",
                    "exposure_rabbits",
                ]
            },
            2: {
                "confidence_threshold": 0.85,
                "description": "Pattern-based (85-90% target)",
                "fields": [
                    # Symptoms with patterns
                    "symptom_asymptomatic",
                    "symptom_cough_dry",
                    "symptom_chest_pressure",
                    "symptom_progression",
                    "symptom_persistence",
                    # CT findings
                    "ct_ground_glass",
                    "ct_solid_nodules",
                    "ct_central_cavitation",
                    "ct_cystic_micronodules",
                    "ct_random",
                    "ct_cheerio",
                    "ct_upper_lobe_predominance",
                    "ct_lower_lobe_predominance",
                    "ct_subpleural_predominance",
                    "ct_assoc_emphysema",
                    "ct_assoc_fibrosis",
                    # IHC markers
                    "ihc_ema_pos",
                    "ihc_ema_neg",
                    "ihc_pr_pos",
                    "ihc_pr_neg",
                    "ihc_vimentin_pos",
                    "ihc_vimentin_neg",
                    "ihc_ttf1_pos",
                    "ihc_ttf1_neg",
                    "ihc_cytokeratin_pos",
                    "ihc_cytokeratin_neg",
                    "ihc_s100_pos",
                    "ihc_s100_neg",
                    "ihc_sma_pos",
                    "ihc_sma_neg",
                ]
            },
            3: {
                "confidence_threshold": 0.70,
                "description": "Numeric fields (70-80% target)",
                "fields": [
                    "age",
                    "number_of_cases",
                    "female_count",
                    "male_count",
                    "followup_interval_imaging_months",
                    "followup_interval_clinical_months",
                    "ihc_ki67_high",
                    "ihc_ki67_neg",
                ]
            },
            4: {
                "confidence_threshold": 0.60,
                "description": "Clinical judgment (65-75% target)",
                "fields": [
                    # Diagnostic fields
                    "biopsy_tblb_diagnostic",
                    "biopsy_endobronchial_diagnostic",
                    "biopsy_ttnb_diagnostic",
                    "biopsy_surgical_diagnostic",
                    "biopsy_cryobiopsy_diagnostic",
                    # Outcomes
                    "outcome_dpm_stable",
                    "outcome_dpm_improved",
                    "outcome_dpm_progressed",
                    "outcome_dpm_died",
                    "outcome_followup_available",
                    # Management
                    "mgmt_observation",
                    "mgmt_hormone_therapy_withdrawal",
                    "mgmt_lung_transplant_referral",
                ]
            },
            5: {
                "confidence_threshold": 0.50,
                "description": "Rare fields (40-60% target)",
                "fields": [
                    # Rare associations
                    "assoc_pulmonary_ca",
                    "assoc_extrapulmonary_ca",
                    "assoc_pulmonary_embolism",
                    "assoc_gerd",
                    "assoc_cad",
                    "assoc_metabolic_disease",
                    "assoc_hypersensitivity_pneumonitis",
                    "assoc_cryptococcus",
                    "assoc_autoimmune_dz",
                    "assoc_hypothyroid",
                    "assoc_turner_syndrome",
                    "assoc_hrt",
                    # Rare management
                    "mgmt_no_followup_data",
                ]
            }
        }
    }


def save_tier_config(config: Dict[str, Any], path: str) -> None:
    """
    Save tier configuration to YAML file.
    
    Args:
        config: Configuration dictionary
        path: Path to save YAML file
    """
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":
    # Generate default tier configuration
    config = create_default_tier_config()
    save_tier_config(config, "config/field_tiers.yaml")
    print(f"Saved tier configuration to config/field_tiers.yaml")
