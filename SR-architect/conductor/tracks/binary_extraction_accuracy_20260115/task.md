# Binary Extraction Accuracy - Task Tracking

## Mission Status

| Phase | Status | Accuracy Target | Progress |
|-------|--------|-----------------|----------|
| Phase 0: Baseline | 🟢 IN PROGRESS | Establish baseline | 75% |
| Phase 1: Rules | ⬜ Pending | 90%+ Tier 1-2 | - |
| Phase 2: Tiered Pipeline | ⬜ Pending | 85% autonomous | - |
| Phase 3: Validation | ⬜ Pending | Catch errors | - |
| Phase 4: Hybrid Review | ⬜ Pending | 95% with review | - |

---

## Active Phase: Phase 0 - Baseline Calibration

### Gold Standard Creation
- [ ] Select 20 diverse papers
- [ ] Create extraction template
- [ ] Rater 1 extraction (10 papers each)
- [ ] Rater 2 extraction (10 papers each)
- [ ] Calculate inter-rater agreement
- [ ] Adjudicate disagreements

### Baseline Measurement Framework
- [x] Write failing tests for accuracy calculation
- [x] Implement `BaselineMeasurement` class
- [x] Implement per-field accuracy calculation
- [x] **Update metrics for `FindingReport` compatibility**
- [x] Implement per-tier accuracy aggregation
- [x] Implement NULL rate calculation
- [x] Generate baseline report

### Rule Coverage Audit
- [x] Map 80 binary fields to existing rules
- [x] Identify uncovered fields (16 found)
- [x] Categorize gaps by domain
- [x] Prioritize by tier and value

### Field Tier Classification
- [x] Create `field_tiers.yaml`
- [x] Classify all 125 fields
- [x] Set confidence thresholds per tier
- [ ] Document classification rationale

### Baseline Report Generation
- [x] Run current pipeline on gold standard (Stubbed run: 0% accuracy)
- [x] Calculate per-field accuracy
- [x] Calculate per-tier accuracy
- [/] **Integrate Real Extraction Pipeline** (Code complete, verification timed out)
- [ ] Identify worst-performing fields
- [ ] Generate improvement priority list

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Schema scope | 95 columns | Remove 30 low-value Tier 5 fields |
| Autonomous accuracy | 85% | Research-calibrated target |
| With review accuracy | 95% | Hybrid AI + human |
| Review rate | 15-20% | Confidence-based flagging |
| Phase 0 first | Yes | Establish realistic baseline |

---

## Communication Log

| Date | From | Message |
|------|------|---------|
| 2026-01-15 | User | Provided research-calibrated accuracy targets |
| 2026-01-15 | Conductor | Created revised implementation plan |
| 2026-01-15 | Conductor | Created Phase 0 task tracking |

---

## Blocked Items

_None currently_

---

## Next Actions

1. **TDD:** Write failing tests for `BaselineMeasurement` class
2. **Implement:** Gold standard framework
3. **Audit:** Map binary fields to existing rules
4. **Classify:** Create field tier configuration
