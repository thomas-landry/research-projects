"""
Tests for RegexExtractor (Tier 0 extraction).
Validates regex patterns for common field extraction.
"""
import unittest
from core.regex_extractor import RegexExtractor, RegexResult


class TestRegexExtractor(unittest.TestCase):
    """Tests for RegexExtractor patterns."""
    
    def setUp(self):
        self.extractor = RegexExtractor()
        
    def test_extract_doi(self):
        """Test DOI extraction from text."""
        text = "The article (doi: 10.1000/xyz123) discusses..."
        result = self.extractor.extract_field("doi", text)
        self.assertIsNotNone(result)
        self.assertEqual(result.value, "10.1000/xyz123")
        self.assertGreater(result.confidence, 0.9)
        
    def test_extract_doi_https(self):
        """Test DOI extraction from URL format."""
        text = "Available at https://doi.org/10.1234/abc.5678"
        result = self.extractor.extract_field("doi", text)
        self.assertEqual(result.value, "10.1234/abc.5678")
        
    def test_extract_publication_year(self):
        """Test publication year extraction."""
        text = "Published online 2023 Mar 15."
        result = self.extractor.extract_field("publication_year", text)
        self.assertEqual(result.value, "2023")
        
    def test_extract_publication_year_brackets(self):
        """Test year in citation format."""
        text = "Smith et al. (2021) found that..."
        result = self.extractor.extract_field("publication_year", text)
        self.assertEqual(result.value, "2021")
        
    def test_extract_case_count(self):
        """Test case count extraction."""
        text = "We identified 25 cases of diffuse pulmonary meningotheliomatosis."
        result = self.extractor.extract_field("case_count", text)
        self.assertEqual(result.value, "25")
        
    def test_extract_case_count_patients(self):
        """Test patient count extraction."""
        text = "This study included 150 patients with confirmed diagnosis."
        result = self.extractor.extract_field("case_count", text)
        self.assertEqual(result.value, "150")
        
    def test_extract_sample_size(self):
        """Test sample size extraction."""
        text = "The sample size was n=42."
        result = self.extractor.extract_field("sample_size", text)
        self.assertEqual(result.value, "42")
        
    def test_extract_patient_age_years_old(self):
        """Test age extraction with 'years old' pattern."""
        text = "A 57-year-old woman presented with..."
        result = self.extractor.extract_field("patient_age", text)
        self.assertEqual(result.value, "57")
        
    def test_extract_patient_age_range(self):
        """Test age range extraction."""
        text = "Ages ranged from 37 to 73 years."
        result = self.extractor.extract_field("patient_age", text)
        self.assertEqual(result.value, "37-73")
        
    def test_extract_patient_age_median(self):
        """Test median age extraction."""
        text = "The median age was 59.5 years."
        result = self.extractor.extract_field("patient_age", text)
        self.assertEqual(result.value, "59.5")
        
    def test_extract_no_match_returns_none(self):
        """Test that no match returns None."""
        text = "This text has no relevant data."
        result = self.extractor.extract_field("doi", text)
        self.assertIsNone(result)
        
    def test_extract_all_fields(self):
        """Test extracting all supported fields at once."""
        text = """
        A 63-year-old female presented with pulmonary nodules.
        DOI: 10.1234/example.2023.456
        Published 2023. A total of 25 patients were included.
        """
        results = self.extractor.extract_all(text)
        
        self.assertIn("doi", results)
        self.assertIn("patient_age", results)
        self.assertIn("publication_year", results)
        self.assertIn("case_count", results)
        
        self.assertEqual(results["doi"].value, "10.1234/example.2023.456")
        self.assertEqual(results["patient_age"].value, "63")
        self.assertEqual(results["publication_year"].value, "2023")
        self.assertEqual(results["case_count"].value, "25")


if __name__ == "__main__":
    unittest.main()
