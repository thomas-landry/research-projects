import pytest
from unittest.mock import MagicMock, patch
from agents.synthesizer import SynthesizerAgent, SynthesisReport

@pytest.fixture
def mock_utils():
    with patch("core.utils.get_llm_client") as mock:
        yield mock

def test_synthesizer_init(mock_utils):
    agent = SynthesizerAgent(provider="openai")
    assert agent.provider == "openai"
    # Logger should handle init
    assert agent.logger is not None

def test_synthesize_success(mock_utils):
    # Setup mock
    mock_report = SynthesisReport(
        title="Test Meta-Analysis",
        executive_summary="Summary",
        sample_size_total=100,
        key_findings=["Finding 1"],
        conflicting_evidence=[],
        consensus_points=["Consensus 1"],
        limitations=["Limit 1"]
    )
    
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_report
    mock_utils.return_value = mock_client
    
    agent = SynthesizerAgent(api_key="test")
    
    input_data = [
        {"pmid": "1", "sample_size": 50, "outcome": "positive"},
        {"pmid": "2", "sample_size": 50, "outcome": "positive"}
    ]
    
    result = agent.synthesize(input_data, theme="Testing")
    
    assert result.sample_size_total == 100
    assert result.title == "Test Meta-Analysis"
    mock_client.chat.completions.create.assert_called_once()

def test_synthesize_empty_input():
    agent = SynthesizerAgent(api_key="test")
    with pytest.raises(ValueError) as exc:
        agent.synthesize([])
    assert "No results provided" in str(exc.value)

def test_synthesize_failure(mock_utils):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API fail")
    mock_utils.return_value = mock_client
    
    agent = SynthesizerAgent(api_key="test")
    input_data = [{"id": 1}]
    
    with pytest.raises(RuntimeError) as exc:
        agent.synthesize(input_data)
    assert "Synthesis failed" in str(exc.value)
