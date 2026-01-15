import unittest
from unittest.mock import MagicMock, patch
from core.hierarchical_pipeline import HierarchicalExtractionPipeline, DocumentChunk, ParsedDocument
from pydantic import BaseModel

class SampleSchema(BaseModel):
    field1: str

class TestPipelineIntegration(unittest.TestCase):
    @patch("core.hierarchical_pipeline.ContentFilter")
    @patch("core.hierarchical_pipeline.RelevanceClassifier")
    @patch("core.hierarchical_pipeline.StructuredExtractor")
    @patch("core.hierarchical_pipeline.ExtractionChecker")
    @patch("core.hierarchical_pipeline.QualityAuditorAgent")
    @patch("core.hierarchical_pipeline.SchemaDiscoveryAgent")
    @patch("core.hierarchical_pipeline.MetaAnalystAgent")
    def test_new_agents_wiring(self, MockMeta, MockSchema, MockAuditor, MockChecker, MockExtractor, MockRelevance, MockFilter):
        # Setup mocks
        mock_filter = MockFilter.return_value
        mock_filter.filter_chunks.return_value.filtered_chunks = [DocumentChunk(text="foo")]
        
        mock_relevance = MockRelevance.return_value
        mock_relevance.get_relevant_chunks.return_value = ([DocumentChunk(text="foo")], {})
        
        mock_extractor = MockExtractor.return_value
        extract_res = MagicMock()
        extract_res.data = {"field1": "value"}
        extract_res.evidence = []
        mock_extractor.extract_with_evidence.return_value = extract_res
        
        mock_checker = MockChecker.return_value
        check_res = MagicMock()
        check_res.passed = True
        check_res.overall_score = 1.0
        check_res.accuracy_score = 1.0
        check_res.consistency_score = 1.0
        check_res.issues = []
        check_res.suggestions = []
        mock_checker.check.return_value = check_res
        
        # --- MOCK THE NEW AGENT ---
        mock_auditor = MockAuditor.return_value
        audit_res = MagicMock()
        audit_res.passed = False  # Simulate a failure to test logic
        audit_res.audits = []
        # Simulate logic: if audit fails, score should drop
        mock_auditor.audit_extraction.return_value = audit_res
        
        # Initialize Pipeline
        pipeline = HierarchicalExtractionPipeline()
        
        # Verify agents initialized
        self.assertIsNotNone(pipeline.quality_auditor)
        self.assertIsNotNone(pipeline.schema_discoverer)
        self.assertIsNotNone(pipeline.meta_analyst)
        
        # Run Extraction
        doc = ParsedDocument(filename="test.pdf", chunks=[DocumentChunk(text="foo")], full_text="foo")
        result = pipeline.extract_document(doc, SampleSchema, theme="test")
        
        # VERIFY CALLS
        self.assertGreaterEqual(mock_auditor.audit_extraction.call_count, 1)
        print("\n✅ QualityAuditorAgent was called successfully!")
        
        # Verify Score Penalty Logic (Should be reduced from 1.0)
        self.assertLess(result.final_overall_score, 1.0)
        print("✅ Score penalty logic for failed audit verified!")
        
        # Verify Schema Discovery Method exists and delegetes
        pipeline.discover_schema("dir")
        pipeline.schema_discoverer.discover_schema.assert_called_with("dir", 3)
        print("✅ discover_schema wired correctly!")

if __name__ == "__main__":
    unittest.main()
