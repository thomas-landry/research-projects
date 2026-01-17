# Binary Extraction Accuracy - Decision Log

## Decision 1: Hybrid Extraction Approach

**Date:** 2026-01-15  
**Decision:** Use hybrid LLM + rule-based extraction for binary fields  
**Rationale:**
- ✅ Combines LLM intelligence with rule reliability
- ✅ Catches edge cases missed by either approach alone
- ✅ Maintains narrative traceability for validation
- ✅ Allows gradual improvement of rules based on LLM output

**Alternatives Considered:**
1. **Pure LLM extraction** - Rejected (too expensive, less reliable for simple patterns)
2. **Pure rule-based** - Rejected (misses complex clinical reasoning)
3. **Ensemble (3 models)** - Rejected (3x cost, overkill)

**Implementation:**
- LLM provides binary hints during narrative extraction
- Rules validate and fill gaps
- Conflicts resolved by narrative evidence

---

## Decision 2: Smart Field Routing by Complexity

**Date:** 2026-01-15  
**Decision:** Route fields to appropriate extraction method based on complexity  
**Rationale:**
- ✅ Optimizes cost/accuracy trade-off
- ✅ Simple keyword fields don't need LLM
- ✅ Complex clinical judgment fields benefit from LLM

**Field Classification:**

**Simple (Rule-only):**
- Keyword presence: `symptom_fever`, `symptom_dyspnea`
- Acronyms: `biopsy_tblb`, `biopsy_vats`
- Exact matches: `exposure_birds`, `exposure_rabbits`

**Medium (LLM + Rules):**
- Numeric thresholds: `ihc_ki67_high` (>5%)
- Pattern recognition: `ct_ground_glass`, `ct_cheerio`
- Anatomical locations: `ct_upper_lobe_predominance`

**Complex (LLM-primary):**
- Clinical judgment: `outcome_dpm_progressed`
- Multi-factor decisions: `biopsy_tblb_diagnostic`
- Temporal reasoning: `symptom_progression`

---

## Decision 3: Validation Before CSV Write

**Date:** 2026-01-15  
**Decision:** Add completeness validation before writing CSV rows  
**Rationale:**
- ✅ Prevents incomplete data from entering analysis
- ✅ Flags low-quality extractions for review
- ✅ Provides quality metrics per extraction

**Validation Rules:**
- Minimum 80% binary field fill rate
- Required fields must be non-NULL
- Age must be numeric or range format
- IHC markers must have pos/neg pairs

**Action on Failure:**
- Set `extraction_status = "PARTIAL"`
- Log specific missing fields in `extraction_notes`
- Still write row (for audit trail)
- Flag for human review

---

## Decision 4: Test-Driven Development for Binary Rules

**Date:** 2026-01-15  
**Decision:** Write tests first for all binary derivation rules  
**Rationale:**
- ✅ Ensures rule coverage for all 80 binary fields
- ✅ Prevents regressions when updating rules
- ✅ Documents expected behavior
- ✅ Enables confident refactoring

**Test Structure:**
```python
# Test 1: Rule coverage
def test_all_binary_fields_have_rules()

# Test 2: Rule accuracy
def test_symptom_rules_extract_correctly()
def test_ct_rules_extract_correctly()
def test_ihc_rules_extract_correctly()

# Test 3: Edge cases
def test_negation_handling()
def test_ambiguous_language()
def test_multiple_mentions()
```

---

## Open Questions

1. **Age Format Standardization:**
   - Should "60-70 years" be stored as "65" (midpoint) or "60-70" (range)?
   - How to handle "elderly" or "middle-aged"?

2. **NULL vs. False Semantics:**
   - NULL = "not mentioned in paper"
   - False = "explicitly stated as absent"
   - Should we distinguish these?

3. **Confidence Thresholds:**
   - What confidence score triggers human review?
   - 0.8? 0.9? Field-dependent?

4. **Binary Pair Consistency:**
   - If `ihc_ema_pos = True`, should `ihc_ema_neg = False` automatically?
   - Or allow both NULL (not tested)?
