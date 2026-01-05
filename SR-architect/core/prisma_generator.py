#!/usr/bin/env python3
"""
PRISMA Flow Diagram Generator.

Generates PRISMA 2020-compliant flow diagrams in multiple formats:
- Mermaid.js (for web/markdown)
- Text (for console)
- Methods text (for manuscripts)
"""

import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.prisma_state import ReviewState


def generate_prisma_mermaid(state: ReviewState) -> str:
    """
    Generate PRISMA flow diagram as Mermaid.js code.
    
    Args:
        state: ReviewState with PRISMA counts
        
    Returns:
        Mermaid.js diagram string
    """
    counts = {
        "identified": state["count_identified"],
        "duplicates": state["count_duplicates"],
        "screened": state["count_screened"],
        "excluded": state["count_excluded"],
        "included": state["count_included"],
    }
    
    # Build exclusion reasons breakdown
    reasons = state.get("count_excluded_reasons", {})
    reason_lines = []
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        # Format reason nicely
        reason_label = reason.replace("_", " ").title()
        reason_lines.append(f"{reason_label}: {count}")
    
    reasons_text = "<br/>".join(reason_lines[:5])  # Top 5 reasons
    if len(reason_lines) > 5:
        others = sum(c for r, c in reasons.items() if r not in dict(list(reasons.items())[:5]))
        reasons_text += f"<br/>Other: {others}"
    
    # Build Mermaid diagram
    mermaid = f"""```mermaid
flowchart TD
    subgraph Identification
        A[Records identified from databases<br/>n = {counts['identified']}]
    end
    
    subgraph Screening
        B[Records after duplicates removed<br/>n = {counts['screened']}]
        C[Records screened<br/>n = {counts['screened']}]
    end
    
    subgraph Included
        G[Studies included in review<br/>n = {counts['included']}]
    end
    
    A --> |Duplicates removed<br/>n = {counts['duplicates']}| B
    B --> C
    C --> |Excluded<br/>n = {counts['excluded']}| E[Excluded records<br/>{reasons_text}]
    C --> |Included| G
    
    style A fill:#e1f5fe
    style G fill:#c8e6c9
    style E fill:#ffcdd2
```"""
    
    return mermaid


def generate_prisma_text(state: ReviewState) -> str:
    """
    Generate PRISMA flow diagram as ASCII text.
    
    Args:
        state: ReviewState with PRISMA counts
        
    Returns:
        Text diagram
    """
    counts = {
        "identified": state["count_identified"],
        "duplicates": state["count_duplicates"],
        "screened": state["count_screened"],
        "excluded": state["count_excluded"],
        "included": state["count_included"],
    }
    
    reasons = state.get("count_excluded_reasons", {})
    
    text = f"""
╔══════════════════════════════════════════════════════════════╗
║                    PRISMA 2020 FLOW DIAGRAM                   ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ┌─────────────────────────────────────────────────────────┐ ║
║  │              IDENTIFICATION                              │ ║
║  │  Records identified from databases: {counts['identified']:>6}              │ ║
║  └─────────────────────────────┬───────────────────────────┘ ║
║                                │                              ║
║                                ▼                              ║
║            Duplicates removed: {counts['duplicates']:>6}                        ║
║                                │                              ║
║                                ▼                              ║
║  ┌─────────────────────────────────────────────────────────┐ ║
║  │              SCREENING                                   │ ║
║  │  Records screened: {counts['screened']:>6}                              │ ║
║  └─────────────────────────────┬───────────────────────────┘ ║
║                                │                              ║
║            ┌───────────────────┴───────────────────┐         ║
║            │                                       │         ║
║            ▼                                       ▼         ║
║  ┌──────────────────────┐            ┌──────────────────────┐║
║  │     EXCLUDED         │            │     INCLUDED         │║
║  │     n = {counts['excluded']:>6}         │            │     n = {counts['included']:>6}         │║
║  └──────────────────────┘            └──────────────────────┘║
║                                                               ║
╠══════════════════════════════════════════════════════════════╣
║  EXCLUSION REASONS:                                          ║"""
    
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        reason_label = reason.replace("_", " ").title()
        text += f"\n║    • {reason_label}: {count:<6}                                      ║"
    
    text += """
╚══════════════════════════════════════════════════════════════╝
"""
    
    return text


def generate_methods_section(state: ReviewState) -> str:
    """
    Generate the Methods section text for the manuscript.
    
    Args:
        state: ReviewState with search strategy and PRISMA counts
        
    Returns:
        Methods section text
    """
    pico = state.get("pico_criteria", {})
    counts = {
        "identified": state["count_identified"],
        "duplicates": state["count_duplicates"],
        "screened": state["count_screened"],
        "excluded": state["count_excluded"],
        "included": state["count_included"],
    }
    reasons = state.get("count_excluded_reasons", {})
    
    # Search strategy narrative
    search_strategies = state.get("search_strategies", [])
    if search_strategies:
        databases = ", ".join(s["database"] for s in search_strategies)
        search_date = search_strategies[0].get("search_date", "")[:10]
    else:
        databases = "electronic databases"
        search_date = "the search date"
    
    # Exclusion reasons breakdown
    reason_text = "; ".join(
        f"{r.replace('_', ' ')} (n={c})"
        for r, c in sorted(reasons.items(), key=lambda x: -x[1])
    )
    
    methods = f"""## Search Strategy

A systematic literature search was conducted in {databases} on {search_date}. The search strategy was developed using the PICO framework:

- **Population:** {pico.get('population', 'Not specified')}
- **Intervention:** {pico.get('intervention', 'Not specified')}
- **Comparator:** {pico.get('comparator', 'Not specified')}
- **Outcome:** {pico.get('outcome', 'Not specified')}

{state.get('search_strategy_log', '')}

## Eligibility Criteria

Studies were included if they met the following criteria:
- Study design: {pico.get('study_design', 'Not specified')}
- Language: {pico.get('language', 'English')}
- Publication period: {pico.get('date_range', 'No restriction')}

Studies were excluded if they were: {', '.join(pico.get('excluded_types', [])) or 'None specified'}.

## Study Selection

The initial search identified {counts['identified']} records. After removing {counts['duplicates']} duplicates, {counts['screened']} records were screened by title and abstract. 

Of these, {counts['excluded']} records were excluded for the following reasons: {reason_text or 'various reasons'}.

A total of **{counts['included']} studies** met the inclusion criteria and were included in the systematic review.

The study selection process is illustrated in the PRISMA flow diagram (Figure 1).
"""
    
    return methods


def generate_prisma_svg(state: ReviewState, output_path: str = "prisma_diagram.svg"):
    """
    Generate PRISMA flow diagram as SVG (requires matplotlib).
    
    Args:
        state: ReviewState with PRISMA counts
        output_path: Path to save SVG
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
    except ImportError:
        print("matplotlib not installed. Using text output instead.")
        return generate_prisma_text(state)
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 12))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    counts = {
        "identified": state["count_identified"],
        "duplicates": state["count_duplicates"],
        "screened": state["count_screened"],
        "excluded": state["count_excluded"],
        "included": state["count_included"],
    }
    
    # Identification box
    rect = patches.FancyBboxPatch((2, 10), 6, 1.5, boxstyle="round,pad=0.1",
                                    facecolor='#e3f2fd', edgecolor='black')
    ax.add_patch(rect)
    ax.text(5, 10.75, f"Records identified (n={counts['identified']})", 
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Arrow down
    ax.annotate('', xy=(5, 8.5), xytext=(5, 10),
                arrowprops=dict(arrowstyle='->', color='black'))
    ax.text(5.5, 9.25, f"Duplicates removed\n(n={counts['duplicates']})", fontsize=8)
    
    # Screening box
    rect = patches.FancyBboxPatch((2, 7), 6, 1.5, boxstyle="round,pad=0.1",
                                    facecolor='#fff3e0', edgecolor='black')
    ax.add_patch(rect)
    ax.text(5, 7.75, f"Records screened (n={counts['screened']})", 
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Two arrows
    ax.annotate('', xy=(2.5, 5.5), xytext=(4, 7),
                arrowprops=dict(arrowstyle='->', color='black'))
    ax.annotate('', xy=(7.5, 5.5), xytext=(6, 7),
                arrowprops=dict(arrowstyle='->', color='black'))
    
    # Excluded box
    rect = patches.FancyBboxPatch((0.5, 4), 3, 1.5, boxstyle="round,pad=0.1",
                                    facecolor='#ffebee', edgecolor='black')
    ax.add_patch(rect)
    ax.text(2, 4.75, f"Excluded (n={counts['excluded']})", 
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Included box
    rect = patches.FancyBboxPatch((6.5, 4), 3, 1.5, boxstyle="round,pad=0.1",
                                    facecolor='#e8f5e9', edgecolor='black')
    ax.add_patch(rect)
    ax.text(8, 4.75, f"Included (n={counts['included']})", 
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Reasons
    reasons = state.get("count_excluded_reasons", {})
    y = 3.5
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1])[:5]:
        ax.text(2, y, f"• {reason.replace('_', ' ')}: {count}", fontsize=8, ha='center')
        y -= 0.4
    
    plt.title("PRISMA 2020 Flow Diagram", fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, format='svg', bbox_inches='tight')
    plt.close()
    
    print(f"PRISMA diagram saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    from core.prisma_state import create_empty_state, PICOCriteria, Paper, PaperStatus, ExclusionReason
    
    # Create demo state
    pico = PICOCriteria(
        population="Adult ICU patients",
        intervention="Bowel protocol",
        comparator="Standard care",
        outcome="Constipation",
        study_design="RCT, cohort",
        language="English",
        date_range="2000-2024",
        excluded_types=["animal_study"],
    )
    
    state = create_empty_state("Demo Review", "Question?", pico)
    
    # Simulate counts
    state["count_identified"] = 150
    state["count_duplicates"] = 25
    state["count_screened"] = 125
    state["count_excluded"] = 100
    state["count_included"] = 25
    state["count_excluded_reasons"] = {
        "wrong_population": 35,
        "wrong_intervention": 25,
        "wrong_study_design": 20,
        "animal_study": 15,
        "review_article": 5,
    }
    
    # Generate outputs
    print("=== MERMAID DIAGRAM ===")
    print(generate_prisma_mermaid(state))
    
    print("\n=== TEXT DIAGRAM ===")
    print(generate_prisma_text(state))
    
    print("\n=== METHODS SECTION ===")
    print(generate_methods_section(state))
