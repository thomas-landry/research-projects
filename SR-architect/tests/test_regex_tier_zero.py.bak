"""Tests for Tier 0 RegexExtractor integration in pipeline.

This test suite follows TDD methodology (RED phase).
Tests verify that RegexExtractor is properly integrated into
HierarchicalExtractionPipeline for cost-optimized extraction.
"""
import pytest
from core.hierarchical_pipeline import HierarchicalExtractionPipeline
from core.regex_extractor import RegexExtractor


class TestRegexIntegration:
    """Test RegexExtractor is properly integrated into the pipeline."""
    
    def test_pipeline_has_regex_extractor(self):
        """Verify RegexExtractor is initialized in pipeline."""
        pipeline = HierarchicalExtractionPipeline()
        assert hasattr(pipeline, 'regex_extractor'), "Pipeline missing regex_extractor attribute"
        assert pipeline.regex_extractor is not None, "regex_extractor should not be None"
    
    def test_regex_extractor_is_correct_type(self):
        """Verify regex_extractor is the right class."""
        pipeline = HierarchicalExtractionPipeline()
        assert isinstance(pipeline.regex_extractor, RegexExtractor), \
            "regex_extractor should be instance of RegexExtractor"
    
    def test_doi_extracted_via_regex(self):
        """Verify DOI is extracted via regex before LLM."""
        pipeline = HierarchicalExtractionPipeline()
        text = "This paper has DOI: 10.1234/test.2024.example"
        
        # Extract using regex
        results = pipeline.regex_extractor.extract_all(text)
        
        assert "doi" in results, "DOI should be extracted by regex"
        assert "10.1234/test.2024.example" in results["doi"].value, \
            "Extracted DOI should match the pattern in text"
    
    def test_publication_year_extracted_via_regex(self):
        """Verify publication year is extracted via regex."""
        pipeline = HierarchicalExtractionPipeline()
        text = "Published: 2024. Copyright 2024."
        
        results = pipeline.regex_extractor.extract_all(text)
        
        assert "publication_year" in results, "Publication year should be extracted"
        assert results["publication_year"].value == "2024", \
            "Extracted year should be 2024"
    
    def test_regex_results_high_confidence(self):
        """Verify regex results have high confidence scores."""
        pipeline = HierarchicalExtractionPipeline()
        text = "DOI: 10.1000/xyz123. Published 2023."
        
        results = pipeline.regex_extractor.extract_all(text)
        
        # Regex extractions should have high confidence (>= 0.90)
        for field_name, result in results.items():
            assert result.confidence >= 0.90, \
                f"{field_name} should have confidence >= 0.90, got {result.confidence}"
    
    def test_regex_extractor_extract_all_method_exists(self):
        """Verify RegexExtractor has extract_all method."""
        pipeline = HierarchicalExtractionPipeline()
        assert hasattr(pipeline.regex_extractor, 'extract_all'), \
            "RegexExtractor should have extract_all method"
        assert callable(pipeline.regex_extractor.extract_all), \
            "extract_all should be callable"
