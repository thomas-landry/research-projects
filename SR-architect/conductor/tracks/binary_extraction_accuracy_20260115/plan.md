# High-Accuracy Extraction - Revised Implementation Plan

**Date:** 2026-01-15  
**Track:** `binary_extraction_accuracy_20260115`  
**Status:** 🎯 READY FOR PHASE 0

---

## Revised Accuracy Targets (Research-Calibrated)

Based on current literature benchmarks (GPT-4o: 72.3%, o3: 75.3%):

| Tier | Original Target | **Revised Target** | With Human Review |
|------|-----------------|-------------------|-------------------|
| **Tier 1** | 98% | **92-95%** | 98% |
| **Tier 2** | 92% | **85-90%** | 95% |
| **Tier 3** | 87% | **70-80%** | 90% |
| **Tier 4** | 80% | **65-75%** | 88% |
| **Tier 5** | 60% | **40-60%** | 75% |

**Overall:** 85% autonomous → 95% with hybrid review (15-20% flagged)

---

## Schema Scope Decision

**Keep: 95 columns** (remove 30 low-value)

| Category | Keep | Remove | Reason |
|----------|------|--------|--------|
| Tier 1-3 | 70 | 0 | Core extractable |
| Critical Tier 4 | 10 | 5 | High-value outcomes |
| Select Tier 5 | 15 | 25 | Remove <10% mention rate |

---

## Phase 0: Baseline Calibration (Week 1) ← START HERE

### Goal
Establish gold standard and measure realistic baseline accuracy

### Deliverables

1. **Gold Standard Dataset** (20 papers)
   - Manual extraction by 2 raters
   - Inter-rater agreement (Cohen's kappa)
   - Consensus adjudication for disagreements

2. **Baseline Accuracy Report**
   - Per-field accuracy
   - Per-tier accuracy
   - NULL rate analysis
   - Worst-performing fields list

3. **Rule Coverage Audit**
   - Map all 80 binary fields to existing rules
   - Identify 35 uncovered fields
   - Prioritize by tier and value

4. **Field Tier Classification**
   - `field_tiers.yaml` with all 125 fields classified
   - Confidence thresholds per tier

### Implementation Tasks

#### Task 1: Create Gold Standard Framework

```python
# tests/test_gold_standard.py
def test_gold_standard_schema_matches_extraction():
    """Gold standard CSV has all required columns."""
    
def test_inter_rater_agreement():
    """Cohen's kappa > 0.7 for all fields."""
    
def test_consensus_adjudication():
    """All disagreements have consensus value."""
```

#### Task 2: Build Baseline Measurement Tool

```python
# core/metrics/baseline.py
class BaselineMeasurement:
    def measure_accuracy(self, predictions, gold_standard):
        """Calculate per-field accuracy against gold standard."""
    
    def measure_by_tier(self, predictions, gold_standard, tier_config):
        """Calculate accuracy grouped by tier."""
    
    def generate_report(self) -> dict:
        """Generate comprehensive baseline report."""
```

#### Task 3: Create Rule Coverage Audit

```python
# core/binary/coverage_audit.py
def audit_rule_coverage(schema, rules) -> dict:
    """Map all schema binary fields to rules."""
    
def identify_gaps() -> List[str]:
    """Return list of uncovered fields."""
```

#### Task 4: Implement Field Tier Classification

```yaml
# config/field_tiers.yaml
tiers:
  1:  # Keyword-based (92-95% target)
    confidence_threshold: 0.90
    fields:
      - symptom_fever
      - symptom_dyspnea
      - biopsy_tblb
      # ...
  2:  # Pattern-based (85-90% target)
    confidence_threshold: 0.85
    fields:
      - ct_ground_glass
      - symptom_asymptomatic
      # ...
  # ... tiers 3-5
```

### Phase 0 Tests (TDD)

```python
# tests/test_baseline_measurement.py

def test_baseline_accuracy_calculates_correctly():
    """Accuracy = correct / total."""
    predictions = {"field1": True, "field2": False}
    gold = {"field1": True, "field2": True}
    
    accuracy = calculate_field_accuracy(predictions, gold, "field1")
    assert accuracy == 1.0
    
    accuracy = calculate_field_accuracy(predictions, gold, "field2")
    assert accuracy == 0.0

def test_tier_accuracy_aggregates_correctly():
    """Tier accuracy is average of field accuracies."""
    tier_config = {"tier_1": ["field1", "field2"]}
    field_accuracies = {"field1": 0.9, "field2": 0.8}
    
    tier_accuracy = calculate_tier_accuracy(field_accuracies, tier_config, 1)
    assert tier_accuracy == 0.85

def test_null_rate_calculated():
    """NULL rate = null_count / total."""
    data = {"field1": [None, "value", None, "value"]}
    
    null_rate = calculate_null_rate(data, "field1")
    assert null_rate == 0.5
```

---

## Phase 1: Rules Enhancement (Week 2)

### Goal
Achieve 90%+ accuracy for Tier 1-2 fields (55 fields)

### Missing Rules to Add (35 fields)

**Biopsy Diagnostic (9 fields):**
- `biopsy_tblb_diagnostic`
- `biopsy_endobronchial_diagnostic`
- `biopsy_ttnb_diagnostic`
- `biopsy_surgical_diagnostic`
- `biopsy_cryobiopsy_diagnostic`
- `biopsy_endobronchial`
- `biopsy_ttnb`
- `biopsy_autopsy`

**Pathology Features (6 fields):**
- `gross_subpleural_predominance`
- `gross_features`
- `ultrastructure_em_features`
- `primary_histologic_pattern`
- `ct_thickened_intralobular_septum`
- `ct_central_perihilar_predominance`

**Exposures (3 fields):**
- `exposure_birds`
- `exposure_rabbits`
- `exposure_other`

**Additional fields as identified in audit**

---

## Phase 2: Tiered Extraction Pipeline (Week 3)

### Goal
Implement confidence-weighted tiered extraction

### Core Components

```python
# core/extraction/tiered_extractor.py
class TieredExtractor:
    def __init__(self, tier_config: dict):
        self.tier_config = tier_config
        self.confidence_thresholds = {
            1: 0.90, 2: 0.85, 3: 0.70, 4: 0.60, 5: 0.50
        }
    
    def extract(self, pdf, schema) -> List[ExtractionResult]:
        """Route each field to optimal extraction method."""
        results = []
        
        for field in schema.fields:
            tier = self.get_tier(field)
            
            if tier <= 2:
                result = self.extract_with_rules(pdf, field)
            elif tier == 3:
                result = self.extract_numeric(pdf, field)
            else:
                result = self.extract_with_llm(pdf, field)
            
            result.should_flag = result.confidence < self.confidence_thresholds[tier]
            results.append(result)
        
        return results
```

---

## Phase 3: Validation Layer (Week 3)

### Goal
Multi-layer validation before CSV write

### Validation Types

1. **Type validation** - Ensure correct data types
2. **Range validation** - Numeric fields within expected ranges
3. **Cross-field validation** - Mutually exclusive fields
4. **Completeness validation** - Flag sparse rows

```python
# core/validation/validators.py
class ValidationPipeline:
    validators = [
        TypeValidator(),
        RangeValidator(),
        CrossFieldValidator(),
        CompletenessValidator(min_fill_rate=0.6),
    ]
    
    def validate(self, extraction) -> ValidationResult:
        errors = []
        warnings = []
        
        for validator in self.validators:
            result = validator.validate(extraction)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
```

---

## Phase 4: Hybrid Review Workflow (Week 4)

### Goal
Achieve 95% accuracy through confidence-based human review

### Review Queue

```python
# core/review/queue.py
class ReviewQueue:
    def prioritize(self, extractions) -> List[ReviewItem]:
        """Flag low-confidence fields for human review."""
        queue = []
        
        for paper in extractions:
            for result in paper.results:
                if result.should_flag:
                    queue.append(ReviewItem(
                        paper_id=paper.id,
                        field=result.field,
                        value=result.value,
                        confidence=result.confidence,
                        context=result.source_text[:500],
                        priority=self.calculate_priority(result),
                    ))
        
        return sorted(queue, key=lambda x: -x.priority)
```

### Human Review Interface

- Web UI showing extracted value + context
- Accept / Reject / Modify actions
- Tracks reviewer, time, rationale

---

## Provenance Tracking

```python
# core/extraction/provenance.py
@dataclass
class ExtractionResult:
    field: str
    value: Any
    confidence: float
    tier: int
    method: Literal["rule", "llm", "hybrid"]
    source_text: str
    timestamp: datetime
    model_version: Optional[str] = None
    rule_name: Optional[str] = None
    
    def to_audit_log(self) -> dict:
        return {
            "field": self.field,
            "value": self.value,
            "confidence": self.confidence,
            "provenance": self.source_text[:200],
            "method": self.method,
            "tier": self.tier,
        }
```

---

## Success Metrics

### Autonomous Extraction (Target: 85%)

| Metric | Target | Measured |
|--------|--------|----------|
| Tier 1 accuracy | 92% | TBD |
| Tier 2 accuracy | 87% | TBD |
| Tier 3 accuracy | 75% | TBD |
| Tier 4 accuracy | 70% | TBD |
| Tier 5 accuracy | 50% | TBD |
| **Weighted avg** | **85%** | **TBD** |

### With Human Review (Target: 95%)

| Metric | Target |
|--------|--------|
| Review rate | 15-20% |
| Post-review accuracy | 95% |
| Review time/paper | <5 min |

### Cost Metrics

| Approach | Accuracy | Cost/Paper |
|----------|----------|------------|
| Pure LLM | 85% | $2.00 |
| Hybrid (AI+human) | 95% | $5.95 |
| Pure human | 90% | $50.00 |

---

## Week 1 Action Items

### Day 1-2: Gold Standard Creation
- [ ] Select 20 diverse papers (case reports, series, cohorts)
- [ ] Create extraction template matching schema
- [ ] Assign 2 raters for independent extraction
- [ ] Set up inter-rater agreement calculation

### Day 3: Baseline Measurement Setup
- [ ] Write tests for accuracy calculation (TDD)
- [ ] Implement `BaselineMeasurement` class
- [ ] Create per-field accuracy report generator

### Day 4: Rule Coverage Audit
- [ ] Map all 80 binary fields to existing rules
- [ ] Identify 35+ uncovered fields
- [ ] Prioritize gaps by tier and value

### Day 5: Field Tier Classification
- [ ] Classify all 125 fields into 5 tiers
- [ ] Create `field_tiers.yaml`
- [ ] Set confidence thresholds per tier

### End of Week 1: Baseline Report
- [ ] Run current pipeline on gold standard
- [ ] Calculate per-field accuracy
- [ ] Identify worst-performing fields
- [ ] Generate improvement priority list

---

## Verification Plan

### Automated Tests
```bash
# Run all accuracy tests
python3 -m pytest tests/test_baseline_measurement.py -v

# Run accuracy on gold standard
python3 -m pytest tests/test_gold_standard.py -v

# Coverage audit
python3 core/binary/coverage_audit.py --output reports/coverage.md
```

### Manual Verification
1. Review gold standard with medical expert
2. Validate inter-rater agreement
3. Confirm field tier classifications

---

## Decisions Confirmed

- ✅ Schema scope: 95 columns (remove 30 low-value)
- ✅ Accuracy target: 85% autonomous, 95% with review
- ✅ Review budget: 10-15% steady state
- ✅ Prioritize accuracy over speed for Phase 0
- ✅ Hybrid approach from Day 1

---

## Next Steps

1. **Create task.md** for tracking Phase 0 progress
2. **Write first failing tests** for baseline measurement
3. **Begin gold standard paper selection**
4. **Route to appropriate specialists** for implementation
