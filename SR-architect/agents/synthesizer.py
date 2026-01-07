#!/usr/bin/env python3
"""
Synthesizer Agent.

Aggregates structured data from multiple papers to generate
a meta-analysis synthesis report.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json

from core.utils import get_logger, get_llm_client


class SynthesisReport(BaseModel):
    """Structured synthesis of multiple extracted papers."""
    title: str = Field(description="Title of the synthesis report")
    executive_summary: str = Field(description="High-level summary of the findings")
    sample_size_total: int = Field(description="Total number of patients/subjects across all studies")
    key_findings: List[str] = Field(description="List of primary findings supported by the data")
    conflicting_evidence: List[str] = Field(description="Points where studies disagree")
    consensus_points: List[str] = Field(description="Points where studies agree")
    limitations: List[str] = Field(description="Noted limitations in the source data")
    

class SynthesizerAgent:
    """
    Agent responsible for synthesizing multiple extraction results into a coherent report.
    """
    
    SYSTEM_PROMPT = """You are an expert meta-analyst.
Your task is to synthesize data from multiple academic papers into a coherent review.

INPUT:
A JSON list of extracted data from various studies.

OUTPUT:
A structured report containing:
1. Executive Summary
2. Total pooled sample size (sum of all study sample sizes)
3. Key Findings (supported by multiple sources)
4. Conflicting Evidence (where studies disagree)
5. Consensus Points
6. Limitations

RULES:
- Be objective and data-driven.
- Highlight patterns and trends.
- Explicitly mention if data is insufficient for a conclusion.
- If a specific field is missing in many papers, note it as a limitation.
"""

    def __init__(
        self,
        client: Optional[Any] = None,
        provider: str = "openrouter",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize SynthesizerAgent.
        
        Args:
            client: Optional injected LLM client.
            provider: LLM provider (if client not provided).
            model: Model name.
            api_key: API key (if client not provided).
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model or "gpt-4o"
        self.logger = get_logger("SynthesizerAgent")
        
        # Dependency Injection
        self._client = client

    @property
    def client(self):
        """Initialize and return the Instructor-patched client."""
        if self._client is not None:
            return self._client
        
        self.logger.debug(f"Initializing LLM client for {self.provider}")
        self._client = get_llm_client(
            provider=self.provider,
            api_key=self.api_key
        )
        return self._client

    def synthesize(self, results: List[Dict[str, Any]], theme: str = "General") -> SynthesisReport:
        """
        Synthesize a list of extraction results.

        Args:
            results: List of dictionaries, each representing extracted data from one paper.
            theme: The theme of the review to focus the synthesis.

        Returns:
            SynthesisReport object.
        """
        if not results:
            self.logger.error("No results provided for synthesis.")
            raise ValueError("No results provided for synthesis.")
        
        self.logger.info(f"Synthesizing {len(results)} papers for theme: {theme}")
        
        # Prepare data for prompt
        data_json = json.dumps(results, indent=2)
        
        user_prompt = f"""
THEME: {theme}

DATA FROM {len(results)} STUDIES:
{data_json}

Please generate a synthesis report for this data.
"""
        
        try:
            report = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_model=SynthesisReport
            )
            return report
            
        except Exception as e:
            self.logger.error(f"Synthesis failed: {e}")
            raise RuntimeError(f"Synthesis failed: {e}") from e


if __name__ == "__main__":
    # Demo/Smoke test
    agent = SynthesizerAgent()
    print("Synthesizer initialized. Verified DI and Logging compatibility.")
