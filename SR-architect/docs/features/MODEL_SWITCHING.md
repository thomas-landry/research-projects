# Model Switching & Configuration

**Last Updated:** 2026-01-08

SR-Architect supports multiple LLM providers and models, with a focus on ease of switching between cost-optimized cloud models and local privacy-focused models.

## Quick Switching (Aliases)

You can use short aliases instead of full model paths with the `--model` flag:

| Alias | Full Model String | Use Case |
|-------|-------------------|----------|
| `gemini` | `google/gemini-2.5-flash-lite` | **Default**. Lowest cost ($0.10/M tokens). High speed. |
| `flash` | `google/gemini-2.5-flash-lite` | Same as `gemini`. |
| `sonnet` | `anthropic/claude-3.5-sonnet` | High reasoning capability. Best for complex logic. |
| `haiku` | `anthropic/claude-3-haiku` | Fast, cheap alternative to Sonnet. |
| `gpt4o` | `openai/gpt-4o` | General purpose high performance. |
| `llama3` | `llama3.1:8b` | **Local**. Requires Ollama. Privacy & Zero cost. |

### Examples

```bash
# Run with default (Gemini Flash Lite)
python cli.py extract ./papers

# Switch to Claude Sonnet for difficult papers
python cli.py extract ./papers --model sonnet

# Run locally with Llama 3 (requires Ollama running)
python cli.py extract ./papers --model llama3 --provider ollama
```

## Provider Configuration

### OpenRouter (Default)
Set your key in `.env`:
```bash
OPENROUTER_API_KEY=sk-...
DEFAULT_OPENROUTER_MODEL=google/gemini-2.5-flash-lite
```

### Ollama (Local)
Ensure Ollama is running (`ollama serve`).
```bash
# In .env
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.1:8b
```

## Hybrid Mode
The pipeline defaults to `--hybrid-mode`, which routes simpler extraction tasks to smaller local models (if available) or simpler logic, reserving the main LLM for complex reasoning.
