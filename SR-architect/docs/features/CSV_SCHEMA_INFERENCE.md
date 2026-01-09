# CSV Schema Inference

**Last Updated:** 2026-01-08

The **CSV Schema Inference** feature allows SR-Architect to automatically derive an extraction schema from a target CSV template. This eliminates the need for manual mapping of columns to Pydantic models.

## How It Works

When you provide a CSV file to the `--schema` argument, the system:
1.  **Reads the Header**: Identifies column names from the second line (index 1) of the CSV (standard for our templates).
2.  **Analyzes Data**: Inspects subsequent rows to infer data types:
    *   **Integer**: Columns containing only integers or 0/1 flags.
    *   **Float**: Columns with decimal values.
    *   **Text**: All other columns.
3.  **Generates Schema**: dynamically builds a Pydantic model with `FieldDefinition` objects for each column.

## Usage

```bash
python cli.py extract ./papers \
  --schema "./data/Systematic data template CSV.csv" \
  --output ./output/results.csv
```

## Field Inference Rules

| CSV Data Type | Inferred Field Type | Notes |
|---------------|---------------------|-------|
| `0` / `1` | `Integer` | Treated as binary flags |
| `123` | `Integer` | Standard counts |
| `12.5` | `Float` | Continuous variables |
| "Text..." | `Text` | Narrative fields |

## Benefits

*   **Zero Configuration**: No need to write Python code for new systematic reviews.
*   **Exact Alignment**: The output CSV is guaranteed to have the same columns as the template.
*   **Traceability**: Automatically adds `_quote` fields for every extracted variable to track source provenance.

## Known Limitations

### Gemini Flash Lite & Large Schemas
When using `google/gemini-2.0-flash-lite-001` with large schemas (>50 fields), you will encounter a `400 Bad Request` error:
`"The specified schema produces a constraint that has too many states for serving."`

**Cause**: Gemini Flash Lite has strict grammar complexity limits. Even with all fields marked as required, 80+ fields with quote fields (~160 total keys) exceeds the model's constraint solver capacity.

**Solution**: Use **[Schema Chunking](SCHEMA_CHUNKING.md)** (automatic for schemas >30 fields):
- Splits schema into chunks of ~25 fields
- Runs multiple extractions per document
- Merges results automatically
- **Cost**: $0.44 vs $9.96 (96% savings)

Alternatively, use a more capable model:
- `anthropic/claude-3.5-sonnet` (handles any schema size)
- `openai/gpt-4o`

