# Generalizable Binary Rule System - Design Brainstorm

**Date:** 2026-01-15  
**Goal:** Add 16 missing rules while making system reusable for other systematic reviews

---

## Current Architecture (DPM-Specific)

### Problems with Current Design

```python
DerivationRule(
    field_name="symptom_asymptomatic",
    source_narrative="symptom_narrative",  # ← Hard-coded DPM field
    positive_patterns=[...],
)
```

**Issues:**
1. ❌ **Hard-coded source fields** - `symptom_narrative`, `ct_narrative` are DPM-specific
2. ❌ **No schema discovery** - Rules manually specify which narrative to search
3. ❌ **Not composable** - Can't reuse "asymptomatic" logic for other studies
4. ❌ **Tight coupling** - Rules are coupled to DPM schema structure

---

## Design Options

### Option 1: Auto-Discovery of Source Narratives

**Approach:** Rules specify field name only, system auto-discovers relevant narrative

```python
DerivationRule(
    field_name="symptom_asymptomatic",
    # No source_narrative!
    positive_patterns=[r"\basymptomatic\b", ...],
)

# System infers:
# - "symptom_asymptomatic" starts with "symptom_"
# - Search for narrative field: "symptom_narrative" OR "symptoms" OR "presenting_symptoms"
# - Use fuzzy matching: symptom* → symptom_narrative
```

**Pros:**
- ✅ Schema-agnostic (works with any schema)
- ✅ Rules are more portable
- ✅ Less verbose rule definitions

**Cons:**
- ⚠️ Inference can fail for non-matching names
- ⚠️ Ambiguous: `ct_ground_glass` could match `ct_narrative` or `imaging_findings`
- ⚠️ Magic behavior (harder to debug)

---

### Option 2: Rule Templates with Schema Mapping

**Approach:** Define reusable templates, map to schema explicitly

```python
# Template (reusable across studies)
ASYMPTOMATIC_TEMPLATE = RuleTemplate(
    pattern_name="asymptomatic",
    positive_patterns=[r"\basymptomatic\b", r"\bincidental\b", ...],
    description="Detects asymptomatic/incidental findings",
)

# Schema-specific mapping (DPM)
DPM_MAPPINGS = {
    "symptom_asymptomatic": ("symptom_narrative", ASYMPTOMATIC_TEMPLATE),
    "presentation_asymptomatic": ("presenting_symptoms", ASYMPTOMATIC_TEMPLATE),
}

# Schema-specific mapping (Other Study)
CANCER_MAPPINGS = {
    "incidental_finding": ("clinical_presentation", ASYMPTOMATIC_TEMPLATE),
}
```

**Pros:**
- ✅ **Highly reusable** - Templates used across studies
- ✅ **Explicit mapping** - Clear which narrative to search
- ✅ **Testable** - Templates tested once, mappings tested per-schema
- ✅ **Discoverable** - Easy to see what templates exist

**Cons:**
- ⚠️ More verbose (need mapping layer)
- ⚠️ Two files to maintain (templates + mappings)

---

### Option 3: Hybrid with Fallback Discovery

**Approach:** Allow manual specification OR auto-discovery

```python
DerivationRule(
    field_name="symptom_asymptomatic",
    source_narrative=None,  # ← Auto-discover
    positive_patterns=[...],
)

DerivationRule(
    field_name="ihc_ki67_high",
    source_narrative="immunohistochemistry_narrative",  # ← Explicit (ambiguous case)
    positive_patterns=[...],
)
```

**Discovery logic:**
1. If `source_narrative` specified → use it
2. If None → infer from field name prefix
3. If inference fails → raise error with suggestions

**Pros:**
- ✅ Best of both worlds
- ✅ Explicit when needed, auto when obvious
- ✅ Backward compatible

**Cons:**
- ⚠️ Still some magic behavior
- ⚠️ Need good error messages

---

## Recommended Approach: **Option 2 (Rule Templates)**

### Why Templates Win

1. **Reusability:** "Asymptomatic" logic works for any study with incidental findings
2. **Testability:** Test templates once with synthetic data
3. **Maintainability:** Update template → all studies benefit
4. **Clarity:** Explicit mapping shows intent
5. **Extensibility:** New studies = new mapping file only

### Architecture

```
core/binary/
├── templates/          # Reusable rule templates
│   ├── __init__.py
│   ├── symptoms.py     # symptom_asymptomatic, symptom_dyspnea, etc.
│   ├── imaging.py      # ct_ground_glass, ct_solid_nodules, etc.
│   ├── ihc.py          # ihc_ema_pos, ihc_pr_pos, etc.
│   ├── biopsy.py       # biopsy_tblb, biopsy_diagnostic, etc.
│   └── exposure.py     # exposure_birds, exposure_rabbits, etc.
│
├── mappings/           # Schema-specific mappings
│   ├── __init__.py
│   ├── dpm.py          # DPM study mappings
│   └── cancer.py       # Example: Cancer study mappings
│
├── core.py             # BinaryDeriver class
└── rules.py            # DEPRECATED (backward compat only)
```

---

## Implementation Plan

### Phase 1: Create Template System

**New:** `core/binary/templates/base.py`

```python
@dataclass
class RuleTemplate:
    """Reusable rule template."""
    pattern_name: str
    positive_patterns: List[str]
    negative_patterns: List[str] = None
    case_sensitive: bool = False
    description: str = ""
```

**New:** `core/binary/templates/symptoms.py`

```python
ASYMPTOMATIC = RuleTemplate(
    pattern_name="asymptomatic",
    positive_patterns=[
        r"\basymptomatic\b",
        r"\bincidental\b",
        r"\bno symptoms\b",
    ],
    description="Detects asymptomatic/incidental presentations",
)

DYSPNEA = RuleTemplate(
    pattern_name="dyspnea",
    positive_patterns=[
        r"\bdyspnea\b",
        r"\bshortness of breath\b",
        r"\bSOB\b",
    ],
    description="Detects dyspnea/breathlessness",
)
```

### Phase 2: Create Schema Mapping

**New:** `core/binary/mappings/dpm.py`

```python
from core.binary.templates import symptoms, imaging, ihc, biopsy

DPM_RULE_MAPPINGS = [
    # Symptoms
    ("symptom_asymptomatic", "symptom_narrative", symptoms.ASYMPTOMATIC),
    ("symptom_dyspnea", "symptom_narrative", symptoms.DYSPNEA),
    
    # CT findings
    ("ct_ground_glass", "ct_narrative", imaging.GROUND_GLASS),
    
    # IHC markers
    ("ihc_ema_pos", "immunohistochemistry_narrative", ihc.EMA_POSITIVE),
    
    # Biopsy
    ("biopsy_tblb", "diagnostic_approach", biopsy.TBLB),
]

def get_dpm_rules() -> List[DerivationRule]:
    """Generate DerivationRules from templates."""
    return [
        DerivationRule(
            field_name=field,
            source_narrative=source,
            positive_patterns=template.positive_patterns,
            negative_patterns=template.negative_patterns,
            case_sensitive=template.case_sensitive,
        )
        for field, source, template in DPM_RULE_MAPPINGS
    ]
```

### Phase 3: Add Missing Templates

**16 new templates needed:**

1. **Biopsy diagnostics (8):**
   - `BIOPSY_DIAGNOSTIC` - Generic "diagnostic yield" template
   - Applied to: `biopsy_tblb_diagnostic`, `biopsy_surgical_diagnostic`, etc.

2. **CT patterns (2):**
   - `CT_CENTRAL_PERIHILAR` - "central", "perihilar" patterns
   - `CT_SEPTAL_THICKENING` - "septal", "interlobular" patterns

3. **Exposures (2):**
   - `EXPOSURE_BIRDS` - "bird", "avian", "pigeon" patterns
   - `EXPOSURE_RABBITS` - "rabbit", "lagomorph" patterns

4. **Management/outcomes (4):**
   - `FOLLOWUP_AVAILABLE` - "follow-up", "serial imaging" patterns
   - `NO_FOLLOWUP` - "lost to follow-up", "no follow-up data" patterns
   - `LUNG_TRANSPLANT_REFERRAL` - "transplant", "referral" patterns

---

## Benefits for Other Studies

### Example: Cancer Systematic Review

```python
# Can reuse DPM templates!
from core.binary.templates import symptoms, imaging, biopsy

CANCER_RULE_MAPPINGS = [
    # Reuse asymptomatic template
    ("incidental_finding", "clinical_presentation", symptoms.ASYMPTOMATIC),
    
    # Reuse ground glass template
    ("imaging_ggo", "radiology_findings", imaging.GROUND_GLASS),
    
    # Reuse biopsy template
    ("biopsy_core_needle", "diagnostic_procedures", biopsy.CORE_NEEDLE),
]
```

**No need to redefine patterns!** Just map to different narrative fields.

---

## Migration Strategy

### Backward Compatibility

Keep `core/binary/rules.py` for now:

```python
# rules.py (deprecated)
from .mappings.dpm import get_dpm_rules

# Maintain old interface
ALL_RULES = get_dpm_rules()
```

**Users can:**
- Use old `ALL_RULES` (works as before)
- Migrate to new template system (better long-term)

### Gradual Migration

1. **Phase 1:** Add template system (new code only)
2. **Phase 2:** Migrate existing rules to templates
3. **Phase 3:** Deprecate `rules.py` (warning message)
4. **Phase 4:** Remove `rules.py` (major version bump)

---

## Testing Strategy

### Test Templates (Once)

```python
def test_asymptomatic_template():
    """Test asymptomatic template with synthetic text."""
    text = "Patient was asymptomatic on presentation"
    
    # Template should match
    assert matches_template(ASYMPTOMATIC, text) == True
    
    text = "Patient presented with severe symptoms"
    assert matches_template(ASYMPTOMATIC, text) == False
```

### Test Mappings (Per Schema)

```python
def test_dpm_symptom_asymptomatic_mapping():
    """Test DPM-specific mapping for symptom_asymptomatic."""
    rules = get_dpm_rules()
    
    # Find rule for symptom_asymptomatic
    rule = next(r for r in rules if r.field_name == "symptom_asymptomatic")
    
    # Should map to symptom_narrative
    assert rule.source_narrative == "symptom_narrative"
    
    # Should use ASYMPTOMATIC template patterns
    assert r"\basymptomatic\b" in rule.positive_patterns
```

---

## Questions for User

Before implementing, need clarification:

1. **Scope:** Should I refactor ALL 58 existing rules to templates, or just add the 16 new ones using templates?
   - **Option A:** Add 16 new ones as templates, keep 58 old ones as-is (hybrid)
   - **Option B:** Migrate all 74 to templates (cleaner but more work)

2. **Naming:** Do you prefer:
   - `core/binary/templates/` (chosen above)
   - `core/binary/patterns/` (alternative name)
   - `core/rules/templates/` (different hierarchy)

3. **Template granularity:** Should `BIOPSY_DIAGNOSTIC` be:
   - **Generic:** One template for all biopsy types
   - **Specific:** Separate templates per biopsy type (TBLB_DIAGNOSTIC, SURGICAL_DIAGNOSTIC)

4. **Testing priority:** Test coverage for:
   - **All templates** (100% coverage)
   - **Critical templates only** (e.g., biopsy diagnostic)

---

## Recommendation

**Start with Option A (hybrid):**
1. Add template system (new infrastructure)
2. Add 16 missing rules as templates
3. Keep 58 existing rules as-is
4. User sees benefit immediately
5. Migrate remaining 58 later if valuable

**Next session:** Full migration to templates (low priority, nice-to-have)
