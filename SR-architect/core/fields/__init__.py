"""Core fields package for semantic schema."""

from core.fields.spec import ColumnSpec, generate_extraction_prompt
from core.fields.library import FieldLibrary

__all__ = ["ColumnSpec", "generate_extraction_prompt", "FieldLibrary"]
