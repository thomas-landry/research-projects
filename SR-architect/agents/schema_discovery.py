#!/usr/bin/env python3
"""
Schema Discovery Agent - Analyzes sample papers to suggest extraction variables.

This implements the adaptive schema discovery pattern where the first N papers
are analyzed to discover what data points are available, then the user approves
a final schema before full extraction.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field
from collections import Counter

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import BaseModel, Field
from core.parser import DocumentParser, ParsedDocument
from core.schema_builder import FieldDefinition, FieldType


class SuggestedField(BaseModel):
    """A field suggested by the discovery agent."""
    field_name: str = Field(description="Snake_case identifier for this field")
    description: str = Field(description="What this field captures")
    data_type: str = Field(description="text, integer, float, boolean, or list_text")
    example_value: str = Field(description="Example value from this paper")
    extraction_difficulty: str = Field(description="easy, medium, or hard")
    section_found: str = Field(description="Which section contained this data")


class DiscoveryResult(BaseModel):
    """Result from analyzing a single paper."""
    filename: str
    suggested_fields: List[SuggestedField]
    paper_type: str = Field(description="case_report, rct, cohort, review, etc.")
    quality_notes: Optional[str] = None


class UnifiedField(BaseModel):
    """A canonical field resulting from merging synonymous suggestions."""
    canonical_name: str = Field(description="Standardized snake_case name")
    description: str = Field(description="Comprehensive description")
    field_type: str = Field(description="text, integer, float, boolean, or list_text")
    synonyms_merged: List[str] = Field(description="List of original field names merged into this one")
    frequency: int = Field(description="How many papers mentioned this concept")

class UnificationResult(BaseModel):
    """Result of the semantic unification process."""
    fields: List[UnifiedField]

class SchemaDiscoveryAgent:
    """
    Analyzes sample papers to discover potential extraction variables.
    
    Workflow:
    1. Parse first N papers
    2. For each paper, ask LLM what data points could be extracted
    3. SEMANTIC UNIFICATION: Aggregate and merge synonyms via LLM
    4. Return refined schema
    """
    
    DISCOVERY_PROMPT = """You are an expert systematic reviewer analyzing a paper to identify extractable data points.

Read the following academic paper content and identify ALL data points that could be systematically extracted and compared across multiple papers in a systematic review.

For each data point, provide:
- field_name: snake_case identifier (e.g., patient_age, sample_size)
- description: clear description of what this captures
- data_type: text, integer, float, boolean, or list_text
- example_value: the actual value from THIS paper
- extraction_difficulty: easy (clearly stated), medium (requires interpretation), hard (implicit or scattered)
- section_found: which section contains this information

Focus on extracting:
1. PATIENT DEMOGRAPHICS: age, sex, ethnicity, comorbidities
2. CLINICAL PRESENTATION: symptoms, duration, severity
3. DIAGNOSTIC INFORMATION: methods, imaging, pathology, lab values
4. TREATMENT: interventions, medications, procedures
5. OUTCOMES: response, survival, complications, follow-up
6. STUDY CHARACTERISTICS: design, setting, sample size, timeframe

Be thorough - it's better to suggest too many fields than to miss important ones.
The user will filter later.

PAPER CONTENT:
{content}
"""

    UNIFICATION_PROMPT = """You are a schema architect.
Your task is to consolidate a list of raw field suggestions extracted from multiple papers into a clean, canonical schema.

INPUT:
A list of suggested fields (name, description, type) found in various papers. Many will be duplicates or synonyms (e.g., "age", "patient_age", "years").

OUTPUT:
A list of UNIQUE, CANONICAL fields.
- Merge synonyms into a single best field name (e.g. merge "sex", "gender", "male_female" -> "sex").
- Use snake_case for names.
- Provide a clear, merged description.
- count how many times this concept appeared (frequency).
- Select the most appropriate data type.

Input Fields:
{fields_json}
"""

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize the discovery agent."""
        self.provider = provider
        self.model = model or "gpt-4o"
        self.api_key = api_key
        self.parser = DocumentParser()
        self._extractor = None
        self._client = None
        
        from core.utils import get_logger
        self.logger = get_logger("SchemaDiscoveryAgent")
    
    @property
    def client(self):
        """Initialize instructor client."""
        if self._client is not None:
            return self._client
        
        from core.utils import get_llm_client
        self.logger.debug(f"Initializing LLM client for {self.provider}")
        self._client = get_llm_client(
            provider=self.provider,
            api_key=self.api_key
        )
        return self._client
    
    def analyze_paper(self, paper_path: str) -> DiscoveryResult:
        """
        Analyze a single paper to discover possible fields.
        
        Args:
            paper_path: Path to PDF file
            
        Returns:
            DiscoveryResult with suggested fields
        """
        self.logger.info(f"Analyzing paper: {Path(paper_path).name}")
        
        # Parse PDF
        doc = self.parser.parse_pdf(paper_path)
        
        # Get extraction context (Abstract + Methods + Results)
        content = doc.get_extraction_context(max_chars=20000)
        
        # Prepare prompt
        prompt = self.DISCOVERY_PROMPT.format(content=content)
        
        result = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_model=DiscoveryResult,
        )
        
        result.filename = Path(paper_path).name
        return result
    
    def unify_fields(self, suggestions: List[SuggestedField]) -> List[UnifiedField]:
        """Merge synonymous fields using LLM."""
        if not suggestions:
            return []
            
        self.logger.info(f"Unifying {len(suggestions)} raw field suggestions...")
        
        # Convert to compact dicts for prompt to save tokens
        simple_suggestions = [
            {
                "name": s.field_name,
                "desc": s.description,
                "type": s.data_type
            }
            for s in suggestions
        ]
        
        import json
        fields_json = json.dumps(simple_suggestions, indent=2)
        
        prompt = self.UNIFICATION_PROMPT.format(fields_json=fields_json)
        
        try:
            result = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_model=UnificationResult,
            )
            return result.fields
        except Exception as e:
            self.logger.error(f"Unification failed: {e}")
            # Fallback: return raw as if unified (simplified)
            return [
                UnifiedField(
                    canonical_name=s.field_name,
                    description=s.description,
                    field_type=s.data_type,
                    synonyms_merged=[s.field_name],
                    frequency=1
                )
                for s in suggestions
            ]

    def discover_schema(
        self,
        papers_dir: str,
        sample_size: int = 3,
        min_frequency: int = 1,
    ) -> List[FieldDefinition]:
        """
        Analyze sample papers and aggregate field suggestions.
        
        Args:
            papers_dir: Directory containing PDFs
            sample_size: Number of papers to analyze
            min_frequency: Minimum papers a concept must appear in
            
        Returns:
            List of suggested FieldDefinition objects
        """
        papers = list(Path(papers_dir).glob("*.pdf"))[:sample_size]
        
        all_suggestions = []
        
        for paper in papers:
            try:
                result = self.analyze_paper(str(paper))
                all_suggestions.extend(result.suggested_fields)
            except Exception as e:
                self.logger.error(f"Failed to analyze {paper.name}: {e}")
        
        # Semantic Unification
        unified_fields = self.unify_fields(all_suggestions)
        
        # Build FieldDefinition list
        definitions = []
        for uf in unified_fields:
            if uf.frequency >= min_frequency:
                # Map string type to FieldType enum
                type_map = {
                    "text": FieldType.TEXT,
                    "integer": FieldType.INTEGER,
                    "float": FieldType.FLOAT,
                    "boolean": FieldType.BOOLEAN,
                    "list_text": FieldType.LIST_TEXT,
                }
                field_type = type_map.get(uf.field_type, FieldType.TEXT)
                
                definitions.append(FieldDefinition(
                    name=uf.canonical_name,
                    description=f"{uf.description} (Merged: {', '.join(uf.synonyms_merged)})",
                    field_type=field_type,
                    required=uf.frequency >= sample_size,
                    include_quote=True,
                ))
        
        # Sort by frequency (implied by order of processing often, but stability is good)
        # Here we just return them as the LLM ordered them (usually relevance or frequency)
        return definitions


def interactive_discovery(papers_dir: str, sample_size: int = 3):
    """
    Run interactive schema discovery with user approval.
    """
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Confirm, Prompt
    
    console = Console()
    
    console.print("\n[bold cyan]🔍 Adaptive Schema Discovery[/bold cyan]")
    console.print(f"Analyzing {sample_size} sample papers to discover extraction variables...\n")
    
    # Run discovery
    agent = SchemaDiscoveryAgent()
    suggested_fields = agent.discover_schema(papers_dir, sample_size)
    
    # Display suggestions
    table = Table(title=f"Discovered Fields ({len(suggested_fields)} total)")
    table.add_column("#", style="dim")
    table.add_column("Field Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Required", style="yellow")
    table.add_column("Description")
    
    for i, f in enumerate(suggested_fields, 1):
        table.add_row(
            str(i),
            f.name,
            f.field_type.value,
            "Yes" if f.required else "No",
            f.description[:50] + "..." if len(f.description) > 50 else f.description
        )
    
    console.print(table)
    
    # User approval
    console.print("\n[bold]Review the discovered fields:[/bold]")
    
    approved_fields = []
    for f in suggested_fields:
        if Confirm.ask(f"Include '{f.name}'?", default=True):
            approved_fields.append(f)
    
    # Allow adding custom fields
    if Confirm.ask("\nAdd custom fields?", default=False):
        while True:
            name = Prompt.ask("Field name (empty to finish)", default="")
            if not name:
                break
            desc = Prompt.ask("Description")
            approved_fields.append(FieldDefinition(
                name=name.lower().replace(" ", "_"),
                description=desc,
                field_type=FieldType.TEXT,
                required=False,
                include_quote=True,
            ))
    
    console.print(f"\n[green]✓ Final schema: {len(approved_fields)} fields[/green]")
    
    return approved_fields


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Discover extraction schema from sample papers")
    parser.add_argument("papers_dir", help="Directory containing PDFs")
    parser.add_argument("--sample", type=int, default=3, help="Number of papers to analyze")
    parser.add_argument("--interactive", action="store_true", help="Interactive approval mode")
    
    args = parser.parse_args()
    
    if args.interactive:
        fields = interactive_discovery(args.papers_dir, args.sample)
    else:
        agent = SchemaDiscoveryAgent()
        fields = agent.discover_schema(args.papers_dir, args.sample)
        
        print(f"\nDiscovered {len(fields)} fields:")
        for f in fields:
            print(f"  - {f.name}: {f.description[:60]}")
