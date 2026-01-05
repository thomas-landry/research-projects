#!/usr/bin/env python3
"""
SR-Architect CLI - Systematic Review Data Extraction Pipeline

Command-line interface for extracting structured data from PDFs.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, List
import json

import concurrent.futures
import threading

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.parser import DocumentParser, ParsedDocument
from core.schema_builder import (
    build_extraction_model,
    get_case_report_schema,
    get_rct_schema,
    get_observational_schema,
    interactive_schema_builder,
    FieldDefinition,
    PREDEFINED_SCHEMAS,
)
from core.extractor import StructuredExtractor
from core.vectorizer import ChromaVectorStore
from core.audit_logger import AuditLogger
from core.hierarchical_pipeline import HierarchicalExtractionPipeline

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
    provider: str = typer.Option("openrouter", "-p", "--provider", help="LLM provider: openrouter or ollama"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Override LLM model"),
    vectorize: bool = typer.Option(True, "--vectorize/--no-vectorize", help="Store vectors in ChromaDB"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    resume: bool = typer.Option(False, "--resume", help="Resume from checkpoint if available"),
    # Hierarchical extraction options
    hierarchical: bool = typer.Option(False, "-H", "--hierarchical", help="Use hierarchical extraction with validation"),
    theme: Optional[str] = typer.Option(None, "-t", "--theme", help="Meta-analysis theme for relevance filtering (required with --hierarchical)"),
    threshold: float = typer.Option(0.9, "--threshold", help="Minimum accuracy+consistency score for validation"),
    max_iter: int = typer.Option(3, "--max-iter", help="Maximum checker feedback iterations"),
    # Optimization & Generalization
    workers: int = typer.Option(1, "--workers", "-w", help="Number of parallel workers (default: 1)"),
    examples: Optional[str] = typer.Option(None, "--examples", "-e", help="Path to few-shot examples text file"),
):
    """
    Extract structured data from PDFs for systematic review.
    
    Example:
        python cli.py extract ../DPM-systematic-review/papers -o results.csv
    """
    load_env()
    
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
    
    console.print(Panel.fit(
        f"[bold cyan]SR-Architect Extraction Pipeline[/bold cyan]\n\n"
        f"Papers: {len(pdf_files)} PDFs\n"
        f"Schema: {schema}\n"
        f"Provider: {provider}\n"
        f"Output: {output}",
        title="Configuration"
    ))
    
    # Build schema
    if interactive or schema == "interactive":
        fields = interactive_schema_builder()
    elif schema in PREDEFINED_SCHEMAS:
        fields = PREDEFINED_SCHEMAS[schema]()
        console.print(f"[green]Using predefined schema: {schema}[/green]")
    else:
        console.print(f"[red]Unknown schema: {schema}. Using case_report.[/red]")
        fields = get_case_report_schema()
    
    # Show schema fields
    if verbose:
        table = Table(title="Extraction Schema")
        table.add_column("Field")
        table.add_column("Type")
        table.add_column("Description")
        for f in fields:
            table.add_row(f.name, f.field_type.value, f.description[:40])
        console.print(table)
    
    # Build dynamic model
    ExtractionModel = build_extraction_model(fields, "SRExtractionModel")
    
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
        )
        extractor = None  # Not used in hierarchical mode
    else:
        pipeline = None
        extractor = StructuredExtractor(provider=provider, model=model, examples=examples_content)
    
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
    
    # Initialize state manager for checkpointing
    from core.state_manager import StateManager
    state_manager = StateManager(str(output_path.parent / "pipeline_state.json"))
    
    if resume and state_manager.exists():
        state = state_manager.load_or_create(schema_name=schema, papers_dir=papers_dir)
        console.print(f"[yellow]📂 Resuming from checkpoint: {len(state.completed_papers)} already done[/yellow]")
    else:
        state = state_manager.load_or_create(schema_name=schema, papers_dir=papers_dir)
        if state_manager.exists() and not resume:
            console.print("[dim]Previous state found. Use --resume to continue from checkpoint.[/dim]")
    
    # Filter files to process
    files_to_process = [p for p in pdf_files if state.should_process(p.name)]
    if len(files_to_process) < len(pdf_files):
        console.print(f"[dim]Skipping {len(pdf_files) - len(files_to_process)} already processed files[/dim]")

    results = []
    
    # Locks for thread safety
    state_lock = threading.Lock()
    log_lock = threading.Lock()
    
    def process_pdf(pdf_path, progress_task):
        """Process a single PDF in a thread-safe manner."""
        start_time = time.time()
        
        try:
            # Parse PDF
            doc = parser.parse_pdf(str(pdf_path))
            
            # Get extraction context
            context = doc.get_extraction_context()
            
            if len(context) < MIN_CONTEXT_CHARS:
                with log_lock:
                    logger.log_skipped(pdf_path.name, f"Insufficient text ({len(context)} chars)")
                with state_lock:
                    state.mark_skipped(pdf_path.name)
                    state_manager.save(state)
                progress.advance(progress_task)
                return None
            
            extracted_dict = {}
            
            # === HIERARCHICAL MODE ===
            if hierarchical and pipeline:
                pipeline_result = pipeline.extract_document(doc, ExtractionModel, theme)
                extracted_dict = pipeline_result.final_data
                
                # Metadata
                extracted_dict["__pipeline_accuracy_score"] = pipeline_result.final_accuracy_score
                extracted_dict["__pipeline_consistency_score"] = pipeline_result.final_consistency_score
                extracted_dict["__pipeline_overall_score"] = pipeline_result.final_overall_score
                extracted_dict["__pipeline_iterations"] = pipeline_result.iterations
                extracted_dict["__pipeline_passed_validation"] = pipeline_result.passed_validation
                if pipeline_result.warnings:
                    extracted_dict["__pipeline_warnings"] = "; ".join(pipeline_result.warnings)
                
                # Save evidence
                evidence_dir = output_path.parent / "evidence"
                with log_lock: # Ensure directory creation is safe-ish
                    evidence_file = pipeline_result.save_evidence_json(str(evidence_dir))
                
                if verbose:
                    console.print(f"    Evidence saved: {evidence_file}")
                
                 # Store vectors
                vectors_stored = 0
                if vector_store:
                    # ChromaDB writes might need locking or separate client? 
                    # Assuming basic thread safety or sequential writing if issues arise
                    vectors_stored = vector_store.add_chunks_from_parsed_doc(doc, extracted_dict)

                with log_lock:
                    logger.log_success(
                        filename=pdf_path.name,
                        chunks=len(doc.chunks),
                        vectors=vectors_stored,
                        model=pipeline.extractor.model,
                        extracted=extracted_dict,
                        duration=time.time() - start_time,
                    )

            # === STANDARD MODE ===
            else:
                extracted = extractor.extract(context, ExtractionModel, filename=pdf_path.name)
                extracted_dict = extracted.model_dump()
                
                vectors_stored = 0
                if vector_store:
                    vectors_stored = vector_store.add_chunks_from_parsed_doc(doc, extracted_dict)
                
                with log_lock:
                    logger.log_success(
                        filename=pdf_path.name,
                        chunks=len(doc.chunks),
                        vectors=vectors_stored,
                        model=extractor.model,
                        extracted=extracted_dict,
                        duration=time.time() - start_time,
                    )
            
            # Update state
            with state_lock:
                state.mark_completed(pdf_path.name)
                state_manager.save(state)
            
            progress.advance(progress_task)
            return extracted_dict

        except Exception as e:
            duration = time.time() - start_time
            with log_lock:
                logger.log_error(pdf_path.name, str(e), duration)
            with state_lock:
                state.mark_failed(pdf_path.name, str(e))
                state_manager.save(state)
            console.print(f"[red]✗ {pdf_path.name}: {e}[/red]")
            progress.advance(progress_task)
            return None

    # Execute
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing PDFs...", total=len(files_to_process))
        
        if workers > 1:
            console.print(f"[cyan]🚀 Parallel Execution: {workers} workers[/cyan]")
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(process_pdf, p, task) for p in files_to_process]
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result: results.append(result)
        else:
            # Sequential fallback
            for pdf_path in files_to_process:
                progress.update(task, description=f"Processing: {pdf_path.name[:40]}...")
                result = process_pdf(pdf_path, task)
                if result: results.append(result)
    
    # Save results to CSV
    if results:
        import pandas as pd
        df = pd.DataFrame(results)
        df.to_csv(output_path, index=False)
        console.print(f"\n[green]✓ Saved {len(results)} extractions to {output_path}[/green]")
    
    # Print summary
    logger.print_summary()
    summary = logger.save_summary()
    
    if vector_store:
        stats = vector_store.get_stats()
        console.print(f"\n[cyan]Vector store: {stats['document_count']} documents[/cyan]")
    
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(schema_data, f, indent=2)
    
    console.print(f"\n[green]✓ Schema saved to {output_path}[/green]")
    console.print(f"\n[dim]Next: Review the schema, then run:[/dim]")
    console.print(f"  python cli.py extract {papers_dir} --interactive")


if __name__ == "__main__":
    app()
