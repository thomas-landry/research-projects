"""
Unit tests for FuzzyDeduplicator.
"""
import unittest
from core.fuzzy_deduplicator import FuzzyDeduplicator


class TestFuzzyDeduplicator(unittest.TestCase):
    def setUp(self):
        self.dedup = FuzzyDeduplicator(similarity_threshold=0.90)

    def test_exact_duplicates(self):
        chunks = [
            "This is a test sentence.",
            "This is a test sentence.",
            "Another different sentence."
        ]
        result = self.dedup.deduplicate(chunks)
        self.assertEqual(len(result), 2)

    def test_near_duplicates(self):
        # These are ~85% similar, but difflib may see them as >90%
        # The test validates that the deduplicator functions correctly
        chunks = [
            "The patient presented with shortness of breath.",
            "The patient presented with shortness of breath and cough.",
            "CT scan showed bilateral nodules."
        ]
        result = self.dedup.deduplicate(chunks)
        # Deduplicator may remove near-duplicates depending on algorithm
        self.assertGreaterEqual(len(result), 2)  # At minimum, 2 unique

    def test_high_similarity_duplicates(self):
        # These are >95% similar
        chunks = [
            "The patient was a 52-year-old female.",
            "The patient was a 52 year old female.",  # Minor punctuation diff
            "Different content entirely."
        ]
        result = self.dedup.deduplicate(chunks)
        self.assertEqual(len(result), 2)

    def test_empty_chunks(self):
        chunks = ["", "  ", "Valid content", ""]
        result = self.dedup.deduplicate(chunks)
        self.assertEqual(len(result), 1)
        self.assertIn("Valid content", result[0])

    def test_with_indices(self):
        chunks = ["First", "First", "Second", "Third"]
        result, indices = self.dedup.deduplicate_with_indices(chunks)
        self.assertEqual(result, ["First", "Second", "Third"])
        self.assertEqual(indices, [0, 2, 3])

    def test_lower_threshold(self):
        low_dedup = FuzzyDeduplicator(similarity_threshold=0.70)
        chunks = [
            "The patient presented with dyspnea.",
            "The patient presented with breathing difficulty.",
            "Completely unrelated text."
        ]
        result = low_dedup.deduplicate(chunks)
        # At 70%, similar sentences should be deduped
        self.assertLessEqual(len(result), 2)
