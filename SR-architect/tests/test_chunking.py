"""
Unit tests for SemanticChunker and ContextWindowMonitor.
"""
import unittest
from core.semantic_chunker import SemanticChunker
from core.context_window_monitor import ContextWindowMonitor


class TestSemanticChunker(unittest.TestCase):
    def setUp(self):
        self.chunker = SemanticChunker(chunk_size=500, chunk_overlap=50)

    def test_empty_input(self):
        result = self.chunker.chunk("")
        self.assertEqual(result, [])

    def test_short_text(self):
        text = "This is a short paragraph."
        result = self.chunker.chunk(text)
        # Short text should be one chunk (if above min_chunk_size)
        # Default min is 100, so this might be empty
        self.assertLessEqual(len(result), 1)

    def test_paragraph_splitting(self):
        text = """First paragraph with some content here.

Second paragraph with different content.

Third paragraph to complete the test."""
        result = self.chunker.chunk(text)
        # Should combine paragraphs up to chunk_size
        self.assertGreaterEqual(len(result), 1)

    def test_large_paragraph(self):
        # Create a paragraph larger than chunk_size
        text = "This is a sentence. " * 100
        result = self.chunker.chunk(text)
        # Should split into multiple chunks
        self.assertGreater(len(result), 1)


class TestContextWindowMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = ContextWindowMonitor(model="default")

    def test_token_count(self):
        text = "Hello world"
        tokens = self.monitor.count_tokens(text)
        self.assertGreater(tokens, 0)

    def test_short_text_fits(self):
        text = "Short text"
        self.assertTrue(self.monitor.check_fits(text))

    def test_usage_report(self):
        text = "Some sample text for testing."
        report = self.monitor.get_usage_report(text)
        
        self.assertIn("tokens", report)
        self.assertIn("usable_limit", report)
        self.assertIn("usage_percent", report)
        self.assertIn("fits", report)

    def test_truncation(self):
        # Create text that might exceed small context
        small_monitor = ContextWindowMonitor(model="default")
        small_monitor.usable_limit = 10  # Force small limit
        
        text = "This is a much longer text that needs truncation."
        truncated = small_monitor.truncate_to_fit(text)
        
        self.assertLessEqual(len(truncated), len(text))

    def test_model_limits(self):
        claude_monitor = ContextWindowMonitor(model="claude-sonnet-4")
        llama_monitor = ContextWindowMonitor(model="llama3.1:8b")
        
        # Claude should have larger limit
        self.assertGreater(claude_monitor.context_limit, llama_monitor.context_limit)
