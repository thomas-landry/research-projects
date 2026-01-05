#!/usr/bin/env python3
"""
Confidence Router for extraction quality assessment.

Analyzes extraction results and routes to appropriate handling:
- auto_approve: High confidence, proceed automatically
- human_review: Medium confidence, flag for manual check
- re_extract: Low confidence, try again with different prompt
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum


class RouteDecision(str, Enum):
    """Extraction routing decisions."""
    AUTO_APPROVE = "auto_approve"
    HUMAN_REVIEW = "human_review"
    RE_EXTRACT = "re_extract"


@dataclass
class ConfidenceReport:
    """Detailed confidence assessment for an extraction."""
    decision: RouteDecision
    overall_score: float  # 0.0 to 1.0
    
    # Breakdown
    fields_extracted: int
    fields_missing: int
    fields_with_quotes: int
    not_reported_count: int
    
    # Flags
    concerns: List[str]
    
    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "overall_score": round(self.overall_score, 2),
            "fields_extracted": self.fields_extracted,
            "fields_missing": self.fields_missing,
            "fields_with_quotes": self.fields_with_quotes,
            "not_reported_count": self.not_reported_count,
            "concerns": self.concerns,
        }


class ConfidenceRouter:
    """
    Analyzes extraction quality and determines routing.
    
    Scoring factors:
    1. Completeness: % of required fields filled
    2. Traceability: % of fields with source quotes
    3. Uncertainty: Count of "Not reported" values
    4. Self-confidence: LLM's reported confidence (if available)
    """
    
    def __init__(
        self,
        auto_approve_threshold: float = 0.8,
        human_review_threshold: float = 0.5,
        required_fields: List[str] = None,
    ):
        """
        Initialize router with thresholds.
        
        Args:
            auto_approve_threshold: Score >= this → auto approve
            human_review_threshold: Score >= this → human review (else re-extract)
            required_fields: Fields that must be present for high confidence
        """
        self.auto_approve_threshold = auto_approve_threshold
        self.human_review_threshold = human_review_threshold
        self.required_fields = required_fields or []
    
    def assess(self, extracted: Dict[str, Any], schema_fields: List[str]) -> ConfidenceReport:
        """
        Assess extraction quality and determine routing.
        
        Args:
            extracted: The extraction result dict
            schema_fields: List of expected field names (without _quote suffix)
            
        Returns:
            ConfidenceReport with decision and breakdown
        """
        concerns = []
        
        # Count fields
        fields_extracted = 0
        fields_missing = 0
        fields_with_quotes = 0
        not_reported_count = 0
        
        for field in schema_fields:
            value = extracted.get(field)
            quote = extracted.get(f"{field}_quote")
            
            if value is None or value == "":
                fields_missing += 1
            else:
                fields_extracted += 1
                
                # Check for "not reported" variants
                if isinstance(value, str) and any(
                    phrase in value.lower() for phrase in 
                    ["not reported", "not stated", "not available", "n/a", "unknown"]
                ):
                    not_reported_count += 1
            
            # Check quote presence
            if quote and len(str(quote)) > 10:
                fields_with_quotes += 1
        
        total_fields = fields_extracted + fields_missing
        
        # Calculate component scores
        completeness_score = fields_extracted / max(total_fields, 1)
        traceability_score = fields_with_quotes / max(fields_extracted, 1)
        certainty_score = 1.0 - (not_reported_count / max(fields_extracted, 1))
        
        # Check required fields
        required_missing = []
        for req_field in self.required_fields:
            value = extracted.get(req_field)
            if value is None or value == "" or (
                isinstance(value, str) and "not reported" in value.lower()
            ):
                required_missing.append(req_field)
        
        if required_missing:
            concerns.append(f"Missing required fields: {', '.join(required_missing)}")
            completeness_score *= 0.5  # Penalty for missing required
        
        # Use LLM's self-reported confidence if available
        llm_confidence = extracted.get("extraction_confidence", 1.0)
        if llm_confidence and llm_confidence < 0.7:
            concerns.append(f"LLM reported low confidence: {llm_confidence}")
        
        # Calculate overall score (weighted average)
        overall_score = (
            completeness_score * 0.35 +
            traceability_score * 0.30 +
            certainty_score * 0.20 +
            (llm_confidence or 1.0) * 0.15
        )
        
        # Add concerns
        if fields_missing > fields_extracted:
            concerns.append(f"More fields missing ({fields_missing}) than extracted ({fields_extracted})")
        
        if not_reported_count > fields_extracted * 0.5:
            concerns.append(f"High 'not reported' count: {not_reported_count}/{fields_extracted}")
        
        if traceability_score < 0.5:
            concerns.append(f"Low traceability: only {fields_with_quotes}/{fields_extracted} fields have quotes")
        
        # Determine route
        if overall_score >= self.auto_approve_threshold and not concerns:
            decision = RouteDecision.AUTO_APPROVE
        elif overall_score >= self.human_review_threshold:
            decision = RouteDecision.HUMAN_REVIEW
        else:
            decision = RouteDecision.RE_EXTRACT
        
        return ConfidenceReport(
            decision=decision,
            overall_score=overall_score,
            fields_extracted=fields_extracted,
            fields_missing=fields_missing,
            fields_with_quotes=fields_with_quotes,
            not_reported_count=not_reported_count,
            concerns=concerns,
        )
    
    def batch_assess(
        self,
        results: List[Dict[str, Any]],
        schema_fields: List[str],
    ) -> Dict[str, List[str]]:
        """
        Assess multiple extractions and group by route.
        
        Returns:
            Dict mapping route to list of filenames
        """
        routes = {
            RouteDecision.AUTO_APPROVE: [],
            RouteDecision.HUMAN_REVIEW: [],
            RouteDecision.RE_EXTRACT: [],
        }
        
        for result in results:
            filename = result.get("filename", "unknown")
            report = self.assess(result, schema_fields)
            routes[report.decision].append(filename)
        
        return {k.value: v for k, v in routes.items()}


if __name__ == "__main__":
    # Demo
    router = ConfidenceRouter(required_fields=["patient_age", "patient_sex"])
    
    # Good extraction
    good = {
        "patient_age": "52",
        "patient_age_quote": "The patient was a 52-year-old woman",
        "patient_sex": "Female",
        "patient_sex_quote": "52-year-old woman",
        "presenting_symptoms": "Progressive dyspnea",
        "presenting_symptoms_quote": "presented with progressive dyspnea over 6 months",
        "filename": "good_paper.pdf",
        "extraction_confidence": 0.95,
    }
    
    # Poor extraction
    poor = {
        "patient_age": "Not reported",
        "patient_age_quote": "",
        "patient_sex": None,
        "presenting_symptoms": "Unknown",
        "filename": "poor_paper.pdf",
        "extraction_confidence": 0.3,
    }
    
    schema = ["patient_age", "patient_sex", "presenting_symptoms"]
    
    good_report = router.assess(good, schema)
    print(f"Good extraction: {good_report.decision.value} (score: {good_report.overall_score:.2f})")
    
    poor_report = router.assess(poor, schema)
    print(f"Poor extraction: {poor_report.decision.value} (score: {poor_report.overall_score:.2f})")
    print(f"  Concerns: {poor_report.concerns}")
