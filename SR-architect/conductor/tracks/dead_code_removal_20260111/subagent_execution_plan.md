# Complete Subagent Execution Plan - Code Cleanup & Quality Fixes

**Created**: 2026-01-11
**Track**: dead_code_removal_20260111
**Execution Method**: subagent-driven-development
**TDD Required**: YES - All implementation tasks follow test-driven-development

---

## Table of Contents

1. [Phase 1: Dead Code Removal](#phase-1-dead-code-removal)
2. [Phase 2: Critical Regression Fix](#phase-2-critical-regression-fix)
3. [Phase 3: Anti-Pattern Fixes](#phase-3-anti-pattern-fixes)
4. [Phase 4: Code Smell Remediation](#phase-4-code-smell-remediation)
5. [Phase 5: Hardcoded Values](#phase-5-hardcoded-values)
6. [Phase 6: Minor Issues](#phase-6-minor-issues)
7. [Phase 7: Vulture Findings Cleanup](#phase-7-vulture-findings-cleanup)

---

# Phase 1: Dead Code Removal

> [!NOTE]
> These tasks delete unused code. Verify no imports break before committing.

## Task 1.1: Delete Dead Core Modules (5 files)

**Source**: dead_code_findings.md lines 35-46

**Files to Delete**:
| File | Size | Reason |
|------|------|--------|
| `core/abstract_first_extractor.py` | 14.5KB | Never integrated |
| `core/pubmed_fetcher.py` | 11.8KB | Only used by abstract_first |
| `core/auto_corrector.py` | 6.2KB | No imports found |
| `core/validation_rules.py` | 7.6KB | No imports found |
| `core/self_consistency.py` | 9.2KB | No imports found |

**Steps**:
```bash
# 1. Verify no production imports
grep -r "abstract_first_extractor\|pubmed_fetcher\|auto_corrector\|validation_rules\|self_consistency" \
  --include="*.py" . | grep -v "test_" | grep -v ".pyc" | grep -v "__pycache__"

# 2. Delete files
git rm core/abstract_first_extractor.py
git rm core/pubmed_fetcher.py
git rm core/auto_corrector.py
git rm core/validation_rules.py
git rm core/self_consistency.py

# 3. Verify tests pass
pytest tests/ -v --tb=short -x

# 4. Commit
git commit -m "chore: Delete 5 unused core modules (~3,600 LOC)"
```

**Acceptance Criteria**:
- [ ] All 5 files deleted
- [ ] No `ImportError` when running tests
- [ ] All existing tests still pass

**Rollback**: `git checkout HEAD -- core/abstract_first_extractor.py core/pubmed_fetcher.py core/auto_corrector.py core/validation_rules.py core/self_consistency.py`

---

## Task 1.2: Review Test-Only Core Modules (2 files)

**Source**: dead_code_findings.md lines 47-48

**Files to Review**:
| File | Size | Usage | Decision Needed |
|------|------|-------|-----------------|
| `core/complexity_classifier.py` | 7.4KB | Only in `verify_phase2_integration.py` | Keep for Phase 2? |
| `core/fuzzy_deduplicator.py` | 4.4KB | Only in `verify_phase3_integration.py` | Keep for Phase 3? |

**Steps**:
```bash
# 1. Check if verify scripts are still needed
ls -la tests/verify_phase*.py

# 2. If scripts are dead, delete all together
# Otherwise, document as "future feature"
```

**Acceptance Criteria**:
- [ ] Decision documented (KEEP or DELETE)
- [ ] If DELETE: files removed and tests pass
- [ ] If KEEP: Add TODO comment explaining future use

---

## Task 1.3: Delete Dead Agent Modules (3 files)

**Source**: dead_code_findings.md lines 50-57

**Files to Delete**:
| File | Lines | Reason |
|------|-------|--------|
| `agents/researcher_analysis.py` | 79 | Standalone script, never imported |
| `agents/conflict_resolver.py` | 113 | Imported but never used |
| `agents/section_locator.py` | 92 | Imported but never used |

**Steps**:
```bash
# 1. Verify usage (should show only hierarchical_pipeline.py imports)
grep -r "conflict_resolver\|section_locator\|researcher_analysis" \
  --include="*.py" . | grep -v "test_"

# 2. Remove imports from hierarchical_pipeline.py (lines 38-39)
# Edit: Remove lines containing ConflictResolverAgent, SectionLocatorAgent

# 3. Delete files
git rm agents/researcher_analysis.py
git rm agents/conflict_resolver.py
git rm agents/section_locator.py

# 4. Verify
pytest tests/ -v --tb=short -x

# 5. Commit
git commit -m "chore: Delete 3 unused agent modules"
```

**Acceptance Criteria**:
- [ ] All 3 agent files deleted
- [ ] Imports removed from hierarchical_pipeline.py
- [ ] All tests pass

---

## Task 1.4: Delete Dead Test Files (3 files)

**Source**: dead_code_findings.md lines 60-66

**Files to Delete**:
| File | Reason |
|------|--------|
| `tests/test_abstract_first.py` | Tests deleted abstract_first_extractor.py |
| `tests/test_two_pass_gemini.py` | Tests dead code |
| `tests/test_two_pass_premium.py` | Tests dead code |

**Steps**:
```bash
# 1. Verify these test dead code
head -20 tests/test_abstract_first.py
head -20 tests/test_two_pass_gemini.py
head -20 tests/test_two_pass_premium.py

# 2. Delete
git rm tests/test_abstract_first.py
git rm tests/test_two_pass_gemini.py
git rm tests/test_two_pass_premium.py

# 3. Verify test collection works
pytest tests/ --collect-only

# 4. Commit
git commit -m "chore: Delete 3 orphaned test files"
```

**Acceptance Criteria**:
- [ ] All 3 test files deleted
- [ ] Test collection still works
- [ ] Active test count unchanged

---

## Task 1.5: Delete Standalone Scripts (2 files)

**Source**: dead_code_findings.md lines 68-72

**Files to Delete**:
| File | Reason |
|------|--------|
| `agents/researcher_analysis.py` | Already covered in Task 1.3 |
| `debug_openrouter_pricing.py` | One-time debug utility (may already be deleted) |

**Steps**:
```bash
# 1. Check if debug file exists
ls -la debug_openrouter_pricing.py

# 2. If exists, delete
git rm debug_openrouter_pricing.py 2>/dev/null || echo "Already deleted"

# 3. Commit if needed
git commit -m "chore: Remove debug utility script" || echo "Nothing to commit"
```

**Acceptance Criteria**:
- [ ] File deleted or confirmed already deleted
- [ ] No broken references

---

## Task 1.6: Delete Temporary Directories

**Source**: dead_code_findings.md lines 74-77

**Directories to Delete**:
```
temp_healy/
```

**Steps**:
```bash
# 1. Verify contents
ls -la temp_healy/

# 2. Delete
rm -rf temp_healy/

# 3. Commit
git add -A && git commit -m "chore: Remove temporary test directory"
```

**Acceptance Criteria**:
- [ ] Directory removed
- [ ] No broken file references

---

## Task 1.7: Clean Unused Imports in hierarchical_pipeline.py

**Source**: dead_code_findings.md lines 81-94

**Imports to Remove**:
| Line | Import | Reason |
|------|--------|--------|
| 25 | `ExtractionLog`, `ExtractionWarning` | Never used |
| 29 | `AbstractFirstExtractor`, `AbstractExtractionResult` | Module deleted |
| 30 | `PubMedFetcher` | Module deleted |
| 31 | `TwoPassExtractor`, `ModelCascader`, `ExtractionTier` | Will restore in Phase 2 |
| 38 | `ConflictResolverAgent` | Never used |
| 39 | `SectionLocatorAgent` | Never used |

**Instantiations to Remove**:
| Lines | Code | Reason |
|-------|------|--------|
| 125 | `self.abstract_extractor = AbstractFirstExtractor()` | Module deleted |
| 126 | `self.pubmed_fetcher = PubMedFetcher()` | Module deleted |

**Steps**:
```bash
# 1. View current imports
head -50 core/hierarchical_pipeline.py

# 2. Edit file to remove dead imports
# Keep TwoPassExtractor imports (will restore in Phase 2)
# Remove: ExtractionLog, ExtractionWarning, AbstractFirstExtractor, 
#         AbstractExtractionResult, PubMedFetcher, ConflictResolverAgent, SectionLocatorAgent

# 3. Remove dead instantiations in __init__ (around lines 125-126)

# 4. Verify
python -c "from core.hierarchical_pipeline import HierarchicalExtractionPipeline; print('OK')"
pytest tests/ -v --tb=short -x

# 5. Commit
git commit -m "refactor: Remove unused imports from hierarchical_pipeline"
```

**Acceptance Criteria**:
- [ ] Dead imports removed
- [ ] Dead instantiations removed
- [ ] Module still imports correctly
- [ ] All tests pass

---

## Task 1.8: Clean Minor Vulture Findings - Unused Imports

**Source**: dead_code_findings.md lines 98-107

**Unused Imports to Remove**:
| File | Line | Import |
|------|------|--------|
| `core/cache_manager.py` | 21 | `contextmanager` |
| `core/parser.py` | 16 | `BeautifulSoup` |
| `core/relevance_classifier.py` | 13 | `ValidationInfo` |
| `core/schema_builder.py` | 9 | `get_type_hints` |
| `benchmarks/llm_ie_benchmark.py` | 26 | `LLMInformationExtractionDocument` |
| `tests/test_phase4_components.py` | 11 | `CacheEntry` |
| `tests/test_data_loss_diagnostic.py` | 17 | `FlexibleFlag` |

**Steps for each file**:
```bash
# For each file:
# 1. View the import line
# 2. Verify import is unused: grep for the imported name in the file
# 3. Remove the import
# 4. Run tests for that module

# Example for cache_manager.py:
grep "contextmanager" core/cache_manager.py
# If only appears on import line, remove it
# Edit file, remove unused import
pytest tests/ -k "cache" -v
```

**Acceptance Criteria**:
- [ ] All 7 unused imports removed
- [ ] Each file still works
- [ ] No test failures

---

## Task 1.9: Clean Unused Variables

**Source**: dead_code_findings.md lines 109-112

**Unused Variables**:
| Issue | Location | Fix |
|-------|----------|-----|
| Unused `cls` in `@classmethod` | Multiple files | Replace with `_` |
| Unused exception unpacking | `exc_type`, `exc_val`, `exc_tb` | Replace with `_`, `_`, `_` or use `except Exception:` |
| Unused test fixtures | `clean_state`, `MockMeta` | Remove or use |

**Steps**:
```bash
# 1. Find all unused cls parameters
grep -rn "@classmethod" --include="*.py" -A1 . | grep "def.*cls"

# 2. For each, check if cls is used in the method
# If not, replace cls with _

# 3. Find unused exception variables
grep -rn "except.*as.*:" --include="*.py" .

# 4. Replace unused ones with _

# 5. Run tests
pytest tests/ -v
```

**Acceptance Criteria**:
- [ ] No warnings about unused variables
- [ ] All tests pass

---

# Phase 2: Critical Regression Fix

> [!IMPORTANT]
> **Priority**: This phase restores deleted integration code that provides 60-70% cost reduction.

## Task 2.1: Write Failing Tests for RegexExtractor Integration

**Source**: dead_code_findings.md lines 8-26

**TDD RED Phase**:

Create `tests/test_regex_tier_zero.py`:
```python
"""Tests for Tier 0 RegexExtractor integration in pipeline."""
import pytest
from core.hierarchical_pipeline import HierarchicalExtractionPipeline


class TestRegexIntegration:
    """Test RegexExtractor is properly integrated."""
    
    def test_pipeline_has_regex_extractor(self):
        """Verify RegexExtractor is initialized in pipeline."""
        pipeline = HierarchicalExtractionPipeline()
        assert hasattr(pipeline, 'regex_extractor'), "Pipeline missing regex_extractor"
        assert pipeline.regex_extractor is not None

    def test_regex_extractor_is_correct_type(self):
        """Verify regex_extractor is the right class."""
        from core.regex_extractor import RegexExtractor
        pipeline = HierarchicalExtractionPipeline()
        assert isinstance(pipeline.regex_extractor, RegexExtractor)

    def test_doi_extracted_via_regex(self):
        """Verify DOI is extracted via regex before LLM."""
        pipeline = HierarchicalExtractionPipeline()
        text = "This paper has DOI: 10.1234/test.2024.example"
        
        # Extract using regex
        results = pipeline.regex_extractor.extract_all(text)
        
        assert "doi" in results
        assert "10.1234/test.2024.example" in results["doi"].value

    def test_publication_year_extracted_via_regex(self):
        """Verify publication year is extracted via regex."""
        pipeline = HierarchicalExtractionPipeline()
        text = "Published: 2024. Copyright 2024."
        
        results = pipeline.regex_extractor.extract_all(text)
        
        assert "publication_year" in results
        assert results["publication_year"].value == "2024"

    def test_regex_results_passed_to_extractor(self):
        """Verify regex results are passed to LLM extractor."""
        # This tests the integration point
        pipeline = HierarchicalExtractionPipeline()
        assert hasattr(pipeline.extractor, 'extract_with_evidence')
        # Further integration testing requires mocking
```

**Steps**:
```bash
# 1. Create test file
# 2. Run tests - should fail
pytest tests/test_regex_tier_zero.py -v
# Expected: FAILED (no regex_extractor attribute)

# 3. Commit failing test
git add tests/test_regex_tier_zero.py
git commit -m "test: Add failing tests for RegexExtractor integration (TDD RED)"
```

**Acceptance Criteria**:
- [ ] Test file created
- [ ] Tests fail for expected reason (missing regex_extractor)
- [ ] Failing test committed

---

## Task 2.2: Restore RegexExtractor Integration

**TDD GREEN Phase**:

**Changes to `core/hierarchical_pipeline.py`**:

1. **Add Import** (around line 32):
```python
from .regex_extractor import RegexExtractor, RegexResult
```

2. **Add Initialization** (in `__init__`, around line 135):
```python
# Initialize Tier 0 regex extractor
self.regex_extractor = RegexExtractor()
```

3. **Add Tier 0 Extraction** (in `extract_document`, before LLM call, around line 325):
```python
# === Tier 0: Regex Extraction ===
self.logger.info("Tier 0: Regex extraction for structured fields...")
regex_results = self.regex_extractor.extract_all(context)
pre_filled_fields = {}
for field_name, result in regex_results.items():
    if result.confidence >= 0.90:  # High confidence threshold
        pre_filled_fields[field_name] = result.value
        self.logger.info(f"  Regex extracted {field_name}: {result.value} (conf={result.confidence:.2f})")

if pre_filled_fields:
    self.logger.info(f"  Tier 0 extracted {len(pre_filled_fields)} fields via regex")
```

4. **Merge Regex Results** (after LLM extraction, in result building):
```python
# Merge regex-extracted fields (they take precedence)
final_data = best_result.data.copy()
for field_name, value in pre_filled_fields.items():
    if field_name not in final_data or final_data[field_name] is None:
        final_data[field_name] = value
```

**Steps**:
```bash
# 1. Make the changes above
# 2. Run tests - should pass now
pytest tests/test_regex_tier_zero.py -v
# Expected: PASSED

# 3. Run full test suite
pytest tests/ -v --tb=short

# 4. Commit
git commit -m "feat: Restore RegexExtractor integration (TDD GREEN)"
```

**Acceptance Criteria**:
- [ ] Import added
- [ ] Initialization added
- [ ] Tier 0 extraction logic added
- [ ] Merge logic added
- [ ] All tests pass

---

## Task 2.3: Write Failing Tests for TwoPassExtractor Integration

**TDD RED Phase**:

Create `tests/test_two_pass_integration.py`:
```python
"""Tests for TwoPassExtractor integration in pipeline."""
import pytest
from core.hierarchical_pipeline import HierarchicalExtractionPipeline


class TestTwoPassIntegration:
    """Test TwoPassExtractor integration."""
    
    def test_pipeline_has_two_pass_extractor(self):
        """Verify TwoPassExtractor is initialized."""
        pipeline = HierarchicalExtractionPipeline()
        assert hasattr(pipeline, 'two_pass_extractor')
        assert pipeline.two_pass_extractor is not None

    def test_two_pass_extractor_is_correct_type(self):
        """Verify two_pass_extractor is the right class."""
        from core.two_pass_extractor import TwoPassExtractor
        pipeline = HierarchicalExtractionPipeline()
        assert isinstance(pipeline.two_pass_extractor, TwoPassExtractor)

    def test_hybrid_mode_toggleable(self):
        """Verify hybrid mode can be enabled/disabled."""
        pipeline = HierarchicalExtractionPipeline()
        assert hasattr(pipeline, 'hybrid_mode')
        assert hasattr(pipeline, 'set_hybrid_mode')
        
        pipeline.set_hybrid_mode(True)
        assert pipeline.hybrid_mode == True
        
        pipeline.set_hybrid_mode(False)
        assert pipeline.hybrid_mode == False
```

**Steps**:
```bash
# 1. Create test file
# 2. Run tests
pytest tests/test_two_pass_integration.py -v

# 3. Commit
git add tests/test_two_pass_integration.py
git commit -m "test: Add failing tests for TwoPassExtractor integration (TDD RED)"
```

---

## Task 2.4: Verify TwoPassExtractor Integration (Already Present)

Review `core/hierarchical_pipeline.py` - TwoPassExtractor may already be imported and initialized (lines 129-133). If so, verify it works:

```bash
# Verify imports exist
grep "TwoPassExtractor" core/hierarchical_pipeline.py

# Verify initialization exists  
grep "two_pass_extractor" core/hierarchical_pipeline.py

# Run tests
pytest tests/test_two_pass_integration.py -v
```

**Acceptance Criteria**:
- [ ] TwoPassExtractor imported
- [ ] Instance created in `__init__`
- [ ] `hybrid_mode` attribute exists
- [ ] `set_hybrid_mode()` method exists
- [ ] All tests pass

---

## Task 2.5: Add pre_filled_fields Support to StructuredExtractor

**TDD RED Phase**:

Create `tests/test_extractor_prefilled.py`:
```python
"""Tests for pre-filled fields support in StructuredExtractor."""
import pytest
from core.extractor import StructuredExtractor


class TestPrefilledFields:
    """Test pre-filled fields functionality."""
    
    def test_extract_with_evidence_accepts_prefilled(self):
        """Verify method accepts pre_filled_fields parameter."""
        import inspect
        sig = inspect.signature(StructuredExtractor.extract_with_evidence)
        assert 'pre_filled_fields' in sig.parameters

    def test_prefilled_fields_in_prompt(self):
        """Verify pre-filled fields are mentioned in LLM prompt."""
        # This requires mocking the LLM call
        pass  # TODO: Implement with mock

    def test_prefilled_fields_preserved_in_output(self):
        """Verify pre-filled fields appear in extraction result."""
        # This requires mocking the LLM call
        pass  # TODO: Implement with mock
```

**TDD GREEN Phase**:

Add to `core/extractor.py` `extract_with_evidence` method:

```python
def extract_with_evidence(
    self,
    text: str,
    schema: Type[T],
    filename: Optional[str] = None,
    revision_prompts: Optional[List[str]] = None,
    pre_filled_fields: Optional[Dict[str, Any]] = None,  # NEW PARAMETER
) -> ExtractionWithEvidence:
    """
    Extract structured data with self-proving evidence citations.
    
    Args:
        text: Document text to extract from
        schema: Pydantic model class defining extraction schema
        filename: Source filename for metadata
        revision_prompts: Optional feedback from checker for corrections
        pre_filled_fields: Fields pre-extracted via regex (Tier 0)
    """
    # Build the user message
    user_content = f"Extract data from the following academic paper text:\n\n{text}"
    
    # Add pre-filled fields to prompt
    if pre_filled_fields:
        prefilled_text = "\n".join(f"- {k}: {v}" for k, v in pre_filled_fields.items())
        user_content += f"\n\n--- PRE-EXTRACTED FIELDS ---\nThe following fields have been pre-extracted with high confidence. Do not re-extract these unless you find conflicting information:\n{prefilled_text}"
    
    # ... rest of method ...
    
    # At the end, merge pre_filled_fields into result
    if pre_filled_fields:
        for field, value in pre_filled_fields.items():
            if field not in data_dict or data_dict[field] is None:
                data_dict[field] = value
```

**Acceptance Criteria**:
- [ ] New parameter added
- [ ] Pre-filled fields mentioned in prompt
- [ ] Pre-filled fields merged into output
- [ ] Tests pass

---

# Phase 3: Anti-Pattern Fixes

## Task 3.1: Centralize os.getenv() Calls

**Source**: code_quality_issues.md line 28

**Issue**: 15+ locations use `os.getenv()` directly instead of centralized settings.

**TDD RED Phase**:
```python
# tests/test_config_centralization.py
import subprocess
import pytest


def test_no_direct_getenv_in_core():
    """Verify core/ files don't use os.getenv directly (except config.py)."""
    result = subprocess.run(
        ["grep", "-r", "os.getenv", "core/", "--include=*.py", "-l"],
        capture_output=True, text=True
    )
    files_with_getenv = [f for f in result.stdout.strip().split('\n') if f]
    
    # Only config.py should have os.getenv
    non_config = [f for f in files_with_getenv if 'config.py' not in f]
    assert len(non_config) == 0, f"Found os.getenv outside config.py: {non_config}"


def test_no_direct_getenv_in_agents():
    """Verify agents/ files don't use os.getenv directly."""
    result = subprocess.run(
        ["grep", "-r", "os.getenv", "agents/", "--include=*.py", "-l"],
        capture_output=True, text=True
    )
    files = [f for f in result.stdout.strip().split('\n') if f]
    assert len(files) == 0, f"Found os.getenv in agents/: {files}"
```

**TDD GREEN Phase**:

1. **Add settings to `core/config.py`**:
```python
# API Keys
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# Model Defaults
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-20250514")

# Endpoints
OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Feature Flags
HYBRID_MODE: bool = os.getenv("HYBRID_MODE", "true").lower() == "true"
```

2. **Replace usages** in each file:
   - `core/extractor.py` lines 95, 102-104
   - `core/client.py` lines 188, 222
   - All files in `agents/`

**Acceptance Criteria**:
- [ ] All settings centralized in config.py
- [ ] No os.getenv calls outside config.py
- [ ] Tests pass

---

## Task 3.2: Fix Bare Exception Handling

**Source**: code_quality_issues.md lines 19-23

**Issue**: Bare `except Exception` swallows errors.

**Files**:
| File | Line | Issue |
|------|------|-------|
| `core/client.py` | 31-33 | Bare `except Exception` |
| `core/service.py` | 96-105 | Nested try-except |

**TDD RED Phase**:
```python
# tests/test_exception_handling.py
import logging
import pytest


def test_client_logs_connection_errors(caplog):
    """Verify connection errors are logged, not silently swallowed."""
    from core.client import check_ollama_health
    
    with caplog.at_level(logging.WARNING):
        # Force a connection error (invalid host)
        result = check_ollama_health(host="http://invalid.local:11434")
    
    assert result == False
    assert len(caplog.records) > 0, "Error should be logged"
```

**TDD GREEN Phase**:

Fix `core/client.py` lines 31-33:
```python
# Before
except Exception:
    return False

# After
except (ConnectionError, TimeoutError, OSError) as e:
    logger.warning(f"Ollama health check failed: {type(e).__name__}: {e}")
    return False
except Exception as e:
    logger.error(f"Unexpected error in Ollama health check: {e}")
    return False
```

**Acceptance Criteria**:
- [ ] Specific exceptions caught
- [ ] Errors logged with context
- [ ] Tests pass

---

## Task 3.3: Fix Async Import Anti-Pattern

**Source**: code_quality_issues.md line 29

**Issue**: `import asyncio` inside functions (lines 96, 304, 351, 361 in service.py)

**Fix**: Move `import asyncio` to top of file.

**Steps**:
```bash
# 1. View current usage
grep -n "import asyncio" core/service.py

# 2. Add import at top of file (line ~10)
# 3. Remove inline imports

# 4. Verify
python -c "from core.service import ExtractionService; print('OK')"
pytest tests/ -k "service" -v
```

**Acceptance Criteria**:
- [ ] `import asyncio` at module level only
- [ ] No inline asyncio imports
- [ ] Tests pass

---

## Task 3.4: Centralize Client Creation Logic

**Source**: code_quality_issues.md line 30

**Issue**: Client creation duplicated across `extractor.py`, `sentence_extractor.py`, `relevance_classifier.py`.

**TDD RED Phase**:
```python
# tests/test_client_factory.py
def test_llm_client_factory_exists():
    """Verify centralized client factory exists."""
    from core.client import LLMClientFactory
    assert hasattr(LLMClientFactory, 'create')

def test_client_factory_returns_correct_type():
    """Verify factory returns instructor-patched client."""
    from core.client import LLMClientFactory
    client = LLMClientFactory.create(provider="openrouter")
    assert hasattr(client.chat.completions, 'create')
```

**TDD GREEN Phase**:

Add to `core/client.py`:
```python
class LLMClientFactory:
    """Centralized factory for creating LLM clients."""
    
    @staticmethod
    def create(
        provider: str = "openrouter",
        api_key: Optional[str] = None,
        **kwargs
    ):
        """Create an instructor-patched LLM client."""
        return get_llm_client(provider=provider, api_key=api_key, **kwargs)
    
    @staticmethod
    def create_async(
        provider: str = "openrouter",
        api_key: Optional[str] = None,
        **kwargs
    ):
        """Create an async instructor-patched LLM client."""
        return get_async_llm_client(provider=provider, api_key=api_key, **kwargs)
```

**Acceptance Criteria**:
- [ ] Factory class created
- [ ] All extractors use factory
- [ ] Tests pass

---

# Phase 4: Code Smell Remediation

## Task 4.1: Fix Deep Nesting in hierarchical_pipeline.py

**Source**: code_quality_issues.md lines 36-41

**Issue**: 380+ instances of 4-5 levels of nesting.

**Strategy**: Use early returns to reduce nesting.

**Example Fix** (lines 403-424):
```python
# Before (nested)
if check_result.passed:
    missing_fields = []
    if hasattr(schema, 'model_fields'):
        expected_fields = set(schema.model_fields.keys())
        extracted_fields = set(extraction.data.keys())
        for field in expected_fields:
            val = extraction.data.get(field)
            if val is None or val == "" or field not in extracted_fields:
                missing_fields.append(field)
        if missing_fields:
            # ... more nesting

# After (early returns)
if not check_result.passed:
    continue

missing_fields = self._find_missing_fields(schema, extraction.data)
if not missing_fields:
    self.logger.info(f"  ✓ Passed validation on iteration {iteration + 1}")
    break

newly_missing = self._filter_new_missing_fields(missing_fields, previous_prompts)
if newly_missing:
    self._trigger_recall_boost(check_result, newly_missing)
```

**Extract Helper Methods**:
```python
def _find_missing_fields(self, schema: Type[T], data: Dict[str, Any]) -> List[str]:
    """Find fields that are missing or empty in extraction data."""
    if not hasattr(schema, 'model_fields'):
        return []
    
    expected = set(schema.model_fields.keys())
    missing = []
    for field in expected:
        val = data.get(field)
        if val is None or val == "" or field not in data:
            missing.append(field)
    return missing

def _filter_new_missing_fields(
    self, 
    missing: List[str], 
    previous_prompts: List[str]
) -> List[str]:
    """Filter to only fields not already requested."""
    return [f for f in missing if not any(f in p for p in previous_prompts)]
```

**Acceptance Criteria**:
- [ ] Maximum nesting reduced to 3 levels
- [ ] Helper methods extracted
- [ ] All tests pass
- [ ] Behavior unchanged

---

## Task 4.2: Extract run_extraction Sub-functions

**Source**: code_quality_issues.md line 46

**Issue**: `run_extraction` in service.py is ~225 lines doing setup, parsing, execution, callbacks, vectorization.

**Extract these functions**:
```python
def _setup_extraction(self, ...) -> Tuple[...]:
    """Initialize extraction components and directories."""

def _parse_papers(self, papers: List[Path], ...) -> List[ParsedDocument]:
    """Parse all papers using Docling."""

def _execute_extraction(self, documents: List[ParsedDocument], ...) -> List[PipelineResult]:
    """Run extraction on parsed documents."""

def _handle_vectorization(self, results: List[PipelineResult], ...) -> None:
    """Store results in vector database."""

def _write_output(self, results: List[PipelineResult], output_path: Path) -> None:
    """Write results to CSV file."""
```

**Acceptance Criteria**:
- [ ] `run_extraction` reduced to ~50 lines
- [ ] Each sub-function is single-responsibility
- [ ] All tests pass

---

## Task 4.3: Eliminate Sync/Async Duplication

**Source**: code_quality_issues.md lines 47-48

**Issue**: `extract_document` and `extract_document_async` are nearly identical (~185 and ~242 lines).

**Strategy**: Extract shared logic into private methods.

```python
def _validate_extraction_result(self, result: ExtractionWithEvidence, ...) -> CheckerResult:
    """Shared validation logic for sync and async."""
    
def _apply_quality_audit(self, check_result: CheckerResult, ...) -> CheckerResult:
    """Apply quality audit penalties."""
    
def _build_iteration_record(self, iteration: int, check_result: CheckerResult) -> IterationRecord:
    """Build iteration history record."""
```

**Acceptance Criteria**:
- [ ] Shared logic extracted
- [ ] Duplication reduced by ~100 lines
- [ ] Both sync and async methods work
- [ ] All tests pass

---

## Task 4.4: Split Very Large Files

**Source**: code_quality_issues.md lines 52-67

**Files to Split** (prioritized by impact):

| File | Lines | Split Into |
|------|-------|------------|
| `core/hierarchical_pipeline.py` | 824 | `pipeline_core.py`, `pipeline_async.py`, `pipeline_helpers.py` |
| `core/extractor.py` | 654 | `extractor_base.py`, `extractor_evidence.py` |
| `core/binary_deriver.py` | 603 | `deriver_base.py`, `deriver_rules.py` |
| `cli.py` | 588 | `cli/extract.py`, `cli/query.py`, `cli/utils.py` |

**This is a large refactoring task - break into sub-tasks**:

### Task 4.4a: Split hierarchical_pipeline.py
### Task 4.4b: Split extractor.py
### Task 4.4c: Split binary_deriver.py
### Task 4.4d: Split cli.py

Each sub-task follows same pattern:
1. Identify natural boundaries
2. Create new files with imports
3. Move code
4. Update imports in other files
5. Run tests

---

## Task 4.5: Replace Magic Numbers with Constants

**Source**: code_quality_issues.md lines 69-77

**Magic Numbers to Replace**:

| File | Line | Value | Constant Name |
|------|------|-------|---------------|
| `core/client.py` | 29 | `timeout=2.0` | `OLLAMA_HEALTH_CHECK_TIMEOUT` |
| `core/client.py` | 51 | `sleep(1)` | `PROCESS_KILL_GRACE_PERIOD` |
| `core/client.py` | 157 | `sleep(2)` | `OLLAMA_RESTART_POLL_INTERVAL` |
| `core/client.py` | 157 | `range(5)` | `OLLAMA_RESTART_MAX_ATTEMPTS` |
| `core/service.py` | 173 | `hybrid_mode: bool = True` | Use `settings.HYBRID_MODE` |
| `core/hierarchical_pipeline.py` | 110 | `"anthropic/claude-3-haiku"` | `FALLBACK_MODEL` |
| `core/hierarchical_pipeline.py` | 130-131 | `"qwen3:14b"`, `"gpt-4o-mini"` | `DEFAULT_LOCAL_MODEL`, `DEFAULT_CLOUD_MODEL` |

**TDD RED Phase**:
```python
# tests/test_constants.py
def test_client_constants_defined():
    from core.client import (
        OLLAMA_HEALTH_CHECK_TIMEOUT,
        PROCESS_KILL_GRACE_PERIOD,
        OLLAMA_RESTART_POLL_INTERVAL,
        OLLAMA_RESTART_MAX_ATTEMPTS,
    )
    assert OLLAMA_HEALTH_CHECK_TIMEOUT == 2.0
    assert PROCESS_KILL_GRACE_PERIOD == 1.0
    assert OLLAMA_RESTART_POLL_INTERVAL == 2.0
    assert OLLAMA_RESTART_MAX_ATTEMPTS == 5
```

**TDD GREEN Phase**:

Add constants at top of each file and replace usages.

**Acceptance Criteria**:
- [ ] All magic numbers replaced with named constants
- [ ] Constants are importable
- [ ] All tests pass

---

## Task 4.6: Improve Ambiguous Variable Names

**Source**: code_quality_issues.md lines 79-84

**Variables to Rename**:
| File | Line | Current | Better Name |
|------|------|---------|-------------|
| `core/service.py` | 255 | `f` | `csv_file` or `output_handle` |
| `core/service.py` | 156 | `i` | `attempt` or `retry_count` |
| Multiple | - | `data` | `extraction_data`, `input_data`, etc. |
| Multiple | - | `result` | `extraction_result`, `validation_result`, etc. |
| Multiple | - | `res` | Full descriptive name |

**Steps**:
```bash
# For each file, use IDE rename refactoring
# Or careful search-and-replace

# Example for service.py:
# 1. Open file
# 2. Find line 255, rename `f` to `csv_file`
# 3. Find line 156, rename `i` to `attempt`
# 4. Run tests
pytest tests/ -k "service" -v
```

**Acceptance Criteria**:
- [ ] No single-letter variable names (except loop indices)
- [ ] No generic names like `data`, `result`
- [ ] All tests pass

---

# Phase 5: Hardcoded Values

## Task 5.1: Move Hardcoded Paths to Settings

**Source**: code_quality_issues.md lines 112-117

**Hardcoded Paths**:
| File | Line | Value | Setting Name |
|------|------|-------|--------------|
| `core/service.py` | 184 | `audit_log_dir = output_path.parent / "logs"` | `settings.AUDIT_LOG_DIR` |
| `core/service.py` | 228 | `vector_dir = output_path.parent / "vector_store"` | `settings.VECTOR_STORE_DIR` |

**Steps**:
1. Add to `core/config.py`:
```python
AUDIT_LOG_DIR: Path = Path(os.getenv("AUDIT_LOG_DIR", "./output/logs"))
VECTOR_STORE_DIR: Path = Path(os.getenv("VECTOR_STORE_DIR", "./output/vector_store"))
```

2. Update `core/service.py` to use settings.

**Acceptance Criteria**:
- [ ] Paths configurable via environment
- [ ] Default behavior unchanged
- [ ] Tests pass

---

## Task 5.2: Deduplicate API Endpoints

**Source**: code_quality_issues.md lines 119-123

**Issue**: OpenRouter URL duplicated in client.py.

| Line | Value |
|------|-------|
| 188 | `"https://openrouter.ai/api/v1"` |
| 222 | `"https://openrouter.ai/api/v1"` |

**Fix**: Use `settings.OPENROUTER_BASE_URL` or define constant.

```python
# At top of client.py
OPENROUTER_BASE_URL = settings.OPENROUTER_BASE_URL

# Replace all usages
base_url = base_url or OPENROUTER_BASE_URL
```

**Acceptance Criteria**:
- [ ] URL defined once
- [ ] All usages reference constant
- [ ] Tests pass

---

## Task 5.3: Move Configuration Values to Settings

**Source**: code_quality_issues.md lines 125-129

**Values to Move**:
| File | Line | Value | Setting |
|------|------|-------|---------|
| `core/service.py` | 173 | `hybrid_mode: bool = True` | `settings.HYBRID_MODE` |
| `core/hierarchical_pipeline.py` | Multiple | Confidence thresholds | `settings.CONFIDENCE_THRESHOLD` |

**Steps**:
1. Add to `core/config.py`:
```python
HYBRID_MODE: bool = os.getenv("HYBRID_MODE", "true").lower() == "true"
CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.85"))
```

2. Update usages.

**Acceptance Criteria**:
- [ ] All configuration values in settings
- [ ] Environment-configurable
- [ ] Tests pass

---

# Phase 6: Minor Issues

## Task 6.1: Add Missing Docstrings

**Source**: code_quality_issues.md lines 90-94

**Missing Docstrings**:
| File | Item | Need |
|------|------|------|
| `core/config.py` | `MODEL_ALIASES` dict | Explain purpose and format |
| `core/client.py` | `_get_client_args` method | Document parameters and return |

**Example Fixes**:
```python
# core/config.py
MODEL_ALIASES: Dict[str, str] = {
    """Map short model names to full provider/model paths.
    
    Used to allow users to specify simple names like 'claude-sonnet'
    instead of full paths like 'anthropic/claude-3.5-sonnet'.
    
    Format: {"short_name": "provider/full_model_name"}
    """
    "claude-sonnet": "anthropic/claude-sonnet-4-20250514",
    "gpt-4o": "openai/gpt-4o",
    # ...
}

# core/client.py
def _get_client_args(self, ...) -> Dict[str, Any]:
    """Build arguments for LLM client initialization.
    
    Args:
        provider: LLM provider (openrouter, openai, ollama)
        api_key: Optional API key override
        
    Returns:
        Dict of arguments to pass to client constructor.
    """
```

**Acceptance Criteria**:
- [ ] All public functions have docstrings
- [ ] Docstrings explain purpose, parameters, returns
- [ ] Lint passes

---

## Task 6.2: Add Missing Type Hints

**Source**: code_quality_issues.md lines 96-100

**Missing Type Hints**:
| File | Function | Need |
|------|----------|------|
| `core/client.py` | `_create_ollama` | Parameter types |
| `core/client.py` | `_create_openrouter` | Parameter types |
| `core/client.py` | `_create_openai` | Parameter types |
| `core/service.py` | `_handle_success` | `writer`, `f`, `vector_store` have `Any` |
| `core/service.py` | `_handle_failure` | Same |

**Steps**:
```python
# Add type hints
def _create_ollama(
    self,
    model: str,
    base_url: Optional[str] = None,
    **kwargs: Any
) -> OpenAI:
    """Create Ollama client."""
```

**Acceptance Criteria**:
- [ ] All parameters have type hints
- [ ] No `Any` types where specific types are known
- [ ] mypy passes (if configured)

---

## Task 6.3: Remove or Fix TODO/FIXME Comments

**Source**: code_quality_issues.md lines 102-106

**TODOs**:
| File | Line | Comment | Action |
|------|------|---------|--------|
| `core/two_pass_extractor.py` | 231 | `# TODO: Implement actual Ollama extraction` | Will be addressed in Phase 2 |
| `core/two_pass_extractor.py` | 260 | `# TODO: Implement actual cloud extraction` | Will be addressed in Phase 2 |

**If keeping TwoPassExtractor**: Implement the TODOs.
**If using placeholder**: Add clear documentation that these are intentional stubs.

---

# Phase 7: Vulture Findings Cleanup

This phase was covered in Tasks 1.8 and 1.9.

---

# Execution Order

```
Phase 1 (Dead Code) ──────────────────────────────────┐
├── Task 1.1: Delete core modules                     │
├── Task 1.2: Review test-only modules                │
├── Task 1.3: Delete agent modules                    │ Can run
├── Task 1.4: Delete test files                       │ in parallel
├── Task 1.5: Delete standalone scripts               │
├── Task 1.6: Delete temp directories                 │
└── Task 1.7: Clean unused imports ◄──────────────────┘
    └── Task 1.8: Clean vulture imports
        └── Task 1.9: Clean unused variables

Phase 2 (Regression Fix) ─────────────────────────────┐
├── Task 2.1: Write regex integration tests (RED)     │ Sequential
├── Task 2.2: Implement regex integration (GREEN)     │ TDD
├── Task 2.3: Write two-pass tests (RED)              │
├── Task 2.4: Verify two-pass integration             │
└── Task 2.5: Add pre_filled_fields support           │

Phase 3 (Anti-Patterns) ──────────────────────────────┐
├── Task 3.1: Centralize os.getenv()                  │
├── Task 3.2: Fix exception handling                  │ Some can
├── Task 3.3: Fix async import pattern                │ parallel
└── Task 3.4: Centralize client creation              │

Phase 4 (Code Smells) ────────────────────────────────┐
├── Task 4.1: Fix deep nesting                        │
├── Task 4.2: Extract run_extraction                  │
├── Task 4.3: Eliminate sync/async duplication        │ Long tasks
├── Task 4.4a-d: Split large files                    │ do serially
├── Task 4.5: Replace magic numbers                   │
└── Task 4.6: Improve variable names                  │

Phase 5 (Hardcoded Values) ───────────────────────────┐
├── Task 5.1: Move paths to settings                  │
├── Task 5.2: Deduplicate endpoints                   │ Can parallel
└── Task 5.3: Move config values                      │

Phase 6 (Minor Issues) ───────────────────────────────┐
├── Task 6.1: Add docstrings                          │
├── Task 6.2: Add type hints                          │ Can parallel
└── Task 6.3: Fix TODOs                               │
```

---

# Verification Checklist (After All Tasks)

```bash
# 1. All tests pass
pytest tests/ -v

# 2. No import errors
python -c "from core.hierarchical_pipeline import HierarchicalExtractionPipeline; print('OK')"
python -c "from core.service import ExtractionService; print('OK')"

# 3. CLI still works
python cli.py --help
python cli.py extract --help

# 4. No os.getenv outside config
grep -r "os.getenv" --include="*.py" core/ agents/ | grep -v config.py
# Should return nothing

# 5. Line count reduction
wc -l core/*.py agents/*.py
# Should be ~4000 lines less than before

# 6. No magic numbers
grep -rn "sleep(1)\|sleep(2)\|range(5)\|timeout=2" core/
# Should only show constants

# 7. Type check (if mypy configured)
mypy core/ --ignore-missing-imports
```

---

# Success Metrics

| Metric | Before | Target | Verification |
|--------|--------|--------|--------------|
| Dead code files | 14 | 0 | `ls core/abstract_first*` returns nothing |
| LOC reduction | 0 | ~4,000 | `wc -l` before/after |
| os.getenv calls outside config | 15+ | 0 | grep command above |
| Magic numbers | 6+ | 0 | grep command above |
| Deep nesting (>3 levels) | 380+ | <50 | Manual review |
| Large functions (>50 lines) | 5 | 0 | Manual review |
| Missing docstrings | 2+ | 0 | Lint check |
| Missing type hints | 5+ | 0 | mypy check |
| Test pass rate | 100% | 100% | pytest |
| Import errors | 0 | 0 | Python -c checks |

---

# Rollback Plan

For any failed task:
1. `git stash` current changes
2. `git checkout HEAD -- <affected files>`
3. Report issue to orchestrator with error details
4. Do not proceed to dependent tasks
5. Fix issue before continuing

For entire phase rollback:
```bash
git log --oneline -10  # Find commit before phase started
git reset --hard <commit_hash>
```

---

# Notes for Subagent Orchestrator

1. **Task Independence**: Most tasks within a phase can run in parallel. Dependencies are noted.

2. **TDD Enforcement**: Tasks in Phases 2-4 MUST follow TDD. Do not skip the RED phase.

3. **Verification**: After each task, run the verification steps before marking complete.

4. **Commits**: Each task should be ONE commit with clear message.

5. **Review Gates**: 
   - After each task: Spec review + Code quality review
   - After each phase: Full test suite + Integration check

6. **Estimated Effort**:
   - Phase 1: ~2 hours (deletions)
   - Phase 2: ~4 hours (integration)
   - Phase 3: ~3 hours (refactoring)
   - Phase 4: ~8 hours (major refactoring)
   - Phase 5: ~1 hour (configuration)
   - Phase 6: ~1 hour (polish)

**Total**: ~19 hours of focused work
