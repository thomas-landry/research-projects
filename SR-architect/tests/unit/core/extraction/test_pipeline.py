"""
Tests for Extraction Pipeline - Phase 5 of Semantic Schema.

Following TDD: Write tests first, verify they fail, then implement.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.fields.spec import ColumnSpec
from core.types.models import FindingReport
from core.types.enums import ExtractionPolicy, Status


class TestNarrativeExtraction:
    """Tests for hierarchical narrative extraction."""
    
    @pytest.mark.asyncio
    async def test_extract_narratives_returns_dict(self):
        """extract_narratives returns dict of narrative fields."""
        from core.extraction.narratives import extract_narratives
        
        # Mock the LLM service
        mock_service = AsyncMock()
        mock_service.extract.return_value = {
            "ct_narrative": "CT showed GGO.",
            "symptom_narrative": "Patient had cough."
        }
        
        with patch('core.extraction.narratives.llm_service', mock_service):
            narratives = await extract_narratives("doc.pdf")
            
            assert "ct_narrative" in narratives
            assert narratives["ct_narrative"] == "CT showed GGO."
            assert narratives["symptom_narrative"] == "Patient had cough."


class TestFindingsExtraction:
    """Tests for batch findings extraction."""
    
    @pytest.mark.asyncio
    async def test_extract_findings_batch(self):
        """extract_findings_batch extracts multiple findings from narrative."""
        from core.extraction.findings import extract_findings_batch
        from core.fields.library import FieldLibrary
        
        # specs to extract
        specs = [
            FieldLibrary.imaging_finding("ground_glass", ["GGO"]),
            FieldLibrary.imaging_finding("solid_nodules", ["nodule"])
        ]
        
        # Mock LLM response
        mock_response = {
            "ct_ground_glass": {
                "status": "present",
                "n": 5, 
                "N": 10,
                "evidence_quote": "5 of 10 patients had GGO"
            },
            "ct_solid_nodules": {
                "status": "absent",
                "evidence_quote": "no nodules seen"
            }
        }
        
        mock_service = AsyncMock()
        mock_service.extract_structured.return_value = mock_response
        
        with patch('core.extraction.findings.llm_service', mock_service):
            results = await extract_findings_batch(
                narrative="CT showed GGO in 5/10 patients. No nodules.",
                specs=specs
            )
            
            assert "ct_ground_glass" in results
            assert isinstance(results["ct_ground_glass"], FindingReport)
            assert results["ct_ground_glass"].status == Status.PRESENT
            assert results["ct_ground_glass"].n == 5


class TestExtractionRouter:
    """Tests for extraction policy routing."""
    
    def test_route_by_policy(self):
        """Router returns appropriate handler for policy."""
        from core.extraction.router import route_by_policy, ExtractionHandlerType
        from core.fields.spec import ColumnSpec
        
        # Metadata spec
        meta_spec = ColumnSpec(
            key="title", dtype=str, description="Title", 
            extraction_policy=ExtractionPolicy.METADATA
        )
        handler = route_by_policy(meta_spec)
        assert handler == ExtractionHandlerType.METADATA
        
        # Explicit spec
        explicit_spec = ColumnSpec(
            key="age", dtype=str, description="Age",
            extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT
        )
        handler = route_by_policy(explicit_spec)
        assert handler == ExtractionHandlerType.EXPLICIT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
