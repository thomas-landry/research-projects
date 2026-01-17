# High-Accuracy Binary Extraction - Deep Dive Analysis

**Date:** 2026-01-15  
**Goal:** Ensure EVERY schema column can be filled with high accuracy (>95%)  
**Approach:** Systematic analysis of extraction patterns, failure modes, and accuracy improvement strategies

---

## Executive Summary

To achieve **>95% accuracy** for all 125 schema columns, we need a **multi-layered strategy**:

1. **Schema Optimization** - Only include fields we can extract reliably
2. **Extraction Method Matching** - Right tool for each field type
3. **Validation & Quality Gates** - Catch errors before CSV write
4. **Iterative Improvement** - Test, measure, refine

**Key Insight:** Not all fields are created equal. We should **tier fields by extractability** and focus on high-value, high-accuracy fields first.

---

## Part 1: Field Extractability Analysis

### Current Schema Audit (125 columns)

**Existing Binary Derivation Rules:** 45 fields covered  
**Schema Binary Fields:** ~80 fields  
**Coverage Gap:** 35 fields WITHOUT rules (44% uncovered)

#### Rule Coverage by Domain

| Domain | Total Fields | Rules Exist | Coverage | Priority |
|--------|--------------|-------------|----------|----------|
| **Symptoms** | 8 | 8 | ✅ 100% | HIGH |
| **Associations** | 13 | 13 | ✅ 100% | MEDIUM |
| **CT Findings** | 11 | 11 | ✅ 100% | HIGH |
| **IHC Markers** | 16 | 16 | ✅ 100% | CRITICAL |
| **Biopsy Types** | 12 | 3 | ❌ 25% | HIGH |
| **Outcomes** | 5 | 4 | ⚠️ 80% | HIGH |
| **Pathology** | 7 | 1 | ❌ 14% | MEDIUM |
| **Management** | 5 | 2 | ⚠️ 40% | LOW |

**Critical Gaps:**
- ❌ **Biopsy diagnostic fields** (9/12 missing) - e.g., `biopsy_tblb_diagnostic`
- ❌ **Pathology features** (6/7 missing) - e.g., `gross_subpleural_predominance`
- ❌ **Exposure fields** (3/3 missing) - e.g., `exposure_birds`, `exposure_rabbits`
- ❌ **CT distribution** (1/4 missing) - e.g., `ct_central_perihilar_predominance`

---

## Part 2: Extraction Method Taxonomy

### Field Type Classification

#### **Tier 1: Keyword-Based (Highest Accuracy: 98%+)**

**Characteristics:**
- Exact keyword presence/absence
- Minimal ambiguity
- Rule-based extraction sufficient

**Examples:**
```python
# Simple keyword match
"symptom_fever" → search for "fever" or "febrile"
"exposure_birds" → search for "bird", "avian", "pigeon"
"biopsy_tblb" → search for "TBLB", "transbronchial"
```

**Extraction Method:** Regex rules only  
**Estimated Accuracy:** 98%  
**Fields:** ~30 fields

---

#### **Tier 2: Pattern-Based (High Accuracy: 90-95%)**

**Characteristics:**
- Requires pattern matching
- Some context needed
- Negation handling important

**Examples:**
```python
# Pattern with context
"ct_ground_glass" → "ground glass" OR "GGO" OR "GGN"
"symptom_asymptomatic" → "asymptomatic" OR "incidental" OR "no symptoms"
"ct_upper_lobe_predominance" → "upper lobe predominance" OR "apical predominance"
```

**Extraction Method:** Enhanced regex + negation handling  
**Estimated Accuracy:** 92%  
**Fields:** ~25 fields

---

#### **Tier 3: Numeric Threshold (Medium Accuracy: 85-90%)**

**Characteristics:**
- Requires numeric extraction
- Threshold comparison
- Unit normalization needed

**Examples:**
```python
# Numeric extraction + threshold
"ihc_ki67_high" → Extract "Ki67: 8%" → 8 > 5 → True
"age" → Extract "65 years" → Normalize to 65
"followup_interval_imaging_months" → "6 months" → 6
```

**Challenges:**
- Varied formats: "5%", "5 percent", "five percent"
- Range handling: "5-10%" → use midpoint?
- Missing units: "Ki67: 8" → assume percent?

**Extraction Method:** LLM extraction + post-processing validation  
**Estimated Accuracy:** 87%  
**Fields:** ~15 fields

---

#### **Tier 4: Clinical Judgment (Lower Accuracy: 75-85%)**

**Characteristics:**
- Requires interpretation
- Context-dependent
- Multiple factors

**Examples:**
```python
# Complex reasoning
"biopsy_tblb_diagnostic" → Was TBLB sufficient for diagnosis?
  - Requires: TBLB performed AND diagnosis made AND no other biopsy needed
  
"outcome_dpm_progressed" → Did disease progress?
  - Requires: Comparison of before/after imaging + clinical assessment
  
"symptom_progression" → Are symptoms worsening?
  - Requires: Temporal comparison + severity assessment
```

**Extraction Method:** LLM with structured prompting + validation  
**Estimated Accuracy:** 80%  
**Fields:** ~10 fields

---

#### **Tier 5: Rarely Documented (Low Accuracy: 50-70%)**

**Characteristics:**
- Often not mentioned in papers
- High NULL rate expected
- May not be extractable

**Examples:**
```python
# Rarely documented
"exposure_rabbits" → Most papers don't mention rabbit exposure
"assoc_turner_syndrome" → Rare condition, rarely mentioned
"mgmt_lung_transplant_referral" → Uncommon outcome
```

**Extraction Method:** LLM + accept high NULL rate  
**Estimated Accuracy:** 60% (when mentioned)  
**Expected NULL Rate:** 80-90%  
**Fields:** ~15 fields

---

## Part 3: Accuracy Improvement Strategies

### Strategy 1: Tiered Extraction Pipeline

**Approach:** Route each field to the optimal extraction method based on tier

```python
class TieredExtractor:
    def extract(self, pdf, schema):
        results = {}
        
        # Tier 1: Keyword-based (rules only)
        tier1_fields = get_tier1_fields(schema)
        results.update(self.extract_with_rules(pdf, tier1_fields))
        
        # Tier 2: Pattern-based (enhanced rules)
        tier2_fields = get_tier2_fields(schema)
        results.update(self.extract_with_patterns(pdf, tier2_fields))
        
        # Tier 3: Numeric (LLM + validation)
        tier3_fields = get_tier3_fields(schema)
        results.update(self.extract_numeric_fields(pdf, tier3_fields))
        
        # Tier 4: Clinical judgment (LLM with prompting)
        tier4_fields = get_tier4_fields(schema)
        results.update(self.extract_complex_fields(pdf, tier4_fields))
        
        # Tier 5: Rare fields (LLM, accept NULLs)
        tier5_fields = get_tier5_fields(schema)
        results.update(self.extract_rare_fields(pdf, tier5_fields))
        
        return results
```

**Benefits:**
- ✅ Optimizes cost (rules are free, LLM is expensive)
- ✅ Maximizes accuracy (right tool for each job)
- ✅ Faster (parallel execution possible)

---

### Strategy 2: Confidence-Weighted Validation

**Approach:** Assign confidence scores and validate low-confidence extractions

```python
class ConfidenceValidator:
    def validate(self, extraction):
        for field, value in extraction.items():
            confidence = self.calculate_confidence(field, value)
            
            if confidence < 0.7:
                # Re-extract with different method
                value = self.re_extract(field, extraction.narrative)
            
            if confidence < 0.5:
                # Flag for human review
                extraction.flags.append(f"{field}: low confidence")
            
            extraction.confidence_scores[field] = confidence
        
        return extraction
    
    def calculate_confidence(self, field, value):
        # Tier 1 fields: high confidence
        if field in TIER1_FIELDS:
            return 0.95 if value is not None else 0.90
        
        # Tier 4 fields: lower confidence
        if field in TIER4_FIELDS:
            return 0.75 if value is not None else 0.60
        
        # Default
        return 0.85
```

---

### Strategy 3: Cross-Field Validation

**Approach:** Use field relationships to validate extractions

```python
class CrossFieldValidator:
    """Validate fields against each other for consistency."""
    
    VALIDATION_RULES = [
        # IHC pairs must be mutually exclusive
        ("ihc_ema_pos", "ihc_ema_neg", "mutually_exclusive"),
        ("ihc_pr_pos", "ihc_pr_neg", "mutually_exclusive"),
        
        # If biopsy performed, at least one must be diagnostic
        ("biopsy_tblb", "biopsy_tblb_diagnostic", "implies"),
        
        # Age and demographics consistency
        ("age", "patient_demographics_narrative", "mentioned_in"),
        
        # Outcome requires follow-up
        ("outcome_dpm_stable", "outcome_followup_available", "requires"),
    ]
    
    def validate(self, extraction):
        errors = []
        
        for field1, field2, rule_type in self.VALIDATION_RULES:
            if rule_type == "mutually_exclusive":
                if extraction[field1] and extraction[field2]:
                    errors.append(f"{field1} and {field2} both True")
            
            elif rule_type == "implies":
                if extraction[field1] and not extraction[field2]:
                    # Warn but don't error (may be legitimately non-diagnostic)
                    extraction.warnings.append(f"{field1} True but {field2} False")
        
        return errors
```

---

### Strategy 4: Iterative Rule Refinement

**Approach:** Test rules against gold standard, identify failures, refine

```python
class RuleRefiner:
    def refine_rules(self, gold_standard_csv, current_rules):
        # Load gold standard
        gold_data = pd.read_csv(gold_standard_csv)
        
        # Test current rules
        results = self.test_rules(gold_data, current_rules)
        
        # Identify low-accuracy fields
        low_accuracy = [
            field for field, acc in results.items()
            if acc < 0.90
        ]
        
        # Analyze failures
        for field in low_accuracy:
            failures = self.get_failures(field, gold_data, results)
            
            # Suggest new patterns
            new_patterns = self.suggest_patterns(failures)
            
            print(f"{field}: {len(failures)} failures")
            print(f"Suggested patterns: {new_patterns}")
        
        return low_accuracy
```

**Process:**
1. Run extraction on gold standard (10 papers)
2. Compare to manual annotations
3. Calculate per-field accuracy
4. For fields <90%: analyze false negatives/positives
5. Add missing patterns to rules
6. Re-test
7. Repeat until >90%

---

## Part 4: Schema Optimization

### Recommendation: Reduce Schema to High-Confidence Fields

**Current:** 125 columns (many with low extractability)  
**Proposed:** 80 columns (high-confidence only)

#### Fields to KEEP (80 columns)

**Tier 1 + Tier 2 fields (55 columns):**
- All symptoms (8)
- All associations (13)
- All CT findings (11)
- All IHC markers (16)
- Core biopsy types (3)
- Core outcomes (4)

**Tier 3 fields with validation (15 columns):**
- Age
- Case count
- Follow-up durations
- IHC thresholds (Ki67)

**Critical Tier 4 fields (10 columns):**
- Diagnostic biopsy fields (if mentioned)
- Primary outcomes

#### Fields to MAKE OPTIONAL (20 columns)

**Tier 5 fields (rarely documented):**
- Rare exposures (rabbits, specific animals)
- Rare conditions (Turner syndrome)
- Uncommon management (transplant referral)

**Strategy:** Mark as `required=False`, accept 80-90% NULL rate

#### Fields to REMOVE (25 columns)

**Candidates for removal:**
- Duplicate information (narrative + binary for same concept)
- Fields never mentioned in papers
- Fields requiring external data (DOI, journal)

---

## Part 5: Implementation Roadmap

### Phase 1: Rule Coverage Audit (Week 1)

**Goal:** Achieve 100% rule coverage for Tier 1-2 fields

**Tasks:**
1. Map all 80 binary fields to tiers
2. Write missing rules for uncovered fields
3. Test rules against gold standard
4. Measure per-field accuracy

**Tests:**
```python
def test_rule_coverage_complete():
    """Every Tier 1-2 field has a derivation rule."""
    tier1_2_fields = TIER1_FIELDS + TIER2_FIELDS
    covered_fields = [r.field_name for r in ALL_RULES]
    
    missing = set(tier1_2_fields) - set(covered_fields)
    assert len(missing) == 0, f"Missing rules: {missing}"

def test_rule_accuracy_above_threshold():
    """All rules achieve >90% accuracy on gold standard."""
    gold_data = load_gold_standard()
    
    for rule in ALL_RULES:
        accuracy = test_rule_accuracy(rule, gold_data)
        assert accuracy > 0.90, f"{rule.field_name}: {accuracy:.2%}"
```

---

### Phase 2: Tiered Extraction Implementation (Week 2)

**Goal:** Implement tiered extraction pipeline

**Tasks:**
1. Create `TieredExtractor` class
2. Classify all fields by tier
3. Implement tier-specific extraction methods
4. Add confidence scoring

**Tests:**
```python
def test_tier1_extraction_uses_rules_only():
    """Tier 1 fields don't call LLM."""
    extractor = TieredExtractor()
    
    with mock.patch('llm.extract') as mock_llm:
        result = extractor.extract_tier1(pdf, TIER1_FIELDS)
        
        # LLM should never be called for Tier 1
        assert mock_llm.call_count == 0

def test_tier3_numeric_normalization():
    """Tier 3 numeric fields are normalized correctly."""
    narrative = "Patient age: 65 years"
    
    result = extract_numeric_field("age", narrative)
    
    assert result == 65
    assert isinstance(result, int)
```

---

### Phase 3: Validation Layer (Week 3)

**Goal:** Add multi-layer validation before CSV write

**Tasks:**
1. Implement `ConfidenceValidator`
2. Implement `CrossFieldValidator`
3. Add completeness checks
4. Generate quality reports

**Tests:**
```python
def test_cross_field_validation_catches_conflicts():
    """IHC pos/neg conflicts are detected."""
    extraction = {
        "ihc_ema_pos": True,
        "ihc_ema_neg": True,  # Conflict!
    }
    
    validator = CrossFieldValidator()
    errors = validator.validate(extraction)
    
    assert len(errors) > 0
    assert "ihc_ema" in errors[0]

def test_completeness_validation_flags_sparse_rows():
    """Rows with <80% fill rate are flagged."""
    extraction = {f"field_{i}": None for i in range(100)}
    extraction["field_1"] = "value"  # Only 1% filled
    
    validator = CompletenessValidator(min_fill_rate=0.8)
    result = validator.validate(extraction)
    
    assert result.is_valid == False
    assert result.fill_rate < 0.02
```

---

### Phase 4: Iterative Refinement (Ongoing)

**Goal:** Continuously improve accuracy through testing

**Process:**
1. Run extraction on gold standard (10 papers)
2. Calculate per-field accuracy
3. Identify fields <90% accuracy
4. Analyze failure patterns
5. Refine rules or prompts
6. Re-test
7. Repeat weekly

**Metrics to Track:**
- Per-field accuracy
- Overall fill rate
- Confidence score distribution
- Human review rate

---

## Part 6: Expected Outcomes

### Accuracy Targets by Tier

| Tier | Fields | Target Accuracy | Expected NULL Rate |
|------|--------|-----------------|-------------------|
| Tier 1 | 30 | 98% | 5% |
| Tier 2 | 25 | 92% | 10% |
| Tier 3 | 15 | 87% | 15% |
| Tier 4 | 10 | 80% | 20% |
| Tier 5 | 15 | 60% | 80% |

### Overall Schema Quality

**Weighted Average Accuracy:** 91%  
**Fields with >90% accuracy:** 70/95 (74%)  
**Fields requiring human review:** <5% of extractions

### Cost Optimization

**Current:** 100% LLM extraction  
**Proposed:** 
- 30% rule-based (free)
- 40% LLM-assisted (medium cost)
- 30% full LLM (high cost)

**Estimated Cost Reduction:** 40%

---

## Part 7: Critical Success Factors

### 1. Gold Standard Quality

**Requirement:** High-quality manual annotations for 20+ papers  
**Use:** Training data for rule refinement and accuracy measurement

### 2. Iterative Testing

**Requirement:** Weekly accuracy testing and rule refinement  
**Use:** Continuous improvement, catch regressions

### 3. Field Prioritization

**Requirement:** Clear understanding of which fields are critical  
**Use:** Focus effort on high-value fields first

### 4. Validation Rigor

**Requirement:** Multi-layer validation before CSV write  
**Use:** Catch errors early, maintain data quality

---

## Recommendations

### Immediate Actions

1. **Audit current rules** - Map to schema, identify gaps
2. **Create tier classification** - Classify all 125 fields
3. **Build test suite** - TDD for all extraction methods
4. **Establish baseline** - Measure current accuracy on gold standard

### Strategic Decisions Needed

1. **Schema scope** - Keep all 125 columns or reduce to 80?
2. **NULL tolerance** - What's acceptable for each tier?
3. **Human review** - Budget for manual validation?
4. **Accuracy vs. cost** - Optimize for accuracy or cost?

### Next Steps

1. Review this analysis with user
2. Get answers to strategic questions
3. Create detailed implementation plan
4. Route to appropriate specialist agents
5. Begin Phase 1 implementation

