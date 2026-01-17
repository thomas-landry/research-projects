# Final Refined Specification - Critical Evaluation

**Date:** 2026-01-15  
**Goal:** Synthesize feedback, identify remaining gaps, propose pragmatic improvements

---

## What's Now Clear (User's Complete Vision)

### Core Architecture

1. **Tri-State + n/N for all findings** (Cochrane standard)
2. **Explicit aggregation units** (PATIENT | LESION | SPECIMEN)
3. **Normalized fields** (raw text + structured values)
4. **ColumnSpec with extraction policies** (not just Pydantic fields)
5. **Spec-to-prompt generation** (automated prompt creation)
6. **Cohort-level rows** (one row per study cohort, not per paper)

### The Evolution

```
v1 (My initial):     bool columns → Simple but wrong
v2 (User critique):  FindingReport(status, n, N) → Correct
v3 (User detail):    + aggregation_unit + ColumnSpec + generators → Complete
```

---

## Critical Evaluation: What's Still Missing or Unclear

### Gap 1: Field Type Hierarchy Complexity ⚠️

**Current approach suggests:**
- `FindingReport` for binary findings
- `AgeData` for age
- `FollowUpDuration` for follow-up
- `CountData` for counts

**Risk:** Type explosion
- Need ~10 specialized types for different field patterns
- Each requires custom validation logic
- Maintenance burden grows

**Pragmatic fix:** Establish a pattern hierarchy

```python
# Level 1: Base types (use directly for simple cases)
str, int, float, bool

# Level 2: Common structured types (reusable)
class FindingReport(BaseModel):
    """For ANY binary/categorical finding with frequencies"""
    status: Status
    n: Optional[int] = None
    N: Optional[int] = None
    aggregation_unit: AggregationUnit = AggregationUnit.PATIENT
    
class MeasurementData(BaseModel):
    """For ANY continuous measurement with normalization"""
    raw_text: Optional[str] = None
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    value_point_estimate: Optional[float] = None
    value_unit: Optional[str] = None  # "years", "months", "mm", "cm"
    
# Level 3: Domain-specific (when Level 2 doesn't fit)
# Only create these if Level 2 is truly inadequate
```

**Rule:** Start with Level 2 types. Only create Level 3 if absolutely necessary.

**Examples:**
- Age → `MeasurementData(value_unit="years")`
- Follow-up → `MeasurementData(value_unit="months")`
- Lesion size → `MeasurementData(value_unit="mm")`

**Benefit:** Reduces type count from ~10 to 2-3 core types.

---

### Gap 2: ColumnSpec vs Pydantic Field Integration Unclear

**User suggests:**
```python
class ColumnSpec:
    key: str
    dtype: str
    extraction_policy: ExtractionPolicy
    # ... metadata
```

**Question:** How does `ColumnSpec` relate to Pydantic schema definition?

**Two options:**

**Option A: ColumnSpec generates Pydantic fields (decoupled)**
```python
# 1. Define specs
age_spec = ColumnSpec(key="age", dtype="MeasurementData", ...)

# 2. Generate Pydantic model
class DPMCohort(BaseModel):
    age: Optional[MeasurementData] = spec_to_field(age_spec)
```

**Pros:** Separation of concerns, specs can be used for prompts too  
**Cons:** Two-step process, potential for spec/model mismatch

**Option B: ColumnSpec IS Pydantic field metadata (coupled)**
```python
# Pydantic field with ColumnSpec in metadata
class DPMCohort(BaseModel):
    age: Optional[MeasurementData] = Field(
        default=None,
        json_schema_extra={
            "column_spec": {
                "extraction_policy": "MUST_BE_EXPLICIT",
                "high_confidence_keywords": ["age", "years old"],
            }
        }
    )
```

**Pros:** One definition, no mismatch  
**Cons:** Metadata buried in Pydantic Field

**Recommendation: Hybrid**

```python
# ColumnSpec library (source of truth)
AGE_SPEC = ColumnSpec(
    key="age",
    dtype=MeasurementData,
    extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
    high_confidence_keywords=["age", "years old"],
)

# Schema references spec
class DPMCohort(BaseModel):
    age: Optional[MeasurementData] = AGE_SPEC.to_field()
    
# Elsewhere: generate prompts from spec
prompt = generate_extraction_prompt(AGE_SPEC)
```

**Why hybrid:**
- Specs are source of truth (DRY)
- `.to_field()` converts to Pydantic (type-safe)
- Specs available for prompt generation
- No duplication

---

### Gap 3: Aggregation Unit Validation Missing

**User correctly identifies:** Need `aggregation_unit` tracking

**Missing piece:** How to validate consistency?

**Problem scenarios:**
1. `ct_ground_glass.N = 5, ct_solid_nodules.N = 10` (different denominators - why?)
2. `ct_ground_glass.aggregation_unit = PATIENT, ihc_ema.aggregation_unit = SPECIMEN` (mixed - expected?)

**Solution: Cohort-level denominators as constraints**

```python
class DPMCohort(BaseModel):
    # === Study linkage ===
    study_id: str
    cohort_id: str
    cohort_n_patients: int  # ← Primary denominator
    
    # === Findings ===
    ct_ground_glass: FindingReport
    
    @validator('ct_ground_glass')
    def validate_patient_denominator(cls, v, values):
        """If aggregation_unit is PATIENT, N should match cohort_n_patients."""
        if v.aggregation_unit == AggregationUnit.PATIENT:
            if v.N is not None and v.N > values['cohort_n_patients']:
                raise ValueError(f"Patient denominator {v.N} exceeds cohort size {values['cohort_n_patients']}")
        return v
```

**Additional validation:**
- Warn if `N` varies across findings with same `aggregation_unit` (data quality issue)
- Require `aggregation_note` if `aggregation_unit = UNCLEAR`

---

### Gap 4: Extraction Prompt Generation Mechanics

**User proposes:** `spec_to_extraction_prompt()`

**Critical questions:**
1. **Per-field prompts or batch prompts?**
   - Per-field: 125 LLM calls (expensive, slow)
   - Batch: 1 call for all fields (cheaper, but LLM may miss some)

2. **How to handle narrative dependencies?**
   - `ct_ground_glass` needs `ct_narrative` field
   - Spec should know: "extract from ct_narrative, not full text"

3. **Evidence quote storage?**
   - User wants `requires_evidence_quote=True`
   - Where does quote get stored? In `FindingReport`? Separate field?

**Pragmatic solutions:**

**1. Hierarchical extraction:**
```python
# Step 1: Extract narratives (1 LLM call)
narratives = extract_narratives(pdf)  # ct_narrative, ihc_narrative, etc.

# Step 2: Derive findings from narratives (batch per domain)
ct_findings = extract_ct_findings_batch(
    narrative=narratives.ct_narrative,
    specs=[CT_GROUND_GLASS_SPEC, CT_SOLID_NODULES_SPEC, ...]
)
```

**Why:** Reduces calls, focuses extraction on relevant text

**2. Spec includes source narrative:**
```python
CT_GROUND_GLASS_SPEC = ColumnSpec(
    key="ct_ground_glass",
    dtype=FindingReport,
    source_narrative_field="ct_narrative",  # ← NEW
    extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
    high_confidence_keywords=["GGO", "ground glass"],
)
```

**3. FindingReport includes evidence:**
```python
class FindingReport(BaseModel):
    status: Optional[Status] = None
    n: Optional[int] = None
    N: Optional[int] = None
    aggregation_unit: AggregationUnit = AggregationUnit.PATIENT
    evidence_quote: Optional[str] = None  # ← NEW: exact quote when required
```

---

### Gap 5: Cohort vs Study Relationship

**User proposes:** Cohort-level rows with `study_id` linkage

**Question:** Do we need a separate `Study` model?

**Scenario:**
```
Study "Smith_2020" has:
- Metadata: title, authors, DOI, journal, year
- Cohort A: "Stage I patients" (n=10)
- Cohort B: "Stage II patients" (n=15)
```

**Option 1: Denormalized (duplicate study metadata in each cohort row)**
```python
class DPMCohort(BaseModel):
    study_id: str
    cohort_id: str
    
    # Duplicated across cohorts
    title: str
    authors: str
    doi: str
    year: int
    
    # Cohort-specific
    cohort_label: str
    cohort_n: int
    ct_ground_glass: FindingReport
```

**Pros:** Simple CSV export, one table  
**Cons:** Duplication, metadata updates need multi-row changes

**Option 2: Relational (separate Study + Cohort models)**
```python
class Study(BaseModel):
    study_id: str  # Primary key
    title: str
    authors: str
    doi: str
    year: int

class DPMCohort(BaseModel):
    cohort_id: str  # Primary key
    study_id: str   # Foreign key to Study
    cohort_label: str
    cohort_n: int
    ct_ground_glass: FindingReport
```

**Pros:** No duplication, normalized  
**Cons:** Requires joins, more complex CSV export

**Recommendation: Denormalized for v1**

**Why:**
- CSV is primary export format for systematic reviews
- Most papers have 1 cohort (duplication minimal)
- Multi-cohort papers are minority (~10-20%)
- Can refactor to relational in v2 if needed

**Compromise:** Flag duplicated fields in schema
```python
class DPMCohort(BaseModel):
    # === Study-level (duplicated across cohorts from same study) ===
    study_id: str
    title: str  # DUPLICATED_STUDY_LEVEL
    authors: str  # DUPLICATED_STUDY_LEVEL
    
    # === Cohort-level (unique per cohort) ===
    cohort_id: str
    cohort_n: int
    ct_ground_glass: FindingReport
```

---

## Refined Implementation Phases

### Phase 1: Core Types (Week 1)

**Deliverables:**
- `Status`, `AggregationUnit`, `ExtractionPolicy` enums
- `FindingReport`, `MeasurementData` models (Level 2 types only)
- `ColumnSpec` class with `.to_field()` method

**Tests:**
```python
def test_finding_report_tri_state():
    finding = FindingReport(
        status=Status.PRESENT,
        n=3,
        N=5,
        aggregation_unit=AggregationUnit.PATIENT,
    )
    assert finding.status == Status.PRESENT

def test_column_spec_to_field():
    spec = ColumnSpec(key="age", dtype=MeasurementData, ...)
    field = spec.to_field()
    assert isinstance(field, FieldInfo)  # Pydantic Field
```

**Critical decision:** Finalize Level 2 type hierarchy before proceeding

---

### Phase 2: Field Library (Week 2)

**Deliverables:**
- 15 universal specs (title, authors, year, age, sex, patient_count, etc.)
- 3 factories (imaging_finding, ihc_marker, biopsy_method)
- Spec-to-prompt generator (basic version)

**Structure:**
```python
# core/fields/library.py
class FieldLibrary:
    # === Universal specs ===
    TITLE = ColumnSpec(key="title", dtype=str, ...)
    AUTHORS = ColumnSpec(key="authors", dtype=str, ...)
    AGE = ColumnSpec(key="age", dtype=MeasurementData, ...)
    
    # === Factories ===
    @staticmethod
    def imaging_finding(name: str, keywords: list[str]) -> ColumnSpec:
        return ColumnSpec(
            key=f"ct_{name}",
            dtype=FindingReport,
            source_narrative_field="ct_narrative",
            high_confidence_keywords=keywords,
            extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
        )
```

**Coverage:** 15 core + (3 factories × ~15 fields) = ~60 reusable specs

---

### Phase 3: DPM Schema (Week 3)

**Deliverables:**
- `DPMCohort` model using library specs
- Cohort-level validators (denominator consistency)
- Migration script from old `DPMGoldStandardSchema`

**Example:**
```python
class DPMCohort(BaseModel):
    # === Study metadata (duplicated) ===
    study_id: str
    title: Optional[str] = FL.TITLE.to_field()
    authors: Optional[str] = FL.AUTHORS.to_field()
    
    # === Cohort identity ===
    cohort_id: str
    cohort_label: Optional[str] = None
    cohort_n_patients: int = Field(..., ge=1)
    
    # === Demographics ===
    age: Optional[MeasurementData] = FL.AGE.to_field()
    sex_female: Optional[FindingReport] = None  # n females, N total
    
    # === CT findings ===
    ct_ground_glass: Optional[FindingReport] = FL.imaging_finding(
        "ground_glass",
        ["GGO", "ground glass"]
    ).to_field()
    
    # Validators
    @validator('ct_ground_glass', 'ct_solid_nodules', ...)
    def validate_patient_denominators(cls, v, values):
        # Check N doesn't exceed cohort_n_patients
        ...
```

---

### Phase 4: Extraction Pipeline (Week 4)

**Deliverables:**
- Prompt generator from ColumnSpec
- Hierarchical extraction (narratives → findings)
- Evidence quote capture for MUST_BE_EXPLICIT fields

**Extraction flow:**
```python
# 1. Extract narratives
narratives = extract_narratives_batch(pdf, [
    "ct_narrative",
    "immunohistochemistry_narrative",
    "diagnostic_approach",
    "symptom_narrative",
    "outcomes_narrative",
])

# 2. For each domain, extract findings
ct_findings = extract_findings_batch(
    narrative=narratives["ct_narrative"],
    specs=get_specs_for_narrative("ct_narrative"),
)

# 3. Validate and assemble cohort
cohort = DPMCohort(
    study_id="Smith_2020",
    cohort_id="Smith_2020_overall",
    cohort_n_patients=5,
    **ct_findings,
    **ihc_findings,
    ...
)
```

---

## Design Principles (Anti-Over-Engineering Rules)

### Rule 1: Use Level 2 types first
Don't create `AgeData`, `FollowUpData`, `LesionSizeData` if `MeasurementData` works.

### Rule 2: Start with denormalized schema
Don't build relational Study + Cohort models until CSV export proves painful.

### Rule 3: Batch extraction when possible
Don't make 125 LLM calls if 5 narrative extractions + batch derivation works.

### Rule 4: Validators are better than new types
Don't create `PositiveInt` type when `Field(ge=0)` validator suffices.

### Rule 5: Specs are source of truth
Don't duplicate metadata in ColumnSpec + Pydantic Field + prompts.

---

## Remaining Questions for User

### Q1: Aggregation unit defaults

Should `FindingReport.aggregation_unit` default to `PATIENT` or `UNCLEAR`?

- `PATIENT` = assume patient-level unless stated otherwise (optimistic)
- `UNCLEAR` = require explicit statement (conservative)

**Recommendation:** Default to `PATIENT` for symptoms/demographics, `UNCLEAR` for imaging/pathology

### Q2: Evidence quote requirement scope

Should `evidence_quote` be:
- **Option A:** Required for ALL findings when `requires_evidence_quote=True`
- **Option B:** Optional but used for low-confidence extractions
- **Option C:** Only for human-reviewed extractions

**Recommendation:** Option B (optional, used when confidence <0.8)

### Q3: Multi-cohort paper handling

If paper has unclear cohorts (e.g., "some patients had X, others had Y"):
- **Option A:** Create 2 cohorts with partial data
- **Option B:** Create 1 cohort with mixed data, flag for review
- **Option C:** Skip extraction, flag paper

**Recommendation:** Option B for v1 (pragmatic), Option A for v2 (rigorous)

---

## Summary of Improvements Over User's Proposal

| Aspect | User's Proposal | Refinement | Why |
|--------|----------------|------------|-----|
| Type hierarchy | Multiple specialized types | 2 Level-2 types (FindingReport, MeasurementData) | Reduces complexity |
| ColumnSpec integration | Separate from Pydantic | `.to_field()` method | DRY, type-safe |
| Aggregation validation | Implicit | Pydantic validators | Catches data quality issues |
| Extraction flow | Unclear | Hierarchical (narratives → findings) | Reduces LLM calls |
| Study vs Cohort | Relational | Denormalized for v1 | Simpler CSV export |

---

## Final Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Field Library                           │
│                                                             │
│  ├─ Universal Specs (15)                                   │
│  │   - TITLE, AUTHORS, YEAR, AGE, SEX, ...                │
│  │                                                         │
│  ├─ Factories (3)                                          │
│  │   - imaging_finding() → 15 CT specs                    │
│  │   - ihc_marker() → 16 IHC specs                        │
│  │   - biopsy_method() → 12 biopsy specs                  │
│  │                                                         │
│  └─ Generators                                             │
│      - spec.to_field() → Pydantic Field                   │
│      - generate_prompt(spec) → LLM prompt                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    DPMCohort Schema                         │
│                                                             │
│  ├─ Study Metadata (duplicated)                           │
│  │   - study_id, title, authors, year, ...                │
│  │                                                         │
│  ├─ Cohort Identity                                        │
│  │   - cohort_id, cohort_label, cohort_n_patients         │
│  │                                                         │
│  ├─ Demographics                                           │
│  │   - age: MeasurementData                               │
│  │   - sex_female: FindingReport (n/N)                    │
│  │                                                         │
│  ├─ Findings (43 factory-generated)                        │
│  │   - ct_X: FindingReport (status, n, N, unit)           │
│  │   - ihc_X: FindingReport                               │
│  │   - biopsy_X: FindingReport                            │
│  │                                                         │
│  └─ Narratives (for rule derivation)                       │
│      - ct_narrative, ihc_narrative, ...                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                 Extraction Pipeline                         │
│                                                             │
│  Step 1: Extract narratives (5 LLM calls)                  │
│  Step 2: Extract findings per domain (batch)               │
│  Step 3: Validate (denominators, units)                    │
│  Step 4: Assemble DPMCohort model                          │
│  Step 5: Write to CSV (one row per cohort)                │
└─────────────────────────────────────────────────────────────┘
```

---

## This Design is Good Enough Because:

1. ✅ Supports Cochrane-standard meta-analysis (tri-state + n/N)
2. ✅ Tracks aggregation units (avoids invalid pooling)
3. ✅ Normalizes measurements (enables regression)
4. ✅ Encodes extraction policies (enables routing)
5. ✅ Generates prompts from specs (DRY)
6. ✅ Cohort-level granularity (unambiguous denominators)
7. ✅ 60 reusable specs (40% reduction vs full custom)
8. ✅ Simple enough to implement in 4 weeks
9. ✅ Extensible to other study types (cancer, cardiology)

**What it doesn't do (and that's OK):**
- Won't eliminate ALL custom field definitions (65/125 still custom)
- Won't auto-discover perfect aggregation units (requires human review)
- Won't solve multi-cohort ambiguity perfectly (need domain expertise)

**But it solves the 80/20:** Common patterns reused, semantics preserved for meta-analysis.
