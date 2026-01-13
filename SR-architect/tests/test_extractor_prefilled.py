"""
Tests for pre_filled_fields parameter in StructuredExtractor.

Task 2.5: Verify that pre_filled_fields support works correctly
in extract_with_evidence and extract_with_evidence_async methods.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from pydantic import BaseModel, Field
from core.extractors import StructuredExtractor, ExtractionWithEvidence


class SampleSchema(BaseModel):
    """Sample schema for testing."""
    doi: str | None = Field(default=None)
    publication_year: int | None = Field(default=None)
    sample_size: int | None = Field(default=None)
    title: str = Field(default="Not reported")


class TestPreFilledFieldsSync:
    """Test pre_filled_fields parameter in synchronous extract_with_evidence."""
    
    def test_pre_filled_fields_included_in_prompt(self):
        """Should include pre-filled fields in the prompt to LLM."""
        # Arrange
        extractor = StructuredExtractor(provider="openrouter")
        
        pre_filled = {
            "doi": "10.1234/test.2024",
            "publication_year": 2024
        }
        
        # Mock the client
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.usage = None
        
        # Mock the data result
        mock_data_result = SampleSchema(
            doi="10.1234/test.2024",
            publication_year=2024,
            sample_size=100
        )
        
        # Mock evidence result
        mock_evidence_result = MagicMock()
        mock_evidence_result.evidence = []
        
        mock_client.chat.completions.create_with_completion.side_effect = [
            (mock_data_result, mock_completion),  # First call for data
            (mock_evidence_result, mock_completion)  # Second call for evidence
        ]
        
        extractor._instructor_client = mock_client
        
        # Act
        result = extractor.extract_with_evidence(
            text="Sample paper text",
            schema=SampleSchema,
            pre_filled_fields=pre_filled
        )
        
        # Assert
        assert mock_client.chat.completions.create_with_completion.called
        first_call_args = mock_client.chat.completions.create_with_completion.call_args_list[0]
        messages = first_call_args[1]['messages']
        user_message = messages[1]['content']
        
        # Verify pre-filled fields are in the prompt
        assert "PRE-EXTRACTED FIELDS" in user_message
        assert "doi: 10.1234/test.2024" in user_message
        assert "publication_year: 2024" in user_message
    
    def test_pre_filled_fields_merged_into_result(self):
        """Should merge pre-filled fields into extraction result."""
        # Arrange
        extractor = StructuredExtractor(provider="openrouter")
        
        pre_filled = {
            "doi": "10.1234/test.2024",
            "publication_year": 2024
        }
        
        # Mock the client
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.usage = None
        
        # LLM extracts sample_size but not doi/year (returns None)
        mock_data_result = SampleSchema(
            doi=None,  # LLM didn't extract
            publication_year=None,  # LLM didn't extract
            sample_size=100  # LLM extracted this
        )
        
        mock_evidence_result = MagicMock()
        mock_evidence_result.evidence = []
        
        mock_client.chat.completions.create_with_completion.side_effect = [
            (mock_data_result, mock_completion),
            (mock_evidence_result, mock_completion)
        ]
        
        extractor._instructor_client = mock_client
        
        # Act
        result = extractor.extract_with_evidence(
            text="Sample paper text",
            schema=SampleSchema,
            pre_filled_fields=pre_filled
        )
        
        # Assert
        assert isinstance(result, ExtractionWithEvidence)
        assert result.data["doi"] == "10.1234/test.2024"  # From pre-filled
        assert result.data["publication_year"] == 2024  # From pre-filled
        assert result.data["sample_size"] == 100  # From LLM
    
    def test_llm_extraction_overrides_empty_prefilled(self):
        """LLM extraction should be used if it provides a value, even if pre-filled exists."""
        # Arrange
        extractor = StructuredExtractor(provider="openrouter")
        
        pre_filled = {
            "doi": "10.1234/test.2024"
        }
        
        # Mock the client
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.usage = None
        
        # LLM extracts a DIFFERENT doi
        mock_data_result = SampleSchema(
            doi="10.5678/different.2024",  # LLM found different value
            sample_size=100
        )
        
        mock_evidence_result = MagicMock()
        mock_evidence_result.evidence = []
        
        mock_client.chat.completions.create_with_completion.side_effect = [
            (mock_data_result, mock_completion),
            (mock_evidence_result, mock_completion)
        ]
        
        extractor._instructor_client = mock_client
        
        # Act
        result = extractor.extract_with_evidence(
            text="Sample paper text",
            schema=SampleSchema,
            pre_filled_fields=pre_filled
        )
        
        # Assert - LLM value should win
        assert result.data["doi"] == "10.5678/different.2024"
    
    def test_no_pre_filled_fields_works_normally(self):
        """Should work normally when pre_filled_fields is None."""
        # Arrange
        extractor = StructuredExtractor(provider="openrouter")
        
        # Mock the client
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.usage = None
        
        mock_data_result = SampleSchema(doi="10.1234/test.2024", sample_size=100)
        mock_evidence_result = MagicMock()
        mock_evidence_result.evidence = []
        
        mock_client.chat.completions.create_with_completion.side_effect = [
            (mock_data_result, mock_completion),
            (mock_evidence_result, mock_completion)
        ]
        
        extractor._instructor_client = mock_client
        
        # Act
        result = extractor.extract_with_evidence(
            text="Sample paper text",
            schema=SampleSchema,
            pre_filled_fields=None  # No pre-filled fields
        )
        
        # Assert
        assert isinstance(result, ExtractionWithEvidence)
        assert result.data["doi"] == "10.1234/test.2024"
        
        # Verify prompt doesn't contain pre-filled section
        first_call_args = mock_client.chat.completions.create_with_completion.call_args_list[0]
        messages = first_call_args[1]['messages']
        user_message = messages[1]['content']
        assert "PRE-EXTRACTED FIELDS" not in user_message


class TestPreFilledFieldsAsync:
    """Test pre_filled_fields parameter in asynchronous extract_with_evidence_async."""
    
    @pytest.mark.asyncio
    async def test_async_pre_filled_fields_included_in_prompt(self):
        """Should include pre-filled fields in the prompt to LLM (async)."""
        # Arrange
        extractor = StructuredExtractor(provider="openrouter")
        
        pre_filled = {
            "doi": "10.1234/test.2024",
            "publication_year": 2024
        }
        
        # Mock the async client
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.usage = None
        
        mock_data_result = SampleSchema(
            doi="10.1234/test.2024",
            publication_year=2024,
            sample_size=100
        )
        
        mock_evidence_result = MagicMock()
        mock_evidence_result.evidence = []
        
        # Track call count manually
        call_count = [0]
        
        # Make create_with_completion async
        async def mock_create(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return (mock_data_result, mock_completion)
            return (mock_evidence_result, mock_completion)
        
        mock_client.chat.completions.create_with_completion = mock_create
        extractor._async_instructor_client = mock_client
        
        # Act
        result = await extractor.extract_with_evidence_async(
            text="Sample paper text",
            schema=SampleSchema,
            pre_filled_fields=pre_filled
        )
        
        # Assert
        assert isinstance(result, ExtractionWithEvidence)
        assert result.data["doi"] == "10.1234/test.2024"
    
    @pytest.mark.asyncio
    async def test_async_pre_filled_fields_merged_into_result(self):
        """Should merge pre-filled fields into extraction result (async)."""
        # Arrange
        extractor = StructuredExtractor(provider="openrouter")
        
        pre_filled = {
            "doi": "10.1234/test.2024",
            "publication_year": 2024
        }
        
        # Mock the async client
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.usage = None
        
        # LLM extracts sample_size but not doi/year
        mock_data_result = SampleSchema(
            doi=None,
            publication_year=None,
            sample_size=100
        )
        
        mock_evidence_result = MagicMock()
        mock_evidence_result.evidence = []
        
        call_count = 0
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (mock_data_result, mock_completion)
            return (mock_evidence_result, mock_completion)
        
        mock_client.chat.completions.create_with_completion = mock_create
        extractor._async_instructor_client = mock_client
        
        # Act
        result = await extractor.extract_with_evidence_async(
            text="Sample paper text",
            schema=SampleSchema,
            pre_filled_fields=pre_filled
        )
        
        # Assert
        assert result.data["doi"] == "10.1234/test.2024"  # From pre-filled
        assert result.data["publication_year"] == 2024  # From pre-filled
        assert result.data["sample_size"] == 100  # From LLM
