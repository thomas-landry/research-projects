# Dead Code Findings Log

**Last Updated**: 2026-01-11 14:35  
**Status**: Verified

---

## Confirmed Dead Code

### Core Extractors (Legacy)
| File | Size | Reason | Action |
|------|------|--------|--------|
| `core/abstract_first_extractor.py` | 14.5KB | Imported in `hierarchical_pipeline.py:29`. Instantiated as `self.abstract_extractor` (line 129) but **never called**. | **DELETE** ✅ |
| `core/two_pass_extractor.py` | 22.3KB | Imported in `hierarchical_pipeline.py:31`. Instantiated as `self.two_pass_extractor` (line 140) but **never called**. | **DELETE** ✅ |
| `core/pubmed_fetcher.py` | 11.8KB | Only used by `abstract_first_extractor.py` (dead code). Also instantiated in `hierarchical_pipeline.py:130` but **never called**. | **DELETE** ✅ |
| ~~`core/regex_extractor.py`~~ | 9.5KB | **ACTIVELY USED** - Called in `hierarchical_pipeline.py:387`. Part of Tier 0 extraction (pipeline optimization). | **KEEP** ❌ |

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

**Total Dead Files**: 8 (was 9, corrected after verification)  
**Total Dead Code (LOC)**: ~3,200+ lines (corrected)  
**Unused Imports**: 12+  
**Unused Variables**: 10+

**Files to Delete**:
1. `core/abstract_first_extractor.py` (14.5KB)
2. `core/two_pass_extractor.py` (22.3KB)
3. `core/pubmed_fetcher.py` (11.8KB)
4. `tests/test_abstract_first.py`
5. `tests/test_two_pass_gemini.py`
6. `tests/test_two_pass_premium.py`
7. `agents/researcher_analysis.py`
8. `debug_openrouter_pricing.py`

**Correction Note**: `regex_extractor.py` and `test_regex_integration.py` are **ACTIVE CODE** (used in Tier 0 extraction), not dead code.
