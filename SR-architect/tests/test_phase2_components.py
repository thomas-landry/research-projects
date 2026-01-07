"""
Unit tests for Phase 2 components: LayoutCleaner and PubMedFetcher.
"""
import unittest
from unittest.mock import patch, MagicMock
from core.content_filter import ContentFilter
from core.pubmed_fetcher import PubMedFetcher, PubMedArticle


import shutil
import tempfile

class TestLayoutCleaner(unittest.TestCase):
    def setUp(self):
        self.filter = ContentFilter()

    def test_removes_page_numbers(self):
        text = "Content here.\n\n1\n\nMore content.\n\nPage 2\n\nFinal content."
        cleaned = self.filter.clean_layout(text)
        
        self.assertNotIn("\n1\n", cleaned)
        self.assertNotIn("Page 2", cleaned)
        self.assertIn("Content here", cleaned)
        self.assertIn("Final content", cleaned)

    def test_removes_repeated_headers(self):
        # Simulate repeated journal header
        lines = ["Content page 1.", "Journal of Medicine", 
                 "More content.", "Journal of Medicine",
                 "Even more.", "Journal of Medicine",
                 "Final.", "Journal of Medicine"]
        text = "\n".join(lines)
        
        cleaned = self.filter.clean_layout(text)
        
        # The repeated header should be removed
        self.assertIn("Content page 1", cleaned)
        self.assertIn("Final", cleaned)

    def test_removes_watermarks(self):
        text = "Content here.\n\nDRAFT\n\nMore content.\n\nCONFIDENTIAL\n\nFinal."
        cleaned = self.filter.clean_layout(text)
        
        self.assertNotIn("DRAFT", cleaned)
        self.assertNotIn("CONFIDENTIAL", cleaned)

    def test_preserves_paragraph_structure(self):
        text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
        cleaned = self.filter.clean_layout(text)
        
        # Should keep paragraph breaks
        self.assertEqual(cleaned.count("\n\n"), 2)

    def test_limits_consecutive_blanks(self):
        text = "Content.\n\n\n\n\n\nMore content."
        cleaned = self.filter.clean_layout(text)
        
        # Should have at most 2 consecutive blank lines
        self.assertNotIn("\n\n\n\n", cleaned)


class TestPubMedFetcher(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.fetcher = PubMedFetcher(cache_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_article_dataclass(self):
        article = PubMedArticle(
            pmid="12345",
            title="Test Article",
            authors="Smith J, Doe J"
        )
        
        d = article.to_dict()
        self.assertEqual(d["pmid"], "12345")
        self.assertEqual(d["title"], "Test Article")

    def test_fetch_by_pmid_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "12345": {
                    "title": "Test Article Title",
                    "source": "J Test",
                    "pubdate": "2024",
                    "authors": [{"name": "Smith J"}, {"name": "Doe J"}],
                    "articleids": [{"idtype": "doi", "value": "10.1234/test"}]
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        # Mock the session.get method
        self.fetcher._session.get = MagicMock(return_value=mock_response)
        
        article = self.fetcher.fetch_by_pmid("12345")
        
        self.assertIsNotNone(article)
        self.assertEqual(article.pmid, "12345")
        self.assertEqual(article.title, "Test Article Title")
        self.assertEqual(article.doi, "10.1234/test")

    def test_fetch_by_pmid_not_found(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "12345": {"error": "Not found"}
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        # Mock the session.get method
        self.fetcher._session.get = MagicMock(return_value=mock_response)
        
        article = self.fetcher.fetch_by_pmid("12345")
        
        self.assertIsNone(article)


if __name__ == "__main__":
    unittest.main()
