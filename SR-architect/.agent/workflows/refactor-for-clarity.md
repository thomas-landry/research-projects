---
description: Specific instructions for refactoring to improve readability without altering runtime behavior
---

# Workflow: Refactor for Clarity

**Trigger**: `/refactor-for-clarity`

**Context**: Improve code readability and maintainability WITHOUT changing behavior.

---

## Phase 1: Critique

Scan the selected code for **Code Smells**:

| Smell | Detection Criteria |
|-------|---------------------|
| **Deep Nesting** | More than 3 levels of indentation (arrow code) |
| **Magic Numbers** | Unnamed numerical constants (e.g., `if x > 86400:`) |
| **Ambiguous Names** | Variables named `data`, `temp`, `x`, `result` |
| **Large Functions** | More than 20 lines doing multiple things |
| **Missing Docs** | Public functions without docstrings |
| **Repeated Code** | Similar logic blocks that could be extracted |

**Output**: List of identified issues with line numbers.

---

## Phase 2: Propose Refactoring Plan

> [!IMPORTANT]
> **Constraint**: You MUST maintain strict **idempotency** — inputs and outputs must remain exactly the same.

Propose specific refactoring moves:

```markdown
1. Extract method `_validate_input()` from `process_document()` (lines 45-62)
2. Rename constant `86400` → `SECONDS_IN_DAY`
3. Rename variable `res` → `extraction_result`
4. Convert nested if/else to early return pattern
5. Add docstring to `filter_chunks()` explaining parameters
```

**STOP**: Wait for user approval before executing changes.

---

## Phase 3: Execute (Surgical Diffs)

1. **Apply changes incrementally** — one refactor at a time
2. **Keep diffs minimal** — do not touch unrelated code
3. **Add documentation**:
   - Docstrings explaining **why** logic exists, not just what it does
   - Type hints on all parameters and return values

4. **Type hardening**: If types are loose (`Any`, `Optional[Any]`), tighten them.

### Example Refactor

**Before**:
```python
def process(data):
    if data:
        res = {}
        for x in data:
            if x.get("type") == "a":
                if x.get("value") > 86400:
                    res[x["id"]] = x["value"]
        return res
    return {}
```

**After**:
```python
SECONDS_IN_DAY = 86400

def process(documents: list[dict]) -> dict[str, int]:
    """Filter documents by type and value threshold.
    
    Args:
        documents: List of document dicts with 'type', 'value', 'id' keys.
        
    Returns:
        Dict mapping document IDs to values for qualifying documents.
    """
    if not documents:
        return {}
    
    return {
        doc["id"]: doc["value"]
        for doc in documents
        if doc.get("type") == "a" and doc.get("value", 0) > SECONDS_IN_DAY
    }
```

---

## Phase 4: Regression Verification

// turbo
1. **Run existing tests BEFORE changes** (establish baseline):
   ```bash
   cd ~/Projects/research-projects/SR-architect && pytest -v
   ```

// turbo
2. **Run tests AFTER changes**:
   ```bash
   pytest -v
   ```

3. **Safety Lock**:
   - **IF Tests FAIL**: **IMMEDIATELY REVERT** all changes and report the conflict.
   - **IF Tests PASS**: Commit the refactor.

4. **Report outcome**:
   ```
   ✅ Refactoring complete
   - Extracted 2 helper functions
   - Renamed 3 variables
   - Added 4 docstrings
   - All 10 tests still passing
   ```
