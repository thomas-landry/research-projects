# Semantic Schema - Design Decisions Log

**Track:** `semantic_schema_20260116`  
**Created:** 2026-01-15

---

## Decision 1: FindingReport over Boolean

**Date:** 2026-01-15  
**Status:** ✅ Approved

**Context:**
Original schema used `bool` for binary findings (e.g., `ct_ground_glass: bool`)

**Problem:**
- `None` conflates "not reported" with "absent"
- Lost n/N proportions (can't do meta-analysis)
- Mixed aggregation units undetectable

**Decision:**
Use `FindingReport(status, n, N, aggregation_unit)` for all binary findings

**Rationale:**
- Cochrane standard requires n/N for dichotomous outcomes
- Tri-state enables valid exclusion of unreported data
- Aggregation unit tracking prevents invalid pooling

**Alternatives Considered:**
1. Separate NULL markers → too complex
2. Confidence scores only → doesn't solve semantics

---

## Decision 2: MeasurementData over String

**Date:** 2026-01-15  
**Status:** ✅ Approved

**Context:**
Original schema used `str` for age, follow-up (e.g., `age: str`)

**Problem:**
- Mixed units (years/months)
- Mixed formats (point/range/IQR)
- Requires second cleaning pipeline

**Decision:**
Use `MeasurementData(raw_text, value_min, value_max, value_point_estimate, value_unit)`

**Rationale:**
- Enables meta-regression without post-processing
- Preserves raw text for auditing
- Standardizes units at extraction time

---

## Decision 3: ColumnSpec with Extraction Policy

**Date:** 2026-01-15  
**Status:** ✅ Approved

**Context:**
Fields need varying extraction strategies

**Problem:**
- METADATA (title, DOI) → low hallucination risk
- MUST_BE_EXPLICIT (IHC results) → high hallucination risk
- No way to route fields to appropriate handlers

**Decision:**
Add `ExtractionPolicy` enum to `ColumnSpec`

**Rationale:**
- Enables automatic routing to HITL for high-risk fields
- Reduces unnecessary human review of low-risk fields
- Generates appropriate prompts per policy

---

## Decision 4: Cohort-Level Rows

**Date:** 2026-01-15  
**Status:** ✅ Approved

**Context:**
Papers may report multiple cohorts (Stage I vs Stage II)

**Problem:**
- Paper-level rows mix cohort denominators
- Can't do stratified analysis
- Ambiguous proportions

**Decision:**
Use `DPMCohort` with `study_id` + `cohort_id` linkage

**Rationale:**
- Unambiguous denominators per cohort
- Enables subgroup meta-analysis
- Duplicated study metadata is acceptable (most papers = 1 cohort)

**Trade-off:**
- More rows for multi-cohort papers
- Some metadata duplication
- Worth it for analysis validity

---

## Decision 5: Denormalized over Relational

**Date:** 2026-01-15  
**Status:** ✅ Approved

**Context:**
Could normalize Study vs Cohort into separate tables

**Problem:**
- CSV is primary export format
- Joins complicate analysis workflow
- Over-engineering for typical case

**Decision:**
Denormalized single-table design for v1

**Rationale:**
- Most papers have 1 cohort (minimal duplication)
- CSV export is simpler
- Can refactor to relational in v2 if needed

**Migration Path:**
- v1: Denormalized DPMCohort
- v2: Split to Study + Cohort if duplication becomes problematic

---

## Decision 6: Two Level-2 Types Only

**Date:** 2026-01-15  
**Status:** ✅ Approved

**Context:**
Could create specialized types: AgeData, FollowUpData, LesionSizeData, etc.

**Problem:**
- Type explosion (10+ specialized types)
- Maintenance burden
- Over-engineering

**Decision:**
Use only 2 core structured types:
1. `FindingReport` - for binary/categorical findings with n/N
2. `MeasurementData` - for continuous measurements with normalization

**Rationale:**
- AgeData, FollowUpData, LesionSizeData all fit MeasurementData pattern
- Reduces type count from ~10 to 2
- Simpler to maintain and understand

**Rule:**
Create Level-3 specialized type ONLY if Level-2 truly inadequate

---

## Decision 7: Field Library as Source of Truth

**Date:** 2026-01-15  
**Status:** ✅ Approved

**Context:**
ColumnSpec could be separate from Pydantic Field

**Problem:**
- Duplication between spec metadata and Field metadata
- Drift between spec and implementation

**Decision:**
ColumnSpec is source of truth, `.to_field()` generates Pydantic Field

**Rationale:**
- DRY: define once, generate Field and prompts
- Type-safe: specs are validated
- Discoverable: IntelliSense shows library methods

---

## Open Questions

### Q1: Evidence Quote Default Behavior
**Status:** 🟡 Needs User Input

When `requires_evidence_quote=True`, should extraction:
- A) FAIL if no quote found
- B) PASS with low confidence and no quote
- C) Flag for human review

**Recommendation:** Option C (flag for review)

### Q2: Aggregation Unit Defaults
**Status:** 🟡 Needs User Input

Should `FindingReport.aggregation_unit` default to:
- A) `PATIENT` (optimistic)
- B) `UNCLEAR` (conservative)

**Recommendation:** 
- `PATIENT` for symptoms/demographics (common case)
- `UNCLEAR` for imaging/pathology (often lesion-level)

### Q3: Multi-Cohort Ambiguity Handling
**Status:** 🟡 Needs User Input

When cohorts are unclear ("some patients had X"):
- A) Create 2 partial cohorts
- B) Create 1 mixed cohort, flag for review
- C) Skip extraction

**Recommendation:** Option B for v1
