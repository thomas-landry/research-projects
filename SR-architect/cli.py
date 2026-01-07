#!/usr/bin/env python3
"""
SR-Architect CLI - Systematic Review Data Extraction Pipeline

Command-line interface for extracting structured data from PDFs.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from core.config import settings
from core import (
    DocumentParser, 
    HierarchicalExtractionPipeline, 
    BatchExecutor, 
    StateManager
)
from core.schema_builder import (
    build_extraction_model,
    get_case_report_schema,
    get_rct_schema,
    get_observational_schema,
    interactive_schema_builder,
    FieldDefinition,
    PREDEFINED_SCHEMAS,
)
from agents.schema_discovery import interactive_discovery
from core.extractor import StructuredExtractor
from core.vectorizer import ChromaVectorStore
from core.audit_logger import AuditLogger
from core.token_tracker import TokenTracker
from core.utils import setup_logging

app = typer.Typer(
    name="sr-architect",
    help="Systematic Review Data Extraction Pipeline",
    add_completion=False,
)
console = Console()
MIN_CONTEXT_CHARS = 100  # Minimum chars required for extraction


def load_env():
    """Load environment variables."""
    env_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent / ".env",
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


@app.command()
def extract(
    papers_dir: str = typer.Argument(..., help="Directory containing PDFs to process"),
    output: str = typer.Option("./output/extraction_results.csv", "-o", "--output", help="Output CSV path"),
    schema: str = typer.Option("case_report", "-s", "--schema", help="Schema: case_report, rct, observational, or 'interactive'"),
    interactive: bool = typer.Option(False, "-i", "--interactive", help="Interactive schema builder"),
    limit: Optional[int] = typer.Option(None, "-l", "--limit", help="Limit number of papers to process"),
    provider: str = typer.Option(settings.LLM_PROVIDER, "-p", "--provider", help="LLM provider: openrouter or ollama"),
    model: Optional[str] = typer.Option(settings.LLM_MODEL, "-m", "--model", help="Override LLM model"),
    vectorize: bool = typer.Option(True, "--vectorize/--no-vectorize", help="Store vectors in ChromaDB"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    resume: bool = typer.Option(False, "--resume", help="Resume from checkpoint if available"),
    # Hierarchical extraction options
    hierarchical: bool = typer.Option(False, "-H", "--hierarchical", help="Use hierarchical extraction with validation"),
    theme: Optional[str] = typer.Option(None, "-t", "--theme", help="Meta-analysis theme for relevance filtering (required with --hierarchical)"),
    threshold: float = typer.Option(settings.SCORE_THRESHOLD, "--threshold", help="Minimum accuracy+consistency score for validation"),
    max_iter: int = typer.Option(settings.MAX_ITERATIONS, "--max-iter", help="Maximum checker feedback iterations"),
    # Optimization & Generalization
    workers: int = typer.Option(settings.WORKERS, "--workers", "-w", help="Number of parallel workers (default: 1)"),
    examples: Optional[str] = typer.Option(None, "--examples", "-e", help="Path to few-shot examples text file"),
    adaptive: bool = typer.Option(False, "--adaptive", help="Automatically discover schema from sample papers"),
):
    """
    Extract structured data from PDFs for systematic review.
    
    Example:
        python cli.py extract ../DPM-systematic-review/papers -o results.csv
    """
    load_env()

    # Initialize logging
    log_file = Path(output).parent / "sr_architect.log"
    setup_logging(level="DEBUG" if verbose else None, log_file=log_file)
    
    papers_path = Path(papers_dir)
    if not papers_path.exists():
        console.print(f"[red]Error: Directory not found: {papers_dir}[/red]")
        raise typer.Exit(1)
    
    # Get PDF files
    pdf_files = list(papers_path.glob("*.pdf"))
    if not pdf_files:
        console.print(f"[red]Error: No PDF files found in {papers_dir}[/red]")
        raise typer.Exit(1)
    
    if limit:
        pdf_files = pdf_files[:limit]
    
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize tracker
    tracker = TokenTracker(log_file=output_path.parent / "token_usage.jsonl")
    
    console.print(Panel.fit(
        f"[bold cyan]SR-Architect Extraction Pipeline[/bold cyan]\n\n"
        f"Papers: {len(pdf_files)} PDFs\n"
        f"Schema: {schema}\n"
        f"Provider: {provider}\n"
        f"Output: {output}",
        title="Configuration"
    ))
    
    # === Schema Selection Phase ===
    fields: List[FieldDefinition] = []
    
    # 1. Base Schema selection
    if interactive or schema == "interactive":
        fields = interactive_schema_builder()
    elif schema in PREDEFINED_SCHEMAS:
        fields = PREDEFINED_SCHEMAS[schema]()
        console.print(f"[green]Using predefined schema: {schema}[/green]")
    elif adaptive:
        # If ONLY adaptive is set, start with empty and discover
        fields = []
    else:
        # Default case (predefined or arg)
        fields = PREDEFINED_SCHEMAS.get(schema, get_case_report_schema)()
        if schema not in PREDEFINED_SCHEMAS and schema != "case_report":
             console.print(f"[yellow]Note: Using fallback case_report schema.[/yellow]")

    # 2. Adaptive Discovery (optional or forced by flag)
    if adaptive:
        fields = interactive_discovery(papers_dir, sample_size=3, existing_schema=fields)
    elif not resume and typer.confirm("\nWould you like to run adaptive discovery to find additional fields?", default=False):
        fields = interactive_discovery(papers_dir, sample_size=3, existing_schema=fields)
    
    if not fields:
        console.print("[red]Error: No extraction fields defined. Aborting.[/red]")
        raise typer.Exit(1)
    
    # Show schema fields
    if verbose or adaptive or interactive:
        table = Table(title="Final Extraction Schema")
        table.add_column("Field", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Description")
        for f in fields:
            table.add_row(f.name, f.field_type.value, f.description[:50])
        console.print(table)
    
    # Confirmation for large batches
    if len(pdf_files) > 25 and not resume:
        console.print(f"\n[bold yellow]⚠ WARNING: Large Batch Detected ({len(pdf_files)} papers)[/bold yellow]")
        console.print("Processing many papers can take significant time and API tokens.")
        if not typer.confirm("Do you want to proceed with the full batch?"):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit()

    # Build dynamic model
    ExtractionModel = build_extraction_model(fields, "SRExtractionModel")
    
    # Pre-flight cost estimate
    if not resume:
        # Hierarchical runs are more expensive (discovery + filter + extract + audit)
        passes = 4 if hierarchical else 1
        estimate = tracker.estimate_extraction_cost(
            num_documents=len(pdf_files),
            model=model or settings.LLM_MODEL or "anthropic/claude-3.5-sonnet",
            num_passes=passes
        )
        console.print(tracker.display_cost_report(estimate))
        if not typer.confirm("Continue with extraction?"):
            raise typer.Exit()
    
    # Validate hierarchical mode requirements
    if hierarchical and not theme:
        console.print("[red]Error: --theme is required when using --hierarchical mode[/red]")
        console.print("[dim]Example: --hierarchical --theme 'patient outcomes in treatment X'[/dim]")
        raise typer.Exit(1)
    
    # Initialize components
    parser = DocumentParser()
    
    # Load examples if provided
    examples_content = None
    if examples:
        try:
            examples_content = Path(examples).read_text()
            console.print(f"[green]Loaded few-shot examples from {examples}[/green]")
        except Exception as e:
            console.print(f"[yellow]Could not load examples from {examples}: {e}[/yellow]")

    # Initialize appropriate extractor based on mode
    if hierarchical:
        console.print(f"\n[bold magenta]🔬 Hierarchical Extraction Mode[/bold magenta]")
        console.print(f"  Theme: {theme}")
        console.print(f"  Threshold: {threshold}")
        console.print(f"  Max iterations: {max_iter}\n")
        
        pipeline = HierarchicalExtractionPipeline(
            provider=provider,
            model=model,
            score_threshold=threshold,
            max_iterations=max_iter,
            verbose=verbose,
            examples=examples_content,
            token_tracker=tracker
        )
        extractor = None  # Not used in hierarchical mode
    else:
        pipeline = None
        extractor = StructuredExtractor(
            provider=provider, 
            model=model, 
            examples=examples_content,
            token_tracker=tracker
        )
    
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    vector_store = None
    if vectorize:
        vector_dir = output_path.parent / "vector_store"
        vector_store = ChromaVectorStore(
            collection_name="sr_extraction",
            persist_directory=str(vector_dir),
        )
    
    logger = AuditLogger(log_dir=str(output_path.parent / "logs"))
    
    # Initialize checkpointing
    checkpoint_path = output_path.parent / "extraction_checkpoint.json"
    state_manager = StateManager(checkpoint_path)
    
    # Initialize Batch Executor
    batch_executor = BatchExecutor(
        pipeline=pipeline if hierarchical else extractor,
        state_manager=state_manager,
        max_workers=workers
    )
    
    # Process batch
    console.print(f"\n[bold yellow]STARTING EXTRACTION...[/bold yellow]")
    
    # We need to adapt the papers to ParsedDocument objects first
    # Or let BatchExecutor handle paths? Current BatchExecutor takes ParsedDocument.
    # Let's parse them first (or update BatchExecutor to take paths).
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        parsing_task = progress.add_task("Parsing PDFs...", total=len(pdf_files))
        parsed_docs = []
        for pdf_path in pdf_files:
            try:
                doc = parser.parse_pdf(str(pdf_path))
                parsed_docs.append(doc)
            except Exception as e:
                console.print(f"[red]Error parsing {pdf_path.name}: {e}[/red]")
            progress.advance(parsing_task)
            
        extraction_task = progress.add_task("Extracting data...", total=len(parsed_docs))
        # Note: BatchExecutor doesn't support rich progress yet, we'll see logs.
        # Future improvement: Add callback to BatchExecutor for UI updates.
        
    import csv
    with open(output_path, "w", newline="") as f:
        # Get field names from model
        fieldnames = list(ExtractionModel.model_fields.keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        def streaming_callback(filename, data, status):
            if status == "success":
                # Handle both Hierarchical (PipelineResult) and Standard extraction results
                extracted_data = data
                if "final_data" in data and isinstance(data["final_data"], dict):
                    # It's a PipelineResult dict
                    extracted_data = data["final_data"]
                
                # Filter data to only include schema fields
                row = {k: v for k, v in extracted_data.items() if k in fieldnames}
                writer.writerow(row)
                f.flush()

        if hierarchical:
            # Use asyncio for hierarchical mode
            import asyncio
            results = asyncio.run(batch_executor.process_batch_async(
                documents=parsed_docs,
                schema=ExtractionModel,
                theme=theme or "General extraction",
                resume=resume,
                callback=streaming_callback,
                concurrency_limit=workers
            ))
        else:
            # Use sync batch for standard mode
            results = batch_executor.process_batch(
                documents=parsed_docs,
                schema=ExtractionModel,
                theme=theme or "General extraction",
                resume=resume,
                callback=streaming_callback
            )
    
    # Final summary with cost
    console.print(f"\n[bold green]✓ Extraction complete. Results saved to {output}[/bold green]")
    
    summary = tracker.get_session_summary()
    table = Table(title="Extraction Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Total handled", str(len(parsed_docs)))
    table.add_row("Total tokens", f"{summary['total_tokens']:,}")
    table.add_row("Total cost (USD)", f"${summary['total_cost_usd']:.4f}")
    console.print(table)
    
    console.print(tracker.display_session_summary())
    
    if vector_store:
        # Note: Vectorization currently happens inside the old process_pdf.
        # BatchExecutor doesn't handle vectorization yet.
        # We should either add vectorization to BatchExecutor or handle it here.
        # For now, let's warn that vectorization is pending update.
        console.print(f"\n[yellow]Note: Vectorization is currently disabled in batch mode.[/yellow]")
    
    console.print(f"\n[dim]Audit log: {logger.log_file}[/dim]")


@app.command()
def query(
    query_text: str = typer.Argument(..., help="Search query"),
    vector_dir: str = typer.Option("./output/vector_store", "-d", "--dir", help="Vector store directory"),
    limit: int = typer.Option(10, "-l", "--limit", help="Number of results"),
    filename: Optional[str] = typer.Option(None, "-f", "--filename", help="Filter by filename"),
):
    """
    Query the vector store for similar content.
    
    Example:
        python cli.py query "treatment outcomes" --limit 5
    """
    load_env()
    
    vector_store = ChromaVectorStore(
        collection_name="sr_extraction",
        persist_directory=vector_dir,
    )
    
    where = {"filename": filename} if filename else None
    results = vector_store.query(query_text, n_results=limit, where=where)
    
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return
    
    console.print(f"\n[bold]Found {len(results)} results for: '{query_text}'[/bold]\n")
    
    for i, r in enumerate(results, 1):
        console.print(Panel(
            f"{r['text'][:300]}{'...' if len(r['text']) > 300 else ''}",
            title=f"[cyan]{i}. {r['metadata'].get('filename', 'Unknown')}[/cyan] (distance: {r['distance']:.3f})",
            subtitle=f"Section: {r['metadata'].get('section', 'N/A')}",
        ))


@app.command()
def schemas():
    """List available predefined extraction schemas."""
    console.print("\n[bold cyan]Available Extraction Schemas[/bold cyan]\n")
    
    for name, schema_fn in PREDEFINED_SCHEMAS.items():
        fields = schema_fn()
        field_names = [f.name for f in fields]
        
        console.print(f"[green]{name}[/green]")
        console.print(f"  Fields: {', '.join(field_names[:5])}{'...' if len(field_names) > 5 else ''}")
        console.print()


@app.command()
def stats(
    vector_dir: str = typer.Option("./output/vector_store", "-d", "--dir", help="Vector store directory"),
):
    """Show statistics about the vector store."""
    load_env()
    
    try:
        vector_store = ChromaVectorStore(
            collection_name="sr_extraction",
            persist_directory=vector_dir,
        )
        stats = vector_store.get_stats()
        
        table = Table(title="Vector Store Statistics")
        table.add_column("Metric")
        table.add_column("Value")
        
        for key, value in stats.items():
            table.add_row(key, str(value))
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def methods(
    log_dir: str = typer.Option("./output/logs", "-d", "--dir", help="Log directory"),
):
    """Generate methods text from extraction logs."""
    log_path = Path(log_dir)
    
    # Find most recent summary
    summaries = list(log_path.glob("summary_*.json"))
    if not summaries:
        console.print("[yellow]No extraction summaries found[/yellow]")
        return
    
    latest = max(summaries, key=lambda p: p.stat().st_mtime)
    
    with open(latest) as f:
        summary = json.load(f)
    
    # Generate methods text
    console.print(Panel.fit(
        f"""## Data Extraction Methods

Data extraction was performed using SR-Architect. The pipeline processed 
**{summary.get('total_files', 'N/A')} PDFs** with a **{summary.get('success_rate', 'N/A')}** success rate.

- Session: `{summary.get('session_name', 'N/A')}`
- Duration: {summary.get('total_duration_seconds', 0):.1f} seconds
- Successful: {summary.get('successful', 0)}/{summary.get('total_files', 0)}

Full extraction logs are available in supplementary materials.""",
        title="Methods Section Text"
    ))


@app.command()
def discover(
    papers_dir: str = typer.Argument(..., help="Directory containing PDFs"),
    sample: int = typer.Option(3, "-n", "--sample", help="Number of papers to analyze"),
    output: str = typer.Option("./discovered_schema.json", "-o", "--output", help="Save schema to JSON"),
):
    """
    Discover extraction schema from sample papers.
    
    Analyzes the first N papers to suggest what variables can be extracted,
    then allows you to approve/modify before full extraction.
    
    Example:
        python cli.py discover ../DPM-systematic-review/papers --sample 3
    """
    load_env()
    
    from agents.schema_discovery import SchemaDiscoveryAgent
    
    papers_path = Path(papers_dir)
    if not papers_path.exists():
        console.print(f"[red]Error: Directory not found: {papers_dir}[/red]")
        raise typer.Exit(1)
    
    pdf_files = list(papers_path.glob("*.pdf"))[:sample]
    if not pdf_files:
        console.print(f"[red]Error: No PDF files found in {papers_dir}[/red]")
        raise typer.Exit(1)
    
    console.print(f"\n[bold cyan]🔍 Adaptive Schema Discovery[/bold cyan]")
    console.print(f"Analyzing {len(pdf_files)} papers to discover extraction variables...\n")
    
    agent = SchemaDiscoveryAgent()
    
    all_suggestions = []
    
    for pdf_path in pdf_files:
        try:
            console.print(f"[dim]Analyzing: {pdf_path.name}...[/dim]")
            result = agent.analyze_paper(str(pdf_path))
            all_suggestions.extend(result.suggested_fields)
            console.print(f"[green]✓ {pdf_path.name}: {len(result.suggested_fields)} fields discovered[/green]")
        except Exception as e:
            console.print(f"[red]✗ {pdf_path.name}: {e}[/red]")
    
    if not all_suggestions:
        console.print("[red]No fields discovered. Check API key and paper format.[/red]")
        raise typer.Exit(1)
    
    # Aggregate by field name
    from collections import Counter
    field_counts = Counter(s.field_name.lower().replace(" ", "_") for s in all_suggestions)
    
    # Display discovered fields
    table = Table(title=f"Discovered Fields ({len(field_counts)} unique)")
    table.add_column("Field Name", style="cyan")
    table.add_column("Frequency", style="yellow")
    table.add_column("Example Value")
    table.add_column("Type", style="green")
    
    examples = {}
    types = {}
    for s in all_suggestions:
        name = s.field_name.lower().replace(" ", "_")
        if name not in examples:
            examples[name] = s.example_value
            types[name] = s.data_type
    
    for name, count in field_counts.most_common(25):
        table.add_row(
            name,
            f"{count}/{sample}",
            examples.get(name, "")[:30],
            types.get(name, "text")
        )
    
    console.print(table)
    
    # Save to JSON
    schema_data = [
        {
            "name": name,
            "frequency": count,
            "example": examples.get(name, ""),
            "type": types.get(name, "text")
        }
        for name, count in field_counts.most_common()
    ]
    
    output_path = Path(output)
    if output_path.exists():
        if not typer.confirm(f"File '{output}' already exists. Overwrite?"):
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(schema_data, f, indent=2)
    
    console.print(f"\n[green]✓ Schema saved to {output_path}[/green]")
    console.print(f"\n[dim]Next: Review the schema, then run:[/dim]")
    console.print(f"  python cli.py extract {papers_dir} --interactive")


if __name__ == "__main__":
    app()
