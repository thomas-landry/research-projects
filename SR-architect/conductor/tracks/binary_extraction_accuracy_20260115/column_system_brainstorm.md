# Generalizable Column System for Systematic Reviews - Brainstorm

**Date:** 2026-01-15  
**Challenge:** How to support DPM's 125 specific columns while creating a system generalizable to ANY systematic review

---

## Part 1: Initial Brainstorm (3 Approaches)

### Approach 1: Domain-Driven Column Taxonomy

**Concept:** Define universal "domains" that exist in ALL systematic reviews

```python
# Universal domains for ANY medical systematic review
DOMAINS = {
    "study_metadata": ["title", "authors", "doi", "year", "study_type"],
    "demographics": ["age", "sex", "patient_count"],
    "diagnostics": ["imaging", "biopsy", "lab_tests"],
    "interventions": ["treatment", "management"],
    "outcomes": ["followup", "survival", "progression"],
}

# DPM-specific implementation
DPM_DOMAINS = {
    "study_metadata": [...same as universal...],
    "demographics": [...universal + "smoking_status"...],
    "diagnostics": {
        "imaging": {
            "ct_findings": ["ct_ground_glass", "ct_solid_nodules", ...],
            "distribution": ["ct_upper_lobe", "ct_subpleural", ...],
        },
        "biopsy": ["biopsy_tblb", "biopsy_surgical", ...],
        "ihc": ["ihc_ema_pos", "ihc_pr_pos", ...],
    },
    "outcomes": [...],
}
```

**How it generalizes:**
- Cancer SR: Similar domains, different specific fields
- Cardiology SR: Same domains, cardiac-specific fields

**Pros:**
- Hierarchical organization
- Clear mental model
- Easy to navigate for users

**Cons:**
- Domain boundaries arbitrary (is "exposure" demographics or diagnostics?)
- Doesn't solve field naming/types
- Still 125 DPM-specific fields to define

---

### Approach 2: Field Type System with Composable Traits

**Concept:** Every field is a combination of "traits"

```python
# Field types
class FieldType(Enum):
    BOOLEAN = "boolean"
    DISCRETE_NUMERIC = "discrete_numeric"  
    CONTINUOUS_NUMERIC = "continuous_numeric"
    CATEGORICAL = "categorical"
    FREE_TEXT = "free_text"

# Field traits
class FieldTrait(Enum):
    NARRATIVE = "narrative"  # LLM extracts
    DERIVED = "derived"       # Rule-based derivation
    METADATA = "metadata"     # Always extracted
    CRITICAL = "critical"     # Required for analysis

# DPM field definitions
DPM_FIELDS = [
    Field(
        name="ct_ground_glass",
        type=FieldType.BOOLEAN,
        traits=[FieldTrait.DERIVED],
        source_narrative="ct_narrative",
        description="Ground glass nodules present",
    ),
    Field(
        name="age",
        type=FieldType.DISCRETE_NUMERIC,
        traits=[FieldTrait.NARRATIVE, FieldTrait.CRITICAL],
        description="Patient age",
    ),
]
```

**How it generalizes:**
- Cancer SR: Define Cancer-specific fields with same trait system
- System knows how to handle each field type/trait combo

**Pros:**
- Type-safe
- Clear extraction strategy per trait
- Composable (narrative + derived = hybrid extraction)

**Cons:**
- Still need to define all 125 DPM fields
- Verbose configuration
- Complex abstraction for simple concept

---

### Approach 3: Schema Templates with Slot Filling

**Concept:** Define schema "templates" with "slots" that studies fill in

```python
# Template for ANY medical systematic review
MEDICAL_SR_TEMPLATE = {
    "study_metadata": {...standard fields...},
    "patient_characteristics": {
        "<AGE_FIELD>": NumericField(),
        "<SEX_FIELD>": CategoricalField(["male", "female"]),
        "<CUSTOM_DEMOGRAPHICS>": [...],  # Study-specific
    },
    "diagnostics": {
        "<PRIMARY_IMAGING>": {...},
        "<TISSUE_DIAGNOSIS>": {...},
        "<CUSTOM_DIAGNOSTICS>": [...],
    },
}

# DPM fills slots
DPM_SCHEMA = MEDICAL_SR_TEMPLATE.fill(
    AGE_FIELD="age",
    SEX_FIELD="patient_sex",
    CUSTOM_DEMOGRAPHICS=["smoking_status", "exposures"],
    PRIMARY_IMAGING={
        "modality": "CT",
        "findings": ["ct_ground_glass", "ct_solid_nodules", ...],  # 15 CT-specific
    },
    TISSUE_DIAGNOSIS={
        "methods": ["biopsy_tblb", "biopsy_surgical", ...],  # 13 biopsy-specific
        "markers": ["ihc_ema_pos", "ihc_pr_pos", ...],  # 18 IHC-specific
    },
)
```

**How it generalizes:**
- Template enforces structure
- Studies customize slots
- Core fields reused, custom fields added

**Pros:**
- Clear base template
- Flexibility for study-specific fields
- Guides users on what to include

**Cons:**
- Template might not fit all study types
- Slot filling still manual for 125 fields
- Rigid structure

---

## Part 2: HARSH CRITIQUE 🔥

### Critique of Approach 1 (Domain-Driven)

**FATAL FLAW #1: Arbitrary Domain Boundaries**
> "Exposure" - is it demographics? Associated conditions? Environment? The taxonomy is MEANINGLESS because medical concepts don't fit neat boxes. You'll spend weeks arguing whether "smoking" is a demographic or an exposure.

**FATAL FLAW #2: Solves Nothing**
> Cool, you organized 125 fields into groups. You STILL have to manually define all 125 fields! The hierarchy is just lipstick on a pig. This is busy work masquerading as design.

**FATAL FLAW #3: User Confusion**
> Which domain does "chest pain" belong to? Symptoms? Physical exam? Clinical features? Your "clear mental model" is actually 5 different mental models and users will hate you.

**FATAL FLAW #4: Doesn't Generalize**
> Cardiology SR: Where do you put "ejection fraction"? Diagnostics? Outcomes? The domains are MEDICAL-FIELD-SPECIFIC, not universal. Useless for oncology, nephrology, etc.

**VERDICT:** ❌ Wasted effort. Provides organization theater without solving the core problem.

---

### Critique of Approach 2 (Field Type System)

**FATAL FLAW #1: Over-Engineering**
> You created an entire type system just to say "this is a boolean." PYDANTIC ALREADY HAS TYPES! You're reinventing the wheel and making it square.

**FATAL FLAW #2: Trait Explosion**
> Oh great, now I need to understand 4 different traits and how they compose. Is NARRATIVE + DERIVED + CRITICAL different from NARRATIVE + CRITICAL + META? This is enterprise Java nightmare fuel.

**FATAL FLAW #3: Still Manual Definition**
> You STILL have to write 125 `Field()` definitions! All you did was make them MORE verbose with your fancy trait system. Congratulations, you made the problem worse.

**FATAL FLAW #4: Abstraction for Abstraction's Sake**
> "Composable traits" - WHO ASKED FOR THIS? The real problem is: "How do I avoid redefining 'age' for every systematic review?" Your answer: "Add more abstraction layers!" WRONG.

**FATAL FLAW #5: Maintenance Nightmare**
> Every new study needs to understand your bespoke type system. Good luck onboarding new users: "First, learn our custom field type enum, then learn field traits, then learn how they compose..." They'll quit.

**VERDICT:** ❌ Over-engineered garbage. Adds complexity without solving the fundamental problem.

---

### Critique of Approach 3 (Schema Templates)

**FATAL FLAW #1: Template Rigidity**
> Your "universal medical template" assumes every study has PRIMARY_IMAGING and TISSUE_DIAGNOSIS. What about:
> - Epidemiology studies (no imaging)
> - Registry studies (no biopsy)
> - Meta-analyses (no original data)
> 
> Your template is PULMONARY-CENTRIC pretending to be universal. Fraud.

**FATAL FLAW #2: Slot Filling is Manual Hell**
> ```python
> DPM_SCHEMA = MEDICAL_SR_TEMPLATE.fill(
>     PRIMARY_IMAGING={
>         "findings": ["ct_ground_glass", "ct_solid_nodules", ...]  # ← YOU STILL TYPE ALL 15 MANUALLY
>     }
> )
> ```
> You didn't solve anything! Still manually defining 125 fields, just with extra ceremony.

**FATAL FLAW #3: Template Versioning Nightmare**
> User starts DPM study with v1 template. Template v2 comes out with better slots. Now what? Migrate? Maintain both? Templates CREATE the versioning problem they claim to solve.

**FATAL FLAW #4: False Generalization**
> Template works for DPM (pulmonary). Breaks for cardiology. Breaks for oncology. Breaks for neurology. You'll need templates for templates. It's tur​tles all the way down.

**FATAL FLAW #5: XML Hell Reborn**
> This is literally XSLT/XML schema patterns from the 2000s. We learned they DON'T WORK for complex domains. Why are you repeating 20-year-old mistakes?

**VERDICT:** ❌ False promises. Template rigidity kills flexibility, slot filling doesn't reduce work.

---

## Part 3: Core Problem Analysis

**Why all 3 approaches FAIL:**

1. **They assume fields are the problem** - No! Fields are FINE. The problem is DUPLICATION across studies.

2. **They don't address the REAL generalization need:**
   - NOT: "How to organize 125 fields?"
   - YES: "How to REUSE field definitions across studies?"

3. **They conflate TWO different problems:**
   - Problem A: How to structure ONE schema (DPM)
   - Problem B: How to SHARE field definitions across schemas
   
   All 3 approaches try to solve BOTH with one mechanism. That's why they fail.

---

## Part 4: REVISED BRAINSTORM (After Harsh Reality Check)

### The Actual Problem

**For DPM:**
- Need 125 specific columns
- Need them organized/documented
- Need extraction rules for each

**For Future Studies:**
- Need to REUSE definitions for common fields (age, sex, outcomes)
- Need to ADD study-specific fields (DPM's IHC markers)
- Need to AVOID redefining universal concepts

**Key Insight:** We need a LIBRARY, not a FRAMEWORK.

---

### Solution: Field Definition Library + Study-Specific Assembly

**Concept:** Central library of reusable field definitions, studies assemble what they need

```python
# core/fields/library.py - REUSABLE FIELD DEFINITIONS
from pydantic import Field

class FieldLibrary:
    """Library of common systematic review fields."""
    
    # === UNIVERSAL FIELDS (every study uses these) ===
    
    @staticmethod
    def title() -> Field:
        return Field(default=None, description="Article title")
    
    @staticmethod
    def authors() -> Field:
        return Field(default=None, description="Author list")
    
    @staticmethod
    def age(description="Patient age") -> Field:
        return Field(
            default=None,
            description=description,
            # Could be "65" or "60-70" range
        )
    
    @staticmethod
    def patient_count() -> Field:
        return Field(default=None, ge=0, description="Number of patients")
    
    # === DOMAIN-SPECIFIC FIELDS ===
    
    @staticmethod
    def imaging_finding(finding_name: str, pattern: str) -> Field:
        """Factory for imaging binary fields."""
        return Field(
            default=None,
            description=f"{finding_name} present on imaging (pattern: {pattern})"
        )
    
    @staticmethod
    def ihc_marker(marker_name: str, positive: bool) -> Field:
        """Factory for IHC markers."""
        polarity = "positive" if positive else "negative"
        return Field(
            default=None,
            description=f"{marker_name} {polarity} on immunohistochemistry"
        )
    
    @staticmethod
    def biopsy_method(method_name: str, diagnostic: bool = False) -> Field:
        """Factory for biopsy fields."""
        suffix = " was diagnostic" if diagnostic else " performed"
        return Field(
            default=None,
            description=f"{method_name}{suffix}"
        )
```

**DPM Schema Assembly:**

```python
# schemas/dpm_gold_standard.py
from core.fields.library import FieldLibrary as FL
from pydantic import BaseModel
from typing import Optional

class DPMGoldStandardSchema(BaseModel):
    """DPM-specific schema assembled from library."""
    
    # === UNIVERSAL FIELDS (reused from library) ===
    title: Optional[str] = FL.title()
    authors: Optional[str] = FL.authors()
    age: Optional[str] = FL.age()
    number_of_cases: Optional[int] = FL.patient_count()
    
    # === CT FINDINGS (generated from factory) ===
    ct_ground_glass: Optional[bool] = FL.imaging_finding("Ground glass nodules", "GGO/GGN")
    ct_solid_nodules: Optional[bool] = FL.imaging_finding("Solid nodules", "solid lesions")
    ct_cheerio: Optional[bool] = FL.imaging_finding("Cheerio sign", "ring-shaped/ring-like")
    # ... 12 more CT fields
    
    # === IHC MARKERS (generated from factory) ===
    ihc_ema_pos: Optional[bool] = FL.ihc_marker("EMA", positive=True)
    ihc_ema_neg: Optional[bool] = FL.ihc_marker("EMA", positive=False)
    ihc_pr_pos: Optional[bool] = FL.ihc_marker("PR", positive=True)
    ihc_pr_neg: Optional[bool] = FL.ihc_marker("PR", positive=False)
    # ... 14 more IHC fields
    
    # === BIOPSY METHODS (generated from factory) ===
    biopsy_tblb: Optional[bool] = FL.biopsy_method("TBLB")
    biopsy_tblb_diagnostic: Optional[bool] = FL.biopsy_method("TBLB", diagnostic=True)
    biopsy_surgical: Optional[bool] = FL.biopsy_method("Surgical biopsy (VATS/open)")
    # ... 11 more biopsy fields
    
    # === DPM-SPECIFIC FIELDS (not in library) ===
    symptom_asymptomatic: Optional[bool] = Field(
        default=None,
        description="Asymptomatic/incidental presentation"
    )
    ct_narrative: Optional[str] = Field(
        default=None,
        description="Full narrative of CT findings"
    )
```

**Cancer Schema (Reuses Library):**

```python
# schemas/cancer_study.py
from core.fields.library import FieldLibrary as FL

class CancerStudySchema(BaseModel):
    # === REUSE UNIVERSAL ===
    title: Optional[str] = FL.title()
    authors: Optional[str] = FL.authors()
    age: Optional[str] = FL.age(description="Patient age at diagnosis")  # Customize description
    patient_count: Optional[int] = FL.patient_count()
    
    # === REUSE IHC FACTORIES (different markers) ===
    ihc_her2_pos: Optional[bool] = FL.ihc_marker("HER2", positive=True)
    ihc_er_pos: Optional[bool] = FL.ihc_marker("ER", positive=True)
    ihc_pr_pos: Optional[bool] = FL.ihc_marker("PR", positive=True)  # ← Same marker name, different study!
    
    # === CANCER-SPECIFIC (not in DPM) ===
    tnm_staging: Optional[str] = Field(...)
    chemo_regimen: Optional[str] = Field(...)
```

---

## Advantages of Library Approach

### 1. **True Reusability**
- `FL.title()` defined ONCE, used in 100 studies
- `FL.ihc_marker()` generates ANY IHC field
- Zero duplication for common concepts

### 2. **Study-Specific Flexibility**
- DPM: 125 fields (library + custom)
- Cancer: 80 fields (library + different custom)
- Registry: 20 fields (library only)

### 3. **No Framework Lock-In**
- Library = optional convenience
- Can still write fields manually
- Pay for what you use

### 4. **Discoverable**
- IntelliSense shows `FL.` methods
- Self-documenting factories
- Easy to learn

### 5. **Testable**
- Test library once
- Each study tests assembly
- Clear boundaries

### 6. **Maintainable**
- Update `FL.age()` → all studies benefit
- Add `FL.mri_finding()` → available everywhere
- No version hell

---

## Implementation Strategy

### Phase 1: Create Field Library

**Structure:**
```
core/fields/
├── __init__.py
├── library.py          # Main FieldLibrary class
├── universal.py        # Universal fields (title, age, etc.)
├── imaging.py          # Imaging field factories
├── ihc.py              # IHC marker factories
├── biopsy.py           # Biopsy/diagnostic factories
└── outcomes.py         # Outcome field factories
```

**Start small:**
1. Define 10-15 most common fields
2. Add factories for CT, IHC, Biopsy
3. Test with DPM schema

### Phase 2: Refactor DPM Schema

**Gradual migration:**
```python
# Before
age: Optional[str] = Field(default=None, description="Patient age")

# After
age: Optional[str] = FL.age()
```

Migrate 10-20 fields, test, iterate.

### Phase 3: Document + Examples

Create `docs/field-library-guide.md`show:
- How to use library
- How to add custom fields
- Examples from multiple studies

---

## Key Design Principles

1. **Library, not Framework**
   - Users can ignore library entirely
   - Optional convenience, not requirement
   - Pay-for-what-you-use

2. **Factories for Patterns**
   - Common patterns → factories
   - Unique fields → manual definition
   - Best of both worlds

3. **Progressive Enhancement**
   - Start with library for common fields
   - Add study-specific fields normally
   - Mix and match freely

4. **No Magic**
   - Explicit field definitions
   - No auto-discovery
   - What you see is what you get

---

## Answers to Original Challenge

**Q: How to incorporate all DPM columns?**
**A:** Use library for ~40 common/pattern fields, define ~85 manually. Total lines of code: similar to current, but...

**Q: How to generalize for future projects?**
**A:** 
- Cancer study: Reuse ~30 library fields, define ~50 cancer-specific
- Registry: Reuse ~20 library fields, define ~10 registry-specific
- **Key:** Never redefine "age", "title", "patient_count" again

**Q: How to avoid duplication?**
**A:** Library eliminates duplication for:
- Universal metadata (10-15 fields)
- Common patterns (IHC, imaging, biopsy via factories)
- Custom fields still custom (acceptable)

---

## Why This Works

**Addresses real pain:**
- "I hate redefining 'age' for every study" → Library has it
- "IHC markers follow same pattern" → Factory generates them
- "My study is unique" → Add custom fields freely

**Doesn't over-abstract:**
- No complex type systems
- No rigid templates
- No domain taxonomies

**Pragmatic:**
- Small library, big benefit
- Gradual adoption
- Escape hatches everywhere

**Actually generalizes:**
- Works for pulmonary, cardiology, oncology
- Works for case reports, registries, meta-analyses
- Works for 20 fields or 200 fields

---

## Final Recommendation

**Implement Field Library approach:**

1. Create `core/fields/library.py` with 10-15 universal fields
2. Add factories for imaging, IHC, biopsy (3 factories cover ~45 DPM fields)
3. Refactor DPM schema to use library where applicable
4. Keep ~80 DPM fields as-is (they're truly DPM-specific)
5. Next study reuses library, adds study-specific fields

**This is NOT perfect, but it's GOOD ENOUGH:**
- Reduces 40% of duplication (common fields + factories)
- Doesn't require rewriting everything  
- Actually works for different study types
- Simple enough to understand and maintain

**Accept:** 60% of DPM fields will always be DPM-specific. That's OKAY.
