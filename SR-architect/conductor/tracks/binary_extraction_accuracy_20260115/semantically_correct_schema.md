# Semantically-Correct Schema Design - Revised Specification

**Date:** 2026-01-15  
**Critical Feedback:** User identified fatal semantic gaps in field library approach

---

## User's Critical Feedback (100% Correct)

### Problem 1: Booleans Can't Represent Frequencies ❌

**My flawed approach:**
```python
ct_ground_glass: Optional[bool]  # True/False/None
```

**What's wrong:**
- `None` conflates "not mentioned" with "explicitly absent"
- No way to capture "3 of 5 patients had GGO"
- Can't do frequency meta-analysis (Cochrane standard)

**User's solution:** Tri-state + n/N counts ✅
```python
class FindingReport(BaseModel):
    status: Status  # PRESENT | ABSENT | NOT_REPORTED | UNCLEAR
    n: Optional[int]  # numerator
    N: Optional[int]  # denominator
    aggregation_unit: AggregationUnit  # PATIENT | LESION | SPECIMEN
```

---

### Problem 2: Missing Denominators, Mixed Aggregation ❌

**My oversight:** Didn't consider that findings can be reported at different levels:
- "3 of 5 **patients** had GGO" 
- "7 of 10 **lesions** showed GGO"
- "Most patients had GGO, few lesions didn't" (MIXED - invalid!)

**Impact:** Silently mixing patient-level and lesion-level proportions **breaks meta-analysis**

**User's solution:** Explicit `aggregation_unit` metadata ✅

---

### Problem 3: Unit Normalization Deferred ❌

**My approach:**
```python
age: Optional[str]  # "median 65 (IQR 45-78)" - requires second pipeline
```

**User's solution:** Capture narrative + normalized split ✅
```python
class AgeData(BaseModel):
    age_text: str               # "median 65 (IQR 45-78)"
    age_min_years: float        # 45.0
    age_max_years: float        # 78.0
    age_point_estimate: float   # 65.0
    age_point_type: str         # "median"
```

---

### Problem 4: Library Doesn't Encode Extraction Policies ❌

**My approach:** Syntactic reuse only (reduce duplication)

**Missing:** Semantic metadata for extraction intelligence:
- Which fields are high hallucination risk?
- Which require explicit evidence vs can be inferred?
- Which need human review?

**User's solution:** Encode extraction policy in specs ✅
```python
class ColumnSpec:
    extraction_policy: ExtractionPolicy  # METADATA | INFERRED | EXPLICIT | DERIVED
    requires_evidence_quote: bool
    high_confidence_keywords: List[str]
```

---

### Problem 5: Row Granularity Ambiguity ❌

**My implicit assumption:** One row per paper

**Problem:** Papers report multiple cohorts!
- "Stage I patients (n=10): ..."
- "Stage II patients (n=15): ..."

Mixing these in one row = incoherent denominators

**User's solution:** Cohort-level rows with `study_id` linkage ✅

---

## Revised Architecture

### Core Data Models

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

# === ENUMS ===

class Status(str, Enum):
    """Tri-state for findings."""
    PRESENT = "present"
    ABSENT = "absent"
    NOT_REPORTED = "not_reported"
    UNCLEAR = "unclear"

class AggregationUnit(str, Enum):
    """Level at which finding is reported."""
    PATIENT = "patient"
    LESION = "lesion"
    SPECIMEN = "specimen"
    BIOPSY = "biopsy"
    IMAGING_SERIES = "imaging_series"
    UNCLEAR = "unclear"

class ExtractionPolicy(str, Enum):
    """How to extract this field."""
    METADATA = "metadata"           # Always extracted (title, authors)
    CAN_BE_INFERRED = "inferred"    # LLM can infer from context
    MUST_BE_EXPLICIT = "explicit"   # Requires explicit statement
    DERIVED = "derived"             # Rule-based from other fields
    HUMAN_REVIEW = "human_review"   # Always flag for review

# === CORE MODELS ===

class FindingReport(BaseModel):
    """Standard format for any binary finding."""
    status: Optional[Status] = None
    n: Optional[int] = Field(None, ge=0, description="Count with finding")
    N: Optional[int] = Field(None, ge=0, description="Total assessed")
    aggregation_unit: Optional[AggregationUnit] = None
    aggregation_note: Optional[str] = Field(
        None,
        description="Clarify if mixed or unclear (e.g., 'some patients, most lesions')"
    )
    evidence_quote: Optional[str] = Field(
        None,
        description="Direct quote supporting this finding"
    )
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class AgeData(BaseModel):
    """Structured age capture with normalization."""
    age_text: Optional[str] = Field(
        None,
        description="Raw text as stated in paper"
    )
    age_min_years: Optional[float] = Field(None, ge=0, le=120)
    age_max_years: Optional[float] = Field(None, ge=0, le=120)
    age_point_estimate: Optional[float] = Field(None, ge=0, le=120)
    age_point_type: Optional[str] = Field(
        None,
        description="mean, median, mode, or single_value"
    )

class FollowUpData(BaseModel):
    """Structured follow-up capture."""
    followup_text: Optional[str] = None
    followup_min_months: Optional[float] = Field(None, ge=0)
    followup_max_months: Optional[float] = Field(None, ge=0)
    followup_median_months: Optional[float] = Field(None, ge=0)
    followup_mean_months: Optional[float] = Field(None, ge=0)

class CountData(BaseModel):
    """Structured count with context."""
    count_text: Optional[str] = None
    count_value: Optional[int] = Field(None, ge=0)
    count_unit: Optional[str] = Field(
        None,
        description="patients, lesions, specimens, etc."
    )

# === COLUMN SPECIFICATION ===

class ColumnSpec(BaseModel):
    """Specification for a schema column."""
    field_name: str
    field_type: str  # "FindingReport", "AgeData", "str", "int", etc.
    description: str
    extraction_policy: ExtractionPolicy
    requires_evidence_quote: bool = False
    high_confidence_keywords: Optional[list[str]] = None
    source_narrative_field: Optional[str] = None
    derivation_template: Optional[str] = None  # For DERIVED fields
```

---

### Field Library (Revised)

```python
class FieldLibrary:
    """Library of reusable column specifications."""
    
    # === UNIVERSAL METADATA ===
    
    @staticmethod
    def title() -> ColumnSpec:
        return ColumnSpec(
            field_name="title",
            field_type="str",
            description="Full article title",
            extraction_policy=ExtractionPolicy.METADATA,
            requires_evidence_quote=False,
        )
    
    @staticmethod
    def authors() -> ColumnSpec:
        return ColumnSpec(
            field_name="authors",
            field_type="str",
            description="Author list",
            extraction_policy=ExtractionPolicy.METADATA,
            requires_evidence_quote=False,
        )
    
    @staticmethod
    def age() -> ColumnSpec:
        return ColumnSpec(
            field_name="age",
            field_type="AgeData",
            description="Patient age with normalization",
            extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
            requires_evidence_quote=True,
            high_confidence_keywords=["age", "years old", "median age", "mean age"],
        )
    
    @staticmethod
    def patient_count() -> ColumnSpec:
        return ColumnSpec(
            field_name="patient_count",
            field_type="CountData",
            description="Number of patients in cohort",
            extraction_policy=ExtractionPolicy.METADATA,
            requires_evidence_quote=True,
            high_confidence_keywords=["patients", "cases", "subjects", "n="],
        )
    
    # === FINDING FACTORIES ===
    
    @staticmethod
    def imaging_finding(
        finding_name: str,
        keywords: list[str],
        source_narrative: str = "ct_narrative"
    ) -> ColumnSpec:
        """Factory for imaging findings with tri-state + n/N."""
        return ColumnSpec(
            field_name=f"ct_{finding_name}",
            field_type="FindingReport",
            description=f"{finding_name.replace('_', ' ').title()} on CT imaging",
            extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
            requires_evidence_quote=True,
            high_confidence_keywords=keywords,
            source_narrative_field=source_narrative,
        )
    
    @staticmethod
    def ihc_marker(
        marker_name: str,
        polarity: str,  # "positive" or "negative"
    ) -> ColumnSpec:
        """Factory for IHC markers."""
        return ColumnSpec(
            field_name=f"ihc_{marker_name.lower()}_{polarity[:3]}",
            field_type="FindingReport",
            description=f"{marker_name} {polarity} on immunohistochemistry",
            extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
            requires_evidence_quote=True,
            high_confidence_keywords=[marker_name, polarity, "+", "-"],
            source_narrative_field="immunohistochemistry_narrative",
        )
    
    @staticmethod
    def biopsy_method(
        method_name: str,
        acronym: str,
        diagnostic: bool = False
    ) -> ColumnSpec:
        """Factory for biopsy methods."""
        suffix = "_diagnostic" if diagnostic else ""
        policy = ExtractionPolicy.MUST_BE_EXPLICIT if diagnostic else ExtractionPolicy.CAN_BE_INFERRED
        
        return ColumnSpec(
            field_name=f"biopsy_{method_name.lower()}{suffix}",
            field_type="FindingReport",
            description=f"{method_name} biopsy {'was diagnostic' if diagnostic else 'performed'}",
            extraction_policy=policy,
            requires_evidence_quote=diagnostic,  # Diagnostic requires quote
            high_confidence_keywords=[acronym, method_name, "biopsy"],
            source_narrative_field="diagnostic_approach",
        )
```

---

### DPM Schema (Cohort-Level)

```python
class DPMCohort(BaseModel):
    """
    Cohort-level extraction for DPM systematic review.
    
    One row per cohort, not per paper.
    Enables stratified analysis and coherent denominators.
    """
    
    # === STUDY LINKAGE ===
    study_id: str = Field(..., description="Unique study identifier (FirstAuthor_Year)")
    cohort_id: str = Field(..., description="Unique cohort identifier (Smith_2020_stageI)")
    cohort_n: int = Field(..., ge=1, description="Number of patients in THIS cohort")
    cohort_label: Optional[str] = Field(None, description="Label for cohort (e.g., 'Stage I patients')")
    
    # === STUDY METADATA (reused from library) ===
    title: Optional[str] = None
    authors: Optional[str] = None
    doi: Optional[str] = None
    year: Optional[int] = None
    
    # === DEMOGRAPHICS (structured with normalization) ===
    age: Optional[AgeData] = None
    sex_distribution: Optional[FindingReport] = Field(
        None,
        description="Sex distribution (n females, N total)"
    )
    non_smoker: Optional[FindingReport] = None
    
    # === CT FINDINGS (tri-state + n/N) ===
    ct_ground_glass: Optional[FindingReport] = None
    ct_solid_nodules: Optional[FindingReport] = None
    ct_central_cavitation: Optional[FindingReport] = None
    ct_cheerio: Optional[FindingReport] = None
    ct_upper_lobe_predominance: Optional[FindingReport] = None
    ct_lower_lobe_predominance: Optional[FindingReport] = None
    ct_subpleural_predominance: Optional[FindingReport] = None
    # ... 8 more CT findings
    
    # === IHC MARKERS (tri-state + n/N) ===
    ihc_ema_pos: Optional[FindingReport] = None
    ihc_ema_neg: Optional[FindingReport] = None
    ihc_pr_pos: Optional[FindingReport] = None
    ihc_pr_neg: Optional[FindingReport] = None
    # ... 14 more IHC markers
    
    # === BIOPSY METHODS (tri-state + n/N) ===
    biopsy_tblb: Optional[FindingReport] = None
    biopsy_tblb_diagnostic: Optional[FindingReport] = None
    biopsy_surgical: Optional[FindingReport] = None
    biopsy_surgical_diagnostic: Optional[FindingReport] = None
    # ... 9 more biopsy fields
    
    # === OUTCOMES (structured) ===
    followup_data: Optional[FollowUpData] = None
    outcome_dpm_stable: Optional[FindingReport] = None
    outcome_dpm_progressed: Optional[FindingReport] = None
    outcome_dpm_died: Optional[FindingReport] = None
    
    # === NARRATIVES (for rule derivation) ===
    ct_narrative: Optional[str] = None
    immunohistochemistry_narrative: Optional[str] = None
    diagnostic_approach: Optional[str] = None
    symptom_narrative: Optional[str] = None
    outcomes_narrative: Optional[str] = None
    
    # === EXTRACTION METADATA ===
    extraction_confidence: Optional[float] = None
    extraction_notes: Optional[str] = None
    extraction_status: Optional[str] = None
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)

**Create core data models:**
- `Status`, `AggregationUnit`, `ExtractionPolicy` enums
- `FindingReport`, `AgeData`, `FollowUpData`, `CountData` models
- `ColumnSpec` specification model

**Tests:**
```python
def test_finding_report_tri_state():
    """Test tri-state status representation."""
    finding = FindingReport(
        status=Status.PRESENT,
        n=3,
        N=5,
        aggregation_unit=AggregationUnit.PATIENT,
    )
    assert finding.status == Status.PRESENT
    assert finding.n == 3
    assert finding.N == 5

def test_age_data_normalization():
    """Test age normalization."""
    age = AgeData(
        age_text="median 65 (IQR 45-78)",
        age_min_years=45.0,
        age_max_years=78.0,
        age_point_estimate=65.0,
        age_point_type="median",
    )
    assert age.age_point_estimate == 65.0
```

---

### Phase 2: Field Library (Week 2)

**Create 15 universal specs:**
- Metadata: title, authors, doi, year
- Demographics: age, sex, patient_count
- Outcomes: followup_data, survival_status

**Create 3 factories:**
- `imaging_finding()` - 15 CT fields
- `ihc_marker()` - 16 IHC fields
- `biopsy_method()` - 12 biopsy fields

**Coverage:**
- 15 universal + 43 factory-generated = 58 fields
- Remaining 67 DPM-specific defined manually

---

### Phase 3: Schema Integration (Week 3)

**Wire library into DPMCohort:**
```python
# Generated from library
age: Optional[AgeData] = FL.age().to_field()
ct_ground_glass: Optional[FindingReport] = FL.imaging_finding(
    "ground_glass",
    keywords=["ground glass", "GGO", "GGN"]
).to_field()
```

**Migration strategy:**
1. Keep old `DPMGoldStandardSchema` for backward compat
2. Create new `DPMCohort` schema
3. Provide migration script
4. Deprecate old schema in v2.0

---

### Phase 4: Extraction Integration (Week 4)

**Generate extraction prompts from specs:**
```python
def generate_prompt_for_field(spec: ColumnSpec, narrative: str) -> str:
    """Generate LLM prompt from column spec."""
    if spec.extraction_policy == ExtractionPolicy.MUST_BE_EXPLICIT:
        return f"""
        Extract {spec.description} from the text.
        
        CRITICAL: Only extract if explicitly stated. Do not infer.
        Provide evidence quote.
        
        Look for keywords: {spec.high_confidence_keywords}
        
        Text: {narrative}
        
        Return FindingReport:
        - status: PRESENT | ABSENT | NOT_REPORTED | UNCLEAR
        - n: number with finding
        - N: total assessed
        - aggregation_unit: PATIENT | LESION | SPECIMEN
        - evidence_quote: exact quote
        """
```

**Route by extraction policy:**
- METADATA → Fast extraction (no validation)
- CAN_BE_INFERRED → Standard LLM call
- MUST_BE_EXPLICIT → LLM + quote requirement
- DERIVED → Rule-based post-processing
- HUMAN_REVIEW → Flag for HITL workflow

---

## Benefits of Revised Architecture

| Aspect | Before (My Approach) | After (User's Correction) |
|--------|---------------------|---------------------------|
| **Frequencies** | `bool` (can't do meta-analysis) | `FindingReport` with n/N (Cochrane standard) |
| **Absent vs Not Reported** | Conflated in `None` | Explicit tri-state |
| **Aggregation** | Implicit, mixed levels | Explicit `aggregation_unit` |
| **Age normalization** | Deferred (`str`) | Immediate (`AgeData`) |
| **Extraction intelligence** | None | `ExtractionPolicy` + routing |
| **Row granularity** | Paper-level (ambiguous) | Cohort-level (coherent) |
| **Library purpose** | Syntactic reuse only | Semantic reuse with policies |

---

## Key Insights from User

1. **Systematic reviews need semantic rigor, not just syntactic organization**
2. **Meta-analysis requires n/N denominators and tri-state status**
3. **Aggregation units matter - can't mix patient-level and lesion-level**
4. **Normalization should happen at extraction, not post-hoc**
5. **Extraction policies enable intelligent routing (auto vs HITL)**
6. **Cohort-level granularity prevents denominator confusion**

---

## Acknowledgment

The user's critique was **absolutely correct**. My initial field library approach solved for:
- ✅ Reducing duplication (syntactic reuse)
- ✅ Organization and discoverability

But **missed critical systematic review requirements:**
- ❌ Frequency meta-analysis (n/N)
- ❌ Tri-state outcomes
- ❌ Aggregation unit tracking
- ❌ Unit normalization
- ❌ Extraction intelligence
- ❌ Cohort-level granularity

The revised specification addresses all gaps while maintaining the library's reusability benefits.

---

## Next Steps

**For user approval:**
1. Confirm revised architecture addresses all 5 problems
2. Prioritize implementation phases
3. Decide: Migrate existing DPM schema or run parallel?
4. Test on 10 papers to validate denominators and tri-state logic
