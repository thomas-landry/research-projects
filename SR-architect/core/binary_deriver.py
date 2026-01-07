#!/usr/bin/env python3
"""
Binary Field Deriver for DPM Extraction.

Derives binary fields from narrative text using pattern matching.
No API calls required - pure post-processing.
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class DerivationRule:
    """Rule for deriving a binary field from narrative."""
    field_name: str
    source_narrative: str  # Which narrative field to check
    positive_patterns: List[str]  # Patterns that indicate True
    negative_patterns: List[str] = None  # Patterns that indicate False
    case_sensitive: bool = False


# =============================================================================
# DERIVATION RULES BY DOMAIN
# =============================================================================

SYMPTOM_RULES = [
    DerivationRule(
        field_name="symptom_asymptomatic",
        source_narrative="symptom_narrative",
        positive_patterns=[
            r"\basymptomatic\b",
            r"\bincidental\b",
            r"\bno symptoms\b",
            r"\bwithout symptoms\b",
            r"\bincidentally\s+(found|detected|discovered)\b",
        ],
    ),
    DerivationRule(
        field_name="symptom_dyspnea",
        source_narrative="symptom_narrative",
        positive_patterns=[
            r"\bdyspnea\b",
            r"\bshortness of breath\b",
            r"\bSOB\b",
            r"\bdifficulty breathing\b",
            r"\bexertional dyspnea\b",
            r"\bbreathing difficulty\b",
        ],
    ),
    DerivationRule(
        field_name="symptom_cough_dry",
        source_narrative="symptom_narrative",
        positive_patterns=[
            r"\bdry cough\b",
            r"\bnon-?productive cough\b",
            r"\bcough\b(?!.*productive)",
            r"\bchronic cough\b",
        ],
    ),
    DerivationRule(
        field_name="symptom_chest_pressure",
        source_narrative="symptom_narrative",
        positive_patterns=[
            r"\bchest pressure\b",
            r"\bchest discomfort\b",
            r"\bchest pain\b",
            r"\bchest tightness\b",
        ],
    ),
    DerivationRule(
        field_name="symptom_wheezing",
        source_narrative="symptom_narrative",
        positive_patterns=[r"\bwheezing\b", r"\bwheeze\b"],
    ),
    DerivationRule(
        field_name="symptom_fever",
        source_narrative="symptom_narrative",
        positive_patterns=[r"\bfever\b", r"\bfebrile\b"],
    ),
    DerivationRule(
        field_name="symptom_progression",
        source_narrative="symptom_narrative",
        positive_patterns=[
            r"\bprogress(ive|ing)\b",
            r"\bworsening\b",
            r"\bincreasing\b",
        ],
    ),
    DerivationRule(
        field_name="symptom_persistence",
        source_narrative="symptom_narrative",
        positive_patterns=[
            r"\bpersistent\b",
            r"\bchronic\b",
            r"\bongoing\b",
            r"\bcontinued\b",
        ],
    ),
]

ASSOCIATION_RULES = [
    DerivationRule(
        field_name="assoc_pulmonary_ca",
        source_narrative="associated_conditions_narrative",
        positive_patterns=[
            r"\blung\s+(cancer|carcinoma|adenocarcinoma)\b",
            r"\bpulmonary\s+(cancer|carcinoma|adenocarcinoma)\b",
            r"\blung\s+malignancy\b",
        ],
    ),
    DerivationRule(
        field_name="assoc_extrapulmonary_ca",
        source_narrative="associated_conditions_narrative",
        positive_patterns=[
            r"\bbreast\s+cancer\b",
            r"\bcolon\s+cancer\b",
            r"\brenal\s+(cell\s+)?carcinoma\b",
            r"\bthyroid\s+cancer\b",
            r"\buterine\s+cancer\b",
            r"\bhepatocellular\s+carcinoma\b",
            r"\bcarcinoid\b",
            r"\bleiomyosarcoma\b",
        ],
    ),
    DerivationRule(
        field_name="assoc_pulmonary_embolism",
        source_narrative="associated_conditions_narrative",
        positive_patterns=[
            r"\bpulmonary\s+emboli(sm)?\b",
            r"\bPE\b",
            r"\bpulmonary\s+embol(us|i)\b",
        ],
    ),
    DerivationRule(
        field_name="assoc_gerd",
        source_narrative="associated_conditions_narrative",
        positive_patterns=[
            r"\bGERD\b",
            r"\bgastroesophageal\s+reflux\b",
            r"\bacid\s+reflux\b",
        ],
    ),
    DerivationRule(
        field_name="assoc_cad",
        source_narrative="associated_conditions_narrative",
        positive_patterns=[
            r"\bcoronary\s+artery\s+disease\b",
            r"\bCAD\b",
            r"\bischemic\s+heart\s+disease\b",
            r"\bmyocardial\s+infarction\b",
        ],
    ),
    DerivationRule(
        field_name="assoc_metabolic_disease",
        source_narrative="associated_conditions_narrative",
        positive_patterns=[
            r"\bdiabetes\b",
            r"\bhyperlipidemia\b",
            r"\bhypercholesterolemia\b",
            r"\bobesity\b",
            r"\bmetabolic syndrome\b",
        ],
    ),
    DerivationRule(
        field_name="assoc_hypersensitivity_pneumonitis",
        source_narrative="associated_conditions_narrative",
        positive_patterns=[
            r"\bhypersensitivity\s+pneumonitis\b",
            r"\bHP\b",
        ],
    ),
    DerivationRule(
        field_name="assoc_cryptococcus",
        source_narrative="associated_conditions_narrative",
        positive_patterns=[r"\bcryptococcus\b", r"\bcryptococcal\b"],
    ),
    DerivationRule(
        field_name="assoc_autoimmune_dz",
        source_narrative="associated_conditions_narrative",
        positive_patterns=[
            r"\bautoimmune\b",
            r"\bscleroderma\b",
            r"\brheumatoid\b",
            r"\blupus\b",
            r"\bvasculitis\b",
            r"\bpolyarteritis\b",
            r"\bgiant\s+cell\s+arteritis\b",
        ],
    ),
    DerivationRule(
        field_name="assoc_hypothyroid",
        source_narrative="associated_conditions_narrative",
        positive_patterns=[r"\bhypothyroid(ism)?\b"],
    ),
    DerivationRule(
        field_name="assoc_turner_syndrome",
        source_narrative="associated_conditions_narrative",
        positive_patterns=[r"\bturner\s+syndrome\b", r"\bturner's\s+syndrome\b"],
    ),
    DerivationRule(
        field_name="assoc_hrt",
        source_narrative="associated_conditions_narrative",
        positive_patterns=[
            r"\bhormone\s+replacement\s+therapy\b",
            r"\bHRT\b",
            r"\bestrogen\s+therapy\b",
        ],
    ),
    DerivationRule(
        field_name="non_smoker",
        source_narrative="patient_demographics_narrative",
        positive_patterns=[
            r"\bnon-?smoker\b",
            r"\bnever\s+smok(er|ed)\b",
            r"\bno\s+smoking\s+history\b",
        ],
    ),
]

CT_RULES = [
    DerivationRule(
        field_name="ct_ground_glass",
        source_narrative="ct_narrative",
        positive_patterns=[
            r"\bground[\s-]?glass\b",
            r"\bGGO\b",
            r"\bGGN\b",
        ],
    ),
    DerivationRule(
        field_name="ct_solid_nodules",
        source_narrative="ct_narrative",
        positive_patterns=[r"\bsolid\s+nodule\b", r"\bsolid\s+lesion\b"],
    ),
    DerivationRule(
        field_name="ct_central_cavitation",
        source_narrative="ct_narrative",
        positive_patterns=[
            r"\bcavitat(ion|ing|ed)\b",
            r"\bcentral\s+lucen(cy|cies)\b",
            r"\bcavitary\b",
        ],
    ),
    DerivationRule(
        field_name="ct_cystic_micronodules",
        source_narrative="ct_narrative",
        positive_patterns=[r"\bcystic\b", r"\bthin-?walled\s+cyst\b"],
    ),
    DerivationRule(
        field_name="ct_random",
        source_narrative="ct_narrative",
        positive_patterns=[r"\brandom\s+distribution\b", r"\brandomly\s+distributed\b"],
    ),
    DerivationRule(
        field_name="ct_cheerio",
        source_narrative="ct_narrative",
        positive_patterns=[r"\bcheerio\b", r"\bring-?shaped\b", r"\bring[\s-]?like\b"],
    ),
    DerivationRule(
        field_name="ct_upper_lobe_predominance",
        source_narrative="ct_narrative",
        positive_patterns=[r"\bupper\s+lobe\s+predominan\w+\b", r"\bapical\s+predominan\w+\b"],
    ),
    DerivationRule(
        field_name="ct_lower_lobe_predominance",
        source_narrative="ct_narrative",
        positive_patterns=[r"\blower\s+lobe\s+predominan\w+\b", r"\bbasal\s+predominan\w+\b"],
    ),
    DerivationRule(
        field_name="ct_subpleural_predominance",
        source_narrative="ct_narrative",
        positive_patterns=[r"\bsubpleural\b", r"\bperipheral\s+predominan\w+\b"],
    ),
    DerivationRule(
        field_name="ct_assoc_emphysema",
        source_narrative="ct_narrative",
        positive_patterns=[r"\bemphysema\b"],
    ),
    DerivationRule(
        field_name="ct_assoc_fibrosis",
        source_narrative="ct_narrative",
        positive_patterns=[r"\bfibrosis\b", r"\bfibrotic\b"],
    ),
]

IHC_RULES = [
    # EMA
    DerivationRule(
        field_name="ihc_ema_pos",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bEMA\s*(positive|\+|pos)\b", r"\bpositive\s*(for)?\s*EMA\b"],
    ),
    DerivationRule(
        field_name="ihc_ema_neg",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bEMA\s*(negative|-|neg)\b", r"\bnegative\s*(for)?\s*EMA\b"],
    ),
    # PR
    DerivationRule(
        field_name="ihc_pr_pos",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[
            r"\bPR\s*(positive|\+|pos)\b",
            r"\bprogesterone\s+receptor\s*(positive|\+)\b",
            r"\bpositive\s*(for)?\s*PR\b",
        ],
    ),
    DerivationRule(
        field_name="ihc_pr_neg",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[
            r"\bPR\s*(negative|-|neg)\b",
            r"\bprogesterone\s+receptor\s*(negative|-)\b",
        ],
    ),
    # Vimentin
    DerivationRule(
        field_name="ihc_vimentin_pos",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bvimentin\s*(positive|\+|pos)\b", r"\bpositive\s*(for)?\s*vimentin\b"],
    ),
    DerivationRule(
        field_name="ihc_vimentin_neg",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bvimentin\s*(negative|-|neg)\b"],
    ),
    # TTF-1
    DerivationRule(
        field_name="ihc_ttf1_pos",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bTTF-?1\s*(positive|\+|pos)\b"],
    ),
    DerivationRule(
        field_name="ihc_ttf1_neg",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bTTF-?1\s*(negative|-|neg)\b", r"\bnegative\s*(for)?\s*TTF-?1\b"],
    ),
    # Cytokeratin
    DerivationRule(
        field_name="ihc_cytokeratin_pos",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bcytokeratin\s*(positive|\+|pos)\b", r"\bCK\s*(positive|\+)\b"],
    ),
    DerivationRule(
        field_name="ihc_cytokeratin_neg",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bcytokeratin\s*(negative|-|neg)\b", r"\bCK\s*(negative|-)\b"],
    ),
    # S100
    DerivationRule(
        field_name="ihc_s100_pos",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bS-?100\s*(positive|\+|pos)\b"],
    ),
    DerivationRule(
        field_name="ihc_s100_neg",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bS-?100\s*(negative|-|neg)\b", r"\bnegative\s*(for)?\s*S-?100\b"],
    ),
    # SMA
    DerivationRule(
        field_name="ihc_sma_pos",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bSMA\s*(positive|\+|pos)\b", r"\bsmooth\s+muscle\s+actin\s*(positive|\+)\b"],
    ),
    DerivationRule(
        field_name="ihc_sma_neg",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bSMA\s*(negative|-|neg)\b", r"\bsmooth\s+muscle\s+actin\s*(negative|-)\b"],
    ),
    # Ki67
    DerivationRule(
        field_name="ihc_ki67_high",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bKi-?67\s*(high|>\s*5%)\b"],
    ),
    DerivationRule(
        field_name="ihc_ki67_neg",
        source_narrative="immunohistochemistry_narrative",
        positive_patterns=[r"\bKi-?67\s*(low|<\s*5%|negative)\b"],
    ),
]

BIOPSY_RULES = [
    DerivationRule(
        field_name="biopsy_tblb",
        source_narrative="diagnostic_approach",
        positive_patterns=[r"\btransbronchial\s+(lung\s+)?biopsy\b", r"\bTBLB\b", r"\bTBB\b"],
    ),
    DerivationRule(
        field_name="biopsy_surgical",
        source_narrative="diagnostic_approach",
        positive_patterns=[
            r"\bVATS\b",
            r"\bvideo-?assisted\b",
            r"\bsurgical\s+(lung\s+)?biopsy\b",
            r"\bwedge\s+resection\b",
            r"\blobectomy\b",
            r"\bthoracoscopic\b",
        ],
    ),
    DerivationRule(
        field_name="biopsy_cryobiopsy",
        source_narrative="diagnostic_approach",
        positive_patterns=[r"\bcryobiopsy\b", r"\bTBLCB\b", r"\bTBLC\b"],
    ),
]

OUTCOME_RULES = [
    DerivationRule(
        field_name="outcome_dpm_stable",
        source_narrative="outcomes",
        positive_patterns=[
            r"\bstable\b",
            r"\bunchanged\b",
            r"\bno\s+change\b",
            r"\bno\s+progression\b",
        ],
    ),
    DerivationRule(
        field_name="outcome_dpm_improved",
        source_narrative="outcomes",
        positive_patterns=[r"\bimproved\b", r"\bimprovement\b", r"\bresolved\b"],
    ),
    DerivationRule(
        field_name="outcome_dpm_progressed",
        source_narrative="outcomes",
        positive_patterns=[r"\bprogressed\b", r"\bprogression\b", r"\bworsened\b"],
    ),
    DerivationRule(
        field_name="outcome_dpm_died",
        source_narrative="outcomes",
        positive_patterns=[r"\bdied\b", r"\bdeath\b", r"\bdeceased\b", r"\bexpired\b"],
    ),
    DerivationRule(
        field_name="mgmt_observation",
        source_narrative="management_narrative",
        positive_patterns=[
            r"\bobservation\b",
            r"\bconservative\b",
            r"\bsurveillance\b",
            r"\bfollow-?up\b",
            r"\bmonitoring\b",
        ],
    ),
    DerivationRule(
        field_name="mgmt_hormone_therapy_withdrawal",
        source_narrative="management_narrative",
        positive_patterns=[
            r"\bHRT\s+(discontinu|withdraw|stopp)\w+\b",
            r"\bhormone\s+therapy\s+(discontinu|withdraw|stopp)\w+\b",
        ],
    ),
]

PATHOLOGY_RULES = [
    DerivationRule(
        field_name="histo_perivascular_distribution",
        source_narrative="histology_narrative",
        positive_patterns=[r"\bperivascular\b", r"\bperivenular\b"],
    ),
]

# Combine all rules
ALL_RULES = (
    SYMPTOM_RULES
    + ASSOCIATION_RULES
    + CT_RULES
    + IHC_RULES
    + BIOPSY_RULES
    + OUTCOME_RULES
    + PATHOLOGY_RULES
)


class BinaryDeriver:
    """
    Derive binary fields from narrative text.
    
    Usage:
        deriver = BinaryDeriver()
        extracted = {"symptom_narrative": "Patient presented with dyspnea and dry cough"}
        derived = deriver.derive_all(extracted)
        # derived = {"symptom_dyspnea": True, "symptom_cough_dry": True, ...}
    """
    
    def __init__(self, rules: List[DerivationRule] = None):
        """Initialize with rules."""
        self.rules = rules or ALL_RULES
    
    def check_pattern(self, text: str, pattern: str, case_sensitive: bool = False) -> bool:
        """Check if pattern matches in text."""
        if not text:
            return False
        flags = 0 if case_sensitive else re.IGNORECASE
        return bool(re.search(pattern, text, flags))
    
    def derive_field(
        self, 
        rule: DerivationRule, 
        narratives: Dict[str, Any]
    ) -> Tuple[str, Optional[bool]]:
        """
        Derive a single binary field from narratives.
        
        Returns:
            Tuple of (field_name, derived_value)
        """
        source_text = narratives.get(rule.source_narrative, "")
        
        if not source_text:
            return rule.field_name, None
        
        # Check positive patterns
        for pattern in rule.positive_patterns:
            if self.check_pattern(source_text, pattern, rule.case_sensitive):
                return rule.field_name, True
        
        # Check negative patterns if defined
        if rule.negative_patterns:
            for pattern in rule.negative_patterns:
                if self.check_pattern(source_text, pattern, rule.case_sensitive):
                    return rule.field_name, False
        
        # No match found
        return rule.field_name, None
    
    def derive_all(self, narratives: Dict[str, Any]) -> Dict[str, Optional[bool]]:
        """
        Derive all binary fields from narrative dict.
        
        Args:
            narratives: Dict with narrative field values
            
        Returns:
            Dict of binary field names to derived values
        """
        derived = {}
        for rule in self.rules:
            field_name, value = self.derive_field(rule, narratives)
            derived[field_name] = value
        return derived
    
    def merge_with_extraction(
        self,
        extracted: Dict[str, Any],
        derived: Dict[str, Optional[bool]],
    ) -> Dict[str, Any]:
        """
        Merge derived binaries with extracted data.
        
        Derived values only fill in missing fields (don't override).
        
        Args:
            extracted: Original extracted data
            derived: Derived binary values
            
        Returns:
            Merged dict
        """
        result = dict(extracted)
        for field, value in derived.items():
            # Only fill if not already set
            if field not in result or result[field] is None:
                result[field] = value
        return result


def process_extraction(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process extraction by deriving binary fields.
    
    Args:
        extracted_data: LLM-extracted narrative data
        
    Returns:
        Complete data with binaries derived
    """
    deriver = BinaryDeriver()
    derived = deriver.derive_all(extracted_data)
    return deriver.merge_with_extraction(extracted_data, derived)


if __name__ == "__main__":
    # Test derivation
    sample = {
        "symptom_narrative": "Patient presented with dyspnea and non-productive cough. The condition was worsening over time.",
        "associated_conditions_narrative": "History of breast cancer and GERD. On HRT.",
        "ct_narrative": "Multiple bilateral ground-glass nodules with central cavitation. Cheerio sign observed.",
        "immunohistochemistry_narrative": "EMA positive, PR positive, vimentin positive. TTF-1 negative.",
        "management_narrative": "Conservative observation with surveillance imaging.",
        "outcomes": "DPM remained stable on 6-month follow-up.",
    }
    
    deriver = BinaryDeriver()
    derived = deriver.derive_all(sample)
    
    print("Derived binary fields:")
    for k, v in sorted(derived.items()):
        if v is not None:
            print(f"  {k}: {v}")
