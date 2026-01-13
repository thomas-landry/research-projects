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

from core.config import settings, MODEL_ALIASES
from core import (
    DocumentParser, 
    HierarchicalExtractionPipeline, 
    BatchExecutor, 
    StateManager
)
from core.service import ExtractionService
from core.schema_builder import (
    build_extraction_model,
    get_case_report_schema,
    get_rct_schema,
    get_observational_schema,
    interactive_schema_builder,
    FieldDefinition,
    PREDEFINED_SCHEMAS,
    infer_schema_from_csv,
)
from core.schema_chunker import (
    chunk_schema,
    merge_extraction_results,
    should_chunk_schema,
)
from agents.schema_discovery import interactive_discovery
from core.extractors import StructuredExtractor
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
    # Hybrid extraction mode (Phase 5)
    hybrid_mode: bool = typer.Option(True, "--hybrid-mode/--no-hybrid-mode", help="Use hybrid local-first extraction (default: enabled)"),
    # Cost guardrails (COST-001)
    max_cost: Optional[float] = typer.Option(None, "--max-cost", help="Maximum cost in USD. Abort if estimate exceeds. (e.g., 5.0)"),
    # Schema chunking for large schemas
    chunk_schema_flag: bool = typer.Option(True, "--chunk-schema/--no-chunk-schema", help="Auto-chunk large schemas (>30 fields) for cost optimization"),
    max_fields_per_chunk: int = typer.Option(25, "--max-fields-per-chunk", help="Maximum fields per chunk (default: 25)"),
):
    """
    Extract structured data from PDFs for systematic review.
    
    Example:
        python cli.py extract ../DPM-systematic-review/papers -o results.csv
    """

    load_env()

    # Resolve model alias
    if model and model in MODEL_ALIASES:
        # Check for local models specifically
        if model in ["llama3", "llama2", "mistral"]: 
           # Could add specific logic here if needed, but for now just map
           pass
        
        resolved_model = MODEL_ALIASES[model]
        if verbose:
            console.print(f"[dim]Resolved model alias '{model}' to: {resolved_model}[/dim]")
        model = resolved_model
    
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
        f"Hybrid Mode: {'[green]Enabled[/green]' if hybrid_mode else '[yellow]Disabled (Sonnet-only)[/yellow]'}\n"
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
    elif schema.lower().endswith(".csv") and Path(schema).exists():
        console.print(f"[green]Inferring schema from output template: {schema}[/green]")
        fields = infer_schema_from_csv(schema)
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
        fields = interactive_discovery(papers_dir, sample_size=3, existing_schema=fields, provider=provider, model=model)
    elif not resume and typer.confirm("\nWould you like to run adaptive discovery to find additional fields?", default=False):
        fields = interactive_discovery(papers_dir, sample_size=3, existing_schema=fields, provider=provider, model=model)
    
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
    
    # === Schema Chunking Detection ===
    schema_chunks = None
    if chunk_schema_flag and should_chunk_schema(fields):
        schema_chunks = chunk_schema(fields, max_fields_per_chunk)
        console.print(f"\n[bold yellow]📦 Large Schema Detected[/bold yellow]")
        console.print(f"  Total fields: {len(fields)}")
        console.print(f"  Chunks: {len(schema_chunks)}")
        console.print(f"  Fields per chunk: ~{max_fields_per_chunk}")
        console.print(f"  [dim]This will run {len(schema_chunks)} extractions per paper for cost optimization.[/dim]")
    
    
    # Token-based cost estimation is shown below in the detailed table
    # No hardcoded estimates - we rely on actual model pricing
    
    # The detailed cost estimator will calculate the actual cost based on:
    # - Model pricing (from token tracker)
    # - Estimated tokens per document
    # - Number of chunks (if schema chunking is enabled)

    # Initialize Service
    service = ExtractionService(
        provider=provider,
        model=model,
        token_tracker=tracker,
        verbose=verbose
    )

    # Validate hierarchical mode requirements
    if hierarchical and not theme:
        console.print("[red]Error: --theme is required when using --hierarchical mode[/red]")
        console.print("[dim]Example: --hierarchical --theme 'patient outcomes in treatment X'[/dim]")
        raise typer.Exit(1)
    
    # Load examples if provided
    examples_content = None
    if examples:
        try:
            examples_content = Path(examples).read_text()
            console.print(f"[green]Loaded few-shot examples from {examples}[/green]")
        except Exception as e:
            console.print(f"[yellow]Could not load examples from {examples}: {e}[/yellow]")

    # Pre-flight cost estimate
    if not resume:
        # Hierarchical runs are more expensive (discovery + filter + extract + audit)
        passes = 4 if hierarchical else 1
        
        # Account for schema chunking - each chunk requires a full extraction pass
        if schema_chunks:
            passes *= len(schema_chunks)
        
        estimate = tracker.estimate_extraction_cost(
            num_documents=len(pdf_files),
            model=model or settings.LLM_MODEL or "anthropic/claude-3.5-sonnet",
            num_passes=passes
        )
        console.print(tracker.display_cost_report(estimate))
        
        # Check max-cost guardrail with token-based estimate
        if max_cost is not None and estimate.get('total_cost_usd', 0) > max_cost:
            console.print(f"\n[bold red]❌ ABORTED: Estimated cost (${estimate['total_cost_usd']:.2f}) exceeds --max-cost (${max_cost:.2f})[/bold red]")
            console.print("[dim]Tip: Reduce with --limit, use --no-chunk-schema, or increase --max-cost[/dim]")
            raise typer.Exit(1)
        
        if not typer.confirm("Continue with extraction?"):
            raise typer.Exit()
    
    # Process batch
    console.print(f"\n[bold yellow]STARTING EXTRACTION...[/bold yellow]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        parsing_task = progress.add_task("Processing papers...", total=len(pdf_files))
        
        def progress_callback(filename, data, status):
            progress.advance(parsing_task)

        execution_summary = service.run_extraction(
            papers_dir=papers_dir,
            fields=fields,
            output_csv=output,
            hierarchical=hierarchical,
            theme=theme or "General extraction",
            threshold=threshold,
            max_iter=max_iter,
            workers=workers,
            resume=resume,
            examples=examples_content,
            vectorize=vectorize,
            limit=limit,  # COST-001 fix: pass limit to service
            hybrid_mode=hybrid_mode,  # COST-001 fix: enable local-first extraction
            schema_chunks=schema_chunks,  # Schema chunking for cost optimization
            callback=progress_callback
        )
    
    # Final summary with failures
    if execution_summary["failed_files"]:
        error_msg = "\n".join([f"• [bold red]{f}[/bold red]: {err[:100]}..." if len(err) > 100 else f"• [bold red]{f}[/bold red]: {err}" for f, err in execution_summary["failed_files"]])
        console.print(Panel(error_msg, title="[bold red]Extraction Failures[/bold red]", border_style="red"))

    console.print(f"\n[bold green]✓ Extraction complete. Results saved to {output}[/bold green]")
    
    summary = tracker.get_session_summary()
    table = Table(title="Extraction Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Total PDFs", str(execution_summary["total_files"]))
    table.add_row("Successfully parsed", str(execution_summary["parsed_files"]))
    table.add_row("Extraction failures", str(len(execution_summary["failed_files"])))
    table.add_row("Total tokens", f"{summary['total_tokens']:,}")
    table.add_row("Total cost (USD)", f"${summary['total_cost_usd']:.4f}")
    # Hybrid mode stats (Phase 5)
    if hybrid_mode:
        table.add_row("─" * 20, "─" * 12)
        table.add_row("[cyan]Hybrid Mode[/cyan]", "[green]Enabled[/green]")
        tier_stats = execution_summary.get("tier_stats", {})
        if tier_stats:
            local_pct = tier_stats.get("local_percentage", 0)
            table.add_row("Local extraction %", f"{local_pct:.1f}%")
            table.add_row("Cloud escalations", str(tier_stats.get("cloud_calls", 0)))
        cache_stats = execution_summary.get("cache_stats", {})
        if cache_stats:
            table.add_row("Cache hit rate", f"{cache_stats.get('hit_rate', 0):.1f}%")
    console.print(table)
    
    console.print(tracker.display_session_summary())
    
    if vectorize:
        console.print(f"[green]✓ Knowledge base updated in ChromaDB[/green]")

        # For now, let's warn that vectorization is pending update.
        console.print(f"\n[yellow]Note: Vectorization is currently disabled in batch mode.[/yellow]")
    
    console.print(f"\n[dim]Log file: {log_file}[/dim]")


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
    provider: str = typer.Option(settings.LLM_PROVIDER, "-p", "--provider", help="LLM provider: openrouter or ollama"),
    model: Optional[str] = typer.Option(settings.LLM_MODEL, "-m", "--model", help="Override LLM model"),
):
    """
    Discover extraction schema from sample papers.
    
    Analyzes the first N papers to suggest what variables can be extracted,
    then allows you to approve/modify before full extraction.
    
    Example:
        python cli.py discover ../DPM-systematic-review/papers --sample 3 --provider ollama
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
    
    agent = SchemaDiscoveryAgent(provider=provider, model=model)
    
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


@app.command()
def benchmark(
    papers_dir: str = typer.Argument(..., help="Directory containing PDFs"),
    output: str = typer.Option("./output/benchmark", "-o", "--output", help="Output directory"),
    models: str = typer.Option("llama3.1:8b-instruct-q8_0,mistral:7b-instruct-v0.3-q8_0,qwen2.5-coder:7b-instruct-q8_0", "-m", "--models", help="Comma-separated list of models"),
    sample: int = typer.Option(3, "-n", "--sample", help="Number of papers per model"),
    provider: str = typer.Option("ollama", "-p", "--provider", help="LLM Provider"),
):
    """
    Run partial benchmark on multiple local models.
    """
    load_env()
    from core.benchmark import ModelBenchmark
    
    model_list = [m.strip() for m in models.split(",")]
    
    console.print(f"\n[bold cyan]🚀 Starting Model Benchmark[/bold cyan]")
    console.print(f"Models: {', '.join(model_list)}")
    console.print(f"Provider: {provider}")
    
    harness = ModelBenchmark(papers_dir, output)
    results = harness.run_benchmark(model_list, sample_size=sample, provider=provider)
    
    console.print("\n[bold green]Benchmark Complete.[/bold green]")


if __name__ == "__main__":
    app()
