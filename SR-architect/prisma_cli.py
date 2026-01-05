#!/usr/bin/env python3
"""
PRISMA-Compliant Systematic Review CLI.

Orchestrates the full systematic review workflow with PRISMA 2020 compliance.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from core.prisma_state import (
    PICOCriteria,
    ReviewState,
    PaperStatus,
    create_empty_state,
    recalculate_counts,
    validate_prisma_counts,
)
from core.prisma_generator import (
    generate_prisma_mermaid,
    generate_prisma_text,
    generate_methods_section,
)
from agents.orchestrator_pi import OrchestratorPI
from agents.librarian import LibrarianAgent, build_pico_query
from agents.screener import ScreenerAgent, RuleBasedPreScreener

app = typer.Typer(
    name="sr-prisma",
    help="PRISMA-Compliant Systematic Review Pipeline",
    add_completion=False,
)
console = Console()


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


def save_state(state: ReviewState, path: str):
    """Save state to JSON file."""
    # Convert to serializable format
    state_dict = dict(state)
    with open(path, "w") as f:
        json.dump(state_dict, f, indent=2)


def load_state(path: str) -> ReviewState:
    """Load state from JSON file."""
    with open(path) as f:
        return json.load(f)


@app.command()
def init(
    title: str = typer.Option(..., "--title", "-t", help="Review title"),
    question: str = typer.Option(..., "--question", "-q", help="Clinical question"),
    population: str = typer.Option(..., "--population", "-P", help="PICO Population"),
    intervention: str = typer.Option(..., "--intervention", "-I", help="PICO Intervention"),
    comparator: str = typer.Option("Standard care", "--comparator", "-C", help="PICO Comparator"),
    outcome: str = typer.Option(..., "--outcome", "-O", help="PICO Outcome"),
    design: str = typer.Option("RCT, cohort, case-control", "--design", "-d", help="Study designs"),
    output: str = typer.Option("./sr_state.json", "--output", "-o", help="State file path"),
):
    """
    Initialize a new PRISMA-compliant systematic review.
    
    Example:
        python prisma_cli.py init \\
            --title "Bowel Protocols in ICU" \\
            --question "Does prophylactic bowel management reduce constipation?" \\
            --population "Adult ICU patients" \\
            --intervention "Bowel protocol, laxative prophylaxis" \\
            --outcome "Constipation, bowel movement"
    """
    pico = PICOCriteria(
        population=population,
        intervention=intervention,
        comparator=comparator,
        outcome=outcome,
        study_design=design,
        language="English",
        date_range="2000-2024",
        excluded_types=["animal_study", "in_vitro_study", "review_article"],
    )
    
    pi = OrchestratorPI()
    state = pi.initialize_review(title, question, pico)
    
    save_state(state, output)
    
    console.print(Panel.fit(
        f"[bold green]✓ Review initialized[/bold green]\n\n"
        f"[cyan]Title:[/cyan] {title}\n"
        f"[cyan]Question:[/cyan] {question}\n\n"
        f"[cyan]PICO:[/cyan]\n"
        f"  P: {population}\n"
        f"  I: {intervention}\n"
        f"  C: {comparator}\n"
        f"  O: {outcome}\n\n"
        f"[dim]State saved to: {output}[/dim]",
        title="SR-PRISMA"
    ))


@app.command()
def search(
    state_file: str = typer.Option("./sr_state.json", "--state", "-s", help="State file"),
    max_results: int = typer.Option(100, "--max", "-m", help="Max papers to fetch"),
):
    """
    Run literature search (Librarian agent).
    
    Example:
        python prisma_cli.py search --max 200
    """
    load_env()
    
    state = load_state(state_file)
    pico = state["pico_criteria"]
    
    # Build query
    query = build_pico_query(
        population=pico["population"],
        intervention=pico["intervention"],
        outcome=pico["outcome"],
    )
    
    console.print(f"[cyan]Search query:[/cyan] {query[:100]}...")
    
    # Run search
    librarian = LibrarianAgent()
    
    with console.status("Searching PubMed..."):
        papers, strategy = librarian.run_search(query, max_results=max_results)
    
    # Update state
    state["bibliography"] = papers
    state["search_strategies"] = [strategy]
    state["search_strategy_log"] = f"PubMed searched on {strategy['search_date'][:10]} with query: {query}"
    state = recalculate_counts(state)
    state["current_phase"] = "deduplication"
    
    save_state(state, state_file)
    
    console.print(f"\n[green]✓ Found {len(papers)} papers[/green]")
    console.print(f"[dim]State updated: {state_file}[/dim]")


@app.command()
def dedupe(
    state_file: str = typer.Option("./sr_state.json", "--state", "-s", help="State file"),
):
    """
    Remove duplicate papers.
    
    Example:
        python prisma_cli.py dedupe
    """
    state = load_state(state_file)
    
    pi = OrchestratorPI(state)
    result = pi.run_deduplication()
    
    if not result.success:
        console.print(f"[red]Error: {result.error}[/red]")
        raise typer.Exit(1)
    
    save_state(pi.state, state_file)
    
    console.print(f"[green]✓ Removed {result.data['count_duplicates']} duplicates[/green]")
    console.print(f"[cyan]Papers to screen: {result.data['count_screened']}[/cyan]")


@app.command()
def screen(
    state_file: str = typer.Option("./sr_state.json", "--state", "-s", help="State file"),
    use_llm: bool = typer.Option(True, "--llm/--rules-only", help="Use LLM or rules only"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit papers to screen"),
):
    """
    Screen papers against PICO criteria.
    
    Example:
        python prisma_cli.py screen --limit 10
    """
    load_env()
    
    state = load_state(state_file)
    pico = state["pico_criteria"]
    
    # Get pending papers
    pending = [p for p in state["bibliography"] if p["status"] == PaperStatus.PENDING.value]
    
    if limit:
        pending = pending[:limit]
    
    console.print(f"[cyan]Screening {len(pending)} papers...[/cyan]")
    
    # Initialize screeners
    pre_screener = RuleBasedPreScreener(pico)
    llm_screener = ScreenerAgent(pico) if use_llm else None
    
    pi = OrchestratorPI(state)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Screening...", total=len(pending))
        
        for paper in pending:
            progress.update(task, description=f"PMID: {paper['pmid']}")
            
            # Try rule-based first
            decision = pre_screener.pre_screen(paper)
            
            # If no rule match and LLM enabled, use LLM
            if decision is None and llm_screener:
                decision = llm_screener.screen_abstract(paper)
            
            # Record decision
            if decision:
                pi.record_screening_decision(
                    pmid=paper["pmid"],
                    include=decision.include,
                    exclusion_reason=decision.exclusion_reason,
                    notes=decision.notes,
                )
            
            progress.advance(task)
    
    # Save updated state
    save_state(pi.state, state_file)
    
    # Show summary
    state = pi.state
    console.print(f"\n[green]✓ Screening complete[/green]")
    console.print(f"  Included: {state['count_included']}")
    console.print(f"  Excluded: {state['count_excluded']}")
    
    if state["count_excluded_reasons"]:
        console.print("\n[cyan]Exclusion breakdown:[/cyan]")
        for reason, count in sorted(state["count_excluded_reasons"].items(), key=lambda x: -x[1]):
            console.print(f"  • {reason}: {count}")


@app.command()
def validate(
    state_file: str = typer.Option("./sr_state.json", "--state", "-s", help="State file"),
):
    """
    Validate PRISMA counts and check for errors.
    
    Example:
        python prisma_cli.py validate
    """
    state = load_state(state_file)
    state = recalculate_counts(state)
    errors = validate_prisma_counts(state)
    
    # Show counts
    table = Table(title="PRISMA Counts")
    table.add_column("Stage")
    table.add_column("Count", justify="right")
    
    table.add_row("Identified", str(state["count_identified"]))
    table.add_row("Duplicates", str(state["count_duplicates"]))
    table.add_row("Screened", str(state["count_screened"]))
    table.add_row("Excluded", str(state["count_excluded"]))
    table.add_row("Included", str(state["count_included"]))
    
    console.print(table)
    
    if errors:
        console.print("\n[red]Validation FAILED:[/red]")
        for error in errors:
            console.print(f"  ✗ {error}")
        raise typer.Exit(1)
    else:
        console.print("\n[green]✓ PRISMA validation passed[/green]")


@app.command()
def diagram(
    state_file: str = typer.Option("./sr_state.json", "--state", "-s", help="State file"),
    format: str = typer.Option("mermaid", "--format", "-f", help="Output format: mermaid, text, svg"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """
    Generate PRISMA flow diagram.
    
    Example:
        python prisma_cli.py diagram --format mermaid
        python prisma_cli.py diagram --format text
    """
    state = load_state(state_file)
    
    if format == "mermaid":
        diagram = generate_prisma_mermaid(state)
    elif format == "text":
        diagram = generate_prisma_text(state)
    elif format == "svg":
        from core.prisma_generator import generate_prisma_svg
        output = output or "prisma_diagram.svg"
        generate_prisma_svg(state, output)
        console.print(f"[green]✓ SVG saved to: {output}[/green]")
        return
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(1)
    
    if output:
        with open(output, "w") as f:
            f.write(diagram)
        console.print(f"[green]✓ Diagram saved to: {output}[/green]")
    else:
        console.print(diagram)


@app.command()
def methods(
    state_file: str = typer.Option("./sr_state.json", "--state", "-s", help="State file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """
    Generate Methods section text.
    
    Example:
        python prisma_cli.py methods --output methods.md
    """
    state = load_state(state_file)
    
    text = generate_methods_section(state)
    
    if output:
        with open(output, "w") as f:
            f.write(text)
        console.print(f"[green]✓ Methods section saved to: {output}[/green]")
    else:
        console.print(Panel(text, title="Methods Section"))


@app.command()
def status(
    state_file: str = typer.Option("./sr_state.json", "--state", "-s", help="State file"),
):
    """
    Show current review status.
    
    Example:
        python prisma_cli.py status
    """
    state = load_state(state_file)
    
    console.print(Panel.fit(
        f"[bold]{state.get('review_title', 'Untitled')}[/bold]\n\n"
        f"[cyan]Phase:[/cyan] {state.get('current_phase', 'unknown')}\n"
        f"[cyan]Identified:[/cyan] {state['count_identified']}\n"
        f"[cyan]Screened:[/cyan] {state['count_screened']}\n"
        f"[cyan]Included:[/cyan] {state['count_included']}\n"
        f"[cyan]Excluded:[/cyan] {state['count_excluded']}\n",
        title="Review Status"
    ))


if __name__ == "__main__":
    app()
