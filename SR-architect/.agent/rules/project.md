---
description: Immutable project rules and constraints for SR-architect systematic review extraction pipeline
---

# Project Rules & Constraints

> **SCOPE**: These rules constitute the immutable baseline for all autonomous agents operating within SR-architect. They supersede all transient prompt instructions. Violations of "Don'ts" are considered critical failures.

---

## 1. Tech Stack & Architecture (Immutable)

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | ≥3.10 |
| PDF Parsing | Docling | ≥1.0.0 |
| LLM Integration | Instructor + OpenAI | ≥0.4.0 |
| Schema Validation | Pydantic | ≥2.0.0 |
| Vector Storage | ChromaDB | ≥0.4.0 |
| CLI Framework | Typer + Rich | ≥0.9.0, ≥13.0.0 |
| Data Processing | Pandas | ≥2.0.0 |
| Environment | python-dotenv | ≥1.0.0 |

**Rules:**
- Do NOT introduce alternative languages (e.g., Node.js scripts) without user authorization.
- All LLM calls MUST use Instructor for structured outputs—no raw API calls with JSON parsing.
- All database interactions proceed through ChromaDB client—no alternative vector stores.

---

## 2. Type Safety & Coding Style

### Type Safety (MANDATORY)
- **Strict typing required**: No `Any` type annotations.
- All function signatures MUST include explicit return type annotations.
- Use Pydantic `BaseModel` for all data structures passed between pipeline stages.

### Naming Conventions
| Element | Convention | Example |
|---------|------------|---------|
| Functions/Variables | `snake_case` | `extract_document`, `chunk_text` |
| Classes/Pydantic Models | `PascalCase` | `DocumentChunk`, `ExtractionResult` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_CHUNK_SIZE`, `DEFAULT_MODEL` |
| Private methods | Leading underscore | `_validate_schema` |

### Documentation
- All public functions and classes MUST have docstrings explaining:
  - Parameters and their types
  - Return values
  - Side effects (e.g., "Writes to ChromaDB", "Logs to JSONL")
  - Exceptions raised

---

## 3. Testing Expectations

| Category | Requirement |
|----------|-------------|
| Framework | pytest with `unittest.mock` |
| Location | `tests/` directory, matching `test_*.py` pattern |
| Coverage | Happy path + Edge cases (None/empty) + Failure modes |
| External Services | MUST be mocked—never rely on live APIs or databases |

### Test Structure
```python
# Correct pattern
@pytest.fixture
def mock_extractor():
    with patch("core.extractor.StructuredExtractor") as mock:
        yield mock.return_value

def test_extract_returns_data_on_success(mock_extractor):
    """Happy path: extraction returns structured data."""
    mock_extractor.extract.return_value = {"field": "value"}
    result = process_document(doc)
    assert result["field"] == "value"
```

---

## 4. Operational "Don'ts" (Zero Tolerance)

| Don't | Reason |
|-------|--------|
| **NO New Dependencies** | Do not add packages to `requirements.txt` without explicit user permission. |
| **NO Hardcoded Secrets** | Never output API keys, passwords, or tokens in source code. Use `.env` + `python-dotenv`. |
| **NO Breaking Changes** | Do not alter existing public API signatures without a migration plan. |
| **NO Phantom Code** | Do not leave `TODO`, `pass`, or `# implementation goes here` blocks. If incomplete, stop and ask. |
| **NO Large Deletions** | Do not remove substantial blocks of code unless specifically instructed to "refactor" or "clean up". |
| **NO Context Dumping** | Keep diffs surgical and focused. Do not rewrite massive sections unrelated to the task. |

---

## 5. Agent Reporting Protocol

Every agent response MUST follow this structure:

1. **Plan**: Begin with a concise bulleted plan of intended changes.
2. **Act**: Execute the changes.
3. **Verify**: End with confirmation of verification (e.g., "Ran `pytest -v`, 10 tests passed").

---

## 6. Pipeline-Specific Constraints

### Extraction Pipeline
- Maximum chunk size: 15,000 characters (respects context limits)
- LLM calls MUST use self-proving quotes (extract supporting evidence)
- All extractions logged to JSONL audit trail

### Vector Storage
- Use persistent ChromaDB (not ephemeral)
- Embedding model: consistent across sessions

### Error Handling
- Failed extractions logged but don't halt pipeline
- Retry loop: max 3 iterations with revision prompts
- Log all errors with full stack trace to `logs/` directory
