# Track Plan: Fix Pre-Existing Test Suite Failures

## Phase 1: Parser Test Fixes
- [ ] Task: Update `test_parser_extended.py` to use current `DocumentParser` API
- [ ] Task: Verify parser tests pass after updates

## Phase 2: Extractor Test Fixes
- [ ] Task: Fix mock configuration in `test_extractor.py` for `create_with_completion`
- [ ] Task: Verify extractor tests pass after updates

## Phase 3: Integration Test Fixes
- [ ] Task: Add proper mocking or skip decorators for `test_integration.py` auth requirements
- [ ] Task: Verify integration tests pass (or skip gracefully) after updates

## Phase 4: Bug Fix Test Compatibility
- [ ] Task: Fix `test_bug_fixes.py::test_vectorizer_metadata_sanitization` TypeError
- [ ] Task: Fix `test_bug_fixes.py::test_parser_null_section_attribute` pydantic error
- [ ] Task: Fix `test_bug_fixes.py::test_extractor_evidence_truncation` ImportError
- [ ] Task: Verify bug fix tests pass after updates

## Phase 5: Other Test Fixes
- [ ] Task: Fix `test_adaptive_cli.py` assertion failures
- [ ] Task: Fix `test_schema_discovery.py::test_unify_fields_logic` assertion
- [ ] Task: Fix `test_synthesizer.py::test_synthesize_success` RuntimeError
- [ ] Task: Conductor - User Manual Verification 'All Tests Pass' (Protocol in workflow.md)
