

import pandas as pd
import sys
from pathlib import Path
from typing import Optional

# Constants for analysis thresholds
LOW_FILL_RATE_THRESHOLD = 0.5  # 50% fill rate minimum
MAX_UNIQUE_VALUES_FOR_CATEGORICAL = 5  # Threshold for "messy" categorical data


def analyze_extraction(csv_path: str) -> None:
    """Analyze extraction results from CSV and generate research report.
    
    Generates a markdown-formatted report with:
    - Executive summary of dataset
    - Field-by-field analysis with fill rates
    - Ghost column detection (100% missing)
    - Data standardization recommendations
    
    Args:
        csv_path: Path to CSV file containing extraction results
    """
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: File not found {csv_path}")
        return

    print(f"# Research Report: {pd.Timestamp.now().strftime('%Y-%m-%d')}")
    print(f"\n## 1. Executive Summary")
    print(f"- **Dataset**: `{Path(csv_path).name}`")
    print(f"- **Papers**: {len(df)}")
    print(f"- **Total Columns**: {len(df.columns)}")
    
    # Exclude system columns
    sys_cols = [c for c in df.columns if c.startswith('__') or c in ['filename', 'extraction_notes', 'extraction_confidence']]
    data_cols = [c for c in df.columns if c not in sys_cols]
    
    # 2. Field Analysis
    print(f"\n## 2. Field Analysis")
    print(f"| Field | Fill Rate | Mean Confidence | Issues |")
    print(f"|-------|-----------|-----------------|--------|")
    
    ghost_columns = []
    
    for col in data_cols:
        # Fill Rate
        non_null = df[col].count()
        fill_rate = non_null / len(df)
        
        # Confidence (if we can infer it, otherwise N/A)
        # Note: Current CSV structure might not have per-column confidence unless evidence JSON is joined.
        # We'll use global confidence if available or skip.
        conf_val = "N/A"
        
        issues = []
        if fill_rate == 0:
            ghost_columns.append(col)
            issues.append("Ghost Column (100% missing)")
        elif fill_rate < LOW_FILL_RATE_THRESHOLD:
            issues.append(f"Low Fill Rate (<{LOW_FILL_RATE_THRESHOLD:.0%})")
            
        # detections of "Not reported" as text
        not_reported = df[col].astype(str).str.contains("Not reported", case=False, na=False).sum()
        if not_reported > 0:
            issues.append(f"Contains 'Not reported' ({not_reported})")

        issue_str = ", ".join(issues) if issues else "None"
        print(f"| {col} | {fill_rate:.0%} | {conf_val} | {issue_str} |")

    # 3. Findings
    print(f"\n## 3. Findings & Recommendations")
    
    if ghost_columns:
        print(f"\n### 👻 Ghost Columns")
        print(f"The following columns were never extracted:")
        for c in ghost_columns:
            print(f"- `{c}`")
        print("\n**Recommendation**: Verify if these fields are relevant for this subset (DPM) or if the schema definition is ambiguous.")

    print(f"\n### 📊 Data Standardization")
    # Check for non-standard values in categorical-like columns
    for col in ['patient_sex', 'outcome']:
        if col in df.columns:
            unique_vals = df[col].unique()
            if len(unique_vals) > MAX_UNIQUE_VALUES_FOR_CATEGORICAL:
                 print(f"- **{col}**: High variance in values (`{list(unique_vals)[:3]}...`). Consider strict Enum or normalization.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python researcher_analysis.py <csv_file>")
        sys.exit(1)
    analyze_extraction(sys.argv[1])
