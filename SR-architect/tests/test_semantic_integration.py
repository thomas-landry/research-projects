"""
Integration test for Semantic Chunker in Pipeline.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from core.pipeline import HierarchicalExtractionPipeline
from core.parser import DocumentChunk

# @pytest.mark.asyncio -- removed to allow synchronous chunk() call
def test_pipeline_segment_document():
    # Mock dependencies
    provider = "mock"
    model = "mock-model"
    
    # Patch utils.get_async_llm_client to return a mock
    with patch('core.utils.get_async_llm_client') as mock_get_client:
        mock_client = MagicMock()
        mock_create = AsyncMock()
        mock_create.return_value.choices[0].message.content = '[{"title": "Methods", "anchor_text": "Methods"}]'
        mock_client.chat.completions.create = mock_create
        mock_get_client.return_value = mock_client
        
        pipeline = HierarchicalExtractionPipeline(provider=provider, model=model)
        
        text = "Abstract\nContent.\nMethods\nStart of methods."
        chunks = pipeline.segment_document(text, doc_id="test_doc")
        
        assert len(chunks) > 0
        assert isinstance(chunks[0], DocumentChunk)
        # Should find "Methods" section
        # Logic: Intro -> Methods (Abstract)
        # Methods -> End (Methods)
        assert len(chunks) == 2
        assert chunks[1].section == "Methods"
