# Dead Code Removal & Code Quality Fixes - Task Breakdown

**Track**: `conductor/tracks/dead_code_removal_20260111/`  
**Execution Method**: Subagent-driven development with TDD  
**Created**: 2026-01-11

---

## Phase 1: Dead Code Removal

### Core Modules
- [ ] **Task 1.1**: Delete 3 dead core modules
  - Files: `abstract_first_extractor.py`, `pubmed_fetcher.py`, `validation_rules.py`, `self_consistency.py`
  - Owner: `/senior_dev`
  
- [ ] **Task 1.2**: Archive auto_corrector.py
  - Move to `archive/` directory (may be needed in future)
  - Owner: `/senior_dev`
  
- [ ] **Task 1.3**: Add rapidfuzz to requirements.txt
  - Required for `fuzzy_deduplicator.py`
  - Owner: `/senior_dev`

### Agent Modules
- [ ] **Task 1.4**: Delete 2 unused agent modules
  - Files: `conflict_resolver.py`, `section_locator.py`
  - Note: Keeping `researcher_analysis.py` for future use
  - Owner: `/senior_dev`

### Test Files
- [ ] **Task 1.5**: Delete orphaned test file
  - File: `test_abstract_first.py`
  - Owner: `/senior_dev`

### Cleanup
- [ ] **Task 1.6**: Delete standalone scripts
  - File: `debug_openrouter_pricing.py` (if exists)
  - Owner: `/senior_dev`

- [ ] **Task 1.7**: Delete temporary directories
  - Directory: `temp_healy/`
  - Owner: `/senior_dev`

- [ ] **Task 1.8**: Clean unused imports in `hierarchical_pipeline.py`
  - Remove dead imports and instantiations
  - Owner: `/senior_dev`

- [ ] **Task 1.9**: Clean minor Vulture findings - unused imports (7 files)
  - Owner: `/senior_dev`

- [ ] **Task 1.10**: Clean unused variables
  - Replace unused `cls`, exception variables with `_`
  - Owner: `/senior_dev`

### Documentation Updates
- [ ] **Task 1.11**: Update track documentation
  - Files: `code_quality_issues.md`, `dead_code_findings.md`
  - Mark completed items, update status
  - Owner: `/docs_agent`

---

## Phase 2: Critical Regression Fix ⚠️ HIGH PRIORITY

> **Impact**: Restores 60-70% cost reduction via Tier 0 regex extraction

### RegexExtractor Integration
- [x] **Task 2.1**: Write failing tests for RegexExtractor (TDD RED)
  - Create `tests/test_regex_tier_zero.py`
  - Owner: `/senior_dev`

- [x] **Task 2.2**: Restore RegexExtractor integration (TDD GREEN)
  - Add import, initialization, Tier 0 extraction logic
  - Owner: `/senior_dev`

### TwoPassExtractor Integration
- [x] **Task 2.3**: Write failing tests for TwoPassExtractor (TDD RED)
  - Create `tests/test_two_pass_integration.py`
  - Owner: `/senior_dev`

- [x] **Task 2.4**: Verify TwoPassExtractor integration
  - Check if already present, add if missing
  - Owner: `/senior_dev`

### Extractor Enhancement
- [x] **Task 2.5**: Add `pre_filled_fields` support to StructuredExtractor
  - TDD RED: Create `tests/test_extractor_prefilled.py`
  - TDD GREEN: Implement parameter and logic
  - Owner: `/senior_dev`

---

## Phase 3: Anti-Pattern Fixes

- [x] **Task 3.1**: Centralize `os.getenv()` calls
  - Move 15+ calls to `core/config.py`
  - TDD: Create `tests/test_config_centralization.py`
  - Owner: `/senior_dev`

- [x] **Task 3.2**: Fix bare exception handling
  - Files: `core/client.py`, `core/service.py`
  - Add specific exceptions and logging
  - Owner: `/senior_dev`

- [x] **Task 3.3**: Fix async import anti-pattern
  - Move `import asyncio` to module level in `service.py`
  - Owner: `/senior_dev`

- [x] **Task 3.4**: Centralize client creation logic
  - Use `LLMClientFactory` everywhere (VERIFIED: already done)
  - Owner: `/senior_dev`

- [x] **Task 3.5**: Comprehensive config audit
  - Ensure ALL API calls, local model switching, global configs in `config.py`
  - Owner: `/senior_dev`

- [x] **Task 3.6**: Refactor `token_tracker.py` for clarity
  - Move pricing constants to `config.py`
  - Fix API pricing fetch (never hardcode, always fetch + cache)
  - Fix code smells: magic numbers, bare exceptions, ambiguous names
  - Add comprehensive type hints and documentation
  - Owner: `/refactor_standards_guardian`

---

## Phase 4: Code Smell Remediation

### Phase 4A: Extract Magic Numbers (DO FIRST)
- [x] **Task 4.0**: Extract magic numbers to config.py and constants.py
  - Create `core/constants.py` for algorithm parameters ✅
  - Add threshold/limit fields to `config.py` ✅
  - Replace magic numbers in 15+ files ✅ (9 files refactored)
  - Test after each file replacement ✅
  - Owner: `/refactor-for-clarity`

### Phase 4B: Critical Path File Splitting
- [x] **Task 4.5**: Split `hierarchical_pipeline.py` (860 lines) ✅ COMPLETE
  - Created 7 files totaling 1,163 lines
  - Eliminated 90 lines of sync/async duplication
  - Introduced dependency injection pattern
  - All files pass `/refactor-for-clarity` standards
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.6**: Split `extractor.py` (696 lines)
  - Split into: `extractors/base.py`, `extractors/evidence.py`, `extractors/retry.py`
  - Use composition pattern for sync/async
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.7**: Split `extraction_checker.py` (509 lines)
  - Split into: `validation/checker.py`, `validation/validators.py`, `validation/formatters.py`
  - Rename ambiguous variables (v → validation_score, item → field_result)
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.9**: Refactor `batch_processor.py` (280 lines) - CRITICAL PATH
  - Extract `ExecutionHandler` class with shared logic
  - Fix deep nesting (5 → 3 levels) in `_execute_single_async`
  - Eliminate sync/async duplication (composition pattern)
  - Owner: `/refactor-for-clarity`

### Phase 4C: Remaining File Splitting
- [ ] **Task 4.8**: Split `parser.py` (500 lines)
  - Split into: `parsers/base.py`, `parsers/docling.py`, `parsers/fallbacks.py`
  - Use strategy pattern
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.12**: Split `binary_deriver.py` (603 lines)
  - Split into: `binary/core.py`, `binary/rules.py`
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.13**: Split `relevance_classifier.py` (470 lines)
  - Split into: `classification/classifier.py`, `classification/helpers.py`
  - Owner: `/refactor-for-clarity`

### Phase 4D: Large Function Extraction
- [ ] **Task 4.3**: Extract `service.py::run_extraction` (226 lines)
  - Split into: setup, parsing, execution, callbacks, vectorization
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.4**: Extract `hierarchical_pipeline.py::extract_document` (200 lines)
  - Extract stage methods: filter, classify, extract, finalize
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.14**: Extract `extractor.py::extract_with_evidence` (128 lines)
  - Extract: prompt building, response parsing, validation
  - Owner: `/refactor-for-clarity`

### Phase 4E: Deep Nesting Fixes
- [ ] **Task 4.1**: Fix deep nesting in `hierarchical_pipeline.py`
  - Extract nested logic into helper methods
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.2**: Fix deep nesting in `service.py`
  - Use early returns, extract nested loops
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.15**: Fix deep nesting in `vectorizer.py`
  - Extract nested loops into `_process_batch()`
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.16**: Fix deep nesting in `extraction_checker.py`
  - Extract validation steps, use guard clauses
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.18**: Fix deep nesting in `study_classifier.py`
  - Extract conditional logic into helpers
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.10**: Fix ambiguous variable names
  - Files: `service.py`, `vectorizer.py`, `extraction_checker.py`, multiple others
  - Replace `f`, `i`, `data`, `result`, `v`, `item` with descriptive names
  - Owner: `/refactor-for-clarity`

### Phase 4F: Additional File Refactoring (LOW PRIORITY - defer)
- [ ] **Task 4.22**: Split `cache_manager.py` (419 lines) (DEFERRED)
  - Split into: `cache/manager.py`, `cache/models.py`, `cache/constants.py`
  - Condition: Only if modifying cache schema
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.23**: Extract large function in `client.py` (DEFERRED)
  - Split `restart_service` (45 lines) into platform-specific methods
  - Condition: Only if adding new LLM providers
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.24**: Eliminate client creation duplication in `client.py` (DEFERRED)
  - Extract common client creation pattern
  - Condition: Only if changing providers
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.25**: Fix ambiguous variable names in additional files (LOW)
  - `cache_manager.py`: `row` → `cache_row` / `field_row`
  - Do alongside other refactors, not in isolation
  - Owner: `/refactor-for-clarity`

- [ ] **Task 4.26**: Extract remaining magic numbers (LOW)
  - `client.py`: `2.0` → `constants.OLLAMA_HEALTH_CHECK_TIMEOUT`
  - Add to constants.py during Phase 4A cleanup
  - Owner: `/refactor-for-clarity`

---

## Phase 5: Hardcoded Values

- [ ] **Task 5.1**: Define magic number constants
  - Files: `client.py`, `service.py`, `hierarchical_pipeline.py`
  - Owner: `/senior_dev`

- [ ] **Task 5.2**: Centralize path configuration
  - Use `settings.LOG_DIR`, `settings.VECTOR_DIR`
  - Owner: `/senior_dev`

- [ ] **Task 5.3**: Centralize API endpoints
  - Remove duplicate hardcoded URLs
  - Owner: `/senior_dev`

---

## Phase 6: Minor Issues

- [ ] **Task 6.1**: Add missing docstrings
  - Files: `config.py`, `client.py`
  - Owner: `/docs_agent`

- [ ] **Task 6.2**: Complete type hints
  - Files: `client.py`, `service.py`
  - Owner: `/senior_dev`

- [ ] **Task 6.3**: Remove or fix TODO/FIXME comments
  - Address TODOs in `two_pass_extractor.py`
  - Owner: `/senior_dev`

---

## Phase 7: Vulture Findings Cleanup

- [ ] **Task 7.1**: Final Vulture scan
  - Run Vulture after all changes
  - Document remaining findings
  - Owner: `/senior_dev`

---

## Verification & Documentation

- [ ] **Final Verification**: Run full test suite
  - Command: `pytest tests/ -v --tb=short`
  - Owner: `/qa_agent`

- [ ] **Update Documentation**
  - Update CHANGELOG.md
  - Update `code_quality_issues.md` (mark fixed items)
  - Update `dead_code_findings.md` (mark deleted items)
  - Update `subagent_execution_plan.md` (check completed tasks)
  - Update CODE_MAP.md (if exists)
  - Owner: `/docs_agent`

---

## New Feature Implementation

- [ ] **Task 8.1**: Implement ComplexityClassifier integration
  - Integrate into parsing pipeline
  - TDD approach required
  - Owner: `/senior_dev`

- [ ] **Task 8.2**: Implement FuzzyDeduplicator integration
  - Integrate into chunking pipeline
  - Ensure rapidfuzz is installed
  - TDD approach required
  - Owner: `/senior_dev`

---

## Summary

**Total Tasks**: 45+  
**Estimated LOC Removed**: ~2,500+  
**Estimated LOC Refactored**: ~2,000+  
**Estimated LOC Added**: ~500+ (new features)  
**Critical Priority**: Phase 2 (Regression Fix)
