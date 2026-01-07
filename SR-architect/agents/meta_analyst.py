#!/usr/bin/env python3
"""
Meta Analyst Agent - Assesses feasibility for meta-analysis.

This agent runs AFTER extraction to determine if the extracted data is sufficient
to perform a statistical meta-analysis (e.g. are there means, SDs, sample sizes?).
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class MetaAnalysisFeasibility(BaseModel):
    """Assessment of whether a meta-analysis is possible."""
    feasible: bool = Field(description="Is meta-analysis possible?")
    reason: str = Field(description="Why or why not?")
    missing_critical_fields: List[str] = Field(description="Fields needed but missing (e.g., standard deviation)")
    recommended_method: str = Field(description="fixed_effects, random_effects, or qualitative_synthesis")
    heterogeneity_concern: str = Field(description="low, medium, high")

class MetaAnalystAgent:
    """
    Determines meta-analysis feasibility.
    """
    
    ANALYST_PROMPT = """You are a Meta-Analysis Statistician.
    
    Analyze the provided dataset summary to determine if a quantitative meta-analysis is feasible.
    
    DATA SUMMARY:
    {summary}
    
    CRITERIA:
    1. Are there measures of effect (mean differences, odds ratios)?
    2. Are there measures of variance (SD, SE, CI)?
    3. Is the sample size available?
    4. Are the interventions/outcomes sufficiently similar?
    
    Provide a feasibility assessment.
    """
    
    def __init__(self, provider: str = "openrouter", model: Optional[str] = None, token_tracker: Optional["TokenTracker"] = None):
        self.provider = provider
        self.model = model or "gpt-4o" 
        self.token_tracker = token_tracker
        self._client = None
        
        from core.utils import get_logger
        self.logger = get_logger("MetaAnalystAgent")
        
    @property
    def client(self):
        if self._client is not None:
            return self._client
        from core.utils import get_llm_client
        self._client = get_llm_client(self.provider)
        return self._client

    def assess_feasibility(self, data: List[Dict[str, Any]]) -> MetaAnalysisFeasibility:
        """
        Assess if the extracted data supports meta-analysis.
        """
        if not data:
            return MetaAnalysisFeasibility(
                feasible=False,
                reason="No data provided",
                missing_critical_fields=[],
                recommended_method="none",
                heterogeneity_concern="high"
            )
            
        df = pd.DataFrame(data)
        
        # logical check first (save LLM tokens)
        columns = df.columns.tolist()
        has_n = any("sample_size" in c.lower() or "n_total" in c.lower() for c in columns)
        has_outcome = any("outcome" in c.lower() or "result" in c.lower() for c in columns)
        
        # Prepare valid rows summary for LLM
        valid_rows = df.dropna(how='all').head(5).to_dict(orient='records')
        summary = f"Columns: {columns}\nRow Count: {len(df)}\nSample Data: {valid_rows}"
        
        prompt = self.ANALYST_PROMPT.format(summary=summary)
        
        try:
            response, completion = self.client.chat.completions.create_with_completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_model=MetaAnalysisFeasibility,
                extra_body={"usage": {"include": True}}
            )
            
            # Record usage
            if self.token_tracker and hasattr(completion, 'usage') and completion.usage:
                self.token_tracker.record_usage(
                    usage={
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens
                    },
                    model=self.model,
                    operation="meta_analysis_feasibility"
                )
            
            return response
        except Exception as e:
            self.logger.error(f"Meta-analysis assessment failed: {e}")
            return MetaAnalysisFeasibility(
                feasible=False,
                reason=f"Assessment failed: {e}",
                missing_critical_fields=[],
                recommended_method="qualitative_synthesis",
                heterogeneity_concern="unknown"
            )
