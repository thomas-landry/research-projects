# Fix Known Test Failures Track

**Created**: 2026-01-07
**Status**: 🚀 In Progress
**Owner**: Senior Dev Agent

## Objective
Fix the 2 known test failures identified during Phase 7 to ensure 100% green test suite.

## Issues
1. **TEST-001**: `tests/test_config.py::test_settings_defaults`
   - Error: `assert 4 == 1` (WORKERS mismatch)
   - Route to: `/senior_dev`

2. **TEST-002**: `tests/test_phase2_components.py::TestPubMedFetcher::test_fetch_by_pmid_not_found`
   - Error: Cache returning object instead of `None`
   - Route to: `/senior_dev`

## Tasks
- [ ] Fix TEST-001 (Config)
- [ ] Fix TEST-002 (PubMed Cache)
- [ ] Verify with QA Agent
- [ ] Close issues in task.md
