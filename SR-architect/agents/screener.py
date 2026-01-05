#!/usr/bin/env python3
"""
Screener Agent for Systematic Review - Abstract Screening with PICO Criteria.

Takes an abstract and strictly categorizes it against PICO criteria,
returning a structured decision with exclusion reason.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.prisma_state import Paper, PaperStatus, ExclusionReason, PICOCriteria


class ScreeningDecision(BaseModel):
    """Structured screening decision from the Screener agent."""
    include: bool = Field(description="True to include, False to exclude")
    exclusion_reason: Optional[str] = Field(
        default=None,
        description="Required if include=False. Must be one of the standard reasons."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in this decision (0-1)"
    )
    relevant_quote: Optional[str] = Field(
        default=None,
        description="Quote from abstract supporting the decision"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes"
    )


class ScreenerAgent:
    """
    Screener Agent for abstract-level screening.
    
    Uses LLM to evaluate abstracts against PICO criteria and return
    structured inclusion/exclusion decisions.
    """
    
    SCREENING_PROMPT = """You are a systematic review screener evaluating abstracts for inclusion.

## PICO CRITERIA

**Population:** {population}
**Intervention:** {intervention}
**Comparator:** {comparator}
**Outcome:** {outcome}
**Study Design:** {study_design}

## EXCLUSION CRITERIA
Papers should be EXCLUDED if they match any of these:
{exclusion_criteria}

## VALID EXCLUSION REASONS
You MUST use one of these exact codes if excluding:
- wrong_population: Patients don't match (e.g., wrong disease, pediatric when adults needed)
- wrong_intervention: Treatment doesn't match
- wrong_comparator: Comparator doesn't match
- wrong_outcome: Outcome not measured
- wrong_study_design: Design not appropriate (e.g., editorial, narrative review)
- animal_study: Non-human subjects
- in_vitro_study: Cell/tissue study only
- review_article: Systematic review, meta-analysis, narrative review
- case_report_excluded: Single case report (if excluded per criteria)
- non_english: Not in English
- conference_abstract_only: Only abstract available, no full paper
- other: Other reason (must explain in notes)

## INSTRUCTIONS
1. Read the abstract carefully
2. Check EACH PICO element
3. If ALL criteria are met → include=True
4. If ANY criterion fails → include=False, provide exclusion_reason
5. Always provide confidence (0-1) and a relevant_quote

## ABSTRACT TO SCREEN

**Title:** {title}

**Abstract:**
{abstract}

Respond with a JSON object matching this schema:
{{
    "include": true/false,
    "exclusion_reason": "reason_code" or null,
    "confidence": 0.0-1.0,
    "relevant_quote": "quote from abstract",
    "notes": "optional notes"
}}
"""

    def __init__(
        self,
        pico_criteria: PICOCriteria,
        provider: str = "openrouter",
        model: Optional[str] = None,
    ):
        """
        Initialize Screener with PICO criteria.
        
        Args:
            pico_criteria: PICO inclusion criteria
            provider: LLM provider
            model: Model override
        """
        self.pico = pico_criteria
        self.provider = provider
        self.model = model or "anthropic/claude-sonnet-4-20250514"
        self._client = None
    
    def _load_env(self):
        """Load environment variables."""
        env_paths = [
            Path.cwd() / ".env",
            Path(__file__).parent.parent / ".env",
            Path.home() / "Projects" / ".env",
        ]
        for env_path in env_paths:
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            os.environ.setdefault(key.strip(), value.strip().strip("'\""))
                break
    
    def _get_client(self):
        """Initialize Instructor-patched client."""
        if self._client is not None:
            return self._client
        
        self._load_env()
        
        try:
            import instructor
            from openai import OpenAI
        except ImportError:
            raise ImportError("Install: pip install instructor openai")
        
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        
        self._client = instructor.from_openai(client)
        return self._client
    
    def screen_abstract(self, paper: Paper) -> ScreeningDecision:
        """
        Screen a single paper based on title and abstract.
        
        Args:
            paper: Paper to screen
            
        Returns:
            ScreeningDecision with include/exclude and reason
        """
        client = self._get_client()
        
        # Build exclusion criteria text
        exclusion_text = "\n".join(
            f"- {et}" for et in self.pico.get("excluded_types", [])
        )
        
        prompt = self.SCREENING_PROMPT.format(
            population=self.pico["population"],
            intervention=self.pico["intervention"],
            comparator=self.pico["comparator"],
            outcome=self.pico["outcome"],
            study_design=self.pico["study_design"],
            exclusion_criteria=exclusion_text or "None specified",
            title=paper["title"],
            abstract=paper["abstract"] or "No abstract available",
        )
        
        try:
            decision = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_model=ScreeningDecision,
            )
            
            # Validate exclusion reason if excluded
            if not decision.include and not decision.exclusion_reason:
                decision.exclusion_reason = ExclusionReason.OTHER.value
                decision.notes = (decision.notes or "") + " [Auto-assigned: no reason provided]"
            
            return decision
        
        except Exception as e:
            # Return a conservative decision on error
            return ScreeningDecision(
                include=False,
                exclusion_reason=ExclusionReason.OTHER.value,
                confidence=0.0,
                notes=f"Screening error: {e}",
            )
    
    def screen_batch(
        self,
        papers: List[Paper],
        callback=None,
    ) -> Dict[str, ScreeningDecision]:
        """
        Screen multiple papers.
        
        Args:
            papers: List of papers to screen
            callback: Optional function called after each decision
            
        Returns:
            Dict mapping PMID to ScreeningDecision
        """
        results = {}
        
        for i, paper in enumerate(papers):
            if paper["status"] != PaperStatus.PENDING.value:
                continue
            
            print(f"[Screener] Screening {i+1}/{len(papers)}: {paper['pmid']}")
            
            decision = self.screen_abstract(paper)
            results[paper["pmid"]] = decision
            
            if callback:
                callback(paper["pmid"], decision)
        
        return results


def screen_paper_simple(
    title: str,
    abstract: str,
    pico: PICOCriteria,
) -> ScreeningDecision:
    """
    Convenience function to screen a single paper.
    
    Args:
        title: Paper title
        abstract: Paper abstract
        pico: PICO criteria
        
    Returns:
        ScreeningDecision
    """
    paper = Paper(
        pmid="temp",
        doi=None,
        title=title,
        authors="",
        journal="",
        year=0,
        abstract=abstract,
        status=PaperStatus.PENDING.value,
        exclusion_reason=None,
        exclusion_notes=None,
        source_database="manual",
        retrieved_date="",
    )
    
    screener = ScreenerAgent(pico)
    return screener.screen_abstract(paper)


# Rule-based pre-screener for fast exclusion
class RuleBasedPreScreener:
    """
    Fast rule-based pre-screening to exclude obvious non-matches.
    
    Runs before LLM screening to save API calls.
    """
    
    def __init__(self, pico: PICOCriteria):
        self.pico = pico
        
        # Build exclusion patterns
        self.animal_patterns = [
            "mice", "mouse", "rat", "rats", "murine", "rodent",
            "rabbit", "canine", "porcine", "bovine", "ovine",
        ]
        
        self.in_vitro_patterns = [
            "cell line", "in vitro", "cell culture", "cultured cells",
            "hela", "primary cells",
        ]
        
        self.review_patterns = [
            "systematic review", "meta-analysis", "narrative review",
            "scoping review", "umbrella review",
        ]
    
    def pre_screen(self, paper: Paper) -> Optional[ScreeningDecision]:
        """
        Quick rule-based pre-screening.
        
        Returns decision if definitely excluded, None if needs LLM review.
        """
        text = (paper["title"] + " " + (paper["abstract"] or "")).lower()
        
        # Check animal study
        if "animal_study" in self.pico.get("excluded_types", []):
            for pattern in self.animal_patterns:
                if pattern in text:
                    return ScreeningDecision(
                        include=False,
                        exclusion_reason=ExclusionReason.ANIMAL_STUDY.value,
                        confidence=0.95,
                        relevant_quote=f"Contains '{pattern}'",
                        notes="Rule-based exclusion",
                    )
        
        # Check in vitro
        if "in_vitro_study" in self.pico.get("excluded_types", []):
            for pattern in self.in_vitro_patterns:
                if pattern in text:
                    return ScreeningDecision(
                        include=False,
                        exclusion_reason=ExclusionReason.IN_VITRO_STUDY.value,
                        confidence=0.9,
                        relevant_quote=f"Contains '{pattern}'",
                        notes="Rule-based exclusion",
                    )
        
        # Check review article
        if "review_article" in self.pico.get("excluded_types", []):
            for pattern in self.review_patterns:
                if pattern in text:
                    return ScreeningDecision(
                        include=False,
                        exclusion_reason=ExclusionReason.REVIEW_ARTICLE.value,
                        confidence=0.9,
                        relevant_quote=f"Contains '{pattern}'",
                        notes="Rule-based exclusion",
                    )
        
        # No clear exclusion, needs LLM
        return None


if __name__ == "__main__":
    # Demo
    pico = PICOCriteria(
        population="Adult ICU patients",
        intervention="Prophylactic bowel protocol",
        comparator="Standard care",
        outcome="Constipation incidence",
        study_design="RCT, cohort, before-after",
        language="English",
        date_range="2000-2024",
        excluded_types=["animal_study", "in_vitro_study", "review_article"],
    )
    
    # Test rule-based pre-screener
    pre_screener = RuleBasedPreScreener(pico)
    
    test_papers = [
        Paper(
            pmid="1",
            doi=None,
            title="Effect of laxatives in ICU patients: a meta-analysis",
            authors="",
            journal="",
            year=2023,
            abstract="This systematic review analyzed...",
            status=PaperStatus.PENDING.value,
            exclusion_reason=None,
            exclusion_notes=None,
            source_database="test",
            retrieved_date="",
        ),
        Paper(
            pmid="2",
            doi=None,
            title="Bowel function in critically ill mice",
            authors="",
            journal="",
            year=2023,
            abstract="We studied murine models of critical illness...",
            status=PaperStatus.PENDING.value,
            exclusion_reason=None,
            exclusion_notes=None,
            source_database="test",
            retrieved_date="",
        ),
    ]
    
    for paper in test_papers:
        result = pre_screener.pre_screen(paper)
        if result:
            print(f"PMID {paper['pmid']}: EXCLUDED ({result.exclusion_reason})")
        else:
            print(f"PMID {paper['pmid']}: Needs LLM review")
