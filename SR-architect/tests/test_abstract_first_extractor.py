"""
Unit tests for AbstractFirstExtractor.
Tests extraction of fields from structured abstracts before full PDF parsing.
"""
import unittest
from unittest.mock import MagicMock

from core.abstract_first_extractor import AbstractFirstExtractor, AbstractExtractionResult
from core.pubmed_fetcher import PubMedArticle


class TestAbstractFirstExtractor(unittest.TestCase):
    """Tests for AbstractFirstExtractor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = AbstractFirstExtractor()
        
    def test_extractable_fields_with_structured_abstract(self):
        """Test that extractable fields are correctly identified."""
        article = PubMedArticle(
            pmid="12345",
            title="A Randomized Controlled Trial of Treatment X",
            abstract="BACKGROUND: This study examined... METHODS: We enrolled 120 patients... RESULTS: Primary outcome... CONCLUSION: Treatment X is effective.",
            journal="J Test Med",
            pub_date="2024",
            doi="10.1234/test"
        )
        
        fields = self.extractor.extractable_fields(article)
        
        # Should detect structured abstract sections
        self.assertIn("publication_year", fields)
        self.assertIn("journal_name", fields)
        self.assertIn("doi", fields)
        
    def test_extractable_fields_empty_abstract(self):
        """Test handling of empty abstract but with metadata."""
        article = PubMedArticle(
            pmid="12345",
            title="Some Title",
            abstract="",
            pub_date="2024",  # Has metadata
            journal="Test Journal",
        )
        
        fields = self.extractor.extractable_fields(article)
        
        # Should extract metadata fields even without abstract
        self.assertIn("publication_year", fields)
        self.assertIn("journal_name", fields)
        
    def test_extract_from_abstract_basic_fields(self):
        """Test extraction of basic fields from article metadata."""
        article = PubMedArticle(
            pmid="12345",
            title="Treatment Efficacy Study",
            abstract="We enrolled 100 patients (mean age 65±12 years).",
            journal="Critical Care Medicine",
            pub_date="2024 Jan",
            doi="10.1097/ccm.12345"
        )
        
        result = self.extractor.extract_from_abstract(article)
        
        self.assertIsInstance(result, AbstractExtractionResult)
        self.assertEqual(result.extracted_fields["journal_name"], "Critical Care Medicine")
        self.assertEqual(result.extracted_fields["doi"], "10.1097/ccm.12345")
        self.assertIn("2024", result.extracted_fields.get("publication_year", ""))
        
    def test_extract_sample_size_from_abstract(self):
        """Test extraction of sample size from abstract text."""
        article = PubMedArticle(
            pmid="12345",
            title="Study",
            abstract="We enrolled 150 patients in this prospective study.",
        )
        
        result = self.extractor.extract_from_abstract(article)
        
        self.assertEqual(result.extracted_fields.get("sample_size_raw"), "150")
        
    def test_extract_age_from_abstract(self):
        """Test extraction of age statistics from abstract."""
        article = PubMedArticle(
            pmid="12345",
            title="Study",
            abstract="Patients had a mean age of 62.5 ± 10.3 years.",
        )
        
        result = self.extractor.extract_from_abstract(article)
        
        age_field = result.extracted_fields.get("age_mean_sd")
        self.assertIsNotNone(age_field)
        self.assertIn("62.5", str(age_field))
        
    def test_extraction_result_audit_trail(self):
        """Test that extraction result includes audit information."""
        article = PubMedArticle(
            pmid="12345",
            title="Study",
            abstract="Sample text",
            journal="Test Journal",
        )
        
        result = self.extractor.extract_from_abstract(article)
        
        # Should track which fields came from abstract
        self.assertIn("source", result.audit)
        self.assertEqual(result.audit["source"], "pubmed_abstract")
        self.assertIn("pmid", result.audit)
        
    def test_is_structured_abstract(self):
        """Test detection of structured vs unstructured abstracts."""
        structured = "BACKGROUND: ... METHODS: ... RESULTS: ... CONCLUSION: ..."
        unstructured = "This study examined the effects of treatment X on outcome Y."
        
        self.assertTrue(self.extractor._is_structured_abstract(structured))
        self.assertFalse(self.extractor._is_structured_abstract(unstructured))
        

if __name__ == "__main__":
    unittest.main()
