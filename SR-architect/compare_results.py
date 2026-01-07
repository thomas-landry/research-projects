#!/usr/bin/env python3
"""
Compare extraction results with Gold Standard CSV.
Improved with multi-field matching (Title, Authors, Year) and skip-if-empty-GS logic.
"""

import csv
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from schemas.dpm_gold_standard import COLUMN_NAME_MAPPING

def normalize_value(value: Any) -> str:
    """Normalize value for comparison."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    
    val_str = str(value).strip().lower()
    if val_str in ('true', 'yes', '1'):
        return "1"
    if val_str in ('false', 'no', '0'):
        return "0"
    return str(value).strip()

def similar(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

def load_gold_standard(csv_path: Path) -> List[Dict[str, str]]:
    """Load gold standard CSV."""
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        # Skip first line if it's a title
        first_line = f.readline()
        if "DPM Results" in first_line:
            pass # Header is on next line
        else:
            f.seek(0)
            
        reader = csv.DictReader(f)
        return list(reader)

def find_match(extraction: Dict[str, Any], gold_standard: List[Dict[str, str]]) -> Optional[Tuple[Dict[str, str], int]]:
    """Find matching record in gold standard using multi-field scoring."""
    ext_title = extraction.get('title', '').lower()
    ext_authors = extraction.get('authors', '').lower()
    ext_year = str(extraction.get('year', ''))
    
    best_match = None
    max_score = 0
    
    for i, record in enumerate(gold_standard):
        gs_title = record.get('Title', '').lower()
        if not gs_title:
            continue
            
        gs_authors = record.get('Authors', '').lower()
        gs_year = str(record.get('Year', ''))
        
        # Calculate scores
        title_sim = similar(ext_title, gs_title)
        
        # Author match (check if surname is in authors list)
        author_sim = 0.0
        if ext_authors and gs_authors:
            gs_first_surname = gs_authors.split(' ')[0].replace(',', '')
            if gs_first_surname in ext_authors:
                author_sim = 1.0
            else:
                author_sim = similar(ext_authors, gs_authors)
        
        year_match = 1.0 if ext_year and gs_year and ext_year == gs_year else 0.0
        
        # Weighted score: Title is primary, but Authors break ties (duplicates)
        score = (title_sim * 0.7) + (author_sim * 0.2) + (year_match * 0.1)
        
        if score > max_score and score > 0.7:
            max_score = score
            best_match = (record, i)
            
    return best_match

def compare_results(json_path: Path, csv_path: Path):
    """Compare JSON extraction with CSV gold standard."""
    
    # Load data
    with open(json_path) as f:
        extraction_data = json.load(f)
        
    gold_data = load_gold_standard(csv_path)
    
    print(f"Loaded {len(extraction_data['results'])} extracted records")
    print(f"Loaded {len(gold_data)} gold standard records")
    
    overall_compared = 0
    overall_matches = 0
    
    for result in extraction_data['results']:
        if result['status'] != 'success':
            continue
            
        data = result['data']
        match_info = find_match(data, gold_data)
        
        if not match_info:
            print(f"⚠️  No match found for {data.get('filename')}")
            continue
            
        gs_record, csv_idx = match_info
        print(f"\n[Matched to CSV Row {csv_idx+2}] - {data.get('filename')[:50]}...")
        
        doc_matches = 0
        doc_total = 0
        mismatches = []

        # Compare fields
        for json_field, csv_col in COLUMN_NAME_MAPPING.items():
            if csv_col not in gs_record:
                continue
                
            val_extracted = normalize_value(data.get(json_field))
            val_gold = normalize_value(gs_record.get(csv_col))
            
            # CRITICAL: Skip if GS is empty or '-' to avoid false negatives on sparse rows
            if not val_gold or val_gold == "-":
                continue
            
            # Also skip if both are empty (redundant but safe)
            if not val_extracted and not val_gold:
                continue
                
            doc_total += 1
            
            is_match = False
            if val_extracted == val_gold:
                is_match = True
            elif similar(val_extracted, val_gold) > 0.8: 
                is_match = True
            
            if is_match:
                doc_matches += 1
            else:
                mismatches.append((json_field, val_extracted, val_gold))
        
        if doc_total > 0:
            doc_acc = (doc_matches / doc_total) * 100
            print(f"   Accuracy for this doc: {doc_acc:.1f}% ({doc_matches}/{doc_total})")
            
            if mismatches:
                print("   Top Mismatches:")
                for field, got, expected in mismatches[:5]:
                    print(f"     - {field}: '{got[:50]}...' vs GS: '{expected[:50]}...'")
            
            overall_matches += doc_matches
            overall_compared += doc_total

    if overall_compared == 0:
        print("\nNo comparable fields found in any successfully matched documents.")
    else:
        accuracy = (overall_matches / overall_compared) * 100
        print("\n" + "="*50)
        print(f"OVERALL PERFORMANCE SUMMARY")
        print("="*50)
        print(f"Matched Documents:     {len([r for r in extraction_data['results'] if r['status']=='success'])}")
        print(f"Total Fields Compared: {overall_compared}")
        print(f"Total Matches:         {overall_matches}")
        print(f"Final Pilot Accuracy: {accuracy:.2f}%")
        print("="*50)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", type=Path)
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args()
    
    compare_results(args.json_file, args.csv_file)
