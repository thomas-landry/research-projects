# Refactoring Patterns

This document describes the established patterns for refactoring large files in the SR-architect codebase.

## Module Structure Pattern

When splitting large files (>400 lines), use this consistent structure:

```
core/module_name/
├── __init__.py       # Exports all public API
├── models.py         # Pydantic models, dataclasses
├── helpers.py        # Pure functions (optional)
└── main_class.py     # Business logic
```

### Successfully Applied To

1. **`core/validation/`** (from `extraction_checker.py`, 517 lines)
   - `models.py` - CheckerResult, Issue, CheckerResponse
   - `formatters.py` - Pure formatting functions
   - `checker.py` - ExtractionChecker class

2. **`core/extractors/`** (from `extractor.py`, 715 lines)
   - `models.py` - EvidenceItem, ExtractionWithEvidence, EvidenceResponse
   - `extractor.py` - StructuredExtractor class

3. **`core/classification/`** (from `relevance_classifier.py`, 474 lines)
   - `models.py` - RelevanceResult, ChunkRelevance, RelevanceResponse
   - `helpers.py` - truncate_chunk, build_batch_prompt
   - `classifier.py` - RelevanceClassifier class

## TDD Workflow Pattern

All refactorings follow strict Test-Driven Development:

### Phase 1: Models (RED → GREEN)
1. **RED**: Write failing tests for models
   ```bash
   pytest tests/test_module_models.py -v
   # Expected: ModuleNotFoundError
   ```
2. **Commit RED**: `test(TDD RED): Add failing tests for module models`
3. **GREEN**: Create `module/models.py` with minimal implementation
4. **Verify GREEN**: All model tests pass
5. **Commit GREEN**: `feat(TDD GREEN): Extract module models`

### Phase 2: Helpers (RED → GREEN) - Optional
1. **RED**: Write failing tests for helper functions
2. **Commit RED**: `test(TDD RED): Add failing tests for module helpers`
3. **GREEN**: Create `module/helpers.py` with pure functions
4. **Verify GREEN**: All helper tests pass
5. **Commit GREEN**: `feat(TDD GREEN): Extract module helpers`

### Phase 3: Main Class (GREEN)
1. **GREEN**: Extract main class to `module/main_class.py`
2. Update imports to use new models and helpers
3. **Verify GREEN**: All existing tests still pass
4. **Commit GREEN**: `feat(TDD GREEN): Extract MainClass to module`

### Phase 4: Integration
1. Find all imports: `grep -r "from core.old_file import" .`
2. Update all imports systematically
3. Remove old file: `git rm core/old_file.py`
4. **Verify**: Run full test suite
5. **Commit**: `refactor(Task X COMPLETE): Split old_file.py into module`

## Benefits

### Modularity
- Small, focused files (avg 200 lines vs 500+ lines)
- Single Responsibility Principle
- Easy to navigate and understand

### Testability
- Pure functions are trivial to test
- Models can be tested in isolation
- Business logic has clear dependencies

### Maintainability
- Changes are localized to specific files
- Clear boundaries between concerns
- Safe refactoring with test coverage

## Guidelines

### When to Split a File
- File exceeds 400 lines
- Multiple responsibilities in one file
- Difficult to test or understand
- High cyclomatic complexity

### What to Extract First
1. **Models** - Data structures (Pydantic, dataclasses)
2. **Helpers** - Pure functions with no side effects
3. **Main class** - Business logic using models and helpers

### Naming Conventions
- `models.py` - Always for data structures
- `helpers.py` - For pure utility functions
- `{domain}.py` - For main business logic (e.g., `checker.py`, `classifier.py`, `extractor.py`)

## Testing Requirements

### Minimum Coverage
- **Models**: Test creation, validation, edge cases
- **Helpers**: Test all code paths, edge cases, empty inputs
- **Main class**: Existing tests must continue to pass

### Test Organization
```
tests/
├── test_module_models.py    # Model tests
├── test_module_helpers.py   # Helper tests (if applicable)
└── test_module.py            # Integration tests (existing)
```

## Example: Splitting a 500-line File

```python
# Before: core/big_file.py (500 lines)
class BigClass:
    def __init__(self): ...
    def process(self): ...
    def _helper(self): ...

class DataModel(BaseModel): ...
```

```python
# After: core/big_module/

# models.py
class DataModel(BaseModel): ...

# helpers.py
def helper_function(data): ...

# processor.py
from .models import DataModel
from .helpers import helper_function

class BigClass:
    def __init__(self): ...
    def process(self): ...
```

## Commit Message Format

```
type(scope): description

Task X.Y - TDD Phase

Detailed explanation of changes.
Tests: X/X passing ✅
```

**Types**: `test`, `feat`, `refactor`  
**Scopes**: `TDD RED`, `TDD GREEN`, `Task X.Y COMPLETE`

## References

- [walkthrough.md](file:///Users/thomaslandry/.gemini/antigravity/brain/e5bfd937-aa35-4477-af50-78548734884c/walkthrough.md) - Detailed session summary
- [task.md](file:///Users/thomaslandry/.gemini/antigravity/brain/e5bfd937-aa35-4477-af50-78548734884c/task.md) - Progress tracker
- `/test-driven-development` workflow - TDD guidelines
- `/refactor-for-clarity` workflow - Code quality standards
