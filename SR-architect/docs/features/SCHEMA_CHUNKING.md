# Schema Chunking for Cost Optimization

**Last Updated:** 2026-01-08

Schema chunking automatically splits large extraction schemas into smaller batches to work around grammar complexity limits in cost-effective models like Gemini Flash Lite.

## The Problem

Models like `google/gemini-2.5-flash-lite` have strict grammar complexity limits for structured output. Schemas with >30 fields fail with:
```
400 Bad Request: "The specified schema produces a constraint that has too many states for serving."
```

This forces users to expensive models like Claude Sonnet ($9.96 for 83 papers vs $0.11 with Gemini).

## The Solution

**Automatic Schema Chunking** splits large schemas into multiple smaller extractions per document, then merges the results.

### How It Works

1. **Detection**: If schema has >30 fields, chunking is automatically enabled
2. **Splitting**: Schema is divided into chunks of ~25 fields each
3. **Extraction**: Each chunk runs as a separate LLM call
4. **Merging**: Results are combined into a single CSV row

### Example

For an 80-field schema:
- **Without chunking**: 1 extraction × $9.96 (Claude) = $9.96
- **With chunking**: 4 extractions × $0.11 (Gemini) = $0.44

**96% cost savings** 🎉

## Usage

### Automatic (Recommended)

Chunking is **enabled by default** for schemas >30 fields:

```bash
python3 cli.py extract ./papers \\
  --schema template.csv \\
  --model gemini
```

Output:
```
📦 Large Schema Detected
  Total fields: 80
  Chunks: 4
  Fields per chunk: ~25
  This will run 4 extractions per paper for cost optimization.
```

### Manual Control

```bash
# Disable chunking
python3 cli.py extract ./papers --no-chunk-schema

# Adjust chunk size
python3 cli.py extract ./papers --max-fields-per-chunk 20
```

## Technical Details

### Field Pairing
Each field with `include_quote=True` is treated as a unit (field + `_quote` field stay together).

### Metadata Handling
Metadata fields (`filename`, `extraction_confidence`, `extraction_notes`) are included in every chunk.

### Confidence Averaging
The final `extraction_confidence` is the average across all chunks.

## Limitations

- **Increased API calls**: 4× chunks = 4× API calls per document
- **Slightly slower**: Sequential chunk processing adds latency
- **Not needed for small schemas**: Schemas <30 fields work fine without chunking

## Cost Comparison

| Schema Size | Model | Chunks | Cost/Paper | Total (83 papers) |
|-------------|-------|--------|------------|-------------------|
| 80 fields | Claude Sonnet | 1 | $0.12 | $9.96 |
| 80 fields | Gemini Flash (chunked) | 4 | $0.005 | $0.44 |
| 25 fields | Gemini Flash | 1 | $0.001 | $0.11 |

## See Also

- [CSV Schema Inference](CSV_SCHEMA_INFERENCE.md) - Automatic schema generation from templates
- [Model Switching](MODEL_SWITCHING.md) - Choosing the right model
