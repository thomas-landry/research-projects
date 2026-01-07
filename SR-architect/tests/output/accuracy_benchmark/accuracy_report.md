# Extraction Accuracy Report

Generated: 2026-01-07 08:33

---

## Summary

| Model | Time (s) | Exact | Key Terms | Semantic | Complete | CAS |
|-------|----------|-------|-----------|----------|----------|-----|
| llama3.1:8b | 389.2 | 9% | 45% | 23% | 64% | **0.50** |
| mistral:latest | 585.2 | 6% | 33% | 15% | 45% | **0.35** |
| qwen2.5-coder:7b-instruct-q8_0 | 415.5 | 9% | 27% | 12% | 24% | **0.34** |
| anthropic/claude-3.5-sonnet | 99.7 | 24% | 64% | 58% | 79% | **0.69** |

> **CAS** = Clinical Accuracy Score (weighted by field importance)

---

## llama3.1:8b

### Field-Level Breakdown

| Field | Exact | Terms | Semantic | Present | Errors |
|-------|-------|-------|----------|---------|--------|
| case_count | 0/2 | 0/2 | 0/2 | 0/2 | 2 missing |
| patient_age | 1/2 | 1/2 | 1/2 | 2/2 | 1 wrong |
| patient_sex | 1/2 | 1/2 | 1/2 | 2/2 | 1 wrong |
| presenting_symptoms | 0/2 | 0/2 | 0/2 | 1/2 | 1 missing, 1 wrong |
| diagnostic_method | 0/2 | 1/2 | 1/2 | 2/2 | 1 wrong |
| imaging_findings | 0/2 | 2/2 | 0/2 | 2/2 | - |
| histopathology | 0/2 | 1/2 | 0/2 | 1/2 | 1 missing |
| immunohistochemistry | 0/2 | 1/2 | 0/2 | 0/2 | 1 missing |
| treatment | 0/2 | 2/2 | 1/2 | 2/2 | - |
| outcome | 0/2 | 0/2 | 0/2 | 0/2 | 2 missing |
| comorbidities | 0/2 | 1/2 | 1/2 | 2/2 | 1 wrong |

### Error Examples

**1. [MISSING] case_count** (Virk et al. - 2023 - RIDDLE ME THIS A RA...)
- Gold: `1`
- Extracted: ``
- Note: No value extracted when gold has data

**2. [MISSING] presenting_symptoms** (Virk et al. - 2023 - RIDDLE ME THIS A RA...)
- Gold: `asymptomatic, incidentally discovered during COVID-19 admission`
- Extracted: `[]`
- Note: No value extracted when gold has data

**3. [MISSING] outcome** (Virk et al. - 2023 - RIDDLE ME THIS A RA...)
- Gold: `stable nodules on follow-up`
- Extracted: `[]`
- Note: No value extracted when gold has data


---

## mistral:latest

### Field-Level Breakdown

| Field | Exact | Terms | Semantic | Present | Errors |
|-------|-------|-------|----------|---------|--------|
| case_count | 1/3 | 1/3 | 1/3 | 1/3 | 2 missing |
| patient_age | 0/3 | 1/3 | 1/3 | 1/3 | 2 missing |
| patient_sex | 0/3 | 0/3 | 0/3 | 2/3 | 1 missing, 2 wrong |
| presenting_symptoms | 0/3 | 1/3 | 1/3 | 1/3 | 2 missing |
| diagnostic_method | 0/3 | 1/3 | 0/3 | 1/3 | 2 missing |
| imaging_findings | 0/3 | 2/3 | 0/3 | 1/3 | 1 missing |
| histopathology | 0/3 | 1/3 | 1/3 | 1/3 | 2 missing |
| immunohistochemistry | 0/3 | 2/3 | 0/3 | 1/3 | 1 missing |
| treatment | 1/3 | 2/3 | 1/3 | 2/3 | 1 missing |
| outcome | 0/3 | 0/3 | 0/3 | 2/3 | 1 missing, 2 wrong |
| comorbidities | 0/3 | 0/3 | 0/3 | 2/3 | 1 missing, 2 wrong |

### Error Examples

**1. [MISSING] case_count** (Virk et al. - 2023 - RIDDLE ME THIS A RA...)
- Gold: `1`
- Extracted: ``
- Note: No value extracted when gold has data

**2. [MISSING] patient_age** (Virk et al. - 2023 - RIDDLE ME THIS A RA...)
- Gold: `61`
- Extracted: ``
- Note: No value extracted when gold has data

**3. [MISSING] patient_sex** (Virk et al. - 2023 - RIDDLE ME THIS A RA...)
- Gold: `female`
- Extracted: ``
- Note: No value extracted when gold has data


---

## qwen2.5-coder:7b-instruct-q8_0

### Field-Level Breakdown

| Field | Exact | Terms | Semantic | Present | Errors |
|-------|-------|-------|----------|---------|--------|
| case_count | 1/3 | 1/3 | 1/3 | 1/3 | 2 missing |
| patient_age | 1/3 | 1/3 | 1/3 | 1/3 | 2 missing |
| patient_sex | 1/3 | 1/3 | 1/3 | 1/3 | 2 missing |
| presenting_symptoms | 0/3 | 0/3 | 0/3 | 0/3 | 3 missing |
| diagnostic_method | 0/3 | 1/3 | 0/3 | 1/3 | 2 missing |
| imaging_findings | 0/3 | 2/3 | 0/3 | 1/3 | 1 missing |
| histopathology | 0/3 | 0/3 | 1/3 | 1/3 | 2 missing |
| immunohistochemistry | 0/3 | 2/3 | 0/3 | 1/3 | 1 missing |
| treatment | 0/3 | 1/3 | 0/3 | 0/3 | 2 missing |
| outcome | 0/3 | 0/3 | 0/3 | 0/3 | 3 missing |
| comorbidities | 0/3 | 0/3 | 0/3 | 1/3 | 2 missing, 1 wrong |

### Error Examples

**1. [MISSING] case_count** (Virk et al. - 2023 - RIDDLE ME THIS A RA...)
- Gold: `1`
- Extracted: ``
- Note: No value extracted when gold has data

**2. [MISSING] patient_age** (Virk et al. - 2023 - RIDDLE ME THIS A RA...)
- Gold: `61`
- Extracted: ``
- Note: No value extracted when gold has data

**3. [MISSING] patient_sex** (Virk et al. - 2023 - RIDDLE ME THIS A RA...)
- Gold: `female`
- Extracted: ``
- Note: No value extracted when gold has data


---

## anthropic/claude-3.5-sonnet

### Field-Level Breakdown

| Field | Exact | Terms | Semantic | Present | Errors |
|-------|-------|-------|----------|---------|--------|
| case_count | 2/3 | 2/3 | 2/3 | 3/3 | 1 wrong |
| patient_age | 2/3 | 2/3 | 2/3 | 2/3 | 1 missing |
| patient_sex | 2/3 | 2/3 | 2/3 | 3/3 | 1 partial |
| presenting_symptoms | 0/3 | 1/3 | 1/3 | 2/3 | 1 missing, 1 partial |
| diagnostic_method | 0/3 | 2/3 | 2/3 | 2/3 | 1 missing |
| imaging_findings | 0/3 | 3/3 | 2/3 | 2/3 | - |
| histopathology | 0/3 | 2/3 | 1/3 | 2/3 | 1 missing |
| immunohistochemistry | 1/3 | 2/3 | 2/3 | 2/3 | 1 missing |
| treatment | 1/3 | 3/3 | 2/3 | 3/3 | - |
| outcome | 0/3 | 1/3 | 2/3 | 2/3 | 1 missing |
| comorbidities | 0/3 | 1/3 | 1/3 | 3/3 | 2 wrong |

### Error Examples

**1. [PARTIAL] presenting_symptoms** (Virk et al. - 2023 - RIDDLE ME THIS A RA...)
- Gold: `asymptomatic, incidentally discovered during COVID-19 admission`
- Extracted: `['asymptomatic']`
- Note: Missing: {'discovered', 'covid', 'during', '19', 'incidentally', 'admission'}

**2. [WRONG] comorbidities** (Kuroki et al. - 2002 - Minute Pulmonary ...)
- Gold: `nonsmoker (no other comorbidities reported)`
- Extracted: `['elevated CEA (16.6 ng/mL)']`
- Note: Different value

**3. [WRONG] case_count** (Luvison et al. - 2013 - Pulmonary mening...)
- Gold: `2`
- Extracted: `18`
- Note: Different value


---
