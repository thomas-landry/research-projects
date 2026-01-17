# CSV Output Fix - Implementation Plan

## Problem Statement

CSV output files are being generated with headers but **empty data rows** when extraction fails. This occurs due to two root causes:

1. **Rate limiting errors (429)** from OpenRouter API cause extraction failures
2. **Error handling doesn't write failure data to CSV** - only logs to `failed_files` list

### Evidence

```bash
# Empty CSV output
$ head -5 output/gemini_eval/results.csv
case_count,case_count_quote,patient_age,...
,,,,,,,,,,,,,,,,,,,,,,,,
,,,,,,,,,,,,,,,,,,,,,,,,
,,,,,,,,,,,,,,,,,,,,,,,,

# Log shows rate limiting
2026-01-14 22:20:58,041 - StructuredExtractor - ERROR - Evidence extraction failed:
Error code: 429 - {'error': {'message': 'Rate limit exceeded: free-models-per-min.'}}
```

### Current Behavior (Broken)

```python
# service.py:355-363
def result_handler(filename, data, status):
    if status == "success":
        self._handle_extraction_success(...)
    else:
        failed_files.append((filename, str(data)))  # ← Only logs
        # ❌ NO CSV WRITE - results in empty rows
```

## User Review Required

> [!IMPORTANT]
> **Schema Changes Required**
> All extraction schemas will gain two new fields:
> - `extraction_status`: Enum["SUCCESS", "FAILED", "PARTIAL"]
> - `extraction_notes`: Optional error message/metadata
> 
> This is a **breaking change** for existing CSV consumers.

> [!WARNING]
> **Retry Logic Impact**
> Implementing exponential backoff will increase execution time for failed extractions.
> - Max retry attempts: 3
> - Max backoff: 60 seconds
> - Total delay per failure: ~90 seconds worst case

## Proposed Changes

### Phase 1: Core Error Handling (TDD)

#### [MODIFY] [service.py](file:///Users/thomaslandry/Projects/research-projects/SR-architect/core/service.py)

**Changes:**
- Add `_write_error_row()` method to write partial data on failure
- Modify `result_handler` to call `_write_error_row()` on failure
- Ensure CSV always has matching row count to PDF count

**Tests to write first:**
1. `test_csv_output_on_extraction_failure` - Verify error row written
2. `test_csv_row_count_matches_pdf_count` - Verify no missing rows
3. `test_error_row_contains_filename_and_status` - Verify error metadata

---

### Phase 2: Schema Enhancement

#### [MODIFY] [schema_builder.py](file:///Users/thomaslandry/Projects/research-projects/SR-architect/core/schema_builder.py)

**Changes:**
- Add `extraction_status` and `extraction_notes` to `build_extraction_model()`
- Make these fields optional with defaults
- Update all predefined schemas

**Tests to write first:**
1. `test_schema_includes_extraction_metadata_fields` - Verify fields present
2. `test_extraction_metadata_fields_are_optional` - Verify defaults work
3. `test_csv_fieldnames_include_metadata` - Verify CSV headers correct

---

### Phase 3: Retry Logic with Exponential Backoff

#### [NEW] [retry_handler.py](file:///Users/thomaslandry/Projects/research-projects/SR-architect/core/retry_handler.py)

**Purpose:** Centralized retry logic for API calls with rate limit detection

**Implementation:**
```python
class RetryHandler:
    """Handle retries with exponential backoff for rate-limited APIs."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def is_rate_limit_error(self, error: Exception) -> bool:
        """Detect rate limit errors (429, specific messages)."""
        
    def calculate_backoff(self, attempt: int) -> float:
        """Exponential backoff: 2^attempt * base_delay."""
        
    async def retry_with_backoff(self, func: Callable, *args, **kwargs):
        """Execute function with retry logic."""
```

**Tests to write first:**
1. `test_retry_handler_detects_rate_limit_error` - Verify 429 detection
2. `test_exponential_backoff_calculation` - Verify backoff formula
3. `test_retry_succeeds_after_transient_failure` - Verify retry works
4. `test_retry_exhausts_after_max_attempts` - Verify max retries honored
5. `test_retry_preserves_non_rate_limit_errors` - Verify other errors pass through

---

### Phase 4: Hybrid Mode Fallback

#### [MODIFY] [pipeline/core.py](file:///Users/thomaslandry/Projects/research-projects/SR-architect/core/pipeline/core.py)

**Changes:**
- Integrate `RetryHandler` into extraction pipeline
- On rate limit error, fallback to local model (hybrid mode)
- Track tier escalation stats

**Tests to write first:**
1. `test_pipeline_retries_on_rate_limit` - Verify retry triggered
2. `test_pipeline_falls_back_to_local_on_cloud_failure` - Verify hybrid fallback
3. `test_tier_stats_track_escalations` - Verify stats collected

---

### Phase 5: Integration & CSV Validation

#### [MODIFY] [service.py](file:///Users/thomaslandry/Projects/research-projects/SR-architect/core/service.py)

**Changes:**
- Wire up `RetryHandler` to `ExtractionService`
- Update `_handle_extraction_success` to set `extraction_status="SUCCESS"`
- Update `_write_error_row` to set `extraction_status="FAILED"`

**Tests to write first:**
1. `test_end_to_end_csv_output_with_mixed_results` - Success + failures
2. `test_csv_validates_against_schema` - All fields present
3. `test_extraction_status_field_populated_correctly` - Status values correct

---

## Verification Plan

### Automated Tests

```bash
# Run new test suite
pytest tests/test_csv_error_handling.py -v
pytest tests/test_retry_handler.py -v
pytest tests/test_schema_metadata.py -v

# Run full regression suite
pytest tests/ -v --cov=core --cov-report=term-missing

# Verify all tests pass
pytest tests/ -v | grep -E "PASSED|FAILED"
```

### Manual Verification

1. **Reproduce original bug:**
   ```bash
   # Use rate-limited API to trigger failures
   python cli.py extract papers_validation --limit 3 -o output/test_failures.csv
   ```

2. **Verify CSV output:**
   ```bash
   # Check CSV has correct row count
   wc -l output/test_failures.csv  # Should be 4 (header + 3 rows)
   
   # Check error rows have metadata
   cat output/test_failures.csv | grep "FAILED"
   ```

3. **Verify retry logic:**
   ```bash
   # Monitor logs for retry attempts
   tail -f output/sr_architect.log | grep -i "retry\|backoff"
   ```

4. **Verify hybrid fallback:**
   ```bash
   # Check tier stats in summary
   python cli.py extract papers_validation --limit 3 --hybrid-mode
   # Should show local model usage when cloud fails
   ```

### Success Criteria

- [ ] CSV row count always matches PDF count
- [ ] Failed extractions write error rows with `extraction_status="FAILED"`
- [ ] Successful extractions write `extraction_status="SUCCESS"`
- [ ] Retry logic reduces failure rate by >50%
- [ ] Hybrid fallback activates on rate limit errors
- [ ] All existing tests still pass
- [ ] New tests achieve >90% coverage on changed code

---

## Rollback Plan

If issues arise:

1. **Revert schema changes:**
   ```bash
   git revert <commit-hash>  # Revert schema_builder.py changes
   ```

2. **Disable retry logic:**
   ```python
   # In config.py
   ENABLE_RETRY_LOGIC = False
   ```

3. **Restore original service.py:**
   ```bash
   git checkout HEAD~1 core/service.py
   ```

---

## Dependencies

- No new external dependencies required
- Uses existing `asyncio` for retry logic
- Leverages existing hybrid mode infrastructure

---

## Timeline Estimate

- Phase 1 (Core Error Handling): 2-3 hours
- Phase 2 (Schema Enhancement): 1-2 hours
- Phase 3 (Retry Logic): 3-4 hours
- Phase 4 (Hybrid Fallback): 2-3 hours
- Phase 5 (Integration): 1-2 hours
- **Total: 9-14 hours**

---

## Notes

- Follow TDD strictly - write tests first for every change
- Commit after each passing test
- Update `task.md` after each phase completion
- Run full test suite before moving to next phase
