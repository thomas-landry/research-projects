import pytest
from unittest.mock import MagicMock, patch
from core.extractor import StructuredExtractor
from pydantic import BaseModel

class SampleSchema(BaseModel):
    name: str
    age: int

@pytest.fixture
def mock_utils():
    with patch("core.utils.get_llm_client") as mock:
        yield mock

@pytest.fixture
def extractor(mock_utils):
    # Setup mock client
    mock_client = MagicMock()
    mock_utils.return_value = mock_client
    
    # Initialize extractor
    ext = StructuredExtractor(api_key="test-key", provider="openrouter")
    return ext

def test_initialization(extractor):
    assert extractor.provider == "openrouter"
    assert extractor.client is not None

def test_extract_success(extractor):
    # Setup mock response
    mock_response = SampleSchema(name="John", age=30)
    extractor.client.chat.completions.create.return_value = mock_response
    
    result = extractor.extract("John is 30 years old", SampleSchema)
    
    assert result.name == "John"
    assert result.age == 30
    extractor.client.chat.completions.create.assert_called_once()

def test_extract_failure(extractor):
    # Setup mock failure
    extractor.client.chat.completions.create.side_effect = Exception("API Error")
    
    with pytest.raises(RuntimeError) as excinfo:
        extractor.extract("text", SampleSchema)
    
    assert "Extraction failed" in str(excinfo.value)
    assert "API Error" in str(excinfo.value)

def test_extract_with_retry(extractor):
    # Fail once, then succeed
    mock_response = SampleSchema(name="John", age=30)
    extractor.client.chat.completions.create.side_effect = [Exception("Fail 1"), mock_response]
    
    result = extractor.extract_with_retry("text", SampleSchema, max_retries=1)
    
    assert result.name == "John"
    assert extractor.client.chat.completions.create.call_count == 2
