# Semantically-Correct Schema - Implementation Plan

**Track:** `semantic_schema_20260116`  
**Created:** 2026-01-15  
**Conductor:** @conductor → @orchestrator → @subagent-driven-development  
**Method:** TDD (Red-Green-Refactor for every task)

---

## Mission Status

| Phase | Status | Owner | Deliverables | Tests |
|-------|--------|-------|--------------|-------|
| Phase 1: Core Types | 🔵 READY | Senior Dev | Enums, FindingReport, MeasurementData | 15 |
| Phase 2: ColumnSpec | ⬜ BLOCKED | Senior Dev | ColumnSpec class, .to_field() | 8 |
| Phase 3: Field Library | ⬜ BLOCKED | Senior Dev | Universal specs, 3 factories | 12 |
| Phase 4: DPMCohort Schema | ⬜ BLOCKED | Senior Dev | New schema, validators | 10 |
| Phase 5: Extraction Pipeline | ⬜ BLOCKED | Senior Dev | Prompt generation, routing | 8 |
| Phase 6: Migration | ⬜ BLOCKED | QA Agent | Migration script, tests | 5 |
| **Total** | | | | **58** |

---

## Phase 1: Core Types

**Goal:** Define tri-state enums and structured data models  
**TDD Pattern:** Write test → verify fail → implement → verify pass → commit

### Task 1.1: Status Enum

**Spec:**
```python
class Status(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    NOT_REPORTED = "not_reported"
    UNCLEAR = "unclear"
```

**Test First (RED):**
```python
def test_status_enum_has_four_values():
    """Status enum must have exactly 4 tri-state values."""
    from core.types.enums import Status
    
    assert len(Status) == 4
    assert Status.PRESENT.value == "present"
    assert Status.ABSENT.value == "absent"
    assert Status.NOT_REPORTED.value == "not_reported"
    assert Status.UNCLEAR.value == "unclear"

def test_status_is_string_serializable():
    """Status must serialize to string for CSV export."""
    from core.types.enums import Status
    
    assert str(Status.PRESENT) == "Status.PRESENT"
    assert Status.PRESENT.value == "present"
```

**Acceptance Criteria:**
- [ ] Test fails (import error)
- [ ] Implement `core/types/enums.py`
- [ ] Test passes
- [ ] Commit: "Add Status enum for tri-state findings"

---

### Task 1.2: AggregationUnit Enum

**Spec:**
```python
class AggregationUnit(str, Enum):
    PATIENT = "patient"
    LESION = "lesion"
    SPECIMEN = "specimen"
    BIOPSY = "biopsy"
    IMAGING_SERIES = "imaging_series"
    UNCLEAR = "unclear"
```

**Test First (RED):**
```python
def test_aggregation_unit_has_six_values():
    """AggregationUnit for tracking denominator context."""
    from core.types.enums import AggregationUnit
    
    assert len(AggregationUnit) == 6
    assert AggregationUnit.PATIENT.value == "patient"
    assert AggregationUnit.LESION.value == "lesion"

def test_aggregation_unit_default_is_patient():
    """Default aggregation should be patient-level."""
    from core.types.enums import AggregationUnit
    
    # Test that PATIENT is a valid default
    default = AggregationUnit.PATIENT
    assert default == AggregationUnit.PATIENT
```

**Acceptance Criteria:**
- [ ] Test fails (import error)
- [ ] Add to `core/types/enums.py`
- [ ] Test passes
- [ ] Commit: "Add AggregationUnit enum"

---

### Task 1.3: ExtractionPolicy Enum

**Spec:**
```python
class ExtractionPolicy(str, Enum):
    METADATA = "metadata"
    CAN_BE_INFERRED = "inferred"
    MUST_BE_EXPLICIT = "explicit"
    DERIVED = "derived"
    HUMAN_REVIEW = "human_review"
```

**Test First (RED):**
```python
def test_extraction_policy_has_five_values():
    """ExtractionPolicy for routing extraction to appropriate handler."""
    from core.types.enums import ExtractionPolicy
    
    assert len(ExtractionPolicy) == 5
    assert ExtractionPolicy.METADATA.value == "metadata"
    assert ExtractionPolicy.MUST_BE_EXPLICIT.value == "explicit"
    assert ExtractionPolicy.HUMAN_REVIEW.value == "human_review"
```

**Acceptance Criteria:**
- [ ] Test fails
- [ ] Implement
- [ ] Test passes
- [ ] Commit: "Add ExtractionPolicy enum"

---

### Task 1.4: FindingReport Model

**Spec:**
```python
class FindingReport(BaseModel):
    """Standard format for any binary finding with frequencies."""
    status: Optional[Status] = None
    n: Optional[int] = Field(None, ge=0, description="Count with finding")
    N: Optional[int] = Field(None, ge=0, description="Total assessed")
    aggregation_unit: AggregationUnit = AggregationUnit.PATIENT
    aggregation_note: Optional[str] = None
    evidence_quote: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
```

**Test First (RED):**
```python
def test_finding_report_tri_state():
    """FindingReport captures status, n, and N."""
    from core.types.models import FindingReport
    from core.types.enums import Status, AggregationUnit
    
    finding = FindingReport(
        status=Status.PRESENT,
        n=3,
        N=5,
        aggregation_unit=AggregationUnit.PATIENT,
    )
    
    assert finding.status == Status.PRESENT
    assert finding.n == 3
    assert finding.N == 5
    assert finding.aggregation_unit == AggregationUnit.PATIENT

def test_finding_report_validates_n_cannot_exceed_N():
    """n must not exceed N."""
    from core.types.models import FindingReport
    from core.types.enums import Status
    import pytest
    
    # Valid: n <= N
    f = FindingReport(status=Status.PRESENT, n=3, N=5)
    assert f.n == 3
    
    # Invalid: n > N should raise
    with pytest.raises(ValueError):
        FindingReport(status=Status.PRESENT, n=7, N=5)

def test_finding_report_validates_n_non_negative():
    """n must be >= 0."""
    from core.types.models import FindingReport
    import pytest
    
    with pytest.raises(ValueError):
        FindingReport(n=-1, N=5)

def test_finding_report_evidence_quote_optional():
    """Evidence quote should be optional."""
    from core.types.models import FindingReport
    from core.types.enums import Status
    
    # Without quote
    f1 = FindingReport(status=Status.PRESENT, n=3, N=5)
    assert f1.evidence_quote is None
    
    # With quote
    f2 = FindingReport(
        status=Status.PRESENT,
        n=3,
        N=5,
        evidence_quote="3 of 5 patients had..."
    )
    assert f2.evidence_quote == "3 of 5 patients had..."
```

**Acceptance Criteria:**
- [ ] All 4 tests fail (import error)
- [ ] Implement `core/types/models.py`
- [ ] All 4 tests pass
- [ ] Commit: "Add FindingReport model with validation"

---

### Task 1.5: MeasurementData Model

**Spec:**
```python
class MeasurementData(BaseModel):
    """Generic continuous measurement with normalization."""
    raw_text: Optional[str] = None
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    value_point_estimate: Optional[float] = None
    value_unit: Optional[str] = None  # "years", "months", "mm"
    value_type: Optional[str] = None  # "mean", "median", "range"
```

**Test First (RED):**
```python
def test_measurement_data_age_normalization():
    """MeasurementData captures age with normalization."""
    from core.types.models import MeasurementData
    
    age = MeasurementData(
        raw_text="median 65 (IQR 45-78)",
        value_min=45.0,
        value_max=78.0,
        value_point_estimate=65.0,
        value_unit="years",
        value_type="median",
    )
    
    assert age.raw_text == "median 65 (IQR 45-78)"
    assert age.value_point_estimate == 65.0
    assert age.value_unit == "years"

def test_measurement_data_followup_normalization():
    """MeasurementData captures follow-up duration."""
    from core.types.models import MeasurementData
    
    followup = MeasurementData(
        raw_text="24 months (range 6-60)",
        value_min=6.0,
        value_max=60.0,
        value_point_estimate=24.0,
        value_unit="months",
    )
    
    assert followup.value_unit == "months"
    assert followup.value_min == 6.0
```

**Acceptance Criteria:**
- [ ] Tests fail
- [ ] Implement
- [ ] Tests pass
- [ ] Commit: "Add MeasurementData model"

---

### Task 1.6: CountData Model

**Spec:**
```python
class CountData(BaseModel):
    """Structured count with context."""
    raw_text: Optional[str] = None
    count_value: Optional[int] = Field(None, ge=0)
    count_unit: Optional[str] = None  # "patients", "lesions"
```

**Test First (RED):**
```python
def test_count_data_patient_count():
    """CountData captures patient count."""
    from core.types.models import CountData
    
    count = CountData(
        raw_text="5 patients",
        count_value=5,
        count_unit="patients",
    )
    
    assert count.count_value == 5
    assert count.count_unit == "patients"
```

**Acceptance Criteria:**
- [ ] Test fails
- [ ] Implement
- [ ] Test passes
- [ ] Commit: "Add CountData model"

---

## Phase 2: ColumnSpec System

**Goal:** Create specification class that generates Pydantic fields and prompts  
**Dependencies:** Phase 1 complete

### Task 2.1: ColumnSpec Class

**Spec:**
```python
@dataclass
class ColumnSpec:
    """Machine-readable column specification."""
    key: str
    dtype: type  # FindingReport, MeasurementData, str, int
    description: str
    extraction_policy: ExtractionPolicy
    source_narrative_field: Optional[str] = None
    high_confidence_keywords: Optional[List[str]] = None
    requires_evidence_quote: bool = False
    validation: Optional[Dict[str, Any]] = None
```

**Test First (RED):**
```python
def test_column_spec_basic_creation():
    """ColumnSpec captures field metadata."""
    from core.fields.spec import ColumnSpec
    from core.types.models import FindingReport
    from core.types.enums import ExtractionPolicy
    
    spec = ColumnSpec(
        key="ct_ground_glass",
        dtype=FindingReport,
        description="Ground glass opacity on CT",
        extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
        source_narrative_field="ct_narrative",
        high_confidence_keywords=["GGO", "ground glass"],
        requires_evidence_quote=True,
    )
    
    assert spec.key == "ct_ground_glass"
    assert spec.dtype == FindingReport
    assert spec.extraction_policy == ExtractionPolicy.MUST_BE_EXPLICIT
    assert "GGO" in spec.high_confidence_keywords
```

**Acceptance Criteria:**
- [ ] Test fails
- [ ] Implement `core/fields/spec.py`
- [ ] Test passes
- [ ] Commit: "Add ColumnSpec class"

---

### Task 2.2: ColumnSpec.to_field() Method

**Spec:**
```python
def to_field(self) -> FieldInfo:
    """Convert ColumnSpec to Pydantic Field."""
    return Field(
        default=None,
        description=self.description,
        json_schema_extra={"column_spec": asdict(self)},
    )
```

**Test First (RED):**
```python
def test_column_spec_to_field_returns_pydantic_field():
    """to_field() generates valid Pydantic Field."""
    from core.fields.spec import ColumnSpec
    from core.types.models import FindingReport
    from core.types.enums import ExtractionPolicy
    from pydantic.fields import FieldInfo
    
    spec = ColumnSpec(
        key="ct_ground_glass",
        dtype=FindingReport,
        description="Ground glass opacity",
        extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
    )
    
    field = spec.to_field()
    
    assert isinstance(field, FieldInfo)
    assert field.description == "Ground glass opacity"
    assert field.default is None

def test_column_spec_field_preserves_metadata():
    """to_field() preserves extraction policy in metadata."""
    from core.fields.spec import ColumnSpec
    from core.types.models import FindingReport
    from core.types.enums import ExtractionPolicy
    
    spec = ColumnSpec(
        key="ct_ground_glass",
        dtype=FindingReport,
        description="GGO",
        extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
        high_confidence_keywords=["GGO"],
    )
    
    field = spec.to_field()
    
    # Metadata should be accessible
    assert "column_spec" in field.json_schema_extra
    assert field.json_schema_extra["column_spec"]["key"] == "ct_ground_glass"
```

**Acceptance Criteria:**
- [ ] Tests fail
- [ ] Implement
- [ ] Tests pass
- [ ] Commit: "Add ColumnSpec.to_field() method"

---

### Task 2.3: generate_extraction_prompt()

**Spec:**
```python
def generate_extraction_prompt(spec: ColumnSpec, narrative: str) -> str:
    """Generate LLM extraction prompt from ColumnSpec."""
```

**Test First (RED):**
```python
def test_generate_extraction_prompt_explicit_policy():
    """Prompts for MUST_BE_EXPLICIT require explicit mention."""
    from core.fields.spec import ColumnSpec, generate_extraction_prompt
    from core.types.models import FindingReport
    from core.types.enums import ExtractionPolicy
    
    spec = ColumnSpec(
        key="ct_ground_glass",
        dtype=FindingReport,
        description="Ground glass opacity",
        extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
        high_confidence_keywords=["GGO", "ground glass"],
    )
    
    prompt = generate_extraction_prompt(spec, "CT showed bilateral GGO...")
    
    assert "MUST be explicitly stated" in prompt.lower() or "explicit" in prompt.lower()
    assert "GGO" in prompt
    assert "ground glass" in prompt

def test_generate_extraction_prompt_metadata_policy():
    """Prompts for METADATA are simpler."""
    from core.fields.spec import ColumnSpec, generate_extraction_prompt
    from core.types.enums import ExtractionPolicy
    
    spec = ColumnSpec(
        key="title",
        dtype=str,
        description="Article title",
        extraction_policy=ExtractionPolicy.METADATA,
    )
    
    prompt = generate_extraction_prompt(spec, "Title: Some paper...")
    
    assert "title" in prompt.lower()
    # Should NOT require explicit evidence for metadata
    assert "explicit" not in prompt.lower() or "not require" in prompt.lower()
```

**Acceptance Criteria:**
- [ ] Tests fail
- [ ] Implement
- [ ] Tests pass
- [ ] Commit: "Add generate_extraction_prompt function"

---

## Phase 3: Field Library

**Goal:** Create reusable field specifications and factories  
**Dependencies:** Phase 2 complete

### Task 3.1: Universal Specs (15 fields)

**Spec:**
```python
class FieldLibrary:
    # Study metadata
    TITLE = ColumnSpec(key="title", dtype=str, ...)
    AUTHORS = ColumnSpec(key="authors", dtype=str, ...)
    DOI = ColumnSpec(key="doi", dtype=str, ...)
    YEAR = ColumnSpec(key="year", dtype=int, ...)
    STUDY_TYPE = ColumnSpec(key="study_type", dtype=str, ...)
    
    # Demographics
    AGE = ColumnSpec(key="age", dtype=MeasurementData, ...)
    SEX_FEMALE = ColumnSpec(key="sex_female", dtype=FindingReport, ...)
    PATIENT_COUNT = ColumnSpec(key="patient_count", dtype=CountData, ...)
    
    # Outcomes
    FOLLOWUP = ColumnSpec(key="followup", dtype=MeasurementData, ...)
```

**Test First (RED):**
```python
def test_field_library_has_universal_specs():
    """FieldLibrary provides 15 universal column specs."""
    from core.fields.library import FieldLibrary
    
    # Metadata
    assert FieldLibrary.TITLE.key == "title"
    assert FieldLibrary.AUTHORS.key == "authors"
    assert FieldLibrary.YEAR.key == "year"
    
    # Demographics
    assert FieldLibrary.AGE.key == "age"
    assert FieldLibrary.SEX_FEMALE.key == "sex_female"
    
    # Verify extraction policies
    from core.types.enums import ExtractionPolicy
    assert FieldLibrary.TITLE.extraction_policy == ExtractionPolicy.METADATA
    assert FieldLibrary.AGE.extraction_policy == ExtractionPolicy.MUST_BE_EXPLICIT

def test_field_library_specs_generate_fields():
    """All universal specs generate valid Pydantic fields."""
    from core.fields.library import FieldLibrary
    from pydantic.fields import FieldInfo
    
    specs = [
        FieldLibrary.TITLE,
        FieldLibrary.AUTHORS,
        FieldLibrary.YEAR,
        FieldLibrary.AGE,
    ]
    
    for spec in specs:
        field = spec.to_field()
        assert isinstance(field, FieldInfo)
```

**Acceptance Criteria:**
- [ ] Tests fail
- [ ] Implement `core/fields/library.py`
- [ ] Tests pass
- [ ] Commit: "Add FieldLibrary with 15 universal specs"

---

### Task 3.2: Imaging Finding Factory

**Spec:**
```python
@staticmethod
def imaging_finding(
    name: str,
    keywords: List[str],
    description: Optional[str] = None,
) -> ColumnSpec:
    """Factory for CT/imaging binary findings."""
    return ColumnSpec(
        key=f"ct_{name}",
        dtype=FindingReport,
        description=description or f"{name.replace('_', ' ').title()} on CT",
        extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
        source_narrative_field="ct_narrative",
        high_confidence_keywords=keywords,
        requires_evidence_quote=True,
    )
```

**Test First (RED):**
```python
def test_imaging_finding_factory():
    """imaging_finding() generates CT finding specs."""
    from core.fields.library import FieldLibrary
    from core.types.models import FindingReport
    from core.types.enums import ExtractionPolicy
    
    spec = FieldLibrary.imaging_finding(
        name="ground_glass",
        keywords=["GGO", "ground glass opacity"],
    )
    
    assert spec.key == "ct_ground_glass"
    assert spec.dtype == FindingReport
    assert spec.extraction_policy == ExtractionPolicy.MUST_BE_EXPLICIT
    assert spec.source_narrative_field == "ct_narrative"
    assert "GGO" in spec.high_confidence_keywords
    assert spec.requires_evidence_quote == True

def test_imaging_finding_factory_generates_15_dpm_fields():
    """Factory can generate all 15 DPM CT finding specs."""
    from core.fields.library import FieldLibrary
    
    ct_findings = [
        ("ground_glass", ["GGO", "ground glass"]),
        ("solid_nodules", ["solid nodule", "solid lesion"]),
        ("central_cavitation", ["cavitation", "cavitary"]),
        ("cystic_micronodules", ["cystic", "micronodule"]),
        ("random", ["random distribution"]),
        ("cheerio", ["cheerio sign", "ring-shaped"]),
        ("upper_lobe_predominance", ["upper lobe"]),
        ("lower_lobe_predominance", ["lower lobe"]),
        ("central_perihilar", ["central", "perihilar"]),
        ("subpleural", ["subpleural"]),
        ("emphysema", ["emphysema"]),
        ("fibrosis", ["fibrosis", "fibrotic"]),
        ("thickened_septum", ["septal", "thickened"]),
    ]
    
    for name, keywords in ct_findings:
        spec = FieldLibrary.imaging_finding(name, keywords)
        assert spec.key.startswith("ct_")
        assert len(spec.high_confidence_keywords) > 0
```

**Acceptance Criteria:**
- [ ] Tests fail
- [ ] Implement
- [ ] Tests pass
- [ ] Commit: "Add imaging_finding factory"

---

### Task 3.3: IHC Marker Factory

**Spec:**
```python
@staticmethod
def ihc_marker(
    marker_name: str,
    polarity: Literal["positive", "negative"],
) -> ColumnSpec:
    """Factory for IHC marker findings."""
```

**Test First (RED):**
```python
def test_ihc_marker_factory():
    """ihc_marker() generates IHC staining specs."""
    from core.fields.library import FieldLibrary
    from core.types.models import FindingReport
    
    spec_pos = FieldLibrary.ihc_marker("EMA", "positive")
    spec_neg = FieldLibrary.ihc_marker("EMA", "negative")
    
    assert spec_pos.key == "ihc_ema_pos"
    assert spec_neg.key == "ihc_ema_neg"
    assert spec_pos.dtype == FindingReport
    assert "EMA" in spec_pos.high_confidence_keywords
    assert "positive" in spec_pos.description.lower()
    assert "negative" in spec_neg.description.lower()

def test_ihc_marker_factory_generates_16_dpm_fields():
    """Factory generates all 16 DPM IHC marker specs."""
    from core.fields.library import FieldLibrary
    
    markers = ["EMA", "PR", "Vimentin", "TTF1", "Cytokeratin", "S100", "SMA", "Ki67"]
    
    specs = []
    for marker in markers:
        specs.append(FieldLibrary.ihc_marker(marker, "positive"))
        specs.append(FieldLibrary.ihc_marker(marker, "negative"))
    
    assert len(specs) == 16
    
    # Verify unique keys
    keys = [s.key for s in specs]
    assert len(keys) == len(set(keys))  # No duplicates
```

**Acceptance Criteria:**
- [ ] Tests fail
- [ ] Implement
- [ ] Tests pass
- [ ] Commit: "Add ihc_marker factory"

---

### Task 3.4: Biopsy Method Factory

**Spec:**
```python
@staticmethod
def biopsy_method(
    method_name: str,
    acronym: str,
    diagnostic: bool = False,
) -> ColumnSpec:
    """Factory for biopsy method findings."""
```

**Test First (RED):**
```python
def test_biopsy_method_factory():
    """biopsy_method() generates biopsy procedure specs."""
    from core.fields.library import FieldLibrary
    from core.types.models import FindingReport
    
    spec_done = FieldLibrary.biopsy_method("TBLB", "TBLB", diagnostic=False)
    spec_diag = FieldLibrary.biopsy_method("TBLB", "TBLB", diagnostic=True)
    
    assert spec_done.key == "biopsy_tblb"
    assert spec_diag.key == "biopsy_tblb_diagnostic"
    assert spec_done.dtype == FindingReport
    assert "TBLB" in spec_done.high_confidence_keywords
    
    # Diagnostic fields should require evidence
    assert spec_diag.requires_evidence_quote == True

def test_biopsy_method_factory_generates_12_dpm_fields():
    """Factory generates all 12 DPM biopsy specs."""
    from core.fields.library import FieldLibrary
    
    methods = [
        ("TBLB", "TBLB"),
        ("Endobronchial", "EBB"),
        ("TTNB", "TTNB"),
        ("Surgical", "VATS"),
        ("Cryobiopsy", "cryo"),
        ("Autopsy", "autopsy"),
    ]
    
    specs = []
    for name, acronym in methods:
        specs.append(FieldLibrary.biopsy_method(name, acronym, diagnostic=False))
        specs.append(FieldLibrary.biopsy_method(name, acronym, diagnostic=True))
    
    assert len(specs) == 12
```

**Acceptance Criteria:**
- [ ] Tests fail
- [ ] Implement
- [ ] Tests pass
- [ ] Commit: "Add biopsy_method factory"

---

## Phase 4: DPMCohort Schema

**Goal:** Create new cohort-level schema using Field Library  
**Dependencies:** Phase 3 complete

### Task 4.1: DPMCohort Base Model

**Spec:**
```python
class DPMCohort(BaseModel):
    """Cohort-level extraction for DPM systematic review."""
    
    # Study linkage
    study_id: str
    cohort_id: str
    cohort_label: Optional[str] = None
    cohort_n_patients: int = Field(..., ge=1)
    
    # Metadata (from library)
    title: Optional[str] = FL.TITLE.to_field()
    authors: Optional[str] = FL.AUTHORS.to_field()
    year: Optional[int] = FL.YEAR.to_field()
```

**Test First (RED):**
```python
def test_dpm_cohort_has_required_identifiers():
    """DPMCohort requires study_id, cohort_id, cohort_n_patients."""
    from schemas.dpm_cohort import DPMCohort
    import pytest
    
    # Valid creation
    cohort = DPMCohort(
        study_id="Smith_2020",
        cohort_id="Smith_2020_overall",
        cohort_n_patients=5,
    )
    assert cohort.study_id == "Smith_2020"
    
    # Missing required fields
    with pytest.raises(ValueError):
        DPMCohort(study_id="Smith_2020")  # Missing cohort_id and cohort_n

def test_dpm_cohort_uses_library_fields():
    """DPMCohort uses FieldLibrary specs for metadata."""
    from schemas.dpm_cohort import DPMCohort
    
    cohort = DPMCohort(
        study_id="Smith_2020",
        cohort_id="Smith_2020_overall",
        cohort_n_patients=5,
        title="A study of DPM",
        year=2020,
    )
    
    assert cohort.title == "A study of DPM"
    assert cohort.year == 2020
```

**Acceptance Criteria:**
- [ ] Tests fail
- [ ] Implement `schemas/dpm_cohort.py`
- [ ] Tests pass
- [ ] Commit: "Add DPMCohort base model"

---

### Task 4.2: DPMCohort CT Findings

**Spec:**
```python
# CT findings (factory-generated)
ct_ground_glass: Optional[FindingReport] = FL.imaging_finding("ground_glass", [...]).to_field()
ct_solid_nodules: Optional[FindingReport] = FL.imaging_finding("solid_nodules", [...]).to_field()
# ... 13 more
```

**Test First (RED):**
```python
def test_dpm_cohort_has_ct_findings():
    """DPMCohort has all 15 CT finding fields."""
    from schemas.dpm_cohort import DPMCohort
    from core.types.models import FindingReport
    from core.types.enums import Status, AggregationUnit
    
    cohort = DPMCohort(
        study_id="Smith_2020",
        cohort_id="Smith_2020_overall",
        cohort_n_patients=5,
        ct_ground_glass=FindingReport(
            status=Status.PRESENT,
            n=3,
            N=5,
            aggregation_unit=AggregationUnit.PATIENT,
        ),
    )
    
    assert cohort.ct_ground_glass.status == Status.PRESENT
    assert cohort.ct_ground_glass.n == 3

def test_dpm_cohort_ct_fields_are_optional():
    """CT findings should be optional."""
    from schemas.dpm_cohort import DPMCohort
    
    cohort = DPMCohort(
        study_id="Smith_2020",
        cohort_id="Smith_2020_overall",
        cohort_n_patients=5,
    )
    
    assert cohort.ct_ground_glass is None
    assert cohort.ct_solid_nodules is None
```

**Acceptance Criteria:**
- [ ] Tests fail
- [ ] Add CT findings to DPMCohort
- [ ] Tests pass
- [ ] Commit: "Add CT findings to DPMCohort"

---

### Task 4.3: DPMCohort Validators

**Spec:**
```python
@field_validator('ct_ground_glass', 'ct_solid_nodules', ...)
def validate_patient_denominator(cls, v, info):
    """N should not exceed cohort_n_patients for patient-level."""
    if v is None:
        return v
    if v.aggregation_unit == AggregationUnit.PATIENT:
        if v.N and v.N > info.data.get('cohort_n_patients', float('inf')):
            raise ValueError(f"Denominator {v.N} exceeds cohort size")
    return v
```

**Test First (RED):**
```python
def test_dpm_cohort_validates_denominator():
    """Denominator N cannot exceed cohort_n_patients."""
    from schemas.dpm_cohort import DPMCohort
    from core.types.models import FindingReport
    from core.types.enums import Status, AggregationUnit
    import pytest
    
    # Valid: N <= cohort_n_patients
    cohort = DPMCohort(
        study_id="Smith_2020",
        cohort_id="Smith_2020_overall",
        cohort_n_patients=5,
        ct_ground_glass=FindingReport(
            status=Status.PRESENT,
            n=3,
            N=5,  # N == cohort_n_patients: OK
            aggregation_unit=AggregationUnit.PATIENT,
        ),
    )
    assert cohort.ct_ground_glass.N == 5
    
    # Invalid: N > cohort_n_patients
    with pytest.raises(ValueError, match="exceeds cohort"):
        DPMCohort(
            study_id="Smith_2020",
            cohort_id="Smith_2020_overall",
            cohort_n_patients=5,
            ct_ground_glass=FindingReport(
                status=Status.PRESENT,
                n=7,
                N=10,  # N > cohort_n_patients: INVALID
                aggregation_unit=AggregationUnit.PATIENT,
            ),
        )

def test_dpm_cohort_allows_lesion_level_different_N():
    """Lesion-level findings can have N != cohort_n_patients."""
    from schemas.dpm_cohort import DPMCohort
    from core.types.models import FindingReport
    from core.types.enums import Status, AggregationUnit
    
    # Valid: lesion-level, N = 10 but cohort_n = 5
    cohort = DPMCohort(
        study_id="Smith_2020",
        cohort_id="Smith_2020_overall",
        cohort_n_patients=5,
        ct_ground_glass=FindingReport(
            status=Status.PRESENT,
            n=7,
            N=10,  # 10 lesions in 5 patients: OK
            aggregation_unit=AggregationUnit.LESION,
        ),
    )
    assert cohort.ct_ground_glass.N == 10
```

**Acceptance Criteria:**
- [ ] Tests fail
- [ ] Add validators
- [ ] Tests pass
- [ ] Commit: "Add DPMCohort denominator validators"

---

## Phase 5: Extraction Pipeline Integration

**Goal:** Wire extraction prompts and routing to DPMCohort schema  
**Dependencies:** Phase 4 complete

### Task 5.1: Hierarchical Narrative Extraction

**Spec:**
```python
async def extract_narratives(pdf_path: str) -> Dict[str, str]:
    """Extract narrative fields from PDF."""
    narrative_fields = [
        "ct_narrative",
        "immunohistochemistry_narrative",
        "symptom_narrative",
        "diagnostic_approach",
        "outcomes_narrative",
    ]
    # Single LLM call to extract all narratives
    ...
```

**Test First (RED):**
```python
def test_extract_narratives_returns_dict():
    """extract_narratives returns dict of narrative fields."""
    from core.extraction.narratives import extract_narratives
    
    # Use test PDF or mock
    narratives = extract_narratives("tests/fixtures/sample.pdf")
    
    assert "ct_narrative" in narratives
    assert "symptom_narrative" in narratives
    assert isinstance(narratives["ct_narrative"], str)
```

---

### Task 5.2: Findings Extraction per Domain

**Spec:**
```python
async def extract_findings_batch(
    narrative: str,
    specs: List[ColumnSpec],
) -> Dict[str, FindingReport]:
    """Extract multiple findings from single narrative."""
```

---

### Task 5.3: Extraction Policy Router

**Spec:**
```python
def route_by_policy(spec: ColumnSpec) -> ExtractionHandler:
    """Route to appropriate handler based on extraction policy."""
    if spec.extraction_policy == ExtractionPolicy.METADATA:
        return metadata_handler
    elif spec.extraction_policy == ExtractionPolicy.MUST_BE_EXPLICIT:
        return explicit_handler
    elif spec.extraction_policy == ExtractionPolicy.DERIVED:
        return derivation_handler
    elif spec.extraction_policy == ExtractionPolicy.HUMAN_REVIEW:
        return human_review_handler
```

---

## Phase 6: Migration

**Goal:** Migrate existing DPMGoldStandardSchema to new DPMCohort  
**Dependencies:** Phase 5 complete

### Task 6.1: Migration Script

**Spec:**
```python
def migrate_old_schema(old_data: DPMGoldStandardSchema) -> DPMCohort:
    """Convert old boolean schema to new FindingReport schema."""
```

### Task 6.2: Validation Tests

**Spec:**
Test migration on all existing gold standard papers.

---

## Subagent Dispatch Order

**Using `/subagent-driven-development` workflow:**

```
For each task:
1. Dispatch implementer subagent with task spec
2. Implementer writes failing test (RED)
3. Implementer verifies test fails
4. Implementer writes minimal code (GREEN)
5. Implementer verifies test passes
6. Implementer commits
7. Dispatch spec reviewer subagent
8. If issues: implementer fixes, repeat step 7
9. Dispatch code quality reviewer subagent
10. If issues: implementer fixes, repeat step 9
11. Mark task complete
```

**Estimated effort:**
- Phase 1: 6 tasks × 30 min = 3 hours
- Phase 2: 3 tasks × 45 min = 2.25 hours
- Phase 3: 4 tasks × 45 min = 3 hours
- Phase 4: 3 tasks × 60 min = 3 hours
- Phase 5: 3 tasks × 60 min = 3 hours
- Phase 6: 2 tasks × 45 min = 1.5 hours
- **Total: ~16 hours**

---

## Success Criteria

**Phase 1 Complete When:**
- [ ] All 6 tasks have passing tests
- [ ] 15 tests total pass
- [ ] Commit history shows TDD (test before code)

**Phase 2 Complete When:**
- [ ] ColumnSpec generates valid Pydantic fields
- [ ] generate_extraction_prompt produces policy-aware prompts
- [ ] 8 tests pass

**Phase 3 Complete When:**
- [ ] FieldLibrary has 15 universal specs
- [ ] 3 factories generate 43 DPM-specific specs
- [ ] 12 tests pass

**Phase 4 Complete When:**
- [ ] DPMCohort schema validates cohort-level constraints
- [ ] Old tests still pass (backward compat)
- [ ] 10 tests pass

**Phase 5 Complete When:**
- [ ] Extraction pipeline routes by policy
- [ ] Prompt generation works end-to-end
- [ ] 8 tests pass

**Phase 6 Complete When:**
- [ ] Migration script converts old → new schema
- [ ] Gold standard validation passes
- [ ] 5 tests pass

**All Phases Complete When:**
- [ ] 58 total tests pass
- [ ] No regressions in existing tests
- [ ] DPMCohort produces valid meta-analysis data
