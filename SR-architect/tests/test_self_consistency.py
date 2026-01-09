"""
Tests for SelfConsistencyVoter.
Validates 3x extraction with variance check for critical numeric fields.
"""
import unittest
from unittest.mock import patch, MagicMock
from core.self_consistency import SelfConsistencyVoter, VoteResult


class TestSelfConsistencyVoter(unittest.TestCase):
    """Tests for self-consistency voting logic."""
    
    def setUp(self):
        self.voter = SelfConsistencyVoter(temperature=0.3, num_votes=3)
        
    def test_unanimous_agreement_accepts(self):
        """Test that unanimous agreement results in acceptance."""
        values = [150, 150, 150]
        result = self.voter.vote("sample_size", values)
        
        self.assertTrue(result.accepted)
        self.assertEqual(result.consensus_value, 150)
        self.assertEqual(result.variance, 0.0)
        
    def test_within_tolerance_accepts(self):
        """Test that values within 5% tolerance accept."""
        # 148, 150, 152 all within 5% of 150
        values = [148, 150, 152]
        result = self.voter.vote("sample_size", values)
        
        self.assertTrue(result.accepted)
        self.assertAlmostEqual(result.consensus_value, 150, delta=1)
        
    def test_exceeds_tolerance_escalates(self):
        """Test that values exceeding 5% tolerance escalate."""
        # 100, 150, 200 - too much variance
        values = [100, 150, 200]
        result = self.voter.vote("sample_size", values)
        
        self.assertFalse(result.accepted)
        self.assertTrue(result.needs_escalation)
        
    def test_mean_age_tolerance(self):
        """Test age field within tolerance."""
        values = [57.2, 58.0, 57.5]
        result = self.voter.vote("mean_age", values)
        
        self.assertTrue(result.accepted)
        self.assertGreater(result.confidence, 0.9)
        
    def test_mortality_rate_tolerance(self):
        """Test rate field (0-1 scale) tolerance check."""
        values = [0.45, 0.46, 0.44]  # Within 5%
        result = self.voter.vote("mortality_rate", values)
        
        self.assertTrue(result.accepted)
        
    def test_string_values_use_majority(self):
        """Test that string values use majority voting."""
        values = ["RCT", "RCT", "Cohort"]
        result = self.voter.vote("study_type", values)
        
        self.assertTrue(result.accepted)
        self.assertEqual(result.consensus_value, "RCT")
        
    def test_no_consensus_on_all_different(self):
        """Test that all different values fails consensus."""
        values = ["RCT", "Cohort", "Meta-analysis"]
        result = self.voter.vote("study_type", values)
        
        self.assertFalse(result.accepted)
        

class TestSelfConsistencyVoterIntegration(unittest.TestCase):
    """Integration tests for self-consistency voting with extractor."""
    
    def test_extract_with_voting(self):
        """Test extracting a field with voting enabled."""
        voter = SelfConsistencyVoter()
        
        # Mock the extraction function
        mock_extract_fn = MagicMock(side_effect=[
            {"sample_size": 150, "confidence": 0.9},
            {"sample_size": 152, "confidence": 0.88},
            {"sample_size": 148, "confidence": 0.91},
        ])
        
        result = voter.extract_with_voting(
            extract_fn=mock_extract_fn,
            field_name="sample_size",
            context="Sample text"
        )
        
        self.assertTrue(result.accepted)
        self.assertEqual(mock_extract_fn.call_count, 3)


if __name__ == "__main__":
    unittest.main()
