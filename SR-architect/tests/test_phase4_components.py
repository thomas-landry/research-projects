"""
Tests for CacheManager, ValidationRules, and AutoCorrector.
Tests the caching and validation components for Phase 4.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from core.cache_manager import CacheManager, CacheEntry
from core.validation_rules import ValidationRules, ValidationResult
from core.auto_corrector import AutoCorrector, CorrectionResult


class TestCacheManager(unittest.TestCase):
    """Tests for SQLite-based CacheManager."""
    
    def setUp(self):
        """Create a temp directory for test database."""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_cache.db"
        self.cache = CacheManager(db_path=self.db_path)
        
    def tearDown(self):
        """Clean up temp directory."""
        self.cache.close()
        shutil.rmtree(self.test_dir)
        
    def test_document_cache_set_get(self):
        """Test storing and retrieving document cache."""
        doc_hash = "abc123"
        parsed_text = "Sample document text"
        
        self.cache.set_document(doc_hash, parsed_text, {"title": "Test"})
        result = self.cache.get_document(doc_hash)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["parsed_text"], parsed_text)
        
    def test_document_cache_miss(self):
        """Test cache miss returns None."""
        result = self.cache.get_document("nonexistent")
        self.assertIsNone(result)
        
    def test_field_cache_set_get(self):
        """Test storing and retrieving field extraction cache."""
        doc_hash = "abc123"
        field_name = "sample_size"
        
        self.cache.set_field(
            doc_hash=doc_hash,
            field_name=field_name,
            result={"value": 150, "confidence": 0.92},
            schema_version=1,
            tier_used=2,
        )
        
        result = self.cache.get_field(doc_hash, field_name, schema_version=1)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["result"]["value"], 150)
        
    def test_field_cache_invalidation_on_schema_change(self):
        """Test that cache miss occurs with new schema version."""
        doc_hash = "abc123"
        field_name = "sample_size"
        
        self.cache.set_field(
            doc_hash=doc_hash,
            field_name=field_name,
            result={"value": 150},
            schema_version=1,
            tier_used=2,
        )
        
        # Should miss with different schema version
        result = self.cache.get_field(doc_hash, field_name, schema_version=2)
        self.assertIsNone(result)
        
    def test_cache_stats(self):
        """Test cache statistics tracking."""
        self.cache.get_document("miss1")  # miss
        self.cache.get_document("miss2")  # miss
        self.cache.set_document("hit1", "text", {})
        self.cache.get_document("hit1")  # hit
        
        stats = self.cache.get_stats()
        
        self.assertEqual(stats["misses"], 2)
        self.assertEqual(stats["hits"], 1)


class TestValidationRules(unittest.TestCase):
    """Tests for ValidationRules class."""
    
    def setUp(self):
        self.validator = ValidationRules()
        
    def test_range_check_valid(self):
        """Test valid range check passes."""
        result = self.validator.validate_field("sample_size", 150)
        self.assertTrue(result.is_valid)
        
    def test_range_check_invalid(self):
        """Test invalid range check fails."""
        result = self.validator.validate_field("sample_size", -5)
        self.assertFalse(result.is_valid)
        self.assertIn("out of range", result.message.lower())
        
    def test_mean_age_validation(self):
        """Test mean age validation."""
        self.assertTrue(self.validator.validate_field("mean_age", 65).is_valid)
        self.assertFalse(self.validator.validate_field("mean_age", 150).is_valid)
        
    def test_cross_field_validation(self):
        """Test cross-field validation."""
        data = {"analyzed_n": 100, "enrolled_n": 150}
        result = self.validator.validate_cross_field(data)
        self.assertTrue(result.is_valid)
        
        data = {"analyzed_n": 200, "enrolled_n": 100}  # Invalid: analyzed > enrolled
        result = self.validator.validate_cross_field(data)
        self.assertFalse(result.is_valid)


class TestAutoCorrector(unittest.TestCase):
    """Tests for AutoCorrector class."""
    
    def setUp(self):
        self.corrector = AutoCorrector()
        
    def test_ocr_fix_l_to_1(self):
        """Test OCR 'l' to '1' correction."""
        result = self.corrector.correct("sample_size", "l50")
        self.assertEqual(result.corrected_value, "150")
        self.assertEqual(result.correction_type, "ocr_fix")
        
    def test_ocr_fix_o_to_0(self):
        """Test OCR 'O' to '0' correction."""
        result = self.corrector.correct("sample_size", "1O5")
        self.assertEqual(result.corrected_value, "105")
        
    def test_thousands_separator_removal(self):
        """Test removal of thousands separator."""
        result = self.corrector.correct("sample_size", "1,234")
        self.assertEqual(result.corrected_value, "1234")
        
    def test_percentage_normalization(self):
        """Test percentage to decimal normalization."""
        result = self.corrector.correct("mortality_rate", 45)
        self.assertEqual(result.corrected_value, 0.45)
        self.assertEqual(result.correction_type, "percentage_to_decimal")
        
    def test_no_correction_needed(self):
        """Test that valid values aren't modified."""
        result = self.corrector.correct("sample_size", 150)
        self.assertEqual(result.corrected_value, 150)
        self.assertIsNone(result.correction_type)


if __name__ == "__main__":
    unittest.main()
