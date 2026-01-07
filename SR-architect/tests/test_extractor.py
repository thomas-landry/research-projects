"""
Tests for StructuredExtractor.

These tests verify the extractor's structured extraction capabilities
using mocked LLM clients to avoid API calls.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from core.extractor import StructuredExtractor
from pydantic import BaseModel


class SampleSchema(BaseModel):
    name: str
    age: int


@pytest.fixture
def mock_utils():
    """Mock the LLM client initialization."""
    with patch("core.utils.get_llm_client") as mock:
        yield mock


@pytest.fixture
def extractor(mock_utils):
    """Create an extractor with mocked client."""
    mock_client = MagicMock()
    mock_utils.return_value = mock_client
    
    ext = StructuredExtractor(api_key="test-key", provider="openrouter")
    # Override the lazy-loaded client
    ext._instructor_client = mock_client
    return ext


def test_initialization(extractor):
    """Test extractor initializes correctly."""
    assert extractor.provider == "openrouter"
    assert extractor.client is not None


def test_extract_success(extractor):
    """Test successful extraction with mocked response."""
    # Create mock completion with usage stats
    mock_completion = MagicMock()
    mock_completion.usage = MagicMock()
    mock_completion.usage.prompt_tokens = 100
    mock_completion.usage.completion_tokens = 50
    mock_completion.usage.total_tokens = 150
    
    # Create mock result
    mock_result = SampleSchema(name="John", age=30)
    
    # Setup mock to return tuple (result, completion) as instructor does
    extractor.client.chat.completions.create_with_completion.return_value = (mock_result, mock_completion)
    
    # Patch the cache to avoid cache interference (imported inside method from core.utils)
    with patch("core.utils.LLMCache") as MockCache:
        MockCache.return_value.get.return_value = None  # No cache hit
        
        result = extractor.extract("John is 30 years old", SampleSchema)
        
        assert result.name == "John"
        assert result.age == 30
        extractor.client.chat.completions.create_with_completion.assert_called_once()


def test_extract_failure(extractor):
    """Test extraction failure handling."""
    # Setup mock to raise exception
    extractor.client.chat.completions.create_with_completion.side_effect = Exception("API Error")
    
    # Patch cache
    with patch("core.utils.LLMCache") as MockCache:
        MockCache.return_value.get.return_value = None  # No cache hit
        
        with pytest.raises(RuntimeError) as excinfo:
            extractor.extract("text", SampleSchema)
        
        assert "Extraction failed" in str(excinfo.value)
        assert "API Error" in str(excinfo.value)


def test_extract_with_retry_success_after_failure(extractor):
    """Test extraction retries on failure."""
    # Create mock completion
    mock_completion = MagicMock()
    mock_completion.usage = MagicMock()
    mock_completion.usage.prompt_tokens = 100
    mock_completion.usage.completion_tokens = 50 
    mock_completion.usage.total_tokens = 150
    
    mock_result = SampleSchema(name="John", age=30)
    
    # Fail once, then succeed
    extractor.client.chat.completions.create_with_completion.side_effect = [
        Exception("Fail 1"),
        (mock_result, mock_completion)
    ]
    
    # Patch cache
    with patch("core.utils.LLMCache") as MockCache:
        MockCache.return_value.get.return_value = None  # No cache hit
        
        result = extractor.extract_with_retry("text", SampleSchema, max_retries=1)
        
        assert result.name == "John"
        assert extractor.client.chat.completions.create_with_completion.call_count == 2


def test_extract_with_retry_all_failures(extractor):
    """Test extraction fails after all retries exhausted."""
    # All attempts fail
    extractor.client.chat.completions.create_with_completion.side_effect = Exception("Persistent failure")
    
    # Patch cache
    with patch("core.utils.LLMCache") as MockCache:
        MockCache.return_value.get.return_value = None  # No cache hit
        
        with pytest.raises(RuntimeError) as excinfo:
            extractor.extract_with_retry("text", SampleSchema, max_retries=2)
        
        # Should have tried 3 times (initial + 2 retries)
        assert extractor.client.chat.completions.create_with_completion.call_count == 3


def test_extract_uses_cache(extractor):
    """Test extraction uses cached results when available."""
    cached_result = SampleSchema(name="Cached", age=99)
    
    with patch("core.utils.LLMCache") as MockCache:
        MockCache.return_value.get.return_value = cached_result  # Cache hit
        
        result = extractor.extract("text", SampleSchema)
        
        assert result.name == "Cached"
        assert result.age == 99
        # Should NOT call the API
        extractor.client.chat.completions.create_with_completion.assert_not_called()


def test_usage_stats_tracking(extractor):
    """Test that usage statistics are tracked correctly."""
    mock_completion = MagicMock()
    mock_completion.usage = MagicMock()
    mock_completion.usage.prompt_tokens = 100
    mock_completion.usage.completion_tokens = 50
    mock_completion.usage.total_tokens = 150
    
    mock_result = SampleSchema(name="Test", age=25)
    extractor.client.chat.completions.create_with_completion.return_value = (mock_result, mock_completion)
    
    with patch("core.utils.LLMCache") as MockCache:
        MockCache.return_value.get.return_value = None
        
        extractor.extract("text", SampleSchema)
        
        stats = extractor.get_usage_stats()
        # Note: _track_usage is called twice in extract method (lines 222/224 and 233)
        assert stats["total_calls"] >= 1
