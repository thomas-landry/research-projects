# Dead Code Findings Log

**Last Updated**: 2026-01-11 14:48  
**Status**: Verified + Regression Found

---

## 🔴 CRITICAL REGRESSION DISCOVERED

**Integration Code Deleted**: Between commits c45ec9e → HEAD (cleanup commits c86a233/a420b5e)

| Component | Status | Tests | Integration | Action |
|-----------|--------|-------|-------------|--------|
| `regex_extractor.py` | ✅ Working | 12/12 passing | ❌ **DELETED** | **RESTORE** integration |
| `two_pass_extractor.py` | ✅ Working | 6/6 passing | ❌ **DELETED** | **RESTORE** integration |

**What was deleted**:
- Line 32: `from .regex_extractor import RegexExtractor, RegexResult`
- Lines 153-155: RegexExtractor initialization
- Line 387+: Tier 0 extraction logic
- Integration code that calls the extractors

**Impact**: Pipeline optimization (60-70% cost reduction) is NOT active despite working code.

**Recovery**: Can restore from commit c45ec9e

---

## Confirmed Dead Code

### Core Extractors - Status Update

| File | Size | Tests | Integration | Action |
|------|------|-------|-------------|--------|
| `core/abstract_first_extractor.py` | 14.5KB | 6/8 passing | ❌ Never integrated | **DELETE** ✅ |
| `core/pubmed_fetcher.py` | 11.8KB | N/A | ❌ Only used by abstract_first | **DELETE** ✅ |
| ~~`core/two_pass_extractor.py`~~ | 22.3KB | ✅ 6/6 passing | ❌ **Integration deleted** | **RESTORE** then KEEP |
| ~~`core/regex_extractor.py`~~ | 9.5KB | ✅ 12/12 passing | ❌ **Integration deleted** | **RESTORE** then KEEP |

### Additional Unused Core Modules

| File | Size | Usage | Action |
|------|------|-------|--------|
| `core/auto_corrector.py` | 6.2KB | ❌ No imports found | **DELETE** ✅ |
| `core/validation_rules.py` | 7.6KB | ❌ No imports found | **DELETE** ✅ |
| `core/self_consistency.py` | 9.2KB | ❌ No imports found | **DELETE** ✅ |
| `core/complexity_classifier.py` | 7.4KB | ⚠️ Test-only (`verify_phase2_integration.py`) | **REVIEW** - Keep if future feature |
| `core/fuzzy_deduplicator.py` | 4.4KB | ⚠️ Test-only (`verify_phase3_integration.py`) | **REVIEW** - Keep if future feature |

### Agents Directory - Unused Modules

| File | Size | Usage | Action |
|------|------|-------|--------|
| `agents/researcher_analysis.py` | 79 lines | ❌ No imports found (standalone script) | **DELETE** ✅ |
| `agents/conflict_resolver.py` | 113 lines | ⚠️ Imported in hierarchical_pipeline.py but **never used** | **DELETE** ✅ |
| `agents/section_locator.py` | 92 lines | ⚠️ Imported in hierarchical_pipeline.py but **never used** | **DELETE** ✅ |

**Note**: `meta_analyst.py` IS used (hierarchical_pipeline.py:792) - KEEP ✅

### Associated Test Files
| File | Reason | Action |
|------|--------|--------|
| `tests/test_abstract_first.py` | Tests dead code (`abstract_first_extractor.py`) | **DELETE** ✅ |
| `tests/test_two_pass_gemini.py` | Tests dead code (`two_pass_extractor.py`) | **DELETE** ✅ |
| `tests/test_two_pass_premium.py` | Tests dead code (`two_pass_extractor.py`) | **DELETE** ✅ |
| ~~`tests/test_regex_integration.py`~~ | Tests **ACTIVE CODE** (`regex_extractor.py`) | **KEEP** ❌ |

### Standalone Scripts
| File | Reason | Action |
|------|--------|--------|
| `agents/researcher_analysis.py` | Standalone CLI script, never imported | DELETE or MOVE to scripts/ |
| `debug_openrouter_pricing.py` | One-time debug utility | DELETE |

### Temporary Directories
| Directory | Contents | Action |
|-----------|----------|--------|
| `temp_healy/` | Single test PDF | DELETE |

---

## Unused Imports (hierarchical_pipeline.py)

**Lines to remove**:
- Line 25: `ExtractionLog`, `ExtractionWarning` (from `core.data_types`)
- Line 29: `AbstractFirstExtractor`, `AbstractExtractionResult`
- Line 30: `PubMedFetcher`
- Line 31: `TwoPassExtractor`, `ModelCascader`, `ExtractionTier`
- Line 41: `ConflictResolverAgent` (if unused)
- Line 42: `SectionLocatorAgent` (if unused)

**Instantiations to remove**:
- Lines 129: `self.abstract_extractor = AbstractFirstExtractor()`
- Lines 130: `self.pubmed_fetcher = PubMedFetcher()`
- Lines 140-143: `self.two_pass_extractor = TwoPassExtractor(...)`

---

## Minor Vulture Findings

### Unused Imports
- `core/cache_manager.py:21` - `contextmanager`
- `core/parser.py:16` - `BeautifulSoup`
- `core/relevance_classifier.py:13` - `ValidationInfo`
- `core/schema_builder.py:9` - `get_type_hints`
- `benchmarks/llm_ie_benchmark.py:26` - `LLMInformationExtractionDocument`
- `tests/test_phase4_components.py:11` - `CacheEntry`
- `tests/test_data_loss_diagnostic.py:17` - `FlexibleFlag`

### Unused Variables
- Multiple `cls` parameters in `@classmethod` decorators (can replace with `_`)
- Exception tuple unpacking (`exc_type`, `exc_val`, `exc_tb`) in except blocks
- Test fixtures: `clean_state` in `test_bug_fix_03.py`, `MockMeta` in `verify_pipeline_integration.py`

---

## Summary

**Total Dead Files**: 14 (was 11, updated after agents/ scan)  
**Total Dead Code (LOC)**: ~4,200+ lines  
**Unused Imports**: 15+  
**Unused Variables**: 10+

**Files to Delete**:
1. `core/abstract_first_extractor.py` (14.5KB)
2. `core/pubmed_fetcher.py` (11.8KB)
3. `core/auto_corrector.py` (6.2KB)
4. `core/validation_rules.py` (7.6KB)
5. `core/self_consistency.py` (9.2KB)
6. `agents/researcher_analysis.py` (79 lines) - NEW
7. `agents/conflict_resolver.py` (113 lines) - NEW
8. `agents/section_locator.py` (92 lines) - NEW
9. `tests/test_abstract_first.py`
10. `tests/test_two_pass_gemini.py`
11. `tests/test_two_pass_premium.py`
12. `debug_openrouter_pricing.py`
13. `temp_healy/` directory

**Files to Restore Integration**:
- `core/regex_extractor.py` (integration deleted, needs restore)
- `core/two_pass_extractor.py` (integration deleted, needs restore)

**Files to Review** (test-only usage):
- `core/complexity_classifier.py` - Keep if future feature
- `core/fuzzy_deduplicator.py` - Keep if future feature
