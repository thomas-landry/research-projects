"""
Field Library - Reusable column specifications.

Provides universal specs and factory functions for common field patterns
in systematic reviews.
"""

from typing import List, Literal, Optional
from core.fields.spec import ColumnSpec
from core.types.models import FindingReport, MeasurementData, CountData
from core.types.enums import ExtractionPolicy


class FieldLibrary:
    """Library of reusable column specifications."""
    
    # =========================================================================
    # UNIVERSAL METADATA SPECS
    # =========================================================================
    
    TITLE = ColumnSpec(
        key="title",
        dtype=str,
        description="Full article title",
        extraction_policy=ExtractionPolicy.METADATA,
        requires_evidence_quote=False,
    )
    
    AUTHORS = ColumnSpec(
        key="authors",
        dtype=str,
        description="Author list",
        extraction_policy=ExtractionPolicy.METADATA,
        requires_evidence_quote=False,
    )
    
    DOI = ColumnSpec(
        key="doi",
        dtype=str,
        description="Digital Object Identifier (DOI)",
        extraction_policy=ExtractionPolicy.METADATA,
        requires_evidence_quote=False,
    )
    
    YEAR = ColumnSpec(
        key="year",
        dtype=int,
        description="Publication year",
        extraction_policy=ExtractionPolicy.METADATA,
        requires_evidence_quote=False,
        validation={"ge": 1900, "le": 2030},
    )
    
    STUDY_TYPE = ColumnSpec(
        key="study_type",
        dtype=str,
        description="Type of study (case report, case series, cohort, etc.)",
        extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
        requires_evidence_quote=True,
        high_confidence_keywords=["case report", "case series", "cohort", "systematic review"],
    )
    
    # =========================================================================
    # DEMOGRAPHICS SPECS
    # =========================================================================
    
    AGE = ColumnSpec(
        key="age",
        dtype=MeasurementData,
        description="Patient age with normalization",
        extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
        requires_evidence_quote=True,
        high_confidence_keywords=["age", "years old", "median age", "mean age"],
    )
    
    SEX_FEMALE = ColumnSpec(
        key="sex_female",
        dtype=FindingReport,
        description="Female sex distribution (n females, N total)",
        extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
        requires_evidence_quote=True,
        high_confidence_keywords=["female", "women", "sex", "gender"],
    )
    
    PATIENT_COUNT = ColumnSpec(
        key="patient_count",
        dtype=CountData,
        description="Number of patients in cohort",
        extraction_policy=ExtractionPolicy.METADATA,
        requires_evidence_quote=True,
        high_confidence_keywords=["patients", "cases", "subjects", "n="],
    )
    
    # =========================================================================
    # FACTORY FUNCTIONS
    # =========================================================================
    
    @staticmethod
    def imaging_finding(
        name: str,
        keywords: List[str],
        description: Optional[str] = None,
    ) -> ColumnSpec:
        """
        Factory for CT/imaging binary findings.
        
        Args:
            name: Field name suffix (e.g., "ground_glass" → "ct_ground_glass")
            keywords: High-confidence keywords for extraction
            description: Optional custom description
        
        Returns:
            ColumnSpec for imaging finding
        """
        return ColumnSpec(
            key=f"ct_{name}",
            dtype=FindingReport,
            description=description or f"{name.replace('_', ' ').title()} on CT imaging",
            extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
            source_narrative_field="ct_narrative",
            high_confidence_keywords=keywords,
            requires_evidence_quote=True,
        )
    
    @staticmethod
    def ihc_marker(
        marker_name: str,
        polarity: Literal["positive", "negative"],
    ) -> ColumnSpec:
        """
        Factory for IHC marker findings.
        
        Args:
            marker_name: Marker name (e.g., "EMA", "PR")
            polarity: "positive" or "negative"
        
        Returns:
            ColumnSpec for IHC marker
        """
        polarity_short = "pos" if polarity == "positive" else "neg"
        marker_lower = marker_name.lower()
        
        return ColumnSpec(
            key=f"ihc_{marker_lower}_{polarity_short}",
            dtype=FindingReport,
            description=f"{marker_name} {polarity} on immunohistochemistry",
            extraction_policy=ExtractionPolicy.MUST_BE_EXPLICIT,
            source_narrative_field="immunohistochemistry_narrative",
            high_confidence_keywords=[marker_name, polarity, "+", "-"],
            requires_evidence_quote=True,
        )
    
    @staticmethod
    def biopsy_method(
        method_name: str,
        acronym: str,
        diagnostic: bool = False,
    ) -> ColumnSpec:
        """
        Factory for biopsy method findings.
        
        Args:
            method_name: Full method name (e.g., "TBLB", "Surgical")
            acronym: Acronym for keywords (e.g., "TBLB", "VATS")
            diagnostic: Whether this is about diagnostic yield
        
        Returns:
            ColumnSpec for biopsy method
        """
        suffix = "_diagnostic" if diagnostic else ""
        method_lower = method_name.lower().replace(" ", "_")
        
        desc_suffix = " was diagnostic" if diagnostic else " performed"
        
        # Diagnostic fields require higher evidence standard
        policy = ExtractionPolicy.MUST_BE_EXPLICIT if diagnostic else ExtractionPolicy.CAN_BE_INFERRED
        
        return ColumnSpec(
            key=f"biopsy_{method_lower}{suffix}",
            dtype=FindingReport,
            description=f"{method_name} biopsy{desc_suffix}",
            extraction_policy=policy,
            source_narrative_field="diagnostic_approach",
            high_confidence_keywords=[acronym, method_name, "biopsy"],
            requires_evidence_quote=diagnostic,  # Only diagnostic requires quote
        )
