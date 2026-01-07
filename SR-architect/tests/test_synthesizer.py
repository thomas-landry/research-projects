"""
Tests for SynthesizerAgent.

These tests verify the synthesizer can aggregate extraction results
into a coherent synthesis report.
"""
import pytest
from unittest.mock import MagicMock, patch
from agents.synthesizer import SynthesizerAgent, SynthesisReport


def test_synthesizer_init():
    """Test that SynthesizerAgent initializes correctly."""
    # Use DI to inject mock client
    mock_client = MagicMock()
    agent = SynthesizerAgent(client=mock_client, provider="openai")
    assert agent.provider == "openai"
    assert agent.logger is not None
    assert agent.client is mock_client


def test_synthesize_success():
    """Test successful synthesis with mocked client."""
    mock_report = SynthesisReport(
        title="Test Meta-Analysis",
        executive_summary="Summary",
        sample_size_total=100,
        key_findings=["Finding 1"],
        conflicting_evidence=[],
        consensus_points=["Consensus 1"],
        limitations=["Limit 1"]
    )
    
    # Create mock client and inject via DI
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_report
    
    agent = SynthesizerAgent(client=mock_client)
    
    input_data = [
        {"pmid": "1", "sample_size": 50, "outcome": "positive"},
        {"pmid": "2", "sample_size": 50, "outcome": "positive"}
    ]
    
    result = agent.synthesize(input_data, theme="Testing")
    
    assert result.sample_size_total == 100
    assert result.title == "Test Meta-Analysis"
    mock_client.chat.completions.create.assert_called_once()


def test_synthesize_empty_input():
    """Test that empty input raises ValueError."""
    mock_client = MagicMock()
    agent = SynthesizerAgent(client=mock_client)
    with pytest.raises(ValueError) as exc:
        agent.synthesize([])
    assert "No results provided" in str(exc.value)


def test_synthesize_failure():
    """Test that API failure raises RuntimeError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API fail")
    
    agent = SynthesizerAgent(client=mock_client)
    input_data = [{"id": 1}]
    
    with pytest.raises(RuntimeError) as exc:
        agent.synthesize(input_data)
    assert "Synthesis failed" in str(exc.value)
