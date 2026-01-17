# CSV Output Fix - Design Decisions

## Decision Log

### Decision 1: Write Error Rows vs. Separate Failure File

**Date:** 2026-01-15  
**Decision:** Write error rows to main CSV with `extraction_status` field  
**Rationale:**
- ✅ Maintains 1:1 mapping between PDFs and CSV rows
- ✅ Easier to audit (single file)
- ✅ Simpler downstream processing
- ❌ Rejected: Separate failure CSV (harder to correlate)

**Alternatives Considered:**
1. Separate `results_failures.csv` - Rejected (two files to manage)
2. Skip failed rows entirely - Rejected (loses audit trail)
3. Write partial data only - Rejected (unclear which fields are valid)

---

### Decision 2: Retry Strategy - Exponential Backoff

**Date:** 2026-01-15  
**Decision:** Implement exponential backoff with max 3 retries  
**Rationale:**
- ✅ Industry standard for rate limiting
- ✅ Avoids thundering herd problem
- ✅ Configurable via settings
- Formula: `delay = 2^attempt * base_delay` (2s, 4s, 8s, ...)

**Configuration:**
```python
MAX_RETRIES = 3
BASE_DELAY = 2.0  # seconds
MAX_BACKOFF = 60.0  # cap at 60 seconds
```

---

### Decision 3: Schema Field Names

**Date:** 2026-01-15  
**Decision:** Use `extraction_status` and `extraction_notes`  
**Rationale:**
- ✅ Clear, descriptive names
- ✅ Follows existing naming convention (snake_case)
- ✅ Won't conflict with domain fields
- ❌ Rejected: `__pipeline_status` (too internal)
- ❌ Rejected: `status` (too generic, might conflict)

**Field Specifications:**
```python
extraction_status: Literal["SUCCESS", "FAILED", "PARTIAL"] = "SUCCESS"
extraction_notes: Optional[str] = None  # Error message or metadata
```

---

### Decision 4: Hybrid Mode Fallback Trigger

**Date:** 2026-01-15  
**Decision:** Fallback to local model after 2 failed cloud attempts  
**Rationale:**
- ✅ Balances quality (cloud) with reliability (local)
- ✅ Prevents excessive retries on persistent failures
- ✅ Leverages existing hybrid mode infrastructure

**Fallback Logic:**
1. Attempt 1: Cloud model (Gemini/Claude)
2. Attempt 2: Retry cloud with backoff
3. Attempt 3+: Switch to local model (Ollama)

---

### Decision 5: Error Message Truncation

**Date:** 2026-01-15  
**Decision:** Truncate `extraction_notes` to 500 characters  
**Rationale:**
- ✅ Prevents CSV bloat from stack traces
- ✅ Preserves essential error information
- ✅ Full errors still logged to `sr_architect.log`

**Implementation:**
```python
extraction_notes = str(error)[:500] + "..." if len(str(error)) > 500 else str(error)
```

---

## Open Questions

_None currently_

---

## Future Considerations

1. **Partial Extraction Support:** If some fields succeed but others fail, mark as "PARTIAL"
2. **Retry Budget:** Track total retry time and abort if exceeds threshold
3. **Smart Fallback:** Use complexity classifier to route simple docs to local models first
