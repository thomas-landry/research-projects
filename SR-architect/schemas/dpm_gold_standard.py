#!/usr/bin/env python3
"""
Gold Standard DPM Extraction Schema.

Matches all 125 columns from the systematic review template CSV.
Organized for hybrid extraction: LLM extracts narratives, post-processing derives binaries.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class DPMGoldStandardSchema(BaseModel):
    """
    Complete DPM extraction schema matching gold standard template.
    
    125 columns organized by domain.
    LLM extracts narrative fields; binary fields derived in post-processing.
    """
    
    # =========================================================================
    # STUDY METADATA (10 columns)
    # =========================================================================
    
    title: Optional[str] = Field(default=None, description="Full title of the article")
    authors: Optional[str] = Field(default=None, description="Author list")
    doi: Optional[str] = Field(default=None, description="DOI if available")
    doi_link: Optional[str] = Field(default=None, description="Full DOI URL")
    journal_venue: Optional[str] = Field(default=None, description="Journal or venue name")
    year: Optional[int] = Field(default=None, description="Publication year")
    filename: Optional[str] = Field(default=None, description="Source PDF filename")
    study_type: Optional[str] = Field(
        default=None, 
        description="Type of study: Case Report, Case Series, Cohort, Systematic Review, Literature Review"
    )
    number_of_cases: Optional[int] = Field(default=None, ge=0, description="Number of patients/cases")
    study_type_narrative: Optional[str] = Field(default=None, description="Narrative description of study design")
    
    # =========================================================================
    # DEMOGRAPHICS (6 columns)
    # =========================================================================
    
    patient_demographics_narrative: Optional[str] = Field(
        default=None, 
        description="Full narrative of patient demographics including age, sex, smoking status"
    )
    age: Optional[str] = Field(default=None, description="Patient age(s) - single value or range")
    female_count: Optional[int] = Field(default=None, ge=0, description="Number of female patients")
    male_count: Optional[int] = Field(default=None, ge=0, description="Number of male patients")
    non_smoker: Optional[bool] = Field(default=None, description="Patient described as non-smoker")
    
    # =========================================================================
    # ASSOCIATED CONDITIONS (16 columns)
    # =========================================================================
    
    associated_conditions_narrative: Optional[str] = Field(
        default=None,
        description="Full narrative of comorbidities, associated conditions, and exposures"
    )
    assoc_pulmonary_ca: Optional[bool] = Field(default=None, description="Associated pulmonary carcinoma")
    assoc_extrapulmonary_ca: Optional[bool] = Field(default=None, description="Associated extrapulmonary cancer")
    assoc_pulmonary_embolism: Optional[bool] = Field(default=None, description="Pulmonary embolism")
    assoc_gerd: Optional[bool] = Field(default=None, description="GERD")
    assoc_cad: Optional[bool] = Field(default=None, description="Coronary artery disease")
    assoc_metabolic_disease: Optional[bool] = Field(default=None, description="Diabetes, hyperlipidemia, etc.")
    assoc_hypersensitivity_pneumonitis: Optional[bool] = Field(default=None, description="Hypersensitivity pneumonitis")
    assoc_cryptococcus: Optional[bool] = Field(default=None, description="Cryptococcus infection")
    assoc_autoimmune_dz: Optional[bool] = Field(default=None, description="Autoimmune disease")
    assoc_hypothyroid: Optional[bool] = Field(default=None, description="Hypothyroidism")
    assoc_turner_syndrome: Optional[bool] = Field(default=None, description="Turner syndrome")
    assoc_hrt: Optional[bool] = Field(default=None, description="Hormone replacement therapy")
    exposure_birds: Optional[bool] = Field(default=None, description="Bird exposure")
    exposure_rabbits: Optional[bool] = Field(default=None, description="Rabbit exposure")
    exposure_other: Optional[str] = Field(default=None, description="Other exposures")
    
    # =========================================================================
    # SYMPTOMS & PHYSICAL EXAM (12 columns)
    # =========================================================================
    
    symptom_narrative: Optional[str] = Field(
        default=None,
        description="Full narrative of presenting symptoms"
    )
    symptom_asymptomatic: Optional[bool] = Field(default=None, description="Asymptomatic/incidental")
    symptom_dyspnea: Optional[bool] = Field(default=None, description="Dyspnea present")
    symptom_cough_dry: Optional[bool] = Field(default=None, description="Dry/non-productive cough")
    symptom_chest_pressure: Optional[bool] = Field(default=None, description="Chest pressure/discomfort")
    symptom_wheezing: Optional[bool] = Field(default=None, description="Wheezing")
    symptom_fever: Optional[bool] = Field(default=None, description="Fever")
    symptom_progression: Optional[bool] = Field(default=None, description="Progressive symptoms")
    symptom_persistence: Optional[bool] = Field(default=None, description="Persistent symptoms")
    exam_spo2: Optional[str] = Field(default=None, description="SpO2 value if reported")
    physical_exam_narrative: Optional[str] = Field(default=None, description="Physical exam findings")
    discovery_reason: Optional[str] = Field(default=None, description="Reason for discovery/presentation")
    
    # =========================================================================
    # PULMONARY FUNCTION TESTS (12 columns)
    # =========================================================================
    
    pulmonary_function_testing_spirometry_narrative: Optional[str] = Field(
        default=None,
        description="Full narrative of PFT/spirometry results"
    )
    results_spirometry: Optional[str] = Field(default=None, description="Spirometry result summary")
    results_fev1: Optional[str] = Field(default=None, description="FEV1 value")
    results_fvc: Optional[str] = Field(default=None, description="FVC value")
    results_fev1_fvc: Optional[str] = Field(default=None, description="FEV1/FVC ratio")
    results_dlco: Optional[str] = Field(default=None, description="DLCO value")
    bronchoscopy_findings: Optional[str] = Field(default=None, description="Bronchoscopy findings")
    results_bal: Optional[str] = Field(default=None, description="BAL results")
    results_transbronchial_biopsy: Optional[str] = Field(default=None, description="Transbronchial biopsy results")
    results_negative_narrative: Optional[str] = Field(default=None, description="Negative/normal results")
    laboratory_features: Optional[str] = Field(default=None, description="Laboratory findings")
    clinical_features: Optional[str] = Field(default=None, description="Clinical features summary")
    
    # =========================================================================
    # IMAGING / CT (15 columns)
    # =========================================================================
    
    radiological_characteristics: Optional[str] = Field(default=None, description="Radiological characteristics summary")
    ct_narrative: Optional[str] = Field(
        default=None,
        description="Full narrative of CT findings including nodule size, pattern, distribution"
    )
    ct_size: Optional[str] = Field(default=None, description="Nodule size (e.g., '2-5mm')")
    ct_ground_glass: Optional[bool] = Field(default=None, description="Ground glass nodules")
    ct_solid_nodules: Optional[bool] = Field(default=None, description="Solid nodules")
    ct_central_cavitation: Optional[bool] = Field(default=None, description="Central cavitation")
    ct_cystic_micronodules: Optional[bool] = Field(default=None, description="Cystic micronodules")
    ct_random: Optional[bool] = Field(default=None, description="Random distribution")
    ct_cheerio: Optional[bool] = Field(default=None, description="Cheerio sign")
    ct_upper_lobe_predominance: Optional[bool] = Field(default=None, description="Upper lobe predominance")
    ct_lower_lobe_predominance: Optional[bool] = Field(default=None, description="Lower lobe predominance")
    ct_central_perihilar_predominance: Optional[bool] = Field(default=None, description="Central/perihilar predominance")
    ct_subpleural_predominance: Optional[bool] = Field(default=None, description="Subpleural predominance")
    ct_assoc_emphysema: Optional[bool] = Field(default=None, description="Associated emphysema")
    ct_assoc_fibrosis: Optional[bool] = Field(default=None, description="Associated fibrosis")
    ct_thickened_intralobular_septum: Optional[bool] = Field(default=None, description="Thickened intralobular septum")
    
    # =========================================================================
    # PATHOLOGY (7 columns)
    # =========================================================================
    
    pathological_features_narrative: Optional[str] = Field(
        default=None,
        description="Full narrative of pathological features"
    )
    gross_features: Optional[str] = Field(default=None, description="Gross pathology features")
    gross_subpleural_predominance: Optional[bool] = Field(default=None, description="Gross subpleural predominance")
    histology_narrative: Optional[str] = Field(
        default=None,
        description="Full narrative of histological findings"
    )
    histo_perivascular_distribution: Optional[bool] = Field(default=None, description="Perivascular distribution")
    primary_histologic_pattern: Optional[str] = Field(default=None, description="Primary histologic pattern")
    ultrastructure_em_features: Optional[str] = Field(default=None, description="Electron microscopy features")
    
    # =========================================================================
    # BIOPSY / DIAGNOSTIC APPROACH (13 columns)
    # =========================================================================
    
    diagnostic_approach: Optional[str] = Field(
        default=None,
        description="Full narrative of diagnostic approach and biopsy methods"
    )
    biopsy_tblb: Optional[bool] = Field(default=None, description="TBLB performed")
    biopsy_endobronchial: Optional[bool] = Field(default=None, description="Endobronchial biopsy performed")
    biopsy_ttnb: Optional[bool] = Field(default=None, description="TTNB performed")
    biopsy_surgical: Optional[bool] = Field(default=None, description="Surgical biopsy (VATS/open)")
    biopsy_cryobiopsy: Optional[bool] = Field(default=None, description="Cryobiopsy performed")
    biopsy_autopsy: Optional[bool] = Field(default=None, description="Autopsy")
    biopsy_tblb_diagnostic: Optional[bool] = Field(default=None, description="TBLB was diagnostic")
    biopsy_endobronchial_diagnostic: Optional[bool] = Field(default=None, description="Endobronchial biopsy was diagnostic")
    biopsy_ttnb_diagnostic: Optional[bool] = Field(default=None, description="TTNB was diagnostic")
    biopsy_surgical_diagnostic: Optional[bool] = Field(default=None, description="Surgical biopsy was diagnostic")
    biopsy_cryobiopsy_diagnostic: Optional[bool] = Field(default=None, description="Cryobiopsy was diagnostic")
    method_of_diagnosis: Optional[str] = Field(default=None, description="Primary method of diagnosis")
    
    # =========================================================================
    # IMMUNOHISTOCHEMISTRY (18 columns)
    # =========================================================================
    
    immunohistochemistry_narrative: Optional[str] = Field(
        default=None,
        description="Full narrative of IHC results including all markers tested"
    )
    ihc_ema_pos: Optional[bool] = Field(default=None, description="EMA positive")
    ihc_ema_neg: Optional[bool] = Field(default=None, description="EMA negative")
    ihc_pr_pos: Optional[bool] = Field(default=None, description="PR positive")
    ihc_pr_neg: Optional[bool] = Field(default=None, description="PR negative")
    ihc_vimentin_pos: Optional[bool] = Field(default=None, description="Vimentin positive")
    ihc_vimentin_neg: Optional[bool] = Field(default=None, description="Vimentin negative")
    ihc_ttf1_pos: Optional[bool] = Field(default=None, description="TTF-1 positive")
    ihc_ttf1_neg: Optional[bool] = Field(default=None, description="TTF-1 negative")
    ihc_cytokeratin_pos: Optional[bool] = Field(default=None, description="Cytokeratin positive")
    ihc_cytokeratin_neg: Optional[bool] = Field(default=None, description="Cytokeratin negative")
    ihc_s100_pos: Optional[bool] = Field(default=None, description="S100 positive")
    ihc_s100_neg: Optional[bool] = Field(default=None, description="S100 negative")
    ihc_sma_pos: Optional[bool] = Field(default=None, description="SMA positive")
    ihc_sma_neg: Optional[bool] = Field(default=None, description="SMA negative")
    ihc_ki67_high: Optional[bool] = Field(default=None, description="Ki67 high (>5%)")
    ihc_ki67_neg: Optional[bool] = Field(default=None, description="Ki67 low (<5%)")
    ihc_profile_summary: Optional[str] = Field(default=None, description="IHC profile summary")
    
    # =========================================================================
    # MANAGEMENT (5 columns)
    # =========================================================================
    
    management_narrative: Optional[str] = Field(
        default=None,
        description="Full narrative of treatment and management approach"
    )
    mgmt_observation: Optional[bool] = Field(default=None, description="Conservative observation")
    mgmt_no_followup_data: Optional[bool] = Field(default=None, description="No follow-up data available")
    mgmt_hormone_therapy_withdrawal: Optional[bool] = Field(default=None, description="HRT discontinued")
    mgmt_lung_transplant_referral: Optional[bool] = Field(default=None, description="Lung transplant referral")
    
    # =========================================================================
    # OUTCOMES (10 columns)
    # =========================================================================
    
    outcomes: Optional[str] = Field(
        default=None,
        description="Full narrative of patient outcomes"
    )
    outcome_followup_available: Optional[bool] = Field(default=None, description="Follow-up data available")
    followup_duration_unit_raw: Optional[str] = Field(default=None, description="Follow-up duration as stated")
    followup_interval_imaging_months: Optional[float] = Field(default=None, description="Imaging follow-up interval in months")
    followup_interval_clinical_months: Optional[float] = Field(default=None, description="Clinical follow-up in months")
    outcome_dpm_stable: Optional[bool] = Field(default=None, description="DPM stable on follow-up")
    outcome_dpm_improved: Optional[bool] = Field(default=None, description="DPM improved")
    outcome_dpm_progressed: Optional[bool] = Field(default=None, description="DPM progressed")
    outcome_dpm_died: Optional[bool] = Field(default=None, description="Patient died")
    authors_followup_recommendation_narrative: Optional[str] = Field(
        default=None,
        description="Authors' follow-up recommendations"
    )
    
    # =========================================================================
    # EXTRACTION METADATA
    # =========================================================================
    
    extraction_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Overall extraction confidence"
    )
    extraction_notes: Optional[str] = Field(
        default=None,
        description="Notes about extraction quality or limitations"
    )


# Schema for LLM extraction (narratives only - binaries derived later)
class DPMNarrativeExtractionSchema(BaseModel):
    """
    Narrative-only extraction schema for LLM.
    
    Extracts 15 narrative fields plus key metadata.
    Binary fields are derived in post-processing.
    """
    
    # Metadata
    filename: Optional[str] = Field(default=None)
    study_type: Optional[str] = Field(default=None, description="Case Report, Case Series, etc.")
    number_of_cases: Optional[int] = Field(default=None, ge=0)
    
    # Core narratives (15 fields)
    patient_demographics_narrative: Optional[str] = Field(
        default=None,
        description="Patient age, sex, smoking status, and demographics"
    )
    age: Optional[str] = Field(default=None, description="Patient age(s)")
    female_count: Optional[int] = Field(default=None)
    male_count: Optional[int] = Field(default=None)
    
    associated_conditions_narrative: Optional[str] = Field(
        default=None,
        description="All comorbidities, associated conditions, exposures"
    )
    
    symptom_narrative: Optional[str] = Field(
        default=None,
        description="All presenting symptoms and physical exam findings"
    )
    discovery_reason: Optional[str] = Field(default=None)
    
    pulmonary_function_testing_spirometry_narrative: Optional[str] = Field(
        default=None,
        description="PFT results, spirometry, bronchoscopy, BAL findings"
    )
    
    ct_narrative: Optional[str] = Field(
        default=None,
        description="All CT findings: nodule characteristics, size, distribution, patterns"
    )
    ct_size: Optional[str] = Field(default=None)
    
    pathological_features_narrative: Optional[str] = Field(
        default=None,
        description="Gross and histological findings"
    )
    histology_narrative: Optional[str] = Field(default=None)
    primary_histologic_pattern: Optional[str] = Field(default=None)
    
    diagnostic_approach: Optional[str] = Field(
        default=None,
        description="Biopsy methods and diagnostic approach"
    )
    method_of_diagnosis: Optional[str] = Field(default=None)
    
    immunohistochemistry_narrative: Optional[str] = Field(
        default=None,
        description="All IHC markers and results"
    )
    
    management_narrative: Optional[str] = Field(
        default=None,
        description="Treatment and management approach"
    )
    
    outcomes: Optional[str] = Field(
        default=None,
        description="Patient outcomes and follow-up"
    )
    followup_duration_unit_raw: Optional[str] = Field(default=None)
    
    authors_followup_recommendation_narrative: Optional[str] = Field(default=None)
    
    extraction_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    extraction_notes: Optional[str] = Field(default=None)


# Column name mapping for CSV export
COLUMN_NAME_MAPPING = {
    "title": "Title",
    "authors": "Authors",
    "doi": "DOI",
    "doi_link": "DOI link",
    "journal_venue": "Journal / Venue",
    "year": "Year",
    "filename": "Filename",
    "study_type": "Study Type",
    "number_of_cases": "Number of cases",
    "study_type_narrative": "Study_Type_narrative",
    "patient_demographics_narrative": "Patient_Demographics_narrative",
    "age": "Age",
    "female_count": "Female_count",
    "male_count": "Male_count",
    "non_smoker": "Non-smoker",
    "associated_conditions_narrative": "Associated_Conditions_narrative",
    "assoc_pulmonary_ca": "Assoc_Pulmonary CA",
    "assoc_extrapulmonary_ca": "Assoc_Extrapulmonary CA",
    "assoc_pulmonary_embolism": "Assoc_pulmonaryEmbolism",
    "assoc_gerd": "Assoc_GERD",
    "assoc_cad": "Assoc_CAD",
    "assoc_metabolic_disease": "Assoc_Metabolic disease",
    "assoc_hypersensitivity_pneumonitis": "Assoc_Hypersensitivity pneumonitis",
    "assoc_cryptococcus": "Assoc_Cryptococcus",
    "assoc_autoimmune_dz": "Assoc_Autoimmune dz",
    "assoc_hypothyroid": "Assoc_hypoThyroid",
    "assoc_turner_syndrome": "Assoc_Turner syndrome",
    "assoc_hrt": "Assoc_HRT",
    "exposure_birds": "Exposure_Birds",
    "exposure_rabbits": "Exposure_rabbits",
    "exposure_other": "Exposure_other",
    "symptom_narrative": "Symptom_narrative",
    "symptom_asymptomatic": "Symptom_asymptomatic",
    "symptom_dyspnea": "Symptom_Dyspnea",
    "symptom_cough_dry": "Symptom_Cough_dry",
    "symptom_chest_pressure": "Symptom_Chest_pressure",
    "symptom_wheezing": "Symptom_Wheezing",
    "symptom_fever": "Symptom_Fever",
    "symptom_progression": "Symptom_Progression",
    "symptom_persistence": "Symptom_Persistence",
    "exam_spo2": "Exam_SpO2",
    "physical_exam_narrative": "PhysicalExam_narrative",
    "discovery_reason": "Discovery reason",
    "pulmonary_function_testing_spirometry_narrative": "Pulmonary_Function_Testing_Spirometry_Narrative",
    "results_spirometry": "Results_Spirometry",
    "results_fev1": "Results_FEV1",
    "results_fvc": "Results_FVC",
    "results_fev1_fvc": "Results_FEV1/FVC",
    "results_dlco": "Results_DLCO mL/min/mmHg (%predicted)",
    "bronchoscopy_findings": "Bronchoscopy findings",
    "results_bal": "Results_BAL",
    "results_transbronchial_biopsy": "Results_transbronchial_biopsy",
    "results_negative_narrative": "Results_negative_narrative",
    "laboratory_features": "Laboratory Fetures",
    "clinical_features": "Clinical Features",
    "radiological_characteristics": "Radiological Characteristics",
    "ct_narrative": "CT_narrative",
    "ct_size": "CT_size",
    "ct_ground_glass": "CT_groundGlass",
    "ct_solid_nodules": "CT_solidnodules",
    "ct_central_cavitation": "CT_centralCavitation",
    "ct_cystic_micronodules": "CT_cystic_micronodules",
    "ct_random": "CT_random",
    "ct_cheerio": "CT_cheerio",
    "ct_upper_lobe_predominance": "CT_upperLobePredominance",
    "ct_lower_lobe_predominance": "CT_lowerLobePredominance",
    "ct_central_perihilar_predominance": "CT_central_perihilarPredominance",
    "ct_subpleural_predominance": "CT_subpleural_predominance",
    "ct_assoc_emphysema": "CT_assoc_emphyema",
    "ct_assoc_fibrosis": "CT_assoc_fibrosis",
    "ct_thickened_intralobular_septum": "CT_thickenedIntraLobularSeptum",
    "pathological_features_narrative": "Pathological_Features_narrative",
    "gross_features": "Gross_features",
    "gross_subpleural_predominance": "Gross_subpleural_predominance",
    "histology_narrative": "Histology_narrative",
    "histo_perivascular_distribution": "Histo_perivascular_distribution",
    "primary_histologic_pattern": "Primary_histologic_pattern",
    "ultrastructure_em_features": "Ultrastructure_electronmicroscope_features",
    "diagnostic_approach": "Diagnostic Approach",
    "biopsy_tblb": "Biopsy_TBLB",
    "biopsy_endobronchial": "Biopsy_endobronchial",
    "biopsy_ttnb": "Biopsy_TTNB",
    "biopsy_surgical": "Biopsy_surgical",
    "biopsy_cryobiopsy": "Biopsy_cryobiopsy",
    "biopsy_autopsy": "Biopsy_autopsy",
    "biopsy_tblb_diagnostic": "Biopsy_TBLB_diagnostic",
    "biopsy_endobronchial_diagnostic": "Biopsy_endobronchial_diagnostic",
    "biopsy_ttnb_diagnostic": "Biopsy_TTNB_diagnostic",
    "biopsy_surgical_diagnostic": "Biopsy_surgical_diagnostic",
    "biopsy_cryobiopsy_diagnostic": "Biopsy_cryobiopsy_diagnostic",
    "method_of_diagnosis": "Method of Diagnosis",
    "immunohistochemistry_narrative": "Immunohistochemistry_narrative",
    "ihc_ema_pos": "IHC_EMA_pos",
    "ihc_ema_neg": "IHC_EMA_neg",
    "ihc_pr_pos": "IHC_PR_pos",
    "ihc_pr_neg": "IHC_PR_neg",
    "ihc_vimentin_pos": "IHC_vimentin_pos",
    "ihc_vimentin_neg": "IHC_vimentin_neg",
    "ihc_ttf1_pos": "IHC_TTF1_pos",
    "ihc_ttf1_neg": "IHC_TTF1_neg",
    "ihc_cytokeratin_pos": "IHC_cytokeratin_pos",
    "ihc_cytokeratin_neg": "IHC_cytokeratin_neg",
    "ihc_s100_pos": "IHC_S100_pos",
    "ihc_s100_neg": "IHC_S100_neg",
    "ihc_sma_pos": "IHC_SMA_pos",
    "ihc_sma_neg": "IHC_SMA_neg",
    "ihc_ki67_high": "IHC_Ki67_high",
    "ihc_ki67_neg": "IHC_Ki67_neg",
    "ihc_profile_summary": "IHC_profile_summary",
    "management_narrative": "Management_narrative",
    "mgmt_observation": "Mgmt_observation",
    "mgmt_no_followup_data": "Mgmt_no_followup_data",
    "mgmt_hormone_therapy_withdrawal": "Mgmt_hormone_therapy_withdrawal",
    "mgmt_lung_transplant_referral": "Mgmt_lung_transplant_referral",
    "outcomes": "Outcomes",
    "outcome_followup_available": "Outcome_followup_available",
    "followup_duration_unit_raw": "Followup_duration_unit_raw",
    "followup_interval_imaging_months": "Followup_interval_imaging_months",
    "followup_interval_clinical_months": "Followup_interval_clinical_months",
    "outcome_dpm_stable": "Outcome_DPM_stable",
    "outcome_dpm_improved": "Outcome_DPM_improved",
    "outcome_dpm_progressed": "Outcome_DPM_progressed",
    "outcome_dpm_died": "Outcome_DPM_died",
    "authors_followup_recommendation_narrative": "Authors_followup_recommendation_narrative",
}


def get_csv_column_order() -> list:
    """Return columns in gold standard CSV order."""
    return [
        "", "Title", "Authors", "DOI", "DOI link", "Journal / Venue", "Year", "Filename",
        "Study Type", "Number of cases", "Study_Type_narrative", "Patient_Demographics_narrative",
        "Age", "Female_count", "Male_count", "Non-smoker",
        "Assoc_Pulmonary CA", "Assoc_Extrapulmonary CA", "Assoc_pulmonaryEmbolism", "Assoc_GERD",
        "Assoc_CAD", "Assoc_Metabolic disease", "Assoc_Hypersensitivity pneumonitis", "Assoc_Cryptococcus",
        "Assoc_Autoimmune dz", "Assoc_hypoThyroid", "Assoc_Turner syndrome", "Assoc_HRT",
        "Exposure_Birds", "Exposure_rabbits", "Exposure_other", "Associated_Conditions_narrative",
        "Symptom_narrative", "Symptom_asymptomatic", "Symptom_Dyspnea", "Symptom_Cough_dry",
        "Symptom_Chest_pressure", "Symptom_Wheezing", "Symptom_Fever", "Symptom_Progression",
        "Symptom_Persistence", "Exam_SpO2", "PhysicalExam_narrative", "Discovery reason",
        "Results_Spirometry", "Results_FEV1", "Results_FVC", "Results_FEV1/FVC",
        "Results_DLCO mL/min/mmHg (%predicted)", "Pulmonary_Function_Testing_Spirometry_Narrative",
        "Bronchoscopy findings", "Results_BAL", "Results_transbronchial_biopsy", "Results_negative_narrative",
        "Laboratory Fetures", "Clinical Features", "Radiological Characteristics", "CT_narrative",
        "CT_size", "CT_groundGlass", "CT_solidnodules", "CT_centralCavitation",
        "CT_cystic_micronodules", "CT_random", "CT_cheerio", "CT_upperLobePredominance",
        "CT_lowerLobePredominance", "CT_central_perihilarPredominance", "CT_subpleural_predominance",
        "CT_assoc_emphyema", "CT_assoc_fibrosis", "CT_thickenedIntraLobularSeptum",
        "Pathological_Features_narrative", "Gross_features", "Gross_subpleural_predominance",
        "Histology_narrative", "Histo_perivascular_distribution", "Primary_histologic_pattern",
        "Ultrastructure_electronmicroscope_features", "Diagnostic Approach",
        "Biopsy_TBLB", "Biopsy_endobronchial", "Biopsy_TTNB", "Biopsy_surgical",
        "Biopsy_cryobiopsy", "Biopsy_autopsy", "Biopsy_TBLB_diagnostic", "Biopsy_endobronchial_diagnostic",
        "Biopsy_TTNB_diagnostic", "Biopsy_surgical_diagnostic", "Biopsy_cryobiopsy_diagnostic",
        "Method of Diagnosis", "Immunohistochemistry_narrative",
        "IHC_EMA_pos", "IHC_EMA_neg", "IHC_PR_pos", "IHC_PR_neg",
        "IHC_vimentin_pos", "IHC_vimentin_neg", "IHC_TTF1_pos", "IHC_TTF1_neg",
        "IHC_cytokeratin_pos", "IHC_cytokeratin_neg", "IHC_S100_pos", "IHC_S100_neg",
        "IHC_SMA_pos", "IHC_SMA_neg", "IHC_Ki67_high", "IHC_Ki67_neg", "IHC_profile_summary",
        "Management_narrative", "Mgmt_observation", "Mgmt_no_followup_data",
        "Mgmt_hormone_therapy_withdrawal", "Mgmt_lung_transplant_referral",
        "Outcomes", "Outcome_followup_available", "Followup_duration_unit_raw",
        "Followup_interval_imaging_months", "Followup_interval_clinical_months",
        "Outcome_DPM_stable", "Outcome_DPM_improved", "Outcome_DPM_progressed", "Outcome_DPM_died",
        "Authors_followup_recommendation_narrative",
    ]
