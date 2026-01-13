"""
Tests for validation models.

TDD RED PHASE: These tests will FAIL because core/validation/models.py doesn't exist yet.
This is EXPECTED and REQUIRED for proper TDD.
"""
import pytest
from core.validation.models import Issue, CheckerResponse, CheckerResult


class TestIssue:
    """Test Issue dataclass."""
    
    def test_issue_creation(self):
        """Should create Issue with required fields."""
        issue = Issue(
            field="doi",
            issue_type="missing_quote",
            severity="high",
            detail="No supporting quote found"
        )
        assert issue.field == "doi"
        assert issue.issue_type == "missing_quote"
        assert issue.severity == "high"
        assert issue.detail == "No supporting quote found"
    
    def test_issue_with_suggested_fix(self):
        """Should create Issue with optional suggested_fix."""
        issue = Issue(
            field="title",
            issue_type="formatting",
            severity="low",
            detail="Title should be capitalized",
            suggested_fix="Capitalize first letter"
        )
        assert issue.suggested_fix == "Capitalize first letter"
    
    def test_issue_coerce_to_string(self):
        """Should coerce non-string values to strings in validators."""
        # This tests the field_validator for issue_type
        issue = Issue(
            field="title",
            issue_type=["type1", "type2"],  # List instead of string
            severity="medium",
            detail="Test"
        )
        # Should be coerced to string
        assert isinstance(issue.issue_type, str)


class TestCheckerResponse:
    """Test CheckerResponse Pydantic model."""
    
    def test_checker_response_creation(self):
        """Should create CheckerResponse with all fields."""
        response = CheckerResponse(
            accuracy_score=0.9,
            consistency_score=0.85,
            issues=[],
            suggestions=["Check DOI format", "Verify year"]
        )
        assert response.accuracy_score == 0.9
        assert response.consistency_score == 0.85
        assert len(response.suggestions) == 2
        assert len(response.issues) == 0
    
    def test_accuracy_score_bounds(self):
        """Should enforce 0.0-1.0 bounds on accuracy_score."""
        # Valid scores
        response = CheckerResponse(
            accuracy_score=0.0,
            consistency_score=1.0,
            issues=[],
            suggestions=[]
        )
        assert response.accuracy_score == 0.0
        
        # Out of bounds scores should be clamped to [0, 1]
        response = CheckerResponse(
            accuracy_score=1.5,  # Out of bounds
            consistency_score=0.8,
            issues=[],
            suggestions=[]
        )
        assert response.accuracy_score == 1.0  # Clamped to max
    
    def test_coerce_score_to_float(self):
        """Should coerce None scores to 0.0."""
        response = CheckerResponse(
            accuracy_score=None,  # Will be coerced to 0.0
            consistency_score=0.8,
            issues=[],
            suggestions=[]
        )
        assert response.accuracy_score == 0.0
        assert isinstance(response.accuracy_score, float)
    
    def test_coerce_suggestions_to_strings(self):
        """Should coerce dict suggestions to strings."""
        # Local LLMs sometimes return dicts instead of strings
        response = CheckerResponse(
            accuracy_score=0.9,
            consistency_score=0.85,
            issues=[],
            suggestions=[{"text": "Check this"}]  # Dict instead of string
        )
        # Should be coerced to string
        assert all(isinstance(s, str) for s in response.suggestions)


class TestCheckerResult:
    """Test CheckerResult dataclass."""
    
    def test_checker_result_creation(self):
        """Should create CheckerResult with all fields."""
        result = CheckerResult(
            accuracy_score=0.9,
            consistency_score=0.85,
            overall_score=0.875,
            issues=[],
            suggestions=["Test suggestion"],
            passed=True
        )
        assert result.accuracy_score == 0.9
        assert result.overall_score == 0.875
        assert result.passed is True
    
    def test_checker_result_with_issues(self):
        """Should create CheckerResult with issues."""
        issue = Issue(
            field="doi",
            issue_type="missing",
            severity="high",
            detail="DOI not found"
        )
        result = CheckerResult(
            accuracy_score=0.5,
            consistency_score=0.6,
            overall_score=0.55,
            issues=[issue],
            suggestions=["Add DOI"],
            passed=False
        )
        assert len(result.issues) == 1
        assert result.issues[0].field == "doi"
        assert result.passed is False
    
    def test_checker_result_to_dict(self):
        """Should convert CheckerResult to dict."""
        result = CheckerResult(
            accuracy_score=0.9,
            consistency_score=0.85,
            overall_score=0.875,
            issues=[],
            suggestions=["Test"],
            passed=True
        )
        data = result.to_dict()
        
        assert isinstance(data, dict)
        assert data["accuracy_score"] == 0.9
        assert data["consistency_score"] == 0.85
        assert data["overall_score"] == 0.875
        assert data["passed"] is True
        assert "issues" in data
        assert "suggestions" in data
