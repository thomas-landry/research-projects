# Binary Data Extraction Accuracy - Brainstorming Session

**Date:** 2026-01-15  
**Goal:** Improve extraction accuracy for binary columns (0/1), ages, pathology findings for statistical analysis  
**Current State:** 70% success rate (7/10 files), empty CSV rows on failures

---

## Problem Statement

The systematic review requires **complete, accurate binary data** for statistical analysis:
- **Binary fields** (0/1): IHC markers, CT findings, symptoms, biopsy types
- **Numeric fields**: Ages, follow-up durations, case counts
- **Categorical fields**: Pathology findings, outcomes

**Current Issues:**
1. ❌ Empty CSV rows when extraction fails (rate limiting)
2. ❌ Missing binary values (NULL instead of 0/1)
3. ❌ Inconsistent age formats ("65 years" vs "65" vs "60-70")
4. ❌ Narrative fields extracted but binaries not derived
5. ❌ No validation of binary field completeness

---

## Current Architecture

### Extraction Flow
```
PDF → Parser → LLM Extraction → Binary Derivation → CSV Output
                    ↓                    ↓
              Narratives           0/1 values
```

### Schema Structure (125 columns)
- **15 narrative fields** - LLM extracts rich text
- **~80 binary fields** - Derived from narratives
- **~30 other fields** - Ages, counts, metadata

### Existing Components
1. **`DPMGoldStandardSchema`** - Full 125-column schema
2. **`DPMNarrativeExtractionSchema`** - 15 narrative fields only
3. **`BinaryDeriver`** - Rule-based derivation from narratives
4. **Derivation rules** - Pattern matching for binary fields

---

## Root Cause Analysis

### Why are binary fields empty?

**Hypothesis 1: LLM doesn't extract binaries directly**
- ✅ **Correct** - Schema uses narrative-first approach
- Binary fields are `Optional[bool]` but LLM doesn't populate them
- Relies on post-processing derivation

**Hypothesis 2: Binary derivation rules are incomplete**
- ⚠️ **Partially correct** - Rules exist but may have gaps
- Need to analyze rule coverage vs. schema fields

**Hypothesis 3: Narrative extraction is incomplete**
- ✅ **Correct** - If narrative is empty, binaries can't be derived
- Rate limiting causes empty narratives → empty binaries

**Hypothesis 4: No validation enforces completeness**
- ✅ **Correct** - No checks for required binary fields
- CSV written even if 90% of fields are NULL

---

## Brainstorming Solutions

### **Option 1: Hybrid Extraction (LLM + Rules)** ⭐ **(RECOMMENDED)**

**Approach:**
- LLM extracts **both** narratives AND binary hints
- Post-processing rules **validate and fill gaps**
- Two-pass validation ensures completeness

**Implementation:**
```python
# Pass 1: LLM extraction
extraction = llm.extract(pdf, schema=HybridSchema)
# extraction.ct_narrative = "Ground glass nodules in upper lobes"
# extraction.ct_ground_glass = True  # LLM provides hint

# Pass 2: Rule-based validation
deriver = BinaryDeriver()
validated = deriver.validate_and_fill(extraction)
# If LLM said ct_ground_glass=True, verify in narrative
# If LLM missed it but narrative mentions "ground glass", set True
```

**Pros:**
- ✅ Best of both worlds: LLM intelligence + rule reliability
- ✅ Catches LLM mistakes with rules
- ✅ Fills gaps when LLM misses obvious patterns
- ✅ Maintains narrative traceability

**Cons:**
- ⚠️ More complex logic
- ⚠️ Requires careful rule design to avoid conflicts

---

### **Option 2: Structured Prompting with Examples**

**Approach:**
- Enhance prompts with explicit binary field instructions
- Provide few-shot examples showing binary extraction
- Use chain-of-thought prompting for complex fields

**Example Prompt:**
```
Extract the following from the CT findings:
- ct_ground_glass: True if "ground glass" mentioned, False otherwise
- ct_solid_nodules: True if "solid nodules" mentioned, False otherwise

Example:
Text: "CT showed bilateral ground glass opacities"
Output: {"ct_ground_glass": true, "ct_solid_nodules": false}

Now extract from: [actual text]
```

**Pros:**
- ✅ Simpler than hybrid approach
- ✅ Leverages LLM's natural language understanding
- ✅ No post-processing needed

**Cons:**
- ❌ Relies entirely on LLM accuracy
- ❌ Expensive (longer prompts)
- ❌ May still miss edge cases

---

### **Option 3: Multi-Stage Extraction Pipeline**

**Approach:**
1. **Stage 1:** Extract narratives only (fast, cheap)
2. **Stage 2:** Derive binaries from narratives (rules)
3. **Stage 3:** LLM validates uncertain binaries
4. **Stage 4:** Human review for low-confidence fields

**Implementation:**
```python
# Stage 1: Narrative extraction
narratives = extract_narratives(pdf, model="local")

# Stage 2: Rule-based derivation
binaries = derive_binaries(narratives)

# Stage 3: LLM validation (only uncertain fields)
uncertain_fields = [f for f in binaries if f.confidence < 0.8]
validated = llm_validate(narratives, uncertain_fields, model="cloud")

# Stage 4: Flag for human review
if validated.confidence < 0.9:
    flag_for_review(pdf, validated)
```

**Pros:**
- ✅ Cost-effective (uses local models for bulk work)
- ✅ High accuracy (cloud LLM validates edge cases)
- ✅ Human-in-the-loop for critical decisions

**Cons:**
- ⚠️ More complex pipeline
- ⚠️ Slower (multiple stages)

---

### **Option 4: Ensemble Extraction**

**Approach:**
- Run extraction with **3 different models**
- Aggregate results using voting or confidence weighting
- Use majority vote for binary fields

**Implementation:**
```python
# Extract with 3 models
result_local = extract(pdf, model="llama3")
result_cloud1 = extract(pdf, model="gemini")
result_cloud2 = extract(pdf, model="claude")

# Aggregate binaries
for field in binary_fields:
    votes = [r[field] for r in [result_local, result_cloud1, result_cloud2]]
    final[field] = majority_vote(votes)
```

**Pros:**
- ✅ Highest accuracy (reduces model-specific errors)
- ✅ Confidence scores from agreement

**Cons:**
- ❌ 3x cost
- ❌ 3x time
- ❌ Overkill for simple fields

---

### **Option 5: Smart Field Routing**

**Approach:**
- **Simple binaries** → Rule-based extraction
- **Complex binaries** → LLM extraction
- **Ambiguous cases** → Human review

**Complexity Classification:**
```python
SIMPLE_FIELDS = [
    "symptom_fever",  # "fever" keyword
    "biopsy_tblb",    # "TBLB" acronym
]

COMPLEX_FIELDS = [
    "ihc_ki67_high",  # Requires numeric threshold (>5%)
    "outcome_dpm_progressed",  # Requires clinical judgment
]
```

**Pros:**
- ✅ Optimizes cost/accuracy trade-off
- ✅ Fast for simple fields
- ✅ Accurate for complex fields

**Cons:**
- ⚠️ Requires field complexity classification
- ⚠️ Maintenance overhead

---

## Recommended Approach

**Combine Option 1 (Hybrid) + Option 5 (Smart Routing)**

### Phase 1: Enhance Binary Derivation Rules
- Audit existing rules vs. schema (80 binary fields)
- Add missing rules for uncovered fields
- Test rules against gold standard data

### Phase 2: Implement Hybrid Extraction
- Modify schema to include binary hints from LLM
- Update prompts to explicitly request binary values
- Implement validation layer

### Phase 3: Add Smart Routing
- Classify fields by complexity
- Route simple fields to rules only
- Route complex fields to LLM + rules

### Phase 4: Validation & Completeness Checks
- Add pre-CSV validation
- Flag rows with >20% NULL binaries
- Generate completeness report

---

## Implementation Plan

### Test-Driven Development Approach

**Test 1: Binary Derivation Coverage**
```python
def test_all_binary_fields_have_rules():
    """Verify every binary field has a derivation rule."""
    schema_fields = get_binary_fields(DPMGoldStandardSchema)
    rule_fields = get_covered_fields(ALL_RULES)
    
    missing = set(schema_fields) - set(rule_fields)
    assert len(missing) == 0, f"Missing rules for: {missing}"
```

**Test 2: Hybrid Extraction Accuracy**
```python
def test_hybrid_extraction_fills_binaries():
    """Verify hybrid extraction populates binary fields."""
    narrative = "CT showed ground glass nodules in upper lobes"
    
    result = hybrid_extract(narrative)
    
    assert result.ct_ground_glass == True
    assert result.ct_upper_lobe_predominance == True
    assert result.ct_solid_nodules == False
```

**Test 3: Completeness Validation**
```python
def test_csv_completeness_validation():
    """Verify CSV rows meet completeness threshold."""
    extraction = {...}  # 50% fields NULL
    
    validator = CompletenessValidator(min_fill_rate=0.8)
    result = validator.validate(extraction)
    
    assert result.is_valid == False
    assert "completeness" in result.errors
```

---

## Success Metrics

### Quantitative
- **Binary fill rate:** >90% (currently ~30%)
- **Extraction success rate:** >95% (currently 70%)
- **Age format consistency:** 100% (numeric only)
- **IHC marker accuracy:** >95% (critical for analysis)

### Qualitative
- CSV ready for statistical analysis without manual cleanup
- Confidence scores for uncertain extractions
- Audit trail for binary derivations

---

## Next Steps

1. **Audit binary derivation rules** - Map rules to schema fields
2. **Create test suite** - TDD for binary extraction
3. **Implement hybrid extraction** - LLM + rules
4. **Add validation layer** - Completeness checks
5. **Benchmark accuracy** - Compare to gold standard

---

## Questions for User

1. **Priority:** Which fields are most critical for your statistical analysis?
   - IHC markers?
   - CT findings?
   - Outcomes?

2. **Tolerance:** What's acceptable NULL rate for binary fields?
   - 0% (all must be filled)?
   - 5% (some can be unknown)?
   - 10% (lenient)?

3. **Cost vs. Accuracy:** Would you prefer:
   - Faster, cheaper extraction with 90% accuracy?
   - Slower, expensive extraction with 98% accuracy?

4. **Human Review:** Should the system flag uncertain extractions for manual review?
