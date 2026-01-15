# Code Quality Review: Pipeline Files

**Date**: 2026-01-12  
**Files**: stages.py, validation.py, helpers.py  
**Standard**: `/refactor-for-clarity`

---

## stages.py (156 lines) - ✅ EXCELLENT

### Analysis

| Criteria | Status | Notes |
|----------|--------|-------|
| Deep Nesting | ✅ PASS | Max 2 levels |
| Magic Numbers | ✅ PASS | None found |
| Ambiguous Names | ✅ PASS | All names descriptive |
| Large Functions | ✅ PASS | Largest is 30 lines |
| Missing Docs | ✅ PASS | All functions documented |
| Repeated Code | ✅ PASS | No duplication |

### Type Hints
- ✅ All parameters typed
- ✅ All returns typed
- ⚠️ Minor: `Callable` types could be more specific

**Verdict**: No changes needed. This file is exemplary.

---

## validation.py (244 lines) - ⚠️ NEEDS FIXES

### Issues Found

#### 1. **Magic Number** - Line 94, 204
**Severity**: MEDIUM  
**Location**: Lines 94, 204

```python
check_result.overall_score *= 0.8  # Penalty
```

**Fix**: Extract to constant
```python
# At top of file or in constants.py
QUALITY_AUDIT_PENALTY = 0.8

# In code
check_result.overall_score *= QUALITY_AUDIT_PENALTY
```

#### 2. **Repeated Code** - 90% Duplication
**Severity**: HIGH  
**Location**: Lines 56-133 (sync) vs Lines 166-243 (async)

**Problem**: 90 lines of nearly identical code between sync/async versions

**Fix**: Extract shared logic
```python
def _process_iteration(
    iteration: int,
    max_iterations: int,
    extraction,
    check_result,
    quality_auditor,
    best_check,
    logger
) -> tuple:
    """Process a single iteration (shared logic)."""
    # Apply quality audit if available
    if quality_auditor:
        audit_report = quality_auditor.audit_extraction(
            extraction.data, 
            [e.model_dump() for e in extraction.evidence]
        )
        if not audit_report.passed:
            check_result.overall_score *= QUALITY_AUDIT_PENALTY
            check_result.passed = False
            for audit in audit_report.audits:
                if not audit.is_correct:
                    check_result.issues.append(
                        f"Audit failed for {audit.field_name}: {audit.explanation}"
                    )
                    check_result.suggestions.append(
                        f"For {audit.field_name}: {audit.explanation}"
                    )
    
    # Create iteration record
    iteration_record = IterationRecord(
        iteration_number=iteration + 1,
        accuracy_score=check_result.accuracy_score,
        consistency_score=check_result.consistency_score,
        overall_score=check_result.overall_score,
        issues_count=len(check_result.issues),
        suggestions=check_result.suggestions,
    )
    
    # Track best result
    is_best = best_check is None or check_result.overall_score > best_check.overall_score
    
    return iteration_record, is_best
```

#### 3. **Missing Type Hints**
**Severity**: LOW  
**Location**: Lines 12-13, 138-139

```python
# Current
schema,
extractor,

# Should be
schema: Type[BaseModel],
extractor: StructuredExtractor,
```

#### 4. **Ambiguous Variable Name**
**Severity**: LOW  
**Location**: Line 81, 191

```python
# Current
evidence_dicts = [e.model_dump() for e in extraction.evidence]

# Should be
evidence_dicts = [evidence_item.model_dump() for evidence_item in extraction.evidence]
```

---

## helpers.py (84 lines) - ⚠️ MINOR FIXES

### Issues Found

#### 1. **Missing Type Hints**
**Severity**: LOW  
**Location**: Lines 10-14

```python
# Current
document,
extraction,
check_result,

# Should be
document: ParsedDocument,
extraction: ExtractionWithEvidence,
check_result: CheckerResult,
```

#### 2. **Magic Number**
**Severity**: LOW  
**Location**: Lines 74-76

```python
quality_score=0.0,
accuracy_score=0.0,
consistency_score=0.0,
```

**Fix**: Extract to constant (though 0.0 for "failed" is acceptable)

---

## Summary of Required Fixes

### Priority 1 (HIGH) - validation.py
1. ✅ Extract magic number `0.8` → `QUALITY_AUDIT_PENALTY`
2. ✅ Extract `_process_iteration()` helper to eliminate 90 lines of duplication

### Priority 2 (MEDIUM) - validation.py
3. ✅ Add type hints to function parameters

### Priority 3 (LOW) - helpers.py
4. ✅ Add type hints to function parameters

### Priority 4 (LOW) - validation.py
5. ✅ Rename `e` → `evidence_item` for clarity

---

## Proposed Fixes

### Fix 1: Extract Magic Number

```python
# At top of validation.py
QUALITY_AUDIT_PENALTY = 0.8  # Score penalty for failed quality audit
```

### Fix 2: Extract Shared Iteration Logic

```python
# New function in validation.py
def _process_iteration_result(
    extraction,
    check_result,
    quality_auditor,
    iteration: int,
) -> IterationRecord:
    """
    Process iteration result with quality audit.
    
    Applies quality audit penalties and creates iteration record.
    Pure function - no I/O.
    """
    # Apply quality audit if available
    if quality_auditor:
        evidence_dicts = [item.model_dump() for item in extraction.evidence]
        audit_report = quality_auditor.audit_extraction(
            extraction.data, 
            evidence_dicts
        )
        if not audit_report.passed:
            check_result.overall_score *= QUALITY_AUDIT_PENALTY
            check_result.passed = False
            for audit in audit_report.audits:
                if not audit.is_correct:
                    check_result.issues.append(
                        f"Audit failed for {audit.field_name}: {audit.explanation}"
                    )
                    check_result.suggestions.append(
                        f"For {audit.field_name}: {audit.explanation}"
                    )
    
    # Create iteration record
    return IterationRecord(
        iteration_number=iteration + 1,
        accuracy_score=check_result.accuracy_score,
        consistency_score=check_result.consistency_score,
        overall_score=check_result.overall_score,
        issues_count=len(check_result.issues),
        suggestions=check_result.suggestions,
    )
```

### Fix 3: Add Type Hints

```python
from typing import Type
from pydantic import BaseModel
from core.parser import ParsedDocument
from core.extractor import StructuredExtractor
from core.extraction_checker import ExtractionChecker

def run_validation_loop(
    context: str,
    schema: Type[BaseModel],
    extractor: StructuredExtractor,
    checker: ExtractionChecker,
    # ... rest
) -> PipelineResult:
```

---

## Estimated Time to Fix

- Fix 1 (magic number): 2 minutes
- Fix 2 (extract helper): 15 minutes
- Fix 3 (type hints): 10 minutes
- Fix 4 (rename variable): 2 minutes

**Total**: ~30 minutes

---

## Recommendation

Apply all fixes before proceeding with executor.py to maintain code quality standards.
