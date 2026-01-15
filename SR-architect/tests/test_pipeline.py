import pytest
from unittest.mock import MagicMock, patch
from core.pipeline import HierarchicalExtractionPipeline
from core.parser import DocumentChunk, ParsedDocument
from pydantic import BaseModel

class SampleSchema(BaseModel):
    field1: str

@pytest.fixture
def mock_pipeline_components():
    with patch("core.pipeline.core.ContentFilter") as mock_filter_cls, \
         patch("core.pipeline.core.RelevanceClassifier") as mock_rel_cls, \
         patch("core.pipeline.core.StructuredExtractor") as mock_ext_cls, \
         patch("core.pipeline.core.ExtractionChecker") as mock_check_cls:
        
        # Configure instances
        mock_filter = mock_filter_cls.return_value
        mock_rel = mock_rel_cls.return_value
        mock_ext = mock_ext_cls.return_value
        mock_check = mock_check_cls.return_value
        mock_check.format_revision_prompt.return_value = "fix it"
        
        yield {
            "filter": mock_filter,
            "relevance": mock_rel,
            "extractor": mock_ext,
            "checker": mock_check,
        }

def test_pipeline_initialization(mock_pipeline_components):
    pipeline = HierarchicalExtractionPipeline(provider="test")
    assert pipeline is not None

def test_extract_document_flow(mock_pipeline_components):
    # Setup mocks
    mocks = mock_pipeline_components
    
    # Mock Filter
    mock_filter_res = MagicMock()
    mock_filter_res.filtered_chunks = [DocumentChunk(text="foo")]
    mock_filter_res.token_stats = {"removed_chunks": 0, "estimated_tokens_saved": 0, "reduction_percentage": 0}
    mocks["filter"].filter_chunks.return_value = mock_filter_res
    
    # Mock Relevance
    mocks["relevance"].get_relevant_chunks.return_value = ([DocumentChunk(text="foo")], {"stats": {}})
    mocks["relevance"].get_classification_summary.return_value = {"relevant_chunks": 1, "total_chunks": 1}
    
    # Mock Extractor
    # Step 1: define response models
    mock_extraction = MagicMock()
    mock_extraction.data = {"field1": "value"}
    mock_extraction.evidence = []
    mocks["extractor"].extract_with_evidence.return_value = mock_extraction
    
    # Mock Checker
    mock_check_res = MagicMock()
    mock_check_res.passed = True
    mock_check_res.accuracy_score = 1.0
    mock_check_res.consistency_score = 1.0
    mock_check_res.overall_score = 1.0
    mock_check_res.issues = []
    mock_check_res.suggestions = []
    mock_check_res.suggestions = []
    mock_check_res.suggestions = []
    mock_check_res.suggestions = []
    mock_check_res.suggestions = []
    mocks["checker"].check.return_value = mock_check_res
    
    # Run
    pipeline = HierarchicalExtractionPipeline()
    doc = ParsedDocument(filename="test.pdf", chunks=[DocumentChunk(text="foo")], full_text="foo")
    
    result = pipeline.extract_document(doc, SampleSchema, theme="test")
    
    assert result.passed_validation is True
    assert result.final_data == {"field1": "value"}
    assert result.iterations == 1
    
    # Verify call order
    mocks["filter"].filter_chunks.assert_called_once()
    mocks["relevance"].get_relevant_chunks.assert_called_once()
    mocks["extractor"].extract_with_evidence.assert_called_once()
    mocks["checker"].check.assert_called_once()

def test_pipeline_retry_loop(mock_pipeline_components):
    mocks = mock_pipeline_components
    
    # Setup basics
    mock_filter_res = MagicMock()
    mock_filter_res.filtered_chunks = [DocumentChunk(text="foo")]
    mock_filter_res.token_stats = {
        "removed_chunks": 0,
        "estimated_tokens_saved": 0,
        "reduction_percentage": 0
    }
    mocks["filter"].filter_chunks.return_value = mock_filter_res
    
    mocks["relevance"].get_relevant_chunks.return_value = ([DocumentChunk(text="foo")], {})
    mocks["relevance"].get_classification_summary.return_value = {"relevant_chunks": 1, "total_chunks": 1}
    
    mock_extraction = MagicMock()
    mock_extraction.data = {"field1": "value"}
    mock_extraction.evidence = []
    mocks["extractor"].extract_with_evidence.return_value = mock_extraction
    
    fail_res = MagicMock()
    fail_res.passed = False
    fail_res.overall_score = 0.5
    fail_res.accuracy_score = 0.5
    fail_res.consistency_score = 0.5
    fail_res.issues = ["issue"]
    fail_res.suggestions = ["fix it"]
    
    pass_res = MagicMock()
    pass_res.passed = True
    pass_res.overall_score = 1.0
    pass_res.accuracy_score = 1.0
    pass_res.consistency_score = 1.0
    pass_res.issues = []
    pass_res.suggestions = []
    
    mocks["checker"].check.side_effect = [fail_res, pass_res]
    
    pipeline = HierarchicalExtractionPipeline(max_iterations=3)
    doc = ParsedDocument(filename="test.pdf", chunks=[DocumentChunk(text="foo")], full_text="foo")
    
    result = pipeline.extract_document(doc, SampleSchema, theme="test")
    
    assert result.passed_validation is True
    assert result.iterations == 2
    assert mocks["extractor"].extract_with_evidence.call_count == 2
    # Second call should have revision prompts
    _, kwargs = mocks["extractor"].extract_with_evidence.call_args_list[1]
    assert kwargs["revision_prompts"] == ["fix it"]
