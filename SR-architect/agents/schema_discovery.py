import os
import sys
import random
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import BaseModel, Field
from core.parser import DocumentParser, ParsedDocument
from core.schema_builder import FieldDefinition, FieldType

# Constants for schema discovery
MIN_PDF_SIZE_BYTES = 10 * 1024  # 10KB minimum for valid PDFs
MIN_TXT_SIZE_BYTES = 100  # 100 bytes minimum for valid text files
MAX_CONTEXT_CHARS = 20_000  # Maximum characters for LLM context
DEFAULT_RANDOM_SEED = 42  # Stable seed for reproducible sampling

# Field type mapping for schema discovery
FIELD_TYPE_MAPPING = {
    "text": FieldType.TEXT,
    "integer": FieldType.INTEGER,
    "float": FieldType.FLOAT,
    "boolean": FieldType.BOOLEAN,
    "list_text": FieldType.LIST_TEXT,
}


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

{existing_fields_context}

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

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None, api_key: Optional[str] = None, token_tracker: Optional["TokenTracker"] = None):
        """Initialize the discovery agent."""
        self.provider = provider
        self.model = model or "gpt-4o"
        self.api_key = api_key
        self.token_tracker = token_tracker
        self.parser = DocumentParser()
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
    
    def get_sample_papers(self, papers_dir: str, sample_size: int = 3, seed: Optional[int] = None) -> List[str]:
        """
        Robustly select N papers for schema discovery.
        
        - Filters for .pdf and .txt extensions
        - Filters out files < 100 bytes (for txt) or < 10KB (for pdf)
        - Shuffles for representative sampling
        """
        papers_path = Path(papers_dir)
        all_files = list(papers_path.glob("*.pdf")) + list(papers_path.glob("*.txt"))
        
        # Filter by size
        valid_files = []
        for p in all_files:
            size = p.stat().st_size
            if p.suffix == ".pdf" and size > MIN_PDF_SIZE_BYTES:
                valid_files.append(p)
            elif p.suffix == ".txt" and size > MIN_TXT_SIZE_BYTES:
                valid_files.append(p)
        
        if not valid_files:
            # Fallback to all found files if filtering is too strict
            self.logger.warning(f"No files passing size filter found in {papers_dir}. Using all available files.")
            valid_files = all_files
            
        if not valid_files:
            return []
            
        # Shuffle
        if seed is not None:
            random.seed(seed)
        else:
            random.seed(DEFAULT_RANDOM_SEED)  # Stable default shuffle
            
        random.shuffle(valid_files)
        
        selected = valid_files[:sample_size]
        return [str(p) for p in selected]

    def analyze_paper(self, paper_path: str, existing_fields: Optional[List[str]] = None) -> DiscoveryResult:
        """
        Analyze a single paper to discover possible fields.
        
        Args:
            paper_path: Path to file (PDF or TXT)
            existing_fields: Optional list of fields already in the schema
            
        Returns:
            DiscoveryResult with suggested fields
        """
        self.logger.info(f"Analyzing paper: {Path(paper_path).name}")
        
        # Parse file (supports PDF and TXT)
        doc = self.parser.parse_file(paper_path)
        
        # Get extraction context (Abstract + Methods + Results)
        content = doc.get_extraction_context(max_chars=MAX_CONTEXT_CHARS)
        
        # Prepare existing fields context
        if existing_fields:
            existing_fields_context = (
                "The following fields are ALREADY defined in our schema. "
                "While you can suggest improvements to them, focus primarily on finding "
                "NOVEL variables that are not on this list but are important for this paper:\n"
                f"- {', '.join(existing_fields)}"
            )
        else:
            existing_fields_context = "This is a fresh discovery session. Suggest any relevant data points."

        # Prepare prompt
        prompt = self.DISCOVERY_PROMPT.format(
            content=content,
            existing_fields_context=existing_fields_context
        )
        
        response, completion = self.client.chat.completions.create_with_completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_model=DiscoveryResult,
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
                operation="schema_discovery",
                filename=Path(paper_path).name
            )
        
        response.filename = Path(paper_path).name
        return response
    
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
            response, completion = self.client.chat.completions.create_with_completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_model=UnificationResult,
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
                    operation="schema_unification",
                    filename="unification_process" # No specific paper filename for unification
                )
            return response.fields
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
        existing_schema: Optional[List[FieldDefinition]] = None,
    ) -> List[FieldDefinition]:
        """
        Analyze sample papers and aggregate field suggestions.
        
        Args:
            papers_dir: Directory containing PDFs
            sample_size: Number of papers to analyze
            min_frequency: Minimum papers a concept must appear in
            existing_schema: Optional current schema to augment
            
        Returns:
            List of suggested FieldDefinition objects
        """
        # USE ROBUST SAMPLING
        papers = self.get_sample_papers(papers_dir, sample_size)
        
        field_suggestions_from_all_papers = []
        # Track known fields to enable iterative discovery of NOVEL items
        existing_field_names = [f.name for f in existing_schema] if existing_schema else []
        current_known_fields = set(existing_field_names)
        
        for paper_path in papers:
            try:
                # Pass currently known fields to prompt
                result = self.analyze_paper(paper_path, existing_fields=list(current_known_fields))
                
                # Add new suggestions
                field_suggestions_from_all_papers.extend(result.suggested_fields)
                
                # Update known fields for next iteration (to avoid redundant suggestions)
                for field in result.suggested_fields:
                    current_known_fields.add(field.field_name)
                    
            except Exception as e:
                self.logger.error(f"Failed to analyze {paper_path}: {e}")
                continue
        
        if not field_suggestions_from_all_papers:
            self.logger.warning("No fields discovered from sample papers.")
            return []
        
        # Unify synonymous fields
        unified = self.unify_fields(field_suggestions_from_all_papers)
        
        # Build FieldDefinition list
        definitions = []
        for uf in unified:
            # Skip if already in existing_schema (original set)
            if uf.canonical_name in existing_field_names:
                continue
                
            if uf.frequency >= min_frequency:
                field_type = FIELD_TYPE_MAPPING.get(uf.field_type, FieldType.TEXT)
                
                definitions.append(FieldDefinition(
                    name=uf.canonical_name,
                    description=f"{uf.description} (Merged: {', '.join(uf.synonyms_merged)})",
                    field_type=field_type,
                    required=uf.frequency >= len(papers), # Required if in all samples
                    include_quote=True,
                ))
        
        return definitions


def interactive_discovery(
    papers_dir: str, 
    sample_size: int = 3, 
    existing_schema: Optional[List[FieldDefinition]] = None,
    provider: str = "openrouter",
    model: Optional[str] = None
):
    """
    Run interactive schema discovery with user approval.
    """
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Confirm, Prompt
    
    console = Console()
    
    console.print("\n[bold cyan]🔍 Adaptive Schema Discovery[/bold cyan]")
    
    if existing_schema:
        console.print(f"Analyzing {sample_size} sample papers to find variables MISSING from your current schema...\n")
    else:
        console.print(f"Analyzing {sample_size} sample papers to discover extraction variables...\n")
    
    # Run discovery
    agent = SchemaDiscoveryAgent(provider=provider, model=model)
    suggested_fields = agent.discover_schema(papers_dir, sample_size, existing_schema=existing_schema)
    
    if not suggested_fields:
        console.print("[yellow]No new fields discovered.[/yellow]")
        return existing_schema or []

    # Display suggestions
    table = Table(title=f"Discovered Fields ({len(suggested_fields)} new suggestions)")
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
    
    new_fields = []
    for f in suggested_fields:
        if Confirm.ask(f"Add '{f.name}' to schema?", default=True):
            new_fields.append(f)
    
    final_schema = (existing_schema or []) + new_fields
    
    # Allow adding custom fields manually
    if Confirm.ask("\nAdd more custom fields manually?", default=False):
        console.print("[dim]Commands: 'undo' to remove last manual field[/dim]")
        while True:
            name = Prompt.ask("Field name (empty to finish)", default="")
            if not name:
                break
            
            # Handle Undo
            if name.lower().strip() == "undo":
                # Only allow undoing fields added in THIS loop
                if len(final_schema) > (len(existing_schema or []) + len(new_fields)):
                    removed = final_schema.pop()
                    console.print(f"[yellow]↩ Undid last manual field: {removed.name}[/yellow]\n")
                else:
                    console.print("[dim]Nothing to undo.[/dim]\n")
                continue

            desc = Prompt.ask("Description")
            final_schema.append(FieldDefinition(
                name=name.lower().replace(" ", "_"),
                description=desc,
                field_type=FieldType.TEXT,
                required=False,
                include_quote=True,
            ))
    
    console.print(f"\n[green]✓ Final schema: {len(final_schema)} fields[/green]")
    
    return final_schema


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
