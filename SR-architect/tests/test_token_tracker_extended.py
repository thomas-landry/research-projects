
import pytest
from unittest.mock import MagicMock, patch
from core.token_tracker import TokenTracker

def test_tiktoken_estimation():
    tracker = TokenTracker()
    text = "Hello world " * 100
    
    # Check if tiktoken is importable, otherwise mock
    try:
        import tiktoken
    except ImportError:
        pytest.fail("tiktoken not installed")
        
    tokens = tracker.estimate_tokens(text, model="gpt-4o")
    # 100 repeats of "Hello world " is 200 words. Tokens ~200-300.
    assert tokens > 100

def test_record_usage_with_tier_field():
    tracker = TokenTracker()
    
    # We expect record_usage signature to change
    # Or kwargs?
    # record_usage(..., tier="...", field="...")
    
    # This should fail if signature not updated (Red phase)
    try:
        record = tracker.record_usage(
            usage={"prompt_tokens": 100, "completion_tokens": 10},
            model="test-model",
            tier="tier1",
            field="sample_size"
        )
    except TypeError:
        pytest.fail("record_usage does not accept tier/field")
    
    assert record.tier == "tier1"
    assert record.field == "sample_size"

def test_record_usage_with_direct_cost():
    tracker = TokenTracker()
    
    usage_data = {
        "prompt_tokens": 100, 
        "completion_tokens": 10,
        "cost": 0.005 # Direct cost from API
    }
    
    record = tracker.record_usage(
        usage=usage_data,
        model="test-model"
    )
    
    assert record.cost_usd == 0.005
    
    # Verify calculation logic is bypassed
    with patch.object(tracker, "calculate_cost") as mock_calc:
        tracker.record_usage(usage=usage_data, model="test-model")
        mock_calc.assert_not_called()
