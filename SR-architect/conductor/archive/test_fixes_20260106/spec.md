# Track Spec: Fix Pre-Existing Test Suite Failures

## 1. Overview
This track addresses 18 failing tests discovered during Phase 1 verification of the Token Optimization track. These failures are pre-existing issues unrelated to Phase 1 work and need to be resolved to maintain test suite health.

## 2. Failure Categories

### 2.1 Parser API Changes (5 tests)
- **Tests**: `test_parser_extended.py` (5 tests)
- **Error**: `AttributeError: 'DocumentParser' object has no attribute 'parse_text'`
- **Root Cause**: Parser API was refactored, but tests weren't updated
- **Fix**: Update tests to use current `DocumentParser` API

### 2.2 Extractor Mock Issues (3 tests)
- **Tests**: `test_extractor.py` (3 tests)
- **Error**: `ValueError: not enough values to unpack (expected 2, got 0)`
- **Root Cause**: Mock returns wrong structure for `create_with_completion`
- **Fix**: Update mock to return `(result, completion)` tuple

### 2.3 Integration Auth Errors (3 tests)
- **Tests**: `test_integration.py` (3 tests)
- **Error**: `401 - {'error': {'message': 'No cookie auth credentials found'}}`
- **Root Cause**: Tests hit real API without proper auth
- **Fix**: Add proper mocking or skip when API key unavailable

### 2.4 Bug Fix Test Compatibility (3 tests)
- **Tests**: `test_bug_fixes.py` (3 tests)
- **Errors**: 
  - `TypeError` in vectorizer metadata
  - `pydantic` validation error in parser
  - `ImportError` in extractor evidence
- **Fix**: Update tests to match current module implementations

### 2.5 Other Failures (4 tests)
- `test_adaptive_cli.py` (2 tests) - CLI flow assertions
- `test_schema_discovery.py` (1 test) - `unify_fields` logic
- `test_synthesizer.py` (1 test) - Synthesizer runtime error

## 3. Success Criteria
- All 18 failing tests pass
- No new test failures introduced
- Test coverage maintained at >80%

## 4. Priority
**Medium** - These failures don't block current development but should be fixed before Phase 2 to maintain CI health.

## 5. Estimated Effort
- 2-4 hours for experienced developer
- Primarily test file updates, minimal production code changes
