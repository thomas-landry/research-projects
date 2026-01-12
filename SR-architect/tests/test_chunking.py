"""
Unit tests for SemanticChunker and ContextWindowMonitor.
"""
import unittest
import pytest
from core.semantic_chunker import SemanticChunker
from core.context_window_monitor import ContextWindowMonitor


class TestSemanticChunker(unittest.TestCase):
    def setUp(self):
        # SemanticChunker now requires a client parameter
        # For unit tests, we can pass None and test will skip LLM calls
        self.chunker = SemanticChunker(client=None)

    @pytest.mark.asyncio
    async def test_empty_input(self):
        result = await self.chunker.chunk_document_async("")
        self.assertEqual(result, [])

    @pytest.mark.asyncio
    async def test_short_text(self):
        text = "This is a short paragraph."
        result = await self.chunker.chunk_document_async(text)
        # Without LLM client, should return single chunk fallback
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].section, "Full Text")

    @pytest.mark.asyncio
    async def test_no_client_fallback(self):
        """Test that chunker falls back to single chunk when no client provided."""
        text = """First paragraph with some content here.

Second paragraph with different content.

Third paragraph to complete the test."""
        result = await self.chunker.chunk_document_async(text)
        # Should return single chunk when no client
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].section, "Full Text")


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
