"""
Tests for Field Library - Phase 3 of Semantic Schema.

Following TDD: Write tests first, verify they fail, then implement.
"""

import pytest
from pydantic.fields import FieldInfo


class TestFieldLibraryUniversalSpecs:
    """Tests for universal field specifications."""
    
    def test_field_library_has_universal_specs(self):
        """FieldLibrary provides 15 universal column specs."""
        from core.fields.library import FieldLibrary
        from core.types.enums import ExtractionPolicy
        
        # Metadata
        assert FieldLibrary.TITLE.key == "title"
        assert FieldLibrary.AUTHORS.key == "authors"
        assert FieldLibrary.YEAR.key == "year"
        assert FieldLibrary.DOI.key == "doi"
        assert FieldLibrary.STUDY_TYPE.key == "study_type"
        
        # Demographics
        assert FieldLibrary.AGE.key == "age"
        assert FieldLibrary.SEX_FEMALE.key == "sex_female"
        assert FieldLibrary.PATIENT_COUNT.key == "patient_count"
        
        # Verify extraction policies
        assert FieldLibrary.TITLE.extraction_policy == ExtractionPolicy.METADATA
        assert FieldLibrary.AGE.extraction_policy == ExtractionPolicy.MUST_BE_EXPLICIT
    
    def test_field_library_specs_generate_fields(self):
        """All universal specs generate valid Pydantic fields."""
        from core.fields.library import FieldLibrary
        
        specs = [
            FieldLibrary.TITLE,
            FieldLibrary.AUTHORS,
            FieldLibrary.YEAR,
            FieldLibrary.AGE,
        ]
        
        for spec in specs:
            field = spec.to_field()
            assert isinstance(field, FieldInfo)


class TestImagingFindingFactory:
    """Tests for imaging_finding factory."""
    
    def test_imaging_finding_factory(self):
        """imaging_finding() generates CT finding specs."""
        from core.fields.library import FieldLibrary
        from core.types.models import FindingReport
        from core.types.enums import ExtractionPolicy
        
        spec = FieldLibrary.imaging_finding(
            name="ground_glass",
            keywords=["GGO", "ground glass opacity"],
        )
        
        assert spec.key == "ct_ground_glass"
        assert spec.dtype == FindingReport
        assert spec.extraction_policy == ExtractionPolicy.MUST_BE_EXPLICIT
        assert spec.source_narrative_field == "ct_narrative"
        assert "GGO" in spec.high_confidence_keywords
        assert spec.requires_evidence_quote == True
    
    def test_imaging_finding_factory_generates_15_dpm_fields(self):
        """Factory can generate all 15 DPM CT finding specs."""
        from core.fields.library import FieldLibrary
        
        ct_findings = [
            ("ground_glass", ["GGO", "ground glass"]),
            ("solid_nodules", ["solid nodule", "solid lesion"]),
            ("central_cavitation", ["cavitation", "cavitary"]),
            ("cystic_micronodules", ["cystic", "micronodule"]),
            ("random", ["random distribution"]),
            ("cheerio", ["cheerio sign", "ring-shaped"]),
            ("upper_lobe_predominance", ["upper lobe"]),
            ("lower_lobe_predominance", ["lower lobe"]),
            ("central_perihilar", ["central", "perihilar"]),
            ("subpleural", ["subpleural"]),
            ("emphysema", ["emphysema"]),
            ("fibrosis", ["fibrosis", "fibrotic"]),
            ("thickened_septum", ["septal", "thickened"]),
        ]
        
        for name, keywords in ct_findings:
            spec = FieldLibrary.imaging_finding(name, keywords)
            assert spec.key.startswith("ct_")
            assert len(spec.high_confidence_keywords) > 0


class TestIHCMarkerFactory:
    """Tests for ihc_marker factory."""
    
    def test_ihc_marker_factory(self):
        """ihc_marker() generates IHC staining specs."""
        from core.fields.library import FieldLibrary
        from core.types.models import FindingReport
        
        spec_pos = FieldLibrary.ihc_marker("EMA", "positive")
        spec_neg = FieldLibrary.ihc_marker("EMA", "negative")
        
        assert spec_pos.key == "ihc_ema_pos"
        assert spec_neg.key == "ihc_ema_neg"
        assert spec_pos.dtype == FindingReport
        assert "EMA" in spec_pos.high_confidence_keywords
        assert "positive" in spec_pos.description.lower()
        assert "negative" in spec_neg.description.lower()
    
    def test_ihc_marker_factory_generates_16_dpm_fields(self):
        """Factory generates all 16 DPM IHC marker specs."""
        from core.fields.library import FieldLibrary
        
        markers = ["EMA", "PR", "Vimentin", "TTF1", "Cytokeratin", "S100", "SMA", "Ki67"]
        
        specs = []
        for marker in markers:
            specs.append(FieldLibrary.ihc_marker(marker, "positive"))
            specs.append(FieldLibrary.ihc_marker(marker, "negative"))
        
        assert len(specs) == 16
        
        # Verify unique keys
        keys = [s.key for s in specs]
        assert len(keys) == len(set(keys))  # No duplicates


class TestBiopsyMethodFactory:
    """Tests for biopsy_method factory."""
    
    def test_biopsy_method_factory(self):
        """biopsy_method() generates biopsy procedure specs."""
        from core.fields.library import FieldLibrary
        from core.types.models import FindingReport
        
        spec_done = FieldLibrary.biopsy_method("TBLB", "TBLB", diagnostic=False)
        spec_diag = FieldLibrary.biopsy_method("TBLB", "TBLB", diagnostic=True)
        
        assert spec_done.key == "biopsy_tblb"
        assert spec_diag.key == "biopsy_tblb_diagnostic"
        assert spec_done.dtype == FindingReport
        assert "TBLB" in spec_done.high_confidence_keywords
        
        # Diagnostic fields should require evidence
        assert spec_diag.requires_evidence_quote == True
    
    def test_biopsy_method_factory_generates_12_dpm_fields(self):
        """Factory generates all 12 DPM biopsy specs."""
        from core.fields.library import FieldLibrary
        
        methods = [
            ("TBLB", "TBLB"),
            ("Endobronchial", "EBB"),
            ("TTNB", "TTNB"),
            ("Surgical", "VATS"),
            ("Cryobiopsy", "cryo"),
            ("Autopsy", "autopsy"),
        ]
        
        specs = []
        for name, acronym in methods:
            specs.append(FieldLibrary.biopsy_method(name, acronym, diagnostic=False))
            specs.append(FieldLibrary.biopsy_method(name, acronym, diagnostic=True))
        
        assert len(specs) == 12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
