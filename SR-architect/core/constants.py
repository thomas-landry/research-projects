"""
Algorithm constants for SR-Architect.

These are domain-specific values that rarely change.
Separate from config.py which contains runtime/tunable parameters.
"""

# === LLM Retry Logic ===
MAX_LLM_RETRIES = 3
MAX_LLM_RETRIES_ASYNC = 2

# === Validation Weights ===
VALIDATION_WEIGHT_COMPLETENESS = 0.6
VALIDATION_WEIGHT_ACCURACY = 0.4

# === Batch Processing ===
DEFAULT_BATCH_SIZE = 10
DEFAULT_PREVIEW_CHARS = 500

# === Sentence Extraction ===
SENTENCE_CONTEXT_WINDOW = 2
SENTENCE_CONCURRENCY_LIMIT = 10

# === Relevance Classification ===
RELEVANCE_BATCH_SIZE = 10
RELEVANCE_PREVIEW_CHARS = 500
