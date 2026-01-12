"""Tests for TwoPassExtractor integration in pipeline.

Verifies that TwoPassExtractor is properly initialized and can be used
for local-first extraction strategy.
"""
import pytest
from core.hierarchical_pipeline import HierarchicalExtractionPipeline
from core.two_pass_extractor import TwoPassExtractor, ExtractionTier


class TestTwoPassIntegration:
    """Test TwoPassExtractor is properly integrated into the pipeline."""
    
    def test_pipeline_has_two_pass_extractor(self):
        """Verify TwoPassExtractor is initialized in pipeline."""
        pipeline = HierarchicalExtractionPipeline()
        assert hasattr(pipeline, 'two_pass_extractor'), "Pipeline missing two_pass_extractor attribute"
        assert pipeline.two_pass_extractor is not None, "two_pass_extractor should not be None"
    
    def test_two_pass_extractor_is_correct_type(self):
        """Verify two_pass_extractor is the right class."""
        pipeline = HierarchicalExtractionPipeline()
        assert isinstance(pipeline.two_pass_extractor, TwoPassExtractor), \
            "two_pass_extractor should be instance of TwoPassExtractor"
    
    def test_two_pass_extractor_has_correct_models(self):
        """Verify TwoPassExtractor is configured with correct models."""
        pipeline = HierarchicalExtractionPipeline()
        assert pipeline.two_pass_extractor.local_model == "qwen3:14b", \
            "Local model should be qwen3:14b per model_evaluation.md"
        assert pipeline.two_pass_extractor.cloud_model == "gpt-4o-mini", \
            "Cloud model should be gpt-4o-mini"
    
    def test_hybrid_mode_disabled_by_default(self):
        """Verify hybrid mode is disabled by default."""
        pipeline = HierarchicalExtractionPipeline()
        assert pipeline.hybrid_mode is False, "Hybrid mode should be disabled by default"
    
    def test_set_hybrid_mode(self):
        """Verify hybrid mode can be enabled."""
        pipeline = HierarchicalExtractionPipeline()
        pipeline.set_hybrid_mode(True)
        assert pipeline.hybrid_mode is True, "Hybrid mode should be enabled"
        
        pipeline.set_hybrid_mode(False)
        assert pipeline.hybrid_mode is False, "Hybrid mode should be disabled"
    
    def test_two_pass_extractor_has_cascader(self):
        """Verify TwoPassExtractor has ModelCascader initialized."""
        pipeline = HierarchicalExtractionPipeline()
        assert hasattr(pipeline.two_pass_extractor, 'cascader'), \
            "TwoPassExtractor should have cascader attribute"
        assert pipeline.two_pass_extractor.cascader is not None, \
            "cascader should not be None"
    
    def test_two_pass_extract_method_exists(self):
        """Verify TwoPassExtractor has extract method."""
        pipeline = HierarchicalExtractionPipeline()
        assert hasattr(pipeline.two_pass_extractor, 'extract'), \
            "TwoPassExtractor should have extract method"
        assert callable(pipeline.two_pass_extractor.extract), \
            "extract should be callable"
    
    def test_two_pass_extractor_basic_extraction(self):
        """Test basic two-pass extraction functionality."""
        pipeline = HierarchicalExtractionPipeline()
        
        # Test with simple text
        text = "DOI: 10.1234/test. Published 2024. Sample size: n=50."
        fields = ["doi", "publication_year", "sample_size"]
        
        result = pipeline.two_pass_extractor.extract(text, fields, confidence_threshold=0.85)
        
        # Verify result structure
        assert hasattr(result, 'extracted_fields'), "Result should have extracted_fields"
        assert hasattr(result, 'escalated_fields'), "Result should have escalated_fields"
        assert hasattr(result, 'pass1_only_count'), "Result should have pass1_only_count"
        assert hasattr(result, 'pass2_needed_count'), "Result should have pass2_needed_count"
        
        # Verify all fields were attempted
        assert len(result.extracted_fields) == len(fields), \
            f"Should have results for all {len(fields)} fields"
