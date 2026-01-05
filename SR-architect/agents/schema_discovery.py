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


class SchemaDiscoveryAgent:
    """
    Analyzes sample papers to discover potential extraction variables.
    
    Workflow:
    1. Parse first N papers
    2. For each paper, ask LLM what data points could be extracted
    3. Aggregate suggestions across papers
    4. Rank by frequency and present to user
    5. User approves/modifies → final schema
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

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None):
        """Initialize the discovery agent."""
        self.provider = provider
        self.model = model
        self.parser = DocumentParser()
        self._extractor = None
    
    def _get_extractor(self):
        """Lazy-load extractor."""
        if self._extractor is None:
            from core.extractor import StructuredExtractor
            self._extractor = StructuredExtractor(
                provider=self.provider,
                model=self.model
            )
        return self._extractor
    
    def analyze_paper(self, paper_path: str) -> DiscoveryResult:
        """
        Analyze a single paper to discover possible fields.
        
        Args:
            paper_path: Path to PDF file
            
        Returns:
            DiscoveryResult with suggested fields
        """
        # Parse PDF
        doc = self.parser.parse_pdf(paper_path)
        
        # Get extraction context (Abstract + Methods + Results)
        content = doc.get_extraction_context(max_chars=20000)
        
        # Prepare prompt
        prompt = self.DISCOVERY_PROMPT.format(content=content)
        
        # Extract suggestions via LLM
        extractor = self._get_extractor()
        
        # Use instructor to get structured output
        import instructor
        from openai import OpenAI
        
        client = instructor.from_openai(OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        ))
        
        result = client.chat.completions.create(
            model=self.model or "anthropic/claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": prompt}],
            response_model=DiscoveryResult,
        )
        
        result.filename = Path(paper_path).name
        return result
    
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
            min_frequency: Minimum papers a field must appear in
            
        Returns:
            List of suggested FieldDefinition objects
        """
        papers = list(Path(papers_dir).glob("*.pdf"))[:sample_size]
        
        all_suggestions = []
        paper_types = []
        
        for paper in papers:
            try:
                result = self.analyze_paper(str(paper))
                all_suggestions.extend(result.suggested_fields)
                paper_types.append(result.paper_type)
                print(f"✓ Analyzed: {paper.name} ({len(result.suggested_fields)} fields)")
            except Exception as e:
                print(f"✗ Failed: {paper.name}: {e}")
        
        # Aggregate and rank by frequency
        field_counts = Counter()
        field_examples = {}
        field_descriptions = {}
        field_types = {}
        
        for suggestion in all_suggestions:
            name = suggestion.field_name.lower().replace(" ", "_")
            field_counts[name] += 1
            
            if name not in field_examples:
                field_examples[name] = suggestion.example_value
                field_descriptions[name] = suggestion.description
                field_types[name] = suggestion.data_type
        
        # Build FieldDefinition list
        definitions = []
        for name, count in field_counts.most_common():
            if count >= min_frequency:
                # Map string type to FieldType enum
                type_map = {
                    "text": FieldType.TEXT,
                    "integer": FieldType.INTEGER,
                    "float": FieldType.FLOAT,
                    "boolean": FieldType.BOOLEAN,
                    "list_text": FieldType.LIST_TEXT,
                }
                field_type = type_map.get(field_types.get(name, "text"), FieldType.TEXT)
                
                definitions.append(FieldDefinition(
                    name=name,
                    description=field_descriptions.get(name, ""),
                    field_type=field_type,
                    required=count >= sample_size,  # Required if in all papers
                    include_quote=True,
                ))
        
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
