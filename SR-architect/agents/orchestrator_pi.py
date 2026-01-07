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
from core.batch_processor import BatchExecutor
from core.state_manager import StateManager
from core.schema_builder import get_observational_schema, build_extraction_model
from core.parser import DocumentParser
from core.utils import get_logger
from core.audit_logger import AuditLogger

# Agent Imports
from agents.librarian import LibrarianAgent
from agents.screener import ScreenerAgent
from agents.synthesizer import SynthesizerAgent
from core.extractor import StructuredExtractor
from core.schema_builder import get_observational_schema, build_extraction_model


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
    
    def __init__(
        self, 
        state: Optional[ReviewState] = None,
        librarian: Optional[LibrarianAgent] = None,
        screener: Optional[ScreenerAgent] = None,
        extractor: Optional[StructuredExtractor] = None,
        synthesizer: Optional[SynthesizerAgent] = None
    ):
        """
        Initialize the orchestrator.
        
        Args:
            state: Existing review state (optional)
            librarian: Injected LibrarianAgent
            screener: Injected ScreenerAgent
            extractor: Injected StructuredExtractor
            synthesizer: Injected SynthesizerAgent
        """
        self.state = state
        self.phase = WorkflowPhase.PROTOCOL if state is None else self._detect_phase(state)
        
        # Dependency Injection with lazy defaults if not provided
        self.librarian = librarian or LibrarianAgent()
        self.screener = screener  # Screener often needs PICO, so strictly we might init later if not provided
        self.extractor = extractor or StructuredExtractor()
        self.synthesizer = synthesizer or SynthesizerAgent()
        
        self.logger = get_logger("OrchestratorPI")
        self.audit = AuditLogger()
        self.log_history: List[str] = []
    
    def _detect_phase(self, state: ReviewState) -> WorkflowPhase:
        """Detect current phase from state."""
        if state.get("is_complete"):
            return WorkflowPhase.COMPLETE
        
        if not state.get("bibliography"):
            return WorkflowPhase.IDENTIFICATION
        
        pending = sum(1 for p in state["bibliography"] if p["status"] == PaperStatus.PENDING.value)
        if pending > 0:
            return WorkflowPhase.SCREENING
        
        if state["count_included"] > 0 and not state.get("extraction_results"):
            return WorkflowPhase.EXTRACTION
            
        if state.get("extraction_results"):
            return WorkflowPhase.SYNTHESIS
        
        return WorkflowPhase.COMPLETE
    
    def _log(self, message: str, level: str = "info"):
        """Internal log wrapper."""
        # Keep log history for report generation if needed
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_history.append(f"[{timestamp}] {message}")
        
        if level == "error":
            self.logger.error(message)
        else:
            self.logger.info(message)
    
    def initialize_review(
        self,
        title: str,
        question: str,
        pico: PICOCriteria,
    ) -> ReviewState:
        """Initialize a new systematic review."""
        self._log(f"Initializing review: {title}")
        
        self.state = create_empty_state(title, question, pico)
        if "review_id" not in self.state:
            import uuid
            self.state["review_id"] = str(uuid.uuid4())
            
        self.phase = WorkflowPhase.PROTOCOL
        
        # Re-initialize screener with new PICO if it wasn't injected or needs update
        if not self.screener or self.screener.pico != pico:
            self.screener = ScreenerAgent(pico)

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
        """Process search results from Librarian agent."""
        if self.phase != WorkflowPhase.IDENTIFICATION:
            self._log(f"Cannot run identification in phase: {self.phase}", "error")
            return AgentResponse(False, "Librarian", {}, f"Wrong phase: {self.phase}")
        
        if not search_results:
            self._log("Librarian returned no papers.", "error")
            return AgentResponse(False, "Librarian", {}, "No papers provided")
        
        # Validate input
        for paper in search_results:
            if not paper.get("pmid") or not paper.get("title"):
                self._log(f"Paper missing PMID/title: {paper}", "error")
                return AgentResponse(False, "Librarian", {}, f"Paper missing PMID/title: {paper}")
        
        # Accept results
        self.state["bibliography"] = search_results
        self.state["search_strategy_log"] = strategy_log
        self.state = recalculate_counts(self.state)
        
        self._log(f"Identification complete: {self.state['count_identified']} papers found")
        self.audit.log_event("identification_complete", {"count": len(search_results)})
        
        self.phase = WorkflowPhase.DEDUPLICATION
        
        return AgentResponse(
            success=True,
            agent_name="Librarian",
            data={
                "count_identified": self.state["count_identified"],
                "sources": list(set(p.get("source_database", "unknown") for p in search_results)),
            }
        )
    
    def run_deduplication(self) -> AgentResponse:
        """Remove duplicate papers based on PMID."""
        if self.phase != WorkflowPhase.DEDUPLICATION:
             self._log(f"Cannot run deduplication in phase: {self.phase}", "error")
             return AgentResponse(False, "Deduplicator", {}, f"Wrong phase: {self.phase}")
        
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
        """
        if self.phase != WorkflowPhase.SCREENING:
            return AgentResponse(False, "Screener", {}, f"Wrong phase: {self.phase}")
        
        # Find paper
        paper = next((p for p in self.state["bibliography"] if p["pmid"] == pmid), None)
        
        if paper is None:
            return AgentResponse(False, "Screener", {}, f"PMID {pmid} not found")
        
        # CRITICAL: Enforce exclusion reason
        if not include and not exclusion_reason:
            return AgentResponse(False, "Screener", {}, "Cannot exclude without reason")
        
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
        """Finalize screening phase and validate PRISMA counts."""
        if self.phase != WorkflowPhase.SCREENING:
            return AgentResponse(False, "Orchestrator", {}, f"Wrong phase: {self.phase}")
        
        pending = [
            p["pmid"] for p in self.state["bibliography"]
            if p["status"] == PaperStatus.PENDING.value
        ]
        
        if pending:
            return AgentResponse(False, "Orchestrator", {"pending": pending}, f"{len(pending)} papers pending")
        
        errors = validate_prisma_counts(self.state)
        if errors:
            return AgentResponse(False, "Orchestrator", {"errors": errors}, "PRISMA validation failed")
        
        self._log(f"Screening complete: {self.state['count_included']} included, {self.state['count_excluded']} excluded")
        self.phase = WorkflowPhase.EXTRACTION
        
        return AgentResponse(
            success=True,
            agent_name="Orchestrator",
            data={
                "included": self.state["count_included"],
                "excluded": self.state["count_excluded"],
                "prisma_valid": True,
            }
        )
    
    def get_included_papers(self) -> List[Paper]:
        """Get list of included papers for extraction."""
        return [
            p for p in self.state["bibliography"]
            if p["status"] == PaperStatus.INCLUDED.value
        ]

    async def run_pipeline(self):
        """Execute the full systematic review pipeline automatically (Async)."""
        self._log(f"Starting automated async pipeline. Initial phase: {self.phase}")
        
        while self.phase != WorkflowPhase.COMPLETE:
            if self.phase == WorkflowPhase.PROTOCOL:
                self._log("Protocol phase active. Please initialize review first.", "error")
                break
                
            elif self.phase == WorkflowPhase.IDENTIFICATION:
                self._run_identification_phase()
                
            elif self.phase == WorkflowPhase.DEDUPLICATION:
                self._run_deduplication_phase()
                
            elif self.phase == WorkflowPhase.SCREENING:
                # Screening can be parallel but its callback structure and internal state updates
                # are currently synchronous. screen_batch internally uses ThreadPoolExecutor.
                # We'll stick to calling it but the pipeline remains async-ready.
                self._run_screening_phase()
                
            elif self.phase == WorkflowPhase.EXTRACTION:
                await self._run_extraction_phase()
                
            elif self.phase == WorkflowPhase.SYNTHESIS:
                self._run_synthesis_phase()
                
            else:
                self._log(f"Unknown phase: {self.phase}", "error")
                break
                
        self._log("Pipeline execution finished.")

    def _run_identification_phase(self):
        """Execute Librarian search."""
        self._log("=== PHASE: IDENTIFICATION ===")
        
        pico = self.state['pico_criteria']
        query = f"({pico['population']}) AND ({pico['intervention']}) AND ({pico['outcome']})"
        self._log(f"Generated Query: {query}")
        
        papers, strategy = self.librarian.run_search(query, max_results=20)
        self.run_identification(papers, str(strategy))

    def _run_deduplication_phase(self):
        """Execute Deduplication."""
        self._log("=== PHASE: DEDUPLICATION ===")
        self.run_deduplication()

    def _run_screening_phase(self):
        """Execute Screener agent."""
        self._log("=== PHASE: SCREENING ===")
        
        # Ensure screener is configured
        if not self.screener or self.screener.pico != self.state['pico_criteria']:
            self.screener = ScreenerAgent(self.state['pico_criteria'])
        
        pending = [p for p in self.state["bibliography"] if p["status"] == PaperStatus.PENDING.value]
        self._log(f"Screening {len(pending)} pending papers...")
        
        def _decision_callback(pmid, decision):
            self.record_screening_decision(
                pmid=pmid,
                include=decision.include,
                exclusion_reason=decision.exclusion_reason,
                notes=decision.notes
            )
            
        self.screener.screen_batch(pending, callback=_decision_callback)
        self.complete_screening()

    async def _run_extraction_phase(self):
        """Execute Extraction agent (Async Batch)."""
        self._log("=== PHASE: EXTRACTION ===")
        
        schema_fields = get_observational_schema()
        ExtractionModel = build_extraction_model(schema_fields, "SRExtractionModel")
        
        included = self.get_included_papers()
        self._log(f"Extracting data from {len(included)} included papers in parallel (Async)...")
        
        # 1. Prepare StateManager for batch
        state_path = f".cache/reviews/{self.state['review_id']}_batch.json"
        temp_state_manager = StateManager(state_path)
        
        # 2. Prepare BatchExecutor
        executor = BatchExecutor(
            pipeline=self.extractor, 
            state_manager=temp_state_manager,
            max_workers=5
        )
        
        # 3. Prepare "Documents" 
        from core.parser import ParsedDocument, DocumentChunk
        docs_to_process = []
        for paper in included:
            doc = ParsedDocument(
                filename=f"{paper['pmid']}.pdf",
                full_text=f"Title: {paper['title']}\nAbstract: {paper['abstract']}",
                chunks=[DocumentChunk(text=paper['abstract'], section="Abstract")]
            )
            doc.metadata["pmid"] = paper["pmid"]
            docs_to_process.append(doc)
            
        # 4. Run Batch (Async)
        results_list = await executor.process_batch_async(
            documents=docs_to_process,
            schema=ExtractionModel,
            theme=self.state["review_question"],
            resume=True
        )
        
        # 5. Extract just the successful data items
        extraction_results = [r["final_data"] if "final_data" in r else r for r in results_list if "error" not in r]
        
        self.state["extraction_results"] = extraction_results
        self.phase = WorkflowPhase.SYNTHESIS

    def _run_synthesis_phase(self):
        """Execute Synthesizer agent."""
        self._log("=== PHASE: SYNTHESIS ===")
        
        results = self.state.get("extraction_results", [])
        if not results:
            self._log("No extraction results available.", "error")
            self.phase = WorkflowPhase.COMPLETE
            return
            
        report = self.synthesizer.synthesize(results, theme=self.state["review_question"])
        
        # Log synthesis success
        self._log(f"Synthesis complete: {report.title}")
        self.audit.log_event("synthesis_complete", {"title": report.title})
        
        self.state["synthesis_report"] = report.model_dump()
        self.state["is_complete"] = True
        self.phase = WorkflowPhase.COMPLETE


if __name__ == "__main__":
    import asyncio
    
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
    
    # Initialize with default agents (or inject custom ones)
    pi = OrchestratorPI()
    
    pi.initialize_review(
        title="Bowel Protocols in ICU",
        question="Does prophylactic bowel management reduce constipation?",
        pico=pico,
    )
    
    print(f"\nPhase: {pi.phase}")
    asyncio.run(pi.run_pipeline())
