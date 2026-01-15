# Phase 4 Additional File Evaluation

**Date**: 2026-01-12  
**Files Evaluated**: cache_manager.py, client.py, batch_processor.py  
**Standard**: `/refactor-for-clarity`

---

## File 1: cache_manager.py (419 lines)

### Overview
- **Size**: 419 lines (OVER 400 - file splitting candidate)
- **Functions**: 17 methods
- **Complexity**: Medium-High

### Code Smells Found

#### 1. Deep Nesting (4 levels) - MEDIUM PRIORITY
**Location**: Lines 137-142, 330-332  
**Issue**: SQL query formatting and dict building with 4 levels of indentation  
**Severity**: Medium

```python
# Lines 137-142 - SQL index creation
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_extraction_doc 
    ON extraction_cache(doc_hash)
""")
```

**Recommendation**: SQL queries are acceptable at 4 levels when properly formatted. No action needed.

#### 2. Ambiguous Variable Names - LOW PRIORITY
**Location**: Lines 327-333  
**Issue**: Variable `row` used in multiple contexts  
**Severity**: Low

```python
for row in cursor.fetchall():
    results[row["field_name"]] = {
        "result": json.loads(row["result"]),
        "confidence": row["confidence"],
        "tier_used": row["tier_used"],
    }
```

**Recommendation**: Rename to `cache_row` or `field_row` for clarity.

#### 3. Missing Type Hints - LOW PRIORITY
**Location**: Multiple methods  
**Issue**: Some internal methods lack complete type hints  
**Severity**: Low

**Recommendation**: Add type hints to `_get_connection`, `_init_db`, `close`.

#### 4. File Size - HIGH PRIORITY
**Issue**: 419 lines exceeds 400-line threshold  
**Severity**: High

**Recommendation**: Split into:
- `cache/manager.py` - Core CacheManager class
- `cache/models.py` - CacheEntry dataclass
- `cache/constants.py` - DEFAULT_CACHE_PATH, SCHEMA_VERSION

---

## File 2: client.py (232 lines)

### Overview
- **Size**: 232 lines (OK)
- **Functions**: 11 methods
- **Complexity**: Medium

### Code Smells Found

#### 1. Large Function - MEDIUM PRIORITY
**Location**: Lines 42-86 (45 lines)  
**Function**: `OllamaHealthCheck.restart_service`  
**Issue**: Does multiple things - kill process, restart service, handle platforms  
**Severity**: Medium

**Recommendation**: Extract methods:
- `_kill_existing_process()` - Lines 54-59
- `_restart_via_brew()` - Lines 65-70
- `_restart_via_direct_exec()` - Lines 73-80

#### 2. Magic Numbers - LOW PRIORITY
**Location**: Line 29, 32  
**Issue**: Timeout value `2.0` hardcoded  
**Severity**: Low

```python
resp = requests.get(f"{url}api/version", timeout=2.0)
logger.debug(f"Ollama health check timeout after 2.0s: {e}")
```

**Recommendation**: Extract to `constants.OLLAMA_HEALTH_CHECK_TIMEOUT = 2.0`

#### 3. Deep Nesting - LOW PRIORITY
**Location**: Lines 65-70  
**Issue**: Nested platform checks and subprocess calls  
**Severity**: Low

```python
if platform.system() == "Darwin":
    res = subprocess.run([...])
    if res.returncode == 0:
        logger.info("Restarted via brew services")
        return True
```

**Recommendation**: Extract to `_restart_via_brew()` method.

#### 4. Repeated Code - MEDIUM PRIORITY
**Location**: Lines 149-182, 184-202, 204-218  
**Issue**: Similar client creation logic in `_create_ollama`, `_create_openrouter`, `_create_openai`  
**Severity**: Medium

**Recommendation**: Extract common pattern:
```python
def _create_client(self, provider_config, mode):
    # Common client creation logic
    pass
```

---

## File 3: batch_processor.py (280 lines)

### Overview
- **Size**: 280 lines (OK)
- **Functions**: 12 methods (including nested)
- **Complexity**: High

### Code Smells Found

#### 1. Deep Nesting (5 levels) - HIGH PRIORITY
**Location**: Lines 224-272 (async method)  
**Issue**: Nested try/except with multiple conditional branches  
**Severity**: High

```python
async with semaphore:
    try:
        result = await self.pipeline.extract_document_async(...)
        # Process result
        if hasattr(result, 'to_dict'):
            serialized = result.to_dict()
        elif hasattr(result, 'model_dump'):
            serialized = result.model_dump()
        elif isinstance(result, dict):
            serialized = result
        else:
            serialized = result.__dict__
```

**Recommendation**: Extract methods:
- `_serialize_result(result)` - Lines 230-237
- `_handle_success(doc, serialized)` - Lines 239-244
- `_handle_memory_error(doc)` - Lines 245-253
- `_handle_general_error(doc, e)` - Lines 254-272

#### 2. Large Function - HIGH PRIORITY
**Location**: Lines 219-272 (54 lines)  
**Function**: `_execute_single_async` (nested function)  
**Issue**: Too many responsibilities - execution, serialization, error handling, state management  
**Severity**: High

**Recommendation**: Extract into class methods as listed above.

#### 3. Repeated Code - HIGH PRIORITY
**Location**: Lines 110-127 (sync) vs Lines 219-272 (async)  
**Issue**: Nearly identical logic in `_execute_single` and `_execute_single_async`  
**Severity**: High

**Recommendation**: Use composition pattern:
```python
class ExecutionHandler:
    def serialize_result(self, result):
        # Shared serialization logic
        pass
    
    def handle_errors(self, doc, error):
        # Shared error handling
        pass
```

#### 4. Ambiguous Variable Names - MEDIUM PRIORITY
**Location**: Lines 138, 156  
**Issue**: Variables `data`, `status` are generic  
**Severity**: Medium

```python
filename, data, status = future.result()
```

**Recommendation**: Rename to `extraction_result`, `extraction_status`.

#### 5. Magic Numbers - LOW PRIORITY
**Location**: Line 18, 65  
**Issue**: Circuit breaker threshold `3` hardcoded  
**Severity**: Low

```python
def __init__(self, threshold: int = 3):
self.circuit_breaker = CircuitBreaker(threshold=3)
```

**Recommendation**: Extract to `constants.CIRCUIT_BREAKER_THRESHOLD = 3`

---

## Summary of Findings

### Critical Issues (Require Immediate Attention)
1. **batch_processor.py**: Deep nesting (5 levels) in async method
2. **batch_processor.py**: Large function `_execute_single_async` (54 lines)
3. **batch_processor.py**: Repeated sync/async code

### High Priority Issues
1. **cache_manager.py**: File size (419 lines) - needs splitting
2. **batch_processor.py**: Repeated code between sync/async methods

### Medium Priority Issues
1. **client.py**: Large function `restart_service` (45 lines)
2. **client.py**: Repeated client creation logic
3. **batch_processor.py**: Ambiguous variable names

### Low Priority Issues
1. **cache_manager.py**: Ambiguous variable names
2. **cache_manager.py**: Missing type hints
3. **client.py**: Magic number (timeout 2.0)
4. **batch_processor.py**: Magic number (threshold 3)

---

## Recommended Phase 4 Tasks

### New Tasks to Add

**Task 4.19**: Fix deep nesting in `batch_processor.py`
- Extract `_serialize_result()` method
- Extract `_handle_success()`, `_handle_memory_error()`, `_handle_general_error()`
- Reduce nesting from 5 to 3 levels
- Owner: `/refactor-for-clarity`

**Task 4.20**: Extract large function in `batch_processor.py`
- Split `_execute_single_async` (54 lines) into helper methods
- Apply same pattern to `_execute_single` (sync version)
- Owner: `/refactor-for-clarity`

**Task 4.21**: Eliminate sync/async duplication in `batch_processor.py`
- Create `ExecutionHandler` class with shared logic
- Use composition pattern for serialization and error handling
- Keep sync/async as thin wrappers
- Owner: `/refactor-for-clarity`

**Task 4.22**: Split `cache_manager.py` (419 lines)
- Split into: `cache/manager.py`, `cache/models.py`, `cache/constants.py`
- Owner: `/refactor-for-clarity`

**Task 4.23**: Extract large function in `client.py`
- Split `restart_service` (45 lines) into platform-specific methods
- Extract `_kill_existing_process()`, `_restart_via_brew()`, `_restart_via_direct_exec()`
- Owner: `/refactor-for-clarity`

**Task 4.24**: Eliminate client creation duplication in `client.py`
- Extract common client creation pattern
- Reduce code in `_create_ollama`, `_create_openrouter`, `_create_openai`
- Owner: `/refactor-for-clarity`

**Task 4.25**: Fix ambiguous variable names
- `cache_manager.py`: `row` → `cache_row` / `field_row`
- `batch_processor.py`: `data` → `extraction_result`, `status` → `extraction_status`
- Owner: `/refactor-for-clarity`

**Task 4.26**: Extract remaining magic numbers
- `client.py`: `2.0` → `constants.OLLAMA_HEALTH_CHECK_TIMEOUT`
- `batch_processor.py`: `3` → `constants.CIRCUIT_BREAKER_THRESHOLD`
- Owner: `/refactor-for-clarity`

---

## Priority Order for Implementation

1. **Task 4.19**: Fix deep nesting in batch_processor.py (Critical)
2. **Task 4.20**: Extract large function in batch_processor.py (Critical)
3. **Task 4.21**: Eliminate sync/async duplication (High)
4. **Task 4.22**: Split cache_manager.py (High)
5. **Task 4.23**: Extract large function in client.py (Medium)
6. **Task 4.24**: Eliminate client creation duplication (Medium)
7. **Task 4.25**: Fix ambiguous variable names (Low)
8. **Task 4.26**: Extract remaining magic numbers (Low)

---

## Estimated Effort

- **Critical Tasks (4.19-4.20)**: 4 hours
- **High Priority (4.21-4.22)**: 6 hours
- **Medium Priority (4.23-4.24)**: 4 hours
- **Low Priority (4.25-4.26)**: 2 hours

**Total**: ~16 hours (2 days)
