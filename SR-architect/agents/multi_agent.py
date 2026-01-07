"""
Multi-Agent Orchestration Module.

This module defines the graph nodes and state transitions for the multi-agent system.
It acts as a façade for the individual agent implementations.
"""

from enum import Enum
from typing import Dict, Any, TypedDict, List, Optional

from core.prisma_state import (
    ReviewState,
    Paper,
    PaperStatus,
    ExclusionReason,
    PICOCriteria
)

# Re-export types expected by __init__.py
PaperState = Paper

class AgentType(str, Enum):
    """Types of agents in the system."""
    SCREENER = "screener"
    EXTRACTOR = "extractor"
    AUDITOR = "auditor"
    SYNTHESIZER = "synthesizer"
    LIBRARIAN = "librarian"
    ORCHESTRATOR = "orchestrator"

# ----------------------------------------------------------------------
# Agent Node Functions (LangGraph-style)
# ----------------------------------------------------------------------

def screener_agent(state: ReviewState) -> ReviewState:
    """
    Screener agent node function.
    
    Responsible for screening papers in the 'pending' state.
    """
    # Logic to instantiate ScreenerAgent and process papers
    # This is a stub to satisfy imports for now
    return state

def extractor_agent(state: ReviewState) -> ReviewState:
    """
    Extractor agent node function.
    
    Responsible for extracting data from included papers.
    """
    # Stub
    return state

def auditor_agent(state: ReviewState) -> ReviewState:
    """
    Auditor agent node function.
    
    Responsible for validating extractions.
    """
    # Stub
    return state

def synthesizer_agent(state: ReviewState) -> ReviewState:
    """
    Synthesizer agent node function.
    
    Responsible for aggregating results into a report.
    """
    # Stub
    return state
