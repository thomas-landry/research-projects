#!/usr/bin/env python3
"""
Principal Investigator (PI) Orchestrator for PRISMA-Compliant Systematic Reviews.

This is the master controller that enforces:
- PRISMA 2020 protocol adherence
- Methods section documentation
- Flow diagram accuracy
- Agent coordination
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.prisma_state import (
    ReviewState,
    Paper,
    PaperStatus,
    ExclusionReason,
    PICOCriteria,
    create_empty_state,
    recalculate_counts,
    validate_prisma_counts,
)


# ============================================================================
# ORCHESTRATOR SYSTEM PROMPT
# ============================================================================

ORCHESTRATOR_SYSTEM_PROMPT = """
# Role
You are the Principal Investigator (PI) for a rigorous Systematic Review and Meta-Analysis. Your goal is to oversee the lifecycle of evidence synthesis with strict adherence to the PRISMA 2020 guidelines.

# Mission
Coordinate a team of agents (Librarian, Screener, Statistician) to answer a specific Clinical Question (PICO). You are responsible for the integrity of the "Methods" section and the accuracy of the "PRISMA Flow Diagram."

# Responsibilities

1.  **Protocol Enforcement (The Methods Section)**
    * You must define and LOG the exact search strategy used (Databases, Date Ranges, Boolean Strings).
    * You must record the Inclusion/Exclusion criteria explicitly before screening begins.
    * *Output:* At the end of the run, you must generate the text for the "Methods" section describing exactly how the search and screening were conducted.

2.  **Strict Flow Tracking (The PRISMA Diagram)**
    * You must track the count of records at every stage:
        * `n_identified`: Total raw hits.
        * `n_duplicates_removed`: Count of duplicates.
        * `n_screened`: Papers sent to the Screener.
        * `n_excluded`: Papers rejected by the Screener.
        * `n_included`: Papers passing all criteria.
    * **CRITICAL:** You must enforce that the Screener provides a "Reason for Exclusion" for every rejected paper (e.g., "Wrong Study Design," "Wrong Population," "Animal Study"). You cannot accept a rejection without a tagged reason.

3.  **State Management**
    * Do not allow the "Writer" to start synthesizing until the "Screener" has finished and you (the Orchestrator) have verified the PRISMA counts balance (Identified - Duplicates - Excluded = Included).

# Interaction Style
* Be concise and directive.
* If an agent returns vague data (e.g., "I found some papers"), reject it and demand structured JSON with PMIDs and specific counts.
* Prioritize High-Quality Evidence: RCTs > Cohorts > Case Series.
"""


class WorkflowPhase(str, Enum):
    """Phases of the systematic review workflow."""
    PROTOCOL = "protocol"           # Defining PICO and search strategy
    IDENTIFICATION = "identification"  # Librarian fetching papers
    DEDUPLICATION = "deduplication"   # Removing duplicates
    SCREENING = "screening"          # Screener evaluating papers
    EXTRACTION = "extraction"        # Extracting data from included papers
    SYNTHESIS = "synthesis"          # Writing results
    COMPLETE = "complete"


@dataclass
class AgentResponse:
    """Structured response from any agent."""
    success: bool
    agent_name: str
    data: Dict[str, Any]
    error: Optional[str] = None


class OrchestratorPI:
    """
    Principal Investigator Orchestrator for Systematic Reviews.
    
    Enforces PRISMA 2020 compliance and coordinates agents.
    """
    
    def __init__(self, state: Optional[ReviewState] = None):
        """Initialize the orchestrator with optional existing state."""
        self.state = state
        self.phase = WorkflowPhase.PROTOCOL if state is None else self._detect_phase(state)
        self.agents: Dict[str, Callable] = {}
        self.log: List[str] = []
    
    def _detect_phase(self, state: ReviewState) -> WorkflowPhase:
        """Detect current phase from state."""
        if state["is_complete"]:
            return WorkflowPhase.COMPLETE
        
        if not state["bibliography"]:
            return WorkflowPhase.IDENTIFICATION
        
        pending = sum(1 for p in state["bibliography"] if p["status"] == PaperStatus.PENDING.value)
        if pending > 0:
            return WorkflowPhase.SCREENING
        
        if state["count_included"] > 0:
            return WorkflowPhase.EXTRACTION
        
        return WorkflowPhase.COMPLETE
    
    def _log(self, message: str):
        """Add to orchestrator log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{timestamp}] {message}")
        print(f"[PI] {message}")
    
    def register_agent(self, name: str, agent_fn: Callable):
        """Register an agent function."""
        self.agents[name] = agent_fn
        self._log(f"Registered agent: {name}")
    
    def initialize_review(
        self,
        title: str,
        question: str,
        pico: PICOCriteria,
    ) -> ReviewState:
        """
        Initialize a new systematic review.
        
        Args:
            title: Review title
            question: Clinical question
            pico: PICO criteria
            
        Returns:
            Initialized ReviewState
        """
        self._log(f"Initializing review: {title}")
        
        self.state = create_empty_state(title, question, pico)
        self.phase = WorkflowPhase.PROTOCOL
        
        # Log the protocol
        self.state["screening_protocol"] = f"""
INCLUSION CRITERIA:
- Population: {pico['population']}
- Intervention: {pico['intervention']}
- Comparator: {pico['comparator']}
- Outcome: {pico['outcome']}
- Study Design: {pico['study_design']}
- Language: {pico['language']}
- Date Range: {pico['date_range']}

EXCLUSION CRITERIA:
- Excluded study types: {', '.join(pico['excluded_types'])}
"""
        
        self._log("Protocol defined. Ready for identification phase.")
        self.phase = WorkflowPhase.IDENTIFICATION
        
        return self.state
    
    def run_identification(self, search_results: List[Paper], strategy_log: str) -> AgentResponse:
        """
        Process search results from Librarian agent.
        
        Args:
            search_results: Papers from database search
            strategy_log: Documentation of search strategy
            
        Returns:
            AgentResponse with status
        """
        if self.phase != WorkflowPhase.IDENTIFICATION:
            return AgentResponse(
                success=False,
                agent_name="Librarian",
                data={},
                error=f"Cannot run identification in phase: {self.phase}"
            )
        
        # Validate input
        if not search_results:
            return AgentResponse(
                success=False,
                agent_name="Librarian",
                data={},
                error="REJECTED: No papers provided. Provide structured results with PMIDs."
            )
        
        # Check all papers have required fields
        for paper in search_results:
            if not paper.get("pmid") or not paper.get("title"):
                return AgentResponse(
                    success=False,
                    agent_name="Librarian",
                    data={},
                    error=f"REJECTED: Paper missing PMID or title: {paper}"
                )
        
        # Accept results
        self.state["bibliography"] = search_results
        self.state["search_strategy_log"] = strategy_log
        self.state = recalculate_counts(self.state)
        
        self._log(f"Identification complete: {self.state['count_identified']} papers found")
        self.phase = WorkflowPhase.DEDUPLICATION
        
        return AgentResponse(
            success=True,
            agent_name="Librarian",
            data={
                "count_identified": self.state["count_identified"],
                "sources": list(set(p["source_database"] for p in search_results)),
            }
        )
    
    def run_deduplication(self) -> AgentResponse:
        """
        Remove duplicate papers based on PMID.
        
        Returns:
            AgentResponse with deduplication stats
        """
        if self.phase != WorkflowPhase.DEDUPLICATION:
            return AgentResponse(
                success=False,
                agent_name="Deduplicator",
                data={},
                error=f"Cannot deduplicate in phase: {self.phase}"
            )
        
        seen_pmids = set()
        duplicates = 0
        
        for paper in self.state["bibliography"]:
            if paper["pmid"] in seen_pmids:
                paper["status"] = PaperStatus.DUPLICATE.value
                paper["exclusion_reason"] = ExclusionReason.DUPLICATE.value
                duplicates += 1
            else:
                seen_pmids.add(paper["pmid"])
        
        self.state = recalculate_counts(self.state)
        
        self._log(f"Deduplication complete: {duplicates} duplicates removed")
        self._log(f"Papers to screen: {self.state['count_screened']}")
        self.phase = WorkflowPhase.SCREENING
        
        return AgentResponse(
            success=True,
            agent_name="Deduplicator",
            data={
                "count_duplicates": duplicates,
                "count_screened": self.state["count_screened"],
            }
        )
    
    def record_screening_decision(
        self,
        pmid: str,
        include: bool,
        exclusion_reason: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AgentResponse:
        """
        Record a screening decision for a single paper.
        
        CRITICAL: If excluded, must provide exclusion_reason.
        
        Args:
            pmid: Paper PMID
            include: True to include, False to exclude
            exclusion_reason: Required if excluded
            notes: Optional notes
            
        Returns:
            AgentResponse with decision status
        """
        if self.phase != WorkflowPhase.SCREENING:
            return AgentResponse(
                success=False,
                agent_name="Screener",
                data={},
                error=f"Cannot screen in phase: {self.phase}"
            )
        
        # Find paper
        paper = None
        for p in self.state["bibliography"]:
            if p["pmid"] == pmid:
                paper = p
                break
        
        if paper is None:
            return AgentResponse(
                success=False,
                agent_name="Screener",
                data={},
                error=f"REJECTED: PMID {pmid} not found in bibliography"
            )
        
        # CRITICAL: Enforce exclusion reason
        if not include and not exclusion_reason:
            return AgentResponse(
                success=False,
                agent_name="Screener",
                data={},
                error=f"REJECTED: Cannot exclude PMID {pmid} without a reason. "
                      f"Valid reasons: {[e.value for e in ExclusionReason]}"
            )
        
        # Record decision
        if include:
            paper["status"] = PaperStatus.INCLUDED.value
            paper["exclusion_reason"] = None
        else:
            paper["status"] = PaperStatus.EXCLUDED.value
            paper["exclusion_reason"] = exclusion_reason
            paper["exclusion_notes"] = notes
        
        self.state = recalculate_counts(self.state)
        
        return AgentResponse(
            success=True,
            agent_name="Screener",
            data={
                "pmid": pmid,
                "decision": "included" if include else "excluded",
                "reason": exclusion_reason,
            }
        )
    
    def complete_screening(self) -> AgentResponse:
        """
        Finalize screening phase and validate PRISMA counts.
        
        Returns:
            AgentResponse with validation results
        """
        if self.phase != WorkflowPhase.SCREENING:
            return AgentResponse(
                success=False,
                agent_name="Orchestrator",
                data={},
                error=f"Cannot complete screening in phase: {self.phase}"
            )
        
        # Check for pending papers
        pending = [
            p["pmid"] for p in self.state["bibliography"]
            if p["status"] == PaperStatus.PENDING.value
        ]
        
        if pending:
            return AgentResponse(
                success=False,
                agent_name="Orchestrator",
                data={"pending_count": len(pending)},
                error=f"Cannot complete screening: {len(pending)} papers still pending. "
                      f"PMIDs: {pending[:5]}..."
            )
        
        # Validate PRISMA counts
        errors = validate_prisma_counts(self.state)
        
        if errors:
            return AgentResponse(
                success=False,
                agent_name="Orchestrator",
                data={"validation_errors": errors},
                error=f"PRISMA validation failed: {errors}"
            )
        
        self._log(f"Screening complete: {self.state['count_included']} included, "
                  f"{self.state['count_excluded']} excluded")
        self._log(f"Exclusion breakdown: {self.state['count_excluded_reasons']}")
        
        self.phase = WorkflowPhase.EXTRACTION
        
        return AgentResponse(
            success=True,
            agent_name="Orchestrator",
            data={
                "count_included": self.state["count_included"],
                "count_excluded": self.state["count_excluded"],
                "exclusion_reasons": self.state["count_excluded_reasons"],
                "prisma_valid": True,
            }
        )
    
    def get_prisma_counts(self) -> Dict[str, Any]:
        """Get current PRISMA counts for flow diagram."""
        return {
            "identified": self.state["count_identified"],
            "duplicates": self.state["count_duplicates"],
            "screened": self.state["count_screened"],
            "excluded": self.state["count_excluded"],
            "exclusion_reasons": self.state["count_excluded_reasons"],
            "included": self.state["count_included"],
        }
    
    def get_included_papers(self) -> List[Paper]:
        """Get list of included papers for extraction."""
        return [
            p for p in self.state["bibliography"]
            if p["status"] == PaperStatus.INCLUDED.value
        ]
    
    def can_start_synthesis(self) -> bool:
        """Check if synthesis can begin (all screening complete and valid)."""
        if self.phase not in [WorkflowPhase.EXTRACTION, WorkflowPhase.SYNTHESIS]:
            return False
        
        errors = validate_prisma_counts(self.state)
        return len(errors) == 0


if __name__ == "__main__":
    # Demo workflow
    pico = PICOCriteria(
        population="Adult ICU patients",
        intervention="Prophylactic bowel protocol",
        comparator="Standard care",
        outcome="Constipation incidence",
        study_design="RCT, cohort",
        language="English",
        date_range="2000-2024",
        excluded_types=["animal_study", "in_vitro_study"],
    )
    
    pi = OrchestratorPI()
    
    # Initialize
    pi.initialize_review(
        title="Bowel Protocols in ICU",
        question="Does prophylactic bowel management reduce constipation?",
        pico=pico,
    )
    
    print(f"\nPhase: {pi.phase}")
    print(f"Protocol:\n{pi.state['screening_protocol']}")
