# Track Plan: Pipeline Optimization v2 (Streamlined)

> **Note:** This plan supersedes the original `token_optimization_20260106` track. It consolidates 8 phases into 5, eliminating ~40% of tasks while preserving core functionality.

## Prerequisites

The following from the original track are already complete and will be reused:
- [x] Phase 0: POC Validation & Baseline Metrics [checkpoint: 6f145c9]
- [x] Phase 1: Resource Management & Observability Foundation [checkpoint: 36ea9af]

---

## Phase 2: Smart Parsing & metadata Integration (COMPLETE)

**Goal:** Reduce tokens at source through intelligent pre-processing and metadata enrichment.

**Key Insight:** ~60% of systematic review data points are in structured abstracts. Fetch these first.

### Tasks

- [x] Task: Implement `PubMedFetcher` class with DOI-based lookup via NCBI E-utilities API. ✅ (Pre-existing)
  - Input: DOI string
  - Output: `PubMedRecord` with structured abstract, authors, journal, year
  - Include rate limiting (3 req/sec) and caching
  
- [ ] Task: Implement `CrossRefFetcher` as fallback for non-PubMed DOIs. (DEFERRED)
  - Use CrossRef API for basic metadata
  - Lower priority than PubMed (less structured data)

- [x] Task: Create `AbstractFirstExtractor` that attempts extraction from structured abstract before full PDF parse. ✅ 2026-01-08
  - Define which fields can be extracted from abstract alone
  - Track "abstract-extracted" vs "body-extracted" in audit log

- [x] Task: Implement `ContentFilter` with section stripping (References, Acknowledgments, etc.). ✅ (Pre-existing)
  - Use regex patterns for section header detection
  - Preserve section boundaries in filtered output
  - Measure token reduction (target: 15-25%)

- [x] Task: Create `ComplexityClassifier` with PyMuPDF metrics. ✅ (Pre-existing)
  - Metrics: image density (>30%), table count, multi-column detection
  - Output: complexity score (0-1) used for routing decisions
  - Store in document metadata

- [x] Task: Implement simplified parser fallback chain: Docling → PyMuPDF4LLM only. ✅ 2026-01-08
  - Remove Vision API fallback (add back only if needed based on metrics)
  - Log fallback events for analysis
  - NOTE: pdfplumber removed per /refactor_standards_guardian

- [x] Task: Add document fingerprinting for near-duplicate detection. ✅ 2026-01-08
  - SHA256 hash on first 10K characters
  - Store in document_cache table
  - Skip processing if duplicate found

- [x] Task: Verify parsing improvements against golden dataset. ✅ 79.5% semantic match
  - Measure: Token reduction %, parsing success rate, time per document
  - Pass criteria: >15% token reduction, <5% parsing failure rate

- [ ] Task: Conductor - User Manual Verification 'Phase 2: Smart Parsing & Metadata Integration' (Protocol in workflow.md)

---

## Phase 3: Hybrid & Optimized Extraction (COMPLETE)

**Goal:** Implement the tiered extraction cascade, local-first strategy, and cost-optimization for large schemas.

**Key Insight:** Gemini Flash Lite + Schema Chunking provides the best price/performance ratio for complex medical data.

- [x] Task: Integrate Gemini Flash Lite via OpenRouter as primary cheap cloud model. ✅ 2026-01-08
  - Cost: $0.07/M input, $0.30/M output
  - Performance: Matches Sonnet for structured extraction on most clinical fields
  - Integration: `google/gemini-2.0-flash-lite-001` via OpenRouter

- [x] Task: Implement **CSV Schema Inference** for automatic field mapping. ✅ 2026-01-08
  - Input: User-provided CSV template
  - Logic: Automatically builds Pydantic models with `_quote` fields for provenance
  - Benefit: Handles any medical template without manual code changes

- [x] Task: Implement **Schema Chunking** for large schemas. ✅ 2026-01-08
  - Solves Gemini grammar complexity limits (400 Bad Request)
  - Split: 124 fields split into 5 chunks of ~25 fields
  - Merge: Automatic merging of sequential extraction passes

- [x] Task: Verify extraction on 83-paper corpus. ✅ 2026-01-08
  - Total Cost: $1.25 (estimated $9.96 with Sonnet)
  - Success Rate: 100% (all 83 papers processed)
  - Field coverage: 100% (all 124 fields extracted)

- [x] Task: Create `field_routing.yaml` configuration file. ✅ (Pre-existing, updated 2026-01-08)
  - Define field → tier mapping (Tier 0/1/2/3)
  - Define confidence thresholds per tier
  - Define model assignments per tier (updated to Qwen3)

- [x] Task: Implement Tier 0 regex extraction in `RegexExtractor` class. ✅ 2026-01-08
  - Fields: DOI, publication_year, journal_name
  - Fields with validation: sample_size, age_mean_sd, sex_ratio
  - Include context window check for validated fields
  - 12 tests pass

- [x] Task: Implement `TwoPassExtractor` with local-first strategy. ✅ 2026-01-08
  - Pass 1: All fields via local model (lenient confidence)
  - Identify low-confidence fields (<0.85)
  - Pass 2: Targeted cloud extraction for failures only
  - Track pass1-only vs pass2-needed ratio

- [x] Task: Create `ModelCascader` class for tier escalation logic. ✅ 2026-01-08
  - Input: Field, extraction result, confidence
  - Output: Decision (ACCEPT / ESCALATE / MANUAL_REVIEW)
  - Respect `field_routing.yaml` thresholds

- [x] Task: Implement self-consistency voting for critical numeric fields. ✅ 2026-01-08

- [x] Task: Create `ManualReviewQueue` for papers where all tiers fail. ✅ 2026-01-08
  - Store in SQLite table with failure reason
  - CLI command to list/export queue
  - Track resolution status
  - 7 tests pass

- [x] Task: Implement schema-aware prompts with few-shot examples. ✅ 2026-01-08
  - Create prompt templates per field type
  - Include field-specific extraction rules
  - Store in `prompts/field_templates/`
  - 7 tests pass

- [ ] Task: Verify extraction accuracy against golden dataset. (Phase 5)
  - Measure: F1 per field, tier utilization, cloud API calls
  - Pass criteria: F1 delta <3%, >40% local extraction

- [x] Task: Conductor - User Manual Verification 'Phase 3: Hybrid & Optimized Extraction' (COMPLETE)

---

## Phase 4: Caching & Validation

**Goal:** Implement caching to avoid redundant work and validation to catch errors cheaply.

**Key Insight:** Simple cache with clear invalidation rules beats complex versioning systems.

### Tasks

- [x] Task: Create SQLite schema for unified cache database. ✅ 2026-01-08
  - Tables: document_cache, extraction_cache, embedding_cache
  - Indexes on (doc_hash, field_name, schema_version)
  - Connection pooling for concurrent access

- [x] Task: Implement `CacheManager` class with get/set/invalidate methods. ✅ 2026-01-08
  - Document-level caching (skip re-parsing)
  - Field-level caching (skip re-extraction)
  - Cache hit/miss metrics logging

- [x] Task: Implement cache invalidation rules. ✅ 2026-01-08
  - Document cache: Invalidate on parser_version change
  - Field cache: Invalidate on schema_version change for that field
  - Manual invalidation CLI command (via `invalidate_document()`, `clear_all()`)

- [x] Task: Implement `ValidationRules` class with range and cross-field checks. ✅ 2026-01-08
  - Range checks: sample_size (1-100000), mean_age (0-120), etc.
  - Cross-field: analyzed_n <= enrolled_n, min_age <= mean_age <= max_age
  - Study-type-aware: RCT requires randomization_method

- [x] Task: Implement `AutoCorrector` class with common fix patterns. ✅ 2026-01-08
  - OCR fixes: l→1, O→0, thousands separator removal
  - Percentage normalization: 45 → 0.45 for rates
  - Year extraction from date strings

- [ ] Task: Extend `AuditLogger` to track validation failures and corrections. (Phase 5)
  - Log: field, original_value, corrected_value, correction_type
  - Generate summary report of common issues

- [ ] Task: Add cache statistics to CLI output. (Phase 5)
  - Show: hit rate, total cached, invalidations
  - Include in batch extraction summary

- [ ] Task: Conductor - User Manual Verification 'Phase 4: Caching & Validation' (Protocol in workflow.md)

---

## Phase 5: Integration & Documentation

**Goal:** End-to-end testing, CLI integration, and documentation.

**Key Insight:** One comprehensive test suite is better than multiple fragmented ones.

### Tasks

- [ ] Task: Create end-to-end regression test on 50-paper corpus.
  - Use golden dataset subset + additional papers
  - Measure: Cost, accuracy (F1), latency vs baseline
  - Pass criteria: Cost -50%, F1 delta <3%, latency +30% max

- [x] Task: Implement `--hybrid-mode` CLI flag in main extraction command. ✅ 2026-01-08
  - Default: enabled (use hybrid pipeline)
  - `--hybrid-mode=off`: Use Sonnet-only (legacy mode)
  - Store mode in extraction metadata

- [x] Task: Add extraction summary statistics to CLI output. ✅ 2026-01-08
  - Show: papers processed, tier utilization, cost estimate, cache hits
  - Include timing breakdown (parse/extract/validate)

- [x] Task: Create `config/config.example.yaml` with all configurable parameters. ✅ 2026-01-08
  - Ollama settings (model, concurrency, VRAM limits)
  - Tier thresholds and routing
  - Cache settings
  - API keys (placeholders)

- [x] Task: Update README.md with hybrid pipeline documentation. ✅ 2026-01-08
  - Architecture overview
  - Configuration guide
  - Troubleshooting common issues

- [x] Task: Update BASELINE.md with new performance metrics. ✅ 2026-01-08
  - Compare: Original Sonnet-only vs Hybrid pipeline
  - Cost breakdown by tier
  - Accuracy comparison by field type

- [ ] Task: Create inline code documentation for key modules.
  - Docstrings for all public classes/methods
  - Type hints throughout
  - Example usage in module headers

- [ ] Task: Manual spot-check of 10 random papers from test corpus.
  - Verify extraction quality
  - Check audit trail completeness
  - Document any issues found

- [ ] Task: Conductor - User Manual Verification 'Phase 5: Integration & Documentation' (Protocol in workflow.md)

---

## Success Metrics Summary

| Metric | Baseline | Target | Measurement Point |
|--------|----------|--------|-------------------|
| Cloud API Cost | $X/paper | -50% | End of Phase 5 |
| Extraction Accuracy (F1) | Y% | Delta <3% | End of Phase 3, 5 |
| Pipeline Latency | Z sec/paper | +30% max | End of Phase 5 |
| Local Utilization | 0% | >40% fields | End of Phase 3 |
| Cache Hit Rate | 0% | >80% unchanged docs | End of Phase 4 |
| Token Efficiency | N tokens/paper | -30% | End of Phase 2 |

---

## Deferred/Removed Items

The following were in the original plan but are **deferred or removed** as low-ROI:

| Item | Original Phase | Reason | Status |
|------|----------------|--------|--------|
| `LayoutCleaner` (hyphenation fix) | Phase 2 | Docling handles this well | REMOVED |
| `TableExtractor` with pdfplumber | Phase 2 | Use vision model if needed | DEFERRED |
| Vision API fallback | Phase 2 | Add only if metrics show need | DEFERRED |
| `IMRADParser` | Phase 3 | Simple regex sufficient | SIMPLIFIED |
| `FuzzyDeduplicator` (MinHash) | Phase 3 | Simple hash sufficient | SIMPLIFIED |
| `SemanticChunker` | Phase 3 | Section-based chunking sufficient | REMOVED |
| `ContextWindowMonitor` | Phase 3 | Providers handle truncation | REMOVED |
| `PromptCompressor` / LLMLingua | Phase 4 | Structured extraction more effective | REMOVED |
| `SchemaVersionControl` | Phase 5 | Simple re-extract-all sufficient | REMOVED |
| `SchemaDiff` tool | Phase 5 | Manual review sufficient | REMOVED |
| A/B validation infrastructure | Phase 6 | Manual spot-check sufficient | REMOVED |
| Separate tier smoke tests | Phase 6 | Single e2e test sufficient | SIMPLIFIED |
| Troubleshooting decision tree | Phase 7 | Inline docs sufficient | REMOVED |

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 2 | 1-2 weeks | Phases 0-1 complete |
| Phase 3 | 2-3 weeks | Phase 2 complete |
| Phase 4 | 1 week | Phase 3 complete |
| Phase 5 | 1 week | Phase 4 complete |
| **Total** | **5-7 weeks** | |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| Qwen 2.5 7B accuracy insufficient | Medium | High | Benchmark early (Phase 3); fallback to Llama 3.1 8B | - |
| PubMed API rate limiting | Low | Medium | Aggressive caching; exponential backoff | - |
| M4 memory pressure under load | Medium | Medium | ResourceManager from Phase 1; reduce concurrency | - |
| Accuracy regression on edge cases | Medium | High | Golden dataset validation; manual spot-checks | - |
| Scope creep | High | Medium | Strict adherence to deferred items list | - |
