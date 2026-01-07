# Track Specification: Production Bug Discovery & Remediation

## Context
During the test_fixes_20260106 track, integration tests exposed production bugs that cause:
1. Runtime errors when features are used
2. Excessive token usage from retry loops hitting authentication/undefined errors
3. Test suite relying on skips rather than passing

## Known Bugs (from test failures)

### BUG-001: Undefined Variable in Extractor
- **File**: `core/extractor.py:470`
- **Error**: `NameError: name 'evidence_prompt' is not defined`
- **Impact**: `extract_with_evidence()` always fails, causing retry loops
- **Root Cause**: Variable referenced but never defined in scope

### BUG-002: Missing Attribute in Async Pipeline
- **File**: `core/hierarchical_pipeline.py:449`
- **Error**: `AttributeError: 'HierarchicalExtractionPipeline' object has no attribute '_log'`
- **Impact**: All async extractions fail
- **Root Cause**: Sync path uses `self.logger`, async path uses undefined `self._log`

## Discovery Phase Goals

Beyond the known bugs, systematically scan for:
1. Undefined variables referenced in code
2. Method/attribute name inconsistencies between sync/async paths
3. Mock-only code paths that would fail in production
4. Imports that fail silently

## Success Criteria
- [ ] All known production bugs fixed
- [ ] Integration tests pass (not skipped)
- [ ] Static analysis shows no undefined names
- [ ] No retry-loop token waste from fixable errors

## Estimated Effort
- Known bugs: ~30 minutes
- Discovery scan: ~15 minutes
- Verification: ~15 minutes
