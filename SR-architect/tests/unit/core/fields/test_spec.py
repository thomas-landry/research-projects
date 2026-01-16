"""
Tests for ColumnSpec - Phase 2 of Semantic Schema.

Following TDD: Write tests first, verify they fail, then implement.
"""

import pytest
from pydantic.fields import FieldInfo


class TestColumnSpec:
    """Tests for ColumnSpec class."""
    
    def test_column_spec_basic_creation(self):
        """ColumnSpec captures field metadata."""
        from core.fields.spec import ColumnSpec
        from core.types.models import FindingReport
        from core.types.enums import ExtractionPolicy
        
        spec = ColumnSpec(
            key="ct_ground_glass",
            dtype=FindingReport,
            description="Ground glass opacity on CT",
            extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
            source_narrative_field="ct_narrative",
            high_confidence_keywords=["GGO", "ground glass"],
            requires_evidence_quote=True,
        )
        
        assert spec.key == "ct_ground_glass"
        assert spec.dtype == FindingReport
        assert spec.extraction_policy == ExtractionPolicy.MUST_BE_EXPLICIT
        assert "GGO" in spec.high_confidence_keywords
    
    def test_column_spec_to_field_returns_pydantic_field(self):
        """to_field() generates valid Pydantic Field."""
        from core.fields.spec import ColumnSpec
        from core.types.models import FindingReport
        from core.types.enums import ExtractionPolicy
        
        spec = ColumnSpec(
            key="ct_ground_glass",
            dtype=FindingReport,
            description="Ground glass opacity",
            extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
        )
        
        field = spec.to_field()
        
        assert isinstance(field, FieldInfo)
        assert field.description == "Ground glass opacity"
        assert field.default is None
    
    def test_column_spec_field_preserves_metadata(self):
        """to_field() preserves extraction policy in metadata."""
        from core.fields.spec import ColumnSpec
        from core.types.models import FindingReport
        from core.types.enums import ExtractionPolicy
        
        spec = ColumnSpec(
            key="ct_ground_glass",
            dtype=FindingReport,
            description="GGO",
            extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
            high_confidence_keywords=["GGO"],
        )
        
        field = spec.to_field()
        
        # Metadata should be accessible
        assert "column_spec" in field.json_schema_extra
        assert field.json_schema_extra["column_spec"]["key"] == "ct_ground_glass"


class TestGenerateExtractionPrompt:
    """Tests for generate_extraction_prompt function."""
    
    def test_generate_extraction_prompt_explicit_policy(self):
        """Prompts for MUST_BE_EXPLICIT require explicit mention."""
        from core.fields.spec import ColumnSpec, generate_extraction_prompt
        from core.types.models import FindingReport
        from core.types.enums import ExtractionPolicy
        
        spec = ColumnSpec(
            key="ct_ground_glass",
            dtype=FindingReport,
            description="Ground glass opacity",
            extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
            high_confidence_keywords=["GGO", "ground glass"],
        )
        
        prompt = generate_extraction_prompt(spec, "CT showed bilateral GGO...")
        
        assert "explicit" in prompt.lower()
        assert "GGO" in prompt or "ground glass" in prompt
    
    def test_generate_extraction_prompt_metadata_policy(self):
        """Prompts for METADATA are simpler."""
        from core.fields.spec import ColumnSpec, generate_extraction_prompt
        from core.types.enums import ExtractionPolicy
        
        spec = ColumnSpec(
            key="title",
            dtype=str,
            description="Article title",
            extraction_policy=ExtractionPolicy.METADATA,
        )
        
        prompt = generate_extraction_prompt(spec, "Title: Some paper...")
        
        assert "title" in prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
