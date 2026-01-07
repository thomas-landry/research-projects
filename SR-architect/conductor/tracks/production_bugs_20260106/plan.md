# Track Plan: Production Bug Discovery & Remediation

## Phase 1: Fix Known Bugs
- [ ] Task: Fix undefined `evidence_prompt` in `extractor.py`
- [ ] Task: Fix missing `_log` attribute in `hierarchical_pipeline.py` async path
- [ ] Task: Verify integration tests now pass

## Phase 2: Static Analysis Discovery
- [ ] Task: Run pyflakes/pylint to find undefined names in core/
- [ ] Task: Run pyflakes/pylint to find undefined names in agents/
- [ ] Task: Fix any discovered issues

## Phase 3: Sync/Async Consistency Check
- [ ] Task: Audit all async methods for attribute/method parity with sync versions
- [ ] Task: Fix any inconsistencies found

## Phase 4: Final Verification
- [ ] Task: Run full test suite - target 0 failures, 0 skips (or documented why)
- [ ] Task: Manual smoke test of key extraction paths
- [ ] Task: Commit checkpoint
