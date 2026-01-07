#!/usr/bin/env python3
"""
Modular DPM (Diffuse Pulmonary Meningotheliomatosis) extraction schemas.

Organized by domain for:
1. Better extraction accuracy (focused prompts)
2. Binary field derivation from narratives
3. Study type adaptability (case report vs case series)

Based on gold standard systematic review template.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# =============================================================================
# STUDY METADATA
# =============================================================================

class StudyMetadataSchema(BaseModel):
    """Study-level metadata for classification and routing."""
    
    title: str = Field(description="Full title of the article")
    authors: str = Field(description="Author list (first author et al. format acceptable)")
    doi: Optional[str] = Field(default=None, description="DOI if available")
    journal: Optional[str] = Field(default=None, description="Journal or venue name")
    year: Optional[int] = Field(default=None, description="Publication year")
    
    study_type: Literal[
        "Case Report", 
        "Case Series", 
        "Observational Cohort",
        "Systematic Review",
        "Literature Review"
    ] = Field(description="Type of study - determines extraction strategy")
    
    study_type_narrative: str = Field(
        description="Narrative description of study design from methods/abstract"
    )
    
    case_count: Optional[int] = Field(
        default=1,
        ge=0, 
        description="Number of patients/cases described. 0 for reviews without original cases."
    )


# =============================================================================
# DEMOGRAPHICS
# =============================================================================

class DemographicsSchema(BaseModel):
    """Patient demographics - handles both individual and aggregate data."""
    
    patient_demographics_narrative: str = Field(
        description="Full narrative of patient demographics as described in the paper"
    )
    
    # Age can be single value, range, or mean with SD for case series
    age: Optional[str] = Field(
        default=None,
        description="Patient age(s). Single value for case reports, range or mean±SD for series"
    )
    
    female_count: Optional[int] = Field(
        default=None, ge=0,
        description="Number of female patients"
    )
    
    male_count: Optional[int] = Field(
        default=None, ge=0,
        description="Number of male patients"
    )
    
    non_smoker: Optional[bool] = Field(
        default=None,
        description="True if patient(s) described as non-smoker/never smoker"
    )


# =============================================================================
# SYMPTOMS
# =============================================================================

class SymptomsSchema(BaseModel):
    """Presenting symptoms with narrative for binary derivation."""
    
    symptom_narrative: str = Field(
        description="Full narrative of presenting symptoms as described"
    )
    
    # Binary fields - derived in post-processing from narrative
    symptom_asymptomatic: Optional[bool] = Field(
        default=None,
        description="True if asymptomatic/incidental finding"
    )
    symptom_dyspnea: Optional[bool] = Field(
        default=None,
        description="True if dyspnea/shortness of breath reported"
    )
    symptom_cough_dry: Optional[bool] = Field(
        default=None,
        description="True if dry/non-productive cough reported"
    )
    symptom_chest_pressure: Optional[bool] = Field(
        default=None,
        description="True if chest pressure/discomfort reported"
    )
    symptom_wheezing: Optional[bool] = Field(
        default=None,
        description="True if wheezing reported"
    )
    symptom_fever: Optional[bool] = Field(
        default=None,
        description="True if fever reported"
    )


# =============================================================================
# ASSOCIATED CONDITIONS
# =============================================================================

class AssociatedConditionsSchema(BaseModel):
    """Comorbidities and associated conditions."""
    
    associated_conditions_narrative: str = Field(
        description="Full narrative of comorbidities and associated conditions"
    )
    
    # Common associations - binary
    assoc_pulmonary_ca: Optional[bool] = Field(
        default=None,
        description="Associated pulmonary carcinoma/adenocarcinoma"
    )
    assoc_extrapulmonary_ca: Optional[bool] = Field(
        default=None,
        description="Associated extrapulmonary cancer (breast, colon, etc.)"
    )
    assoc_pulmonary_embolism: Optional[bool] = Field(
        default=None,
        description="Associated pulmonary embolism"
    )
    assoc_gerd: Optional[bool] = Field(
        default=None,
        description="Gastroesophageal reflux disease"
    )
    assoc_cad: Optional[bool] = Field(
        default=None,
        description="Coronary artery disease"
    )
    assoc_metabolic_disease: Optional[bool] = Field(
        default=None,
        description="Metabolic disease (diabetes, hyperlipidemia)"
    )
    assoc_autoimmune_dz: Optional[bool] = Field(
        default=None,
        description="Autoimmune disease"
    )
    assoc_hypothyroid: Optional[bool] = Field(
        default=None,
        description="Hypothyroidism"
    )
    assoc_turner_syndrome: Optional[bool] = Field(
        default=None,
        description="Turner syndrome"
    )
    assoc_hrt: Optional[bool] = Field(
        default=None,
        description="Hormone replacement therapy"
    )


# =============================================================================
# IMAGING (CT)
# =============================================================================

class ImagingSchema(BaseModel):
    """CT and imaging findings."""
    
    ct_narrative: str = Field(
        description="Full narrative of CT/imaging findings as described"
    )
    
    ct_size: Optional[str] = Field(
        default=None,
        description="Size of nodules (e.g., '2-5mm', '<5mm')"
    )
    
    # Binary CT features
    ct_ground_glass: Optional[bool] = Field(
        default=None,
        description="Ground glass nodules present"
    )
    ct_solid_nodules: Optional[bool] = Field(
        default=None,
        description="Solid nodules present"
    )
    ct_central_cavitation: Optional[bool] = Field(
        default=None,
        description="Central cavitation present"
    )
    ct_cystic_micronodules: Optional[bool] = Field(
        default=None,
        description="Cystic micronodules present"
    )
    ct_random_distribution: Optional[bool] = Field(
        default=None,
        description="Random distribution pattern"
    )
    ct_cheerio_sign: Optional[bool] = Field(
        default=None,
        description="Cheerio sign (ring-shaped with central lucency)"
    )
    ct_upper_lobe_predominance: Optional[bool] = Field(
        default=None,
        description="Upper lobe predominance"
    )
    ct_lower_lobe_predominance: Optional[bool] = Field(
        default=None,
        description="Lower lobe predominance"
    )
    ct_subpleural_predominance: Optional[bool] = Field(
        default=None,
        description="Subpleural predominance"
    )


# =============================================================================
# PATHOLOGY
# =============================================================================

class PathologySchema(BaseModel):
    """Histopathology findings."""
    
    histology_narrative: str = Field(
        description="Full narrative of histopathological findings"
    )
    
    gross_features: Optional[str] = Field(
        default=None,
        description="Gross pathology features"
    )
    
    histo_perivascular_distribution: Optional[bool] = Field(
        default=None,
        description="Perivascular distribution pattern"
    )
    
    primary_histologic_pattern: Optional[str] = Field(
        default=None,
        description="Primary histologic pattern (e.g., 'whorled', 'nested')"
    )


# =============================================================================
# IMMUNOHISTOCHEMISTRY
# =============================================================================

class ImmunohistochemistrySchema(BaseModel):
    """IHC marker results."""
    
    ihc_narrative: str = Field(
        description="Full narrative of immunohistochemistry findings"
    )
    
    # Key DPM markers - positive/negative
    ihc_ema_pos: Optional[bool] = Field(
        default=None,
        description="EMA (epithelial membrane antigen) positive"
    )
    ihc_pr_pos: Optional[bool] = Field(
        default=None,
        description="PR (progesterone receptor) positive"
    )
    ihc_vimentin_pos: Optional[bool] = Field(
        default=None,
        description="Vimentin positive"
    )
    ihc_cd56_pos: Optional[bool] = Field(
        default=None,
        description="CD56 positive"
    )
    
    # Typically negative markers
    ihc_ttf1_neg: Optional[bool] = Field(
        default=None,
        description="TTF-1 negative"
    )
    ihc_cytokeratin_neg: Optional[bool] = Field(
        default=None,
        description="Cytokeratin negative"
    )
    ihc_s100_neg: Optional[bool] = Field(
        default=None,
        description="S100 negative"
    )
    ihc_synaptophysin_neg: Optional[bool] = Field(
        default=None,
        description="Synaptophysin negative"
    )
    ihc_chromogranin_neg: Optional[bool] = Field(
        default=None,
        description="Chromogranin negative"
    )
    
    ihc_ki67_low: Optional[bool] = Field(
        default=None,
        description="Ki67 low (<5%)"
    )


# =============================================================================
# DIAGNOSTIC APPROACH
# =============================================================================

class DiagnosticApproachSchema(BaseModel):
    """Biopsy and diagnostic methods."""
    
    diagnostic_approach_narrative: str = Field(
        description="Full narrative of diagnostic workup and approach"
    )
    
    # Biopsy methods
    biopsy_tblb: Optional[bool] = Field(
        default=None,
        description="Transbronchial lung biopsy performed"
    )
    biopsy_surgical: Optional[bool] = Field(
        default=None,
        description="Surgical biopsy (VATS/open) performed"
    )
    biopsy_cryobiopsy: Optional[bool] = Field(
        default=None,
        description="Transbronchial cryobiopsy performed"
    )
    
    # Which was diagnostic
    biopsy_tblb_diagnostic: Optional[bool] = Field(
        default=None,
        description="TBLB was diagnostic"
    )
    biopsy_surgical_diagnostic: Optional[bool] = Field(
        default=None,
        description="Surgical biopsy was diagnostic"
    )
    biopsy_cryobiopsy_diagnostic: Optional[bool] = Field(
        default=None,
        description="Cryobiopsy was diagnostic"
    )


# =============================================================================
# MANAGEMENT & OUTCOMES
# =============================================================================

class OutcomesSchema(BaseModel):
    """Treatment, management, and outcomes."""
    
    management_narrative: str = Field(
        description="Full narrative of treatment and management approach"
    )
    
    # Management approaches
    mgmt_observation: Optional[bool] = Field(
        default=None,
        description="Conservative observation/surveillance"
    )
    mgmt_hormone_therapy_withdrawal: Optional[bool] = Field(
        default=None,
        description="Hormone therapy discontinued"
    )
    mgmt_lung_transplant_referral: Optional[bool] = Field(
        default=None,
        description="Referred for lung transplant evaluation"
    )
    
    # Outcomes
    outcomes_narrative: str = Field(
        description="Full narrative of patient outcomes and follow-up"
    )
    
    followup_available: Optional[bool] = Field(
        default=None,
        description="Follow-up data available"
    )
    followup_duration_months: Optional[float] = Field(
        default=None,
        description="Duration of follow-up in months"
    )
    
    outcome_dpm_stable: Optional[bool] = Field(
        default=None,
        description="DPM remained stable on follow-up"
    )
    outcome_dpm_improved: Optional[bool] = Field(
        default=None,
        description="DPM improved on follow-up"
    )
    outcome_dpm_progressed: Optional[bool] = Field(
        default=None,
        description="DPM progressed on follow-up"
    )


# =============================================================================
# COMPOSITE SCHEMA
# =============================================================================

class DPMFullExtractionSchema(BaseModel):
    """
    Complete DPM extraction combining all sub-schemas.
    
    Use for single-pass extraction when document is simple.
    For complex documents, extract sub-schemas separately.
    """
    
    filename: str = Field(description="Source PDF filename")
    
    # Study metadata
    study_type: str = Field(description="Type of study")
    case_count: int = Field(ge=0, description="Number of cases")
    
    # Demographics
    patient_demographics_narrative: str = Field(description="Demographics narrative")
    age: Optional[str] = Field(default=None, description="Patient age(s)")
    female_count: Optional[int] = Field(default=None, description="Female count")
    male_count: Optional[int] = Field(default=None, description="Male count")
    
    # Symptoms
    symptom_narrative: str = Field(description="Symptoms narrative")
    
    # Imaging
    ct_narrative: str = Field(description="CT findings narrative")
    
    # Pathology
    histology_narrative: str = Field(description="Histopathology narrative")
    
    # IHC
    ihc_narrative: str = Field(description="IHC findings narrative")
    
    # Management/Outcomes
    management_narrative: str = Field(description="Management narrative")
    outcomes_narrative: str = Field(description="Outcomes narrative")
    
    # Key binary fields (subset - post-processing derives the rest)
    symptom_asymptomatic: Optional[bool] = Field(default=None)
    ct_ground_glass: Optional[bool] = Field(default=None)
    ct_cheerio_sign: Optional[bool] = Field(default=None)
    ihc_ema_pos: Optional[bool] = Field(default=None)
    ihc_pr_pos: Optional[bool] = Field(default=None)
    outcome_dpm_stable: Optional[bool] = Field(default=None)
    
    extraction_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Overall extraction confidence"
    )
    extraction_notes: Optional[str] = Field(
        default=None,
        description="Notes about extraction quality or limitations"
    )


# =============================================================================
# MULTI-CASE HANDLING
# =============================================================================

class IndividualPatientData(BaseModel):
    """
    Individual patient data for case series.
    
    For systematic reviews using Individual Patient Data (IPD) approach,
    each patient from a case series gets their own record.
    """
    
    patient_id: str = Field(description="Unique identifier within the study (e.g., 'Patient 1')")
    source_filename: str = Field(description="Source PDF filename")
    
    # Patient-level data
    age: Optional[str] = Field(default=None)
    sex: Optional[Literal["Male", "Female", "Unknown"]] = Field(default=None)
    
    symptom_narrative: str = Field(default="")
    symptom_asymptomatic: Optional[bool] = Field(default=None)
    
    ct_narrative: str = Field(default="")
    histology_narrative: str = Field(default="")
    ihc_narrative: str = Field(default="")
    
    treatment: Optional[str] = Field(default=None)
    outcome: Optional[str] = Field(default=None)
    followup_months: Optional[float] = Field(default=None)


class AggregateStudyData(BaseModel):
    """
    Aggregate study data for case series.
    
    When individual patient data is not extractable,
    use aggregate statistics.
    """
    
    source_filename: str = Field(description="Source PDF filename")
    case_count: int = Field(ge=1)
    
    # Aggregate demographics
    age_range: Optional[str] = Field(default=None, description="Age range (e.g., '32-72')")
    age_mean: Optional[float] = Field(default=None)
    age_median: Optional[float] = Field(default=None)
    
    female_count: Optional[int] = Field(default=None)
    male_count: Optional[int] = Field(default=None)
    
    # Percentages for binary fields
    pct_asymptomatic: Optional[float] = Field(default=None, ge=0, le=100)
    pct_dyspnea: Optional[float] = Field(default=None, ge=0, le=100)
    pct_cough: Optional[float] = Field(default=None, ge=0, le=100)
    
    pct_ground_glass: Optional[float] = Field(default=None, ge=0, le=100)
    pct_cheerio_sign: Optional[float] = Field(default=None, ge=0, le=100)
    
    pct_ema_pos: Optional[float] = Field(default=None, ge=0, le=100)
    pct_pr_pos: Optional[float] = Field(default=None, ge=0, le=100)
    
    pct_stable_outcome: Optional[float] = Field(default=None, ge=0, le=100)
