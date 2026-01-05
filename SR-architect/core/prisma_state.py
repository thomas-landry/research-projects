#!/usr/bin/env python3
"""
PRISMA-Compliant State Schema for Systematic Review Pipeline.

This module defines the state structure that tracks all PRISMA 2020 requirements:
- Identification counts
- Screening decisions with exclusion reasons
- Methods section documentation
- Flow diagram data
"""

from typing import TypedDict, List, Dict, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ExclusionReason(str, Enum):
    """Standardized exclusion reasons for PRISMA compliance."""
    WRONG_POPULATION = "wrong_population"
    WRONG_INTERVENTION = "wrong_intervention"
    WRONG_COMPARATOR = "wrong_comparator"
    WRONG_OUTCOME = "wrong_outcome"
    WRONG_STUDY_DESIGN = "wrong_study_design"
    ANIMAL_STUDY = "animal_study"
    IN_VITRO_STUDY = "in_vitro_study"
    REVIEW_ARTICLE = "review_article"
    CASE_REPORT_EXCLUDED = "case_report_excluded"
    DUPLICATE = "duplicate"
    FULL_TEXT_UNAVAILABLE = "full_text_unavailable"
    NON_ENGLISH = "non_english"
    CONFERENCE_ABSTRACT_ONLY = "conference_abstract_only"
    RETRACTED = "retracted"
    OTHER = "other"


class PaperStatus(str, Enum):
    """Status of a paper in the screening pipeline."""
    PENDING = "pending"
    INCLUDED = "included"
    EXCLUDED = "excluded"
    DUPLICATE = "duplicate"


class Paper(TypedDict):
    """A single paper in the systematic review bibliography."""
    # Identifiers
    pmid: str
    doi: Optional[str]
    
    # Bibliographic data
    title: str
    authors: str
    journal: str
    year: int
    abstract: str
    
    # Screening status
    status: str  # PaperStatus value
    
    # CRITICAL for PRISMA: Must have reason if excluded
    exclusion_reason: Optional[str]  # ExclusionReason value
    exclusion_notes: Optional[str]   # Additional context
    
    # Provenance
    source_database: str  # PubMed, Embase, etc.
    retrieved_date: str


class PICOCriteria(TypedDict):
    """PICO(S) criteria for inclusion/exclusion."""
    population: str           # e.g., "Adult ICU patients"
    intervention: str         # e.g., "Prophylactic bowel protocol"
    comparator: str           # e.g., "Standard care or no protocol"
    outcome: str              # e.g., "Incidence of constipation"
    study_design: str         # e.g., "RCT, cohort, before-after"
    
    # Additional criteria
    language: str             # e.g., "English"
    date_range: str           # e.g., "2000-2024"
    excluded_types: List[str] # e.g., ["animal_study", "in_vitro"]


class SearchStrategy(TypedDict):
    """Documented search strategy for Methods section."""
    database: str
    search_date: str
    search_string: str
    filters_applied: List[str]
    results_count: int


class ReviewState(TypedDict):
    """
    Complete state for PRISMA-compliant systematic review.
    
    This structure is the single source of truth for:
    - The Methods section text
    - The PRISMA Flow Diagram numbers
    - All screening decisions with audit trail
    """
    
    # === PROTOCOL DEFINITION ===
    review_title: str
    review_question: str  # The clinical question
    pico_criteria: PICOCriteria
    
    # === METHODS DOCUMENTATION ===
    search_strategies: List[SearchStrategy]
    search_strategy_log: str  # Narrative for Methods section
    screening_protocol: str   # How screening was conducted
    
    # === THE BIBLIOGRAPHY ===
    bibliography: List[Paper]
    
    # === PRISMA COUNTERS (Auto-calculated from bibliography) ===
    # Identification
    count_identified: int           # Total raw hits from all databases
    count_duplicates: int           # Removed as duplicates
    
    # Screening
    count_screened: int             # Unique papers screened
    count_excluded: int             # Total excluded
    count_excluded_reasons: Dict[str, int]  # Breakdown by reason
    
    # Inclusion
    count_included: int             # Papers passing all criteria
    
    # === WORKFLOW STATUS ===
    current_phase: str              # identification, screening, extraction, synthesis
    is_complete: bool
    validation_errors: List[str]


def create_empty_state(
    title: str,
    question: str,
    pico: PICOCriteria,
) -> ReviewState:
    """Create a new empty review state with initialized counters."""
    return ReviewState(
        review_title=title,
        review_question=question,
        pico_criteria=pico,
        search_strategies=[],
        search_strategy_log="",
        screening_protocol="",
        bibliography=[],
        count_identified=0,
        count_duplicates=0,
        count_screened=0,
        count_excluded=0,
        count_excluded_reasons={},
        count_included=0,
        current_phase="identification",
        is_complete=False,
        validation_errors=[],
    )


def recalculate_counts(state: ReviewState) -> ReviewState:
    """
    Recalculate all PRISMA counts from the bibliography.
    
    This ensures counts are always accurate based on actual paper statuses.
    """
    papers = state["bibliography"]
    
    # Reset counts
    state["count_identified"] = len(papers)
    state["count_duplicates"] = sum(1 for p in papers if p["status"] == PaperStatus.DUPLICATE.value)
    state["count_screened"] = state["count_identified"] - state["count_duplicates"]
    state["count_included"] = sum(1 for p in papers if p["status"] == PaperStatus.INCLUDED.value)
    state["count_excluded"] = sum(1 for p in papers if p["status"] == PaperStatus.EXCLUDED.value)
    
    # Count exclusion reasons
    reason_counts: Dict[str, int] = {}
    for p in papers:
        if p["status"] == PaperStatus.EXCLUDED.value and p["exclusion_reason"]:
            reason = p["exclusion_reason"]
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    state["count_excluded_reasons"] = reason_counts
    
    return state


def validate_prisma_counts(state: ReviewState) -> List[str]:
    """
    Validate that PRISMA counts are balanced and complete.
    
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    # Check: Screened = Identified - Duplicates
    expected_screened = state["count_identified"] - state["count_duplicates"]
    if state["count_screened"] != expected_screened:
        errors.append(
            f"Screened count mismatch: {state['count_screened']} != "
            f"Identified ({state['count_identified']}) - Duplicates ({state['count_duplicates']})"
        )
    
    # Check: Included + Excluded = Screened
    total_decided = state["count_included"] + state["count_excluded"]
    pending = sum(1 for p in state["bibliography"] if p["status"] == PaperStatus.PENDING.value)
    
    if pending > 0:
        errors.append(f"{pending} papers still pending screening")
    
    if total_decided != state["count_screened"]:
        errors.append(
            f"Decision count mismatch: Included ({state['count_included']}) + "
            f"Excluded ({state['count_excluded']}) = {total_decided} != "
            f"Screened ({state['count_screened']})"
        )
    
    # Check: All excluded papers have reasons
    missing_reasons = [
        p["pmid"] for p in state["bibliography"]
        if p["status"] == PaperStatus.EXCLUDED.value and not p["exclusion_reason"]
    ]
    if missing_reasons:
        errors.append(f"Papers excluded without reason: {missing_reasons[:5]}...")
    
    # Check: Exclusion reason counts match
    total_by_reason = sum(state["count_excluded_reasons"].values())
    if total_by_reason != state["count_excluded"]:
        errors.append(
            f"Exclusion reason counts don't sum: {total_by_reason} != {state['count_excluded']}"
        )
    
    state["validation_errors"] = errors
    return errors


if __name__ == "__main__":
    # Demo
    pico = PICOCriteria(
        population="Adult ICU patients",
        intervention="Prophylactic bowel protocol",
        comparator="Standard care",
        outcome="Incidence of constipation",
        study_design="RCT, cohort, before-after",
        language="English",
        date_range="2000-2024",
        excluded_types=["animal_study", "in_vitro_study"],
    )
    
    state = create_empty_state(
        title="Bowel Protocol in ICU",
        question="Does prophylactic bowel management reduce constipation in ICU?",
        pico=pico,
    )
    
    # Add some papers
    state["bibliography"] = [
        Paper(
            pmid="12345678",
            doi="10.1000/example",
            title="Example RCT",
            authors="Smith et al.",
            journal="Crit Care Med",
            year=2023,
            abstract="Background: ...",
            status=PaperStatus.INCLUDED.value,
            exclusion_reason=None,
            exclusion_notes=None,
            source_database="PubMed",
            retrieved_date="2024-01-15",
        ),
        Paper(
            pmid="23456789",
            doi=None,
            title="Animal Study",
            authors="Jones et al.",
            journal="Lab Research",
            year=2022,
            abstract="In mice...",
            status=PaperStatus.EXCLUDED.value,
            exclusion_reason=ExclusionReason.ANIMAL_STUDY.value,
            exclusion_notes="Mouse model, not applicable",
            source_database="PubMed",
            retrieved_date="2024-01-15",
        ),
    ]
    
    state = recalculate_counts(state)
    errors = validate_prisma_counts(state)
    
    print(f"State: {state['count_identified']} identified, {state['count_included']} included")
    print(f"Validation errors: {errors}")
