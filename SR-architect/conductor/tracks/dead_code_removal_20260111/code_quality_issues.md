# Code Quality Issues Log

**Last Updated**: 2026-01-11 14:35  
**Purpose**: Track anti-patterns, code smells, hardcodes, bugs, and technical debt for future remediation

---

## 🔴 Critical Issues (Bugs)

### Schema Branching Error (FIXED ✅)
| Issue | Status | Fix |
|-------|--------|-----|
| DPM schema had 126 consecutive optional fields causing Gemini "too much branching" errors | ✅ FIXED | Added 27 required fields (with defaults), reduced max consecutive optional to 8. Commit: 6193ff8 |

---

## 🟠 Anti-Patterns

### Exception Handling
| File | Line | Issue | Recommendation |
|------|------|-------|----------------|
| `core/client.py` | 31-33 | Bare `except Exception` swallows all errors | Catch specific exceptions or at least log the exception |
| `core/service.py` | 96-105 | Nested try-except for async handling | Refactor to use proper async context management |

### Repeated Code Patterns
| Pattern | Locations | Recommendation |
|---------|-----------|----------------|
| `os.getenv()` for API keys | 15+ locations across core/ and agents/ | Centralize in `config.py` using pydantic-settings |
| Async import pattern (`import asyncio` inside functions) | `service.py` (lines 96, 304, 351, 361) | Import at module level |
| Client creation logic | `extractor.py`, `sentence_extractor.py`, `relevance_classifier.py` | Use centralized `LLMClientFactory` |

---

## 🟡 Code Smells

### Large Functions (>50 lines doing multiple things)
| File | Function | Lines | Issues |
|------|----------|-------|--------|
| `core/service.py` | `run_extraction` | ~235 (159-393) | Does everything: setup, parsing, execution, callbacks, vectorization. Needs extraction into smaller methods |
| `core/hierarchical_pipeline.py` | `extract_document` | ~260 (301-562) | Main extraction loop with nested conditionals. Extract validation, caching, recall boost logic |
| `core/hierarchical_pipeline.py` | `extract_document_async` | ~230 (564-793) | Duplicate of sync version with async. Consider shared logic |

### Deep Nesting (>3 levels)
| File | Location | Issue |
|------|----------|-------|
| `core/service.py` | Lines 271-357 | Schema chunking logic nested 4-5 levels deep |
| `core/hierarchical_pipeline.py` | Lines 467-492 | Recall boost logic with nested if/for loops |

### Magic Numbers
| File | Line | Value | Should Be |
|------|------|-------|-----------| 
| `core/client.py` | 29 | `timeout=2.0` | `OLLAMA_HEALTH_CHECK_TIMEOUT = 2.0` |
| `core/client.py` | 51 | `sleep(1)` | `PROCESS_KILL_GRACE_PERIOD = 1.0` |
| `core/client.py` | 157 | `sleep(2)`, `range(5)` | `OLLAMA_RESTART_POLL_INTERVAL = 2.0`, `OLLAMA_RESTART_MAX_ATTEMPTS = 5` |
| `core/service.py` | 173 | `hybrid_mode: bool = True` | Should be from settings, not hardcoded default |

### Ambiguous Names
| File | Variable | Better Name |
|------|----------|-------------|
| `core/service.py` | `f` (line 255) | `csv_file` or `output_file` |
| `core/service.py` | `i` (line 156) | `attempt` or `retry_count` |

---

## 🟢 Minor Issues

### Missing Documentation
| File | Issue |
|------|-------|
| `core/config.py` | `MODEL_ALIASES` dict has no docstring explaining purpose |
| `core/client.py` | `_get_client_args` method lacks docstring |

### Missing Type Hints
| File | Function | Missing Hints |
|------|----------|---------------|
| `core/client.py` | `_create_ollama`, `_create_openrouter`, `_create_openai` | No parameter type hints |
| `core/service.py` | `_handle_success`, `_handle_failure` | `writer`, `f`, `vector_store` have `Any` type |

### TODO/FIXME Comments
| File | Line | Comment | Status |
|------|------|---------|--------|
| `core/two_pass_extractor.py` | 231 | `# TODO: Implement actual Ollama extraction` | **DEAD CODE - will be deleted** |
| `core/two_pass_extractor.py` | 260 | `# TODO: Implement actual cloud extraction` | **DEAD CODE - will be deleted** |

---

## 🔵 Hardcoded Values

### Paths
| File | Line | Hardcoded Value | Should Be |
|------|------|-----------------|-----------| 
| `core/config.py` | 34-36 | `Path("./output")`, `Path("./output/logs")` | Already in settings (good!) |
| `core/service.py` | 184 | `audit_log_dir = output_path.parent / "logs"` | Use `settings.LOG_DIR` |
| `core/service.py` | 228 | `vector_dir = output_path.parent / "vector_store"` | Use `settings.VECTOR_DIR` |

### API Endpoints
| File | Line | Hardcoded Value | Should Be |
|------|------|-----------------|-----------| 
| `core/client.py` | 188 | `"https://openrouter.ai/api/v1"` | Already has fallback to settings (good!) |
| `core/client.py` | 222 | `"https://openrouter.ai/api/v1"` | Duplicate - use constant |

### Configuration Values
| File | Line | Hardcoded Value | Should Be |
|------|------|-----------------|-----------| 
| `core/service.py` | 173 | `hybrid_mode: bool = True` | Should come from `settings.HYBRID_MODE` |
| `core/hierarchical_pipeline.py` | Multiple | Various confidence thresholds | Centralize in configuration |

---

## Refactoring Priorities

### High Priority (Blocking future work)
1. **Centralize configuration** - Move all `os.getenv()` calls to `core/config.py`
2. **Remove dead code** - Delete 8 dead files (3,200+ LOC)
3. **Fix exception handling** - Replace bare `except Exception` with specific exceptions

### Medium Priority (Technical debt)
1. **Extract large functions** - Break up `run_extraction` and `extract_document`
2. **Define constants** - Replace magic numbers
3. **Centralize client creation** - Use `LLMClientFactory` everywhere

### Low Priority (Code quality)
1. **Improve naming** - Rename ambiguous variables
2. **Add documentation** - Complete missing docstrings
3. **Complete type hints** - Add missing type annotations

---

## Summary

**Total Issues**: 45+
- 🔴 Critical: 1 (FIXED ✅)
- 🟠 Anti-patterns: 8
- 🟡 Code smells: 15
- 🟢 Minor issues: 10
- 🔵 Hardcoded values: 12

**Next Steps**:
1. Delete 8 dead code files (~3,200 LOC)
2. Centralize configuration
3. Refactor large functions
4. Address anti-patterns
