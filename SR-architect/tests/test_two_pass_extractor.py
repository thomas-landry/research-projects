"""
Tests for TwoPassExtractor and ModelCascader.
Tests the local-first extraction strategy and tier escalation logic.
"""
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import dataclass
from typing import Dict, Any, List

from core.two_pass_extractor import (
    TwoPassExtractor, 
    ExtractionTier,
    TierResult,
    ModelCascader,
    CascadeDecision,
)


class TestExtractionTier(unittest.TestCase):
    """Test tier enum ordering."""
    
    def test_tier_ordering(self):
        """Test that tiers are properly ordered."""
        self.assertEqual(ExtractionTier.REGEX.value, 0)
        self.assertEqual(ExtractionTier.LOCAL_LIGHTWEIGHT.value, 1)
        self.assertEqual(ExtractionTier.LOCAL_STANDARD.value, 2)
        self.assertEqual(ExtractionTier.CLOUD_CHEAP.value, 3)
        self.assertEqual(ExtractionTier.CLOUD_PREMIUM.value, 4)


class TestModelCascader(unittest.TestCase):
    """Tests for ModelCascader tier escalation logic."""
    
    def setUp(self):
        self.cascader = ModelCascader()
        
    def test_high_confidence_accepts(self):
        """Test that high confidence result is accepted."""
        result = TierResult(
            field_name="study_type",
            value="RCT",
            confidence=0.95,
            tier=ExtractionTier.LOCAL_STANDARD,
        )
        
        decision = self.cascader.decide(result, threshold=0.85)
        
        self.assertEqual(decision, CascadeDecision.ACCEPT)
        
    def test_low_confidence_escalates(self):
        """Test that low confidence result escalates."""
        result = TierResult(
            field_name="study_type",
            value="RCT",
            confidence=0.60,
            tier=ExtractionTier.LOCAL_STANDARD,
        )
        
        decision = self.cascader.decide(result, threshold=0.85)
        
        self.assertEqual(decision, CascadeDecision.ESCALATE)
        
    def test_premium_tier_does_not_escalate(self):
        """Test that premium tier goes to manual review instead of escalate."""
        result = TierResult(
            field_name="histopathology",
            value="unknown",
            confidence=0.40,
            tier=ExtractionTier.CLOUD_PREMIUM,
        )
        
        decision = self.cascader.decide(result, threshold=0.50)
        
        self.assertEqual(decision, CascadeDecision.MANUAL_REVIEW)


class TestTwoPassExtractor(unittest.TestCase):
    """Tests for TwoPassExtractor local-first strategy."""
    
    def setUp(self):
        # Mock the extractors
        self.mock_local = MagicMock()
        self.mock_cloud = MagicMock()
        
    def test_high_confidence_local_skips_cloud(self):
        """Test that high-confidence local results skip cloud."""
        extractor = TwoPassExtractor()
        
        # Mock local extraction with high confidence
        local_result = {
            "study_type": TierResult("study_type", "RCT", 0.92, ExtractionTier.LOCAL_STANDARD),
            "sample_size": TierResult("sample_size", "150", 0.95, ExtractionTier.LOCAL_STANDARD),
        }
        
        with patch.object(extractor, '_extract_local', return_value=local_result):
            with patch.object(extractor, '_extract_cloud') as mock_cloud:
                # Run extraction
                result = extractor.extract(
                    context="Sample text",
                    fields=["study_type", "sample_size"],
                    confidence_threshold=0.85
                )
                
                # Cloud should NOT be called
                mock_cloud.assert_not_called()
                
    def test_low_confidence_local_triggers_cloud(self):
        """Test that low-confidence local results trigger cloud extraction."""
        extractor = TwoPassExtractor()
        
        # Mock local extraction with low confidence
        local_result = {
            "study_type": TierResult("study_type", "RCT", 0.60, ExtractionTier.LOCAL_STANDARD),
        }
        cloud_result = {
            "study_type": TierResult("study_type", "RCT", 0.92, ExtractionTier.CLOUD_CHEAP),
        }
        
        with patch.object(extractor, '_extract_local', return_value=local_result):
            with patch.object(extractor, '_extract_cloud', return_value=cloud_result) as mock_cloud:
                result = extractor.extract(
                    context="Sample text",
                    fields=["study_type"],
                    confidence_threshold=0.85
                )
                
                # Cloud SHOULD be called for the low-confidence field
                mock_cloud.assert_called_once()


if __name__ == "__main__":
    unittest.main()
