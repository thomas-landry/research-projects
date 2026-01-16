# Binary Field Rule Coverage Report

## Summary

- **Total binary fields:** 74
- **Fields with rules:** 58
- **Fields without rules:** 16
- **Coverage:** 78.4%

## Gaps by Domain

### Biopsy (8 uncovered)

- `biopsy_endobronchial`
- `biopsy_ttnb`
- `biopsy_autopsy`
- `biopsy_tblb_diagnostic`
- `biopsy_endobronchial_diagnostic`
- `biopsy_ttnb_diagnostic`
- `biopsy_surgical_diagnostic`
- `biopsy_cryobiopsy_diagnostic`

### Ct (2 uncovered)

- `ct_central_perihilar_predominance`
- `ct_thickened_intralobular_septum`

### Exposure (2 uncovered)

- `exposure_birds`
- `exposure_rabbits`

### Gross (1 uncovered)

- `gross_subpleural_predominance`

### Mgmt (2 uncovered)

- `mgmt_no_followup_data`
- `mgmt_lung_transplant_referral`

### Outcome (1 uncovered)

- `outcome_followup_available`

## Covered Fields

| Field | Source Narrative | Patterns |
|-------|------------------|----------|
| `assoc_autoimmune_dz` | associated_conditions_narrative | 7 |
| `assoc_cad` | associated_conditions_narrative | 4 |
| `assoc_cryptococcus` | associated_conditions_narrative | 2 |
| `assoc_extrapulmonary_ca` | associated_conditions_narrative | 8 |
| `assoc_gerd` | associated_conditions_narrative | 3 |
| `assoc_hrt` | associated_conditions_narrative | 3 |
| `assoc_hypersensitivity_pneumonitis` | associated_conditions_narrative | 2 |
| `assoc_hypothyroid` | associated_conditions_narrative | 1 |
| `assoc_metabolic_disease` | associated_conditions_narrative | 5 |
| `assoc_pulmonary_ca` | associated_conditions_narrative | 3 |
| `assoc_pulmonary_embolism` | associated_conditions_narrative | 3 |
| `assoc_turner_syndrome` | associated_conditions_narrative | 2 |
| `biopsy_cryobiopsy` | diagnostic_approach | 3 |
| `biopsy_surgical` | diagnostic_approach | 6 |
| `biopsy_tblb` | diagnostic_approach | 3 |
| `ct_assoc_emphysema` | ct_narrative | 1 |
| `ct_assoc_fibrosis` | ct_narrative | 2 |
| `ct_central_cavitation` | ct_narrative | 3 |
| `ct_cheerio` | ct_narrative | 3 |
| `ct_cystic_micronodules` | ct_narrative | 2 |
| `ct_ground_glass` | ct_narrative | 3 |
| `ct_lower_lobe_predominance` | ct_narrative | 2 |
| `ct_random` | ct_narrative | 2 |
| `ct_solid_nodules` | ct_narrative | 2 |
| `ct_subpleural_predominance` | ct_narrative | 2 |
| `ct_upper_lobe_predominance` | ct_narrative | 2 |
| `histo_perivascular_distribution` | histology_narrative | 2 |
| `ihc_cytokeratin_neg` | immunohistochemistry_narrative | 2 |
| `ihc_cytokeratin_pos` | immunohistochemistry_narrative | 2 |
| `ihc_ema_neg` | immunohistochemistry_narrative | 2 |
| `ihc_ema_pos` | immunohistochemistry_narrative | 2 |
| `ihc_ki67_high` | immunohistochemistry_narrative | 1 |
| `ihc_ki67_neg` | immunohistochemistry_narrative | 1 |
| `ihc_pr_neg` | immunohistochemistry_narrative | 2 |
| `ihc_pr_pos` | immunohistochemistry_narrative | 3 |
| `ihc_s100_neg` | immunohistochemistry_narrative | 2 |
| `ihc_s100_pos` | immunohistochemistry_narrative | 1 |
| `ihc_sma_neg` | immunohistochemistry_narrative | 2 |
| `ihc_sma_pos` | immunohistochemistry_narrative | 2 |
| `ihc_ttf1_neg` | immunohistochemistry_narrative | 2 |
| `ihc_ttf1_pos` | immunohistochemistry_narrative | 1 |
| `ihc_vimentin_neg` | immunohistochemistry_narrative | 1 |
| `ihc_vimentin_pos` | immunohistochemistry_narrative | 2 |
| `mgmt_hormone_therapy_withdrawal` | management_narrative | 2 |
| `mgmt_observation` | management_narrative | 5 |
| `non_smoker` | patient_demographics_narrative | 3 |
| `outcome_dpm_died` | outcomes | 4 |
| `outcome_dpm_improved` | outcomes | 3 |
| `outcome_dpm_progressed` | outcomes | 3 |
| `outcome_dpm_stable` | outcomes | 4 |
| `symptom_asymptomatic` | symptom_narrative | 5 |
| `symptom_chest_pressure` | symptom_narrative | 4 |
| `symptom_cough_dry` | symptom_narrative | 4 |
| `symptom_dyspnea` | symptom_narrative | 6 |
| `symptom_fever` | symptom_narrative | 2 |
| `symptom_persistence` | symptom_narrative | 4 |
| `symptom_progression` | symptom_narrative | 3 |
| `symptom_wheezing` | symptom_narrative | 2 |
