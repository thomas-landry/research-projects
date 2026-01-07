"""
Unit tests for ComplexityClassifier.
"""
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from core.complexity_classifier import ComplexityClassifier, ComplexityLevel, ComplexityResult
from core.parser import ParsedDocument, DocumentChunk


class TestComplexityClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = ComplexityClassifier()

    def test_simple_document(self):
        """Short, well-structured document should be SIMPLE."""
        doc = ParsedDocument(
            filename="simple.pdf",
            chunks=[
                DocumentChunk(text="Abstract: This is a study.", section="Abstract"),
                DocumentChunk(text="Introduction: Background info.", section="Introduction"),
                DocumentChunk(text="Methods: We analyzed data.", section="Methods"),
                DocumentChunk(text="Results: Data showed X.", section="Results"),
            ],
            full_text="""
            Abstract
            This is a study about X.
            
            Introduction
            Background information here.
            
            Methods
            We analyzed data using Y.
            
            Results
            The data showed significant findings.
            
            Discussion
            These findings suggest Z.
            """,
            metadata={"page_count": 5}
        )
        
        result = self.classifier.classify(doc)
        
        self.assertIn(result.level, [ComplexityLevel.SIMPLE, ComplexityLevel.MEDIUM])
        self.assertIsInstance(result.score, int)
        self.assertIn("has_tables", result.signals)

    def test_complex_document_with_tables(self):
        """Document with tables should have higher complexity."""
        doc = ParsedDocument(
            filename="complex.pdf",
            chunks=[
                DocumentChunk(text="| Col1 | Col2 |\n|---|---|\n| A | B |", chunk_type="table"),
            ],
            full_text="Short text without standard sections",
            metadata={"page_count": 50}
        )
        
        result = self.classifier.classify(doc)
        
        self.assertTrue(result.signals.get("has_tables"))
        self.assertGreater(result.score, 0)

    def test_recommendations_returned(self):
        """Classifier should return parser recommendations."""
        doc = ParsedDocument(
            filename="test.pdf",
            chunks=[],
            full_text="Some text here",
            metadata={}
        )
        
        result = self.classifier.classify(doc)
        
        self.assertIn("primary", result.recommendations)
        self.assertIn("fallback", result.recommendations)

    def test_missing_sections_detected(self):
        """Documents without IMRAD sections should be flagged."""
        doc = ParsedDocument(
            filename="nonstandard.pdf",
            chunks=[],
            full_text="Just some random text without any academic structure whatsoever.",
            metadata={}
        )
        
        result = self.classifier.classify(doc)
        
        self.assertTrue(result.signals.get("missing_sections"))

    def test_get_parser_strategy(self):
        """get_parser_strategy should return strategy dict."""
        doc = ParsedDocument(
            filename="test.pdf",
            chunks=[],
            full_text="Abstract\nIntroduction\nMethods\nResults\nDiscussion\n" * 100,
            metadata={}
        )
        
        strategy = self.classifier.get_parser_strategy(doc)
        
        self.assertIsInstance(strategy, dict)
        self.assertIn("primary", strategy)


if __name__ == "__main__":
    unittest.main()
