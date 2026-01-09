"""
Tests for PromptTemplateManager.
Validates YAML loading and prompt generation.
"""
import unittest
import tempfile
from pathlib import Path

from core.prompt_templates import PromptTemplateManager, FieldTemplate


class TestPromptTemplateManager(unittest.TestCase):
    """Tests for prompt template loading and generation."""
    
    def setUp(self):
        # Use actual templates dir
        self.manager = PromptTemplateManager()
        
    def test_load_templates(self):
        """Test loading templates from YAML."""
        self.manager.load_templates("systematic_review.yaml")
        
        fields = self.manager.get_available_fields()
        self.assertIn("sample_size", fields)
        self.assertIn("mean_age", fields)
        self.assertIn("patient_sex", fields)
        
    def test_get_template(self):
        """Test getting a specific template."""
        template = self.manager.get_template("sample_size")
        
        self.assertIsNotNone(template)
        self.assertEqual(template.name, "sample_size")
        self.assertEqual(template.field_type, "integer")
        self.assertGreater(len(template.extraction_rules), 0)
        self.assertGreater(len(template.few_shot_examples), 0)
        
    def test_get_extraction_prompt(self):
        """Test generating an extraction prompt."""
        context = "A total of 150 patients were enrolled in the study."
        
        prompt = self.manager.get_extraction_prompt("sample_size", context)
        
        self.assertIn("Extract: sample_size", prompt)
        self.assertIn("150 patients", prompt)
        self.assertIn("Extraction Rules", prompt)
        self.assertIn("Examples", prompt)
        
    def test_prompt_without_examples(self):
        """Test generating prompt without few-shot examples."""
        context = "The study enrolled 50 subjects."
        
        prompt = self.manager.get_extraction_prompt(
            "sample_size",
            context,
            include_examples=False
        )
        
        self.assertNotIn("Examples", prompt)
        
    def test_categorical_field_allowed_values(self):
        """Test that categorical fields include allowed values."""
        template = self.manager.get_template("patient_sex")
        
        self.assertIsNotNone(template.allowed_values)
        self.assertIn("Male", template.allowed_values)
        self.assertIn("Female", template.allowed_values)
        
    def test_unknown_field_basic_prompt(self):
        """Test fallback for unknown fields."""
        context = "Some document text."
        
        prompt = self.manager.get_extraction_prompt("unknown_field", context)
        
        self.assertIn("unknown_field", prompt)
        self.assertIn("Some document text", prompt)
        
    def test_has_template(self):
        """Test checking template existence."""
        self.assertTrue(self.manager.has_template("sample_size"))
        self.assertFalse(self.manager.has_template("nonexistent_field"))


if __name__ == "__main__":
    unittest.main()
