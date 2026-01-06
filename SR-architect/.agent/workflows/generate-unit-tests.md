---
description: This workflow addresses the "Verification" phase of the development lifecycle. The goal is to produce robust, meaningful tests, not just tests that pass (false positives)
---

# Workflow: Generate Unit Tests

**Trigger**: `/generate-unit-tests`

**Context**: The user wants robust verification with pytest and unittest.mock.

---

## Phase 1: Analyze & Plan

// turbo
1. **Identify the target file** and its public interfaces (functions, classes, methods).

2. **List all dependencies** that require mocking:
   - External APIs (OpenRouter, OpenAI)
   - Database connections (ChromaDB)
   - File system operations (PDF parsing with Docling)
   - LLM calls (Instructor)

3. **Assess complexity**: Identify areas with high cyclomatic complexity (nested conditionals, multiple branches).

4. **Output a Test Plan**: List the test cases you will implement:
   - **Happy Path**: Standard successful execution
   - **Edge Cases**: None values, empty lists, malformed inputs
   - **Error States**: API failures, validation errors, timeout handling

> [!IMPORTANT]
> **STOP**: Wait for user approval of the plan before writing code.

---

## Phase 2: Implementation

1. **Create/Update the test file** in `tests/test_<module_name>.py`.

2. **Set up fixtures**:
   ```python
   import pytest
   from unittest.mock import MagicMock, patch
   
   @pytest.fixture
   def mock_dependencies():
       with patch("core.module.ExternalDependency") as mock:
           yield mock.return_value
   ```

3. **Implement test cases** using the plan from Phase 1:
   - Use behavior-driven descriptions: `def test_extract_raises_error_when_chunks_empty()`
   - Follow the **Arrange → Act → Assert** pattern
   - Keep tests atomic and independent

4. **Mock all external services**:
   - Never hit live APIs
   - Use `MagicMock` for complex return values
   - Use `side_effect` for simulating errors

---

## Phase 3: Verification

// turbo
1. **Run the tests**:
   ```bash
   cd ~/Projects/research-projects/SR-architect && pytest tests/test_<module>.py -v
   ```

2. **Analyze failures**:
   - Is the test incorrect (bad assertion/mock setup)?
   - Is the source code buggy?

3. **Decision tree**:
   - If **source bug detected**: Report to user. Do NOT auto-fix source code.
   - If **test bug detected**: Fix the test and re-run.

4. **Report final status**:
   ```
   ✅ Added 4 tests to tests/test_extractor.py
   - test_extract_returns_data_on_success: PASSED
   - test_extract_handles_empty_chunks: PASSED
   - test_extract_raises_on_api_failure: PASSED
   - test_extract_validates_schema: PASSED
   ```

---

## Example Output

For a file `core/extractor.py` with class `StructuredExtractor`:

```python
# tests/test_extractor.py
import pytest
from unittest.mock import MagicMock, patch
from core.extractor import StructuredExtractor

@pytest.fixture
def mock_instructor():
    with patch("core.extractor.instructor") as mock:
        yield mock

def test_extract_with_evidence_returns_structured_data(mock_instructor):
    """Happy path: extraction returns data with evidence quotes."""
    mock_response = MagicMock()
    mock_response.data = {"field": "value"}
    mock_response.evidence = ["Quote from paper"]
    mock_instructor.from_openai().chat.completions.create.return_value = mock_response
    
    extractor = StructuredExtractor(provider="test")
    result = extractor.extract_with_evidence(chunks=["text"], schema=SampleSchema)
    
    assert result.data["field"] == "value"
    assert len(result.evidence) == 1

def test_extract_handles_empty_chunks():
    """Edge case: empty chunk list returns None gracefully."""
    extractor = StructuredExtractor(provider="test")
    result = extractor.extract_with_evidence(chunks=[], schema=SampleSchema)
    assert result is None
```
