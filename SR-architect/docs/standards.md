# SR-Architect Coding Standards

## Core Principles

1.  **AgentOS-Style Architecture**:
    *   **Core**: Pure processing logic, stateless where possible.
    *   **Agents**: Autonomous entities with distinct responsibilities (`Screener`, `Librarian`, `Extractor`).
    *   **State**: All cross-component communication via typed Pydantic models.

2.  **PRISMA Compliance**:
    *   Strict adherence to PRISMA 2020 guidelines.
    *   All exclusions MUST have a recorded reason.
    *   Provenance is mandatory (source file, date, agent version).

3.  **Typer/Rich CLI**:
    *   All user interaction via the CLI.
    *   Use `Rich` for beautiful, informative output.

## Code Structure

*   **Imports**: Standard lib -> Third party -> Local (absolute paths).
*   **Typing**: Strong typing enforced. Use `Optional`, `List`, `Dict`, `TypeVar`.
*   **Error Handling**: specific exceptions (avoid bare `Exception`). Bubble up errors with context.

## Specific Patterns

### Agent Implementation
Agents generally follow this input/output pattern:
```python
def agent_action(state: InputState) -> OutputState:
    # Logic
    return new_state
```

### LLM Interaction
*   Use `StructuredExtractor` wrapper for all LLM calls.
*   **Never** call `openai` or `requests` directly in business logic (wrap in `core` utilities).
*   Use `Pydantic` models for ALL LLM outputs.

### Logging & Auditing
*   Use `AuditLogger` for business events (extraction success/fail).
*   CLI feedback via `rich.console`.

## File Organization
*   `core/`: Shared utilities, heavy lifting (parsing, extraction, vector DB).
*   `agents/`: Autonomous workers (Screener, Librarian).
*   `docs/`: Configuration and standards.
*   `tests/`: Pytest suite.

## Git & Versioning
*   Semantic versioning.
*   Conventional commits (feat, fix, docs, refactor).
