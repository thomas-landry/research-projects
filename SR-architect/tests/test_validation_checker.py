"""
Tests for ExtractionChecker main class.

TDD RED PHASE: These tests will FAIL because core/validation/checker.py doesn't exist yet.
This is EXPECTED and REQUIRED for proper TDD.
"""
import pytest
from unittest.mock import MagicMock, patch
from core.validation import ExtractionChecker
from core.validation.models import CheckerResult, Issue
from core.parser import DocumentChunk


class TestExtractionCheckerInit:
    """Test ExtractionChecker initialization."""
    
    def test_initialization_defaults(self):
        """Should initialize with default settings."""
        checker = ExtractionChecker()
        
        assert checker.provider == "openrouter"
        assert checker.accuracy_weight > 0
        assert checker.consistency_weight > 0
        assert hasattr(checker, 'model')
    
    def test_initialization_custom_provider(self):
        """Should accept custom provider."""
        checker = ExtractionChecker(provider="anthropic")
        assert checker.provider == "anthropic"
    
    def test_initialization_custom_weights(self):
        """Should accept custom accuracy and consistency weights."""
        checker = ExtractionChecker(
            accuracy_weight=0.7,
            consistency_weight=0.3
        )
        assert checker.accuracy_weight == 0.7
        assert checker.consistency_weight == 0.3
    
    def test_initialization_custom_model(self):
        """Should accept custom model name."""
        checker = ExtractionChecker(model="gpt-4")
        assert checker.model == "gpt-4"


class TestFormatRevisionPrompt:
    """Test format_revision_prompt method."""
    
    def test_format_with_issues(self):
        """Should format issues into revision prompt."""
        checker = ExtractionChecker()
        
        result = CheckerResult(
            accuracy_score=0.6,
            consistency_score=0.7,
            overall_score=0.65,
            issues=[
                Issue(
                    field="doi",
                    issue_type="missing_quote",
                    severity="high",
                    detail="No supporting quote found",
                    suggested_fix="Add exact quote from paper"
                )
            ],
            suggestions=["Verify DOI format", "Check quote accuracy"],
            passed=False
        )
        
        prompt = checker.format_revision_prompt(result)
        
        assert "doi" in prompt
        assert "missing_quote" in prompt
        assert "No supporting quote found" in prompt
        assert "Add exact quote from paper" in prompt
        assert "Verify DOI format" in prompt
    
    def test_format_with_passed_result(self):
        """Should return empty string for passed results."""
        checker = ExtractionChecker()
        
        result = CheckerResult(
            accuracy_score=0.95,
            consistency_score=0.9,
            overall_score=0.925,
            issues=[],
            suggestions=[],
            passed=True
        )
        
        prompt = checker.format_revision_prompt(result)
        assert prompt == ""
    
    def test_format_with_no_suggestions(self):
        """Should return empty string when no suggestions."""
        checker = ExtractionChecker()
        
        result = CheckerResult(
            accuracy_score=0.8,
            consistency_score=0.75,
            overall_score=0.775,
            issues=[],
            suggestions=[],  # No suggestions
            passed=False
        )
        
        prompt = checker.format_revision_prompt(result)
        assert prompt == ""


class TestCheckMethod:
    """Test check() method (sync)."""
    
    @patch('core.validation.checker.ExtractionChecker.client', new_callable=lambda: MagicMock())
    def test_check_returns_checker_result(self, mock_client_property):
        """Should return CheckerResult from validation."""
        # Setup mock
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.usage = None
        
        from core.validation.models import CheckerResponse
        mock_response = CheckerResponse(
            accuracy_score=0.9,
            consistency_score=0.85,
            issues=[],
            suggestions=[]
        )
        
        mock_client.chat.completions.create_with_completion.return_value = (mock_response, mock_completion)
        
        # Patch the property to return our mock
        with patch.object(ExtractionChecker, 'client', new=mock_client):
            checker = ExtractionChecker()
            
            chunks = [DocumentChunk(text="Sample text", page_number=1, chunk_index=0)]
            data = {"doi": "10.1234/test"}
            evidence = [{"field_name": "doi", "extracted_value": "10.1234/test", "exact_quote": "DOI: 10.1234/test"}]
            
            result = checker.check(chunks, data, evidence, theme="test theme")
            
            assert isinstance(result, CheckerResult)
            assert result.accuracy_score == 0.9
            assert result.consistency_score == 0.85
    
    @patch('core.validation.checker.ExtractionChecker.client', new_callable=lambda: MagicMock())
    def test_check_calculates_overall_score(self, mock_client_property):
        """Should calculate overall score from accuracy and consistency."""
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.usage = None
        
        from core.validation.models import CheckerResponse
        mock_response = CheckerResponse(
            accuracy_score=0.8,
            consistency_score=0.6,
            issues=[],
            suggestions=[]
        )
        
        mock_client.chat.completions.create_with_completion.return_value = (mock_response, mock_completion)
        
        with patch.object(ExtractionChecker, 'client', new=mock_client):
            checker = ExtractionChecker(accuracy_weight=0.7, consistency_weight=0.3)
            
            chunks = [DocumentChunk(text="Sample", page_number=1, chunk_index=0)]
            result = checker.check(chunks, {}, [], theme="test")
            
            # 0.8 * 0.7 + 0.6 * 0.3 = 0.56 + 0.18 = 0.74
            assert abs(result.overall_score - 0.74) < 0.01
    
    @patch('core.validation.checker.ExtractionChecker.client', new_callable=lambda: MagicMock())
    def test_check_handles_errors_gracefully(self, mock_client_property):
        """Should return failed result on error."""
        mock_client = MagicMock()
        mock_client.chat.completions.create_with_completion.side_effect = Exception("API Error")
        
        with patch.object(ExtractionChecker, 'client', new=mock_client):
            checker = ExtractionChecker()
            
            chunks = [DocumentChunk(text="Sample", page_number=1, chunk_index=0)]
            result = checker.check(chunks, {}, [], theme="test")
            
            assert result.passed is False
            assert result.overall_score == 0.0
            assert len(result.issues) > 0
            assert "error" in result.issues[0].issue_type.lower()


class TestCheckAsyncMethod:
    """Test check_async() method."""
    
    @pytest.mark.asyncio
    @patch('core.validation.checker.ExtractionChecker.async_client', new_callable=lambda: MagicMock())
    async def test_check_async_returns_checker_result(self, mock_async_client_property):
        """Should return CheckerResult from async validation."""
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.usage = None
        
        from core.validation.models import CheckerResponse
        mock_response = CheckerResponse(
            accuracy_score=0.9,
            consistency_score=0.85,
            issues=[],
            suggestions=[]
        )
        
        # Make it async
        async def mock_create(*args, **kwargs):
            return (mock_response, mock_completion)
        
        mock_client.chat.completions.create_with_completion = mock_create
        
        with patch.object(ExtractionChecker, 'async_client', new=mock_client):
            checker = ExtractionChecker()
            
            chunks = [DocumentChunk(text="Sample text", page_number=1, chunk_index=0)]
            data = {"doi": "10.1234/test"}
            evidence = [{"field_name": "doi", "extracted_value": "10.1234/test"}]
            
            result = await checker.check_async(chunks, data, evidence, theme="test theme")
            
            assert isinstance(result, CheckerResult)
            assert result.accuracy_score == 0.9
