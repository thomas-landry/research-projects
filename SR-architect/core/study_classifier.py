#!/usr/bin/env python3
"""
Study type classifier for routing extraction strategy.

Detects:
- Case Report: Single patient, extract individual data
- Case Series: Multiple patients, extract IPD if table available, else aggregate
- Systematic Review: Extract summary statistics only
"""

from typing import Literal, Optional, Tuple
from pydantic import BaseModel, Field

from core.extractor import StructuredExtractor
from core.utils import get_logger


class StudyClassification(BaseModel):
    """Classification result for a study."""
    
    study_type: Literal[
        "Case Report",
        "Case Series", 
        "Cohort Study",
        "Systematic Review",
        "Literature Review",
        "Unknown"
    ] = Field(description="Type of study")
    
    case_count: int = Field(
        ge=0,
        description="Number of patients/cases. 0 for reviews without new cases."
    )
    
    has_individual_patient_table: bool = Field(
        default=False,
        description="True if study contains table with individual patient data"
    )
    
    extraction_strategy: Literal[
        "individual",  # Extract per-patient data
        "aggregate",   # Extract summary statistics
        "skip"         # Don't extract (e.g., editorial)
    ] = Field(description="Recommended extraction approach")
    
    confidence: float = Field(
        ge=0.0, le=1.0, default=0.9,
        description="Classification confidence"
    )
    
    rationale: str = Field(
        description="Brief explanation for classification"
    )


CLASSIFICATION_PROMPT = """You are classifying scientific papers for a systematic review extraction pipeline.

Analyze the following text (abstract and/or methods) and determine:

1. STUDY TYPE:
   - "Case Report": Single patient case
   - "Case Series": Multiple patients (2+) described
   - "Cohort Study": Observational study with patient cohort
   - "Systematic Review": Review synthesizing multiple studies
   - "Literature Review": Narrative review without original cases
   - "Unknown": Cannot determine

2. CASE COUNT:
   - Number of NEW patients described (not from cited studies)
   - Set to 0 for reviews without original cases

3. INDIVIDUAL PATIENT TABLE:
   - True if there's a table listing individual patient demographics/outcomes
   - This enables row-by-row extraction of patient data

4. EXTRACTION STRATEGY:
   - "individual": Can extract per-patient data (case reports, case series with table)
   - "aggregate": Extract summary statistics only (large cohorts, no IPD table)
   - "skip": Editorial, commentary, or not extractable

Respond with your classification."""


class StudyTypeClassifier:
    """
    Classify study type to route extraction strategy.
    
    Usage:
        classifier = StudyTypeClassifier()
        result = classifier.classify(abstract_text)
        
        if result.extraction_strategy == "individual":
            # Use IndividualPatientData schema
        elif result.extraction_strategy == "aggregate":
            # Use AggregateStudyData schema
    """
    
    def __init__(
        self,
        provider: str = "openrouter",
        model: str = "anthropic/claude-sonnet-4-20250514",
        api_key: Optional[str] = None,
        extractor: Optional[StructuredExtractor] = None,
    ):
        """Initialize classifier."""
        self.extractor = extractor or StructuredExtractor(
            provider=provider,
            model=model,
            api_key=api_key,
        )
        self.extractor.system_prompt = CLASSIFICATION_PROMPT
        self.logger = get_logger("StudyTypeClassifier")
    
    def classify(self, text: str, filename: Optional[str] = None) -> StudyClassification:
        """
        Classify a study based on its text.
        
        Args:
            text: Abstract and/or methods section text
            filename: Source filename for tracking
            
        Returns:
            StudyClassification with type and strategy
        """
        result = self.extractor.extract(
            text=text,
            schema=StudyClassification,
            filename=filename,
        )
        return result
    
    def classify_and_route(
        self, 
        text: str,
        filename: Optional[str] = None,
    ) -> Tuple[StudyClassification, str]:
        """
        Classify and return recommended schema name.
        
        Args:
            text: Document text
            filename: Source filename
            
        Returns:
            Tuple of (classification, schema_name)
        """
        classification = self.classify(text, filename)
        
        if classification.extraction_strategy == "skip":
            schema_name = None
        elif classification.extraction_strategy == "individual":
            if classification.case_count == 1:
                schema_name = "DPMFullExtractionSchema"
            else:
                schema_name = "IndividualPatientData"  # Will need multiple rows
        else:
            schema_name = "AggregateStudyData"
        
        return classification, schema_name


# Heuristic-based pre-classification (no API call)
def quick_classify_heuristic(text: str) -> Tuple[str, int]:
    """
    Quick heuristic classification without API call.
    
    Returns:
        Tuple of (likely_type, estimated_case_count)
    """
    text_lower = text.lower()
    
    # Check for systematic review indicators
    if any(term in text_lower for term in [
        "systematic review", 
        "meta-analysis",
        "prisma",
        "literature search",
        "database search"
    ]):
        return "Systematic Review", 0
    
    # Check for case series indicators  
    case_count_indicators = [
        ("we report", 1),
        ("case report", 1),
        ("we present a case", 1),
        ("a single patient", 1),
        ("case series", 5),  # Assume multi
        ("cases were", 5),
        ("patients were", 5),
    ]
    
    for indicator, count in case_count_indicators:
        if indicator in text_lower:
            return ("Case Report" if count == 1 else "Case Series"), count
    
    # Look for explicit numbers
    import re
    number_patterns = [
        r"(\d+)\s*patients",
        r"(\d+)\s*cases",
        r"case series of (\d+)",
    ]
    
    for pattern in number_patterns:
        match = re.search(pattern, text_lower)
        if match:
            count = int(match.group(1))
            return ("Case Report" if count == 1 else "Case Series"), count
    
    return "Unknown", 0


if __name__ == "__main__":
    # Quick demo without API
    sample_abstract = """
    We report a case of diffuse pulmonary meningotheliomatosis in a 
    52-year-old female presenting with progressive dyspnea over 6 months.
    """
    
    study_type, count = quick_classify_heuristic(sample_abstract)
    print(f"Heuristic classification: {study_type}, {count} case(s)")
    
    sample_abstract2 = """
    We conducted a systematic review of the literature on diffuse pulmonary
    meningotheliomatosis. A comprehensive PRISMA-compliant database search
    identified 35 case reports describing 85 patients.
    """
    
    study_type, count = quick_classify_heuristic(sample_abstract2)
    print(f"Heuristic classification: {study_type}, {count} case(s)")
