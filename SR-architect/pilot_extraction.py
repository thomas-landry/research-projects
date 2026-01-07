#!/usr/bin/env python3
"""
Pilot Extraction Script for DPM Systematic Review.

Runs hybrid 2-pass extraction:
1. Metadata (Local LLM): Title, Authors, Year, etc.
2. Clinical (Cloud LLM): Narratives and deep reasoning.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from core.parser import DocumentParser
from core.extractor import StructuredExtractor
from core.token_tracker import TokenTracker
from core.binary_deriver import BinaryDeriver, process_extraction
from schemas.dpm_gold_standard import DPMNarrativeExtractionSchema
from schemas.dpm_modular import StudyMetadataSchema


def load_pdf_text(pdf_path: Path, parser: DocumentParser) -> Optional[str]:
    """Load text from a PDF using DocumentParser."""
    try:
        doc = parser.parse_pdf(str(pdf_path))
        return doc.get_extraction_context()
    except Exception as e:
        print(f"   ⚠️ Failed to parse {pdf_path.name}: {e}")
        return None


def run_pilot(
    papers_dir: Path,
    output_dir: Path,
    sample_size: int = 3,
    metadata_model: str = "llama3.1:8b",
    clinical_model: str = "anthropic/claude-3.5-sonnet",
    metadata_provider: str = "ollama",
    clinical_provider: str = "openrouter",
    dry_run: bool = False,
):
    """Run pilot extraction using Hybrid 2-Pass strategy."""
    
    print("\n" + "="*70)
    print("DPM EXTRACTION PILOT (HYBRID)")
    print("="*70)
    print(f"Pass 1 (Metadata): {metadata_provider}/{metadata_model}")
    print(f"Pass 2 (Clinical): {clinical_provider}/{clinical_model}")
    
    # Initialize document parser
    print("\n📖 Initializing document parser...")
    doc_parser = DocumentParser()
    
    # Find and parse PDFs
    pdf_files = sorted(papers_dir.glob("*.pdf"))
    print(f"📄 Found {len(pdf_files)} PDFs in {papers_dir}")
    
    # Parse sample PDFs
    available_papers = []
    print("\nProcessing sample buffer...")
    for pdf_path in pdf_files[:sample_size * 2]:
        print(f"   Parsing: {pdf_path.name[:50]}...", end=" ")
        text = load_pdf_text(pdf_path, doc_parser)
        if text and len(text) > 100:
            token_estimate = len(text) // 4
            available_papers.append({
                'path': pdf_path,
                'name': pdf_path.stem,
                'text': text,
                'tokens': token_estimate,
            })
            print(f"✓ ({token_estimate:,} tokens)")
        else:
            print("✗ (insufficient text)")
        
        if len(available_papers) >= sample_size:
            break
            
    if not available_papers:
        print("⚠️  No papers parsed successfully.")
        return

    sample = available_papers[:sample_size]
    
    # Initialize components
    tracker = TokenTracker()
    
    # Initialize Extractors
    print(f"\n🤖 Initializing Extractors...")
    # Metadata Extractor (Pass 1)
    metadata_extractor = StructuredExtractor(
        provider=metadata_provider,
        model=metadata_model,
        token_tracker=tracker
    )
    
    # Clinical Extractor (Pass 2)
    clinical_extractor = StructuredExtractor(
        provider=clinical_provider,
        model=clinical_model,
        token_tracker=tracker
    )
    
    deriver = BinaryDeriver()
    
    # Cost Estimation
    total_tokens = sum(p['tokens'] for p in sample)
    
    # Metadata pass tokens (local/free usually)
    meta_tokens = sample_size * 2000 # Header only
    clinical_tokens = total_tokens # Full text
    
    # We only estimate CLINICAL cost if clinical provider is NOT ollama
    clinical_cost = 0.0
    if clinical_provider != "ollama":
        est = tracker.estimate_extraction_cost(
            num_documents=len(sample),
            avg_tokens_per_doc=clinical_tokens // len(sample),
            model=clinical_model
        )
        clinical_cost = est.estimated_cost_usd

    print(f"\n💰 COST ESTIMATE (Clinical Pass Only):")
    print(f"   Input tokens:  ~{clinical_tokens:,}")
    print(f"   Estimated cost: ${clinical_cost:.4f}")
    print(f"   Metadata Pass: Free (Local)" if metadata_provider == "ollama" else "   Metadata Pass: Cloud rate")
    
    if dry_run:
        print("\n🔍 DRY RUN - No extraction performed")
        return
    
    # Confirm
    print("\n" + "-"*70)
    response = input("Proceed with extraction? [y/N]: ").strip().lower()
    if response not in ('y', 'yes'):
        print("Cancelled.")
        return
        
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    
    print(f"\n🚀 Starting Hybrid Extraction...")
    
    for i, paper in enumerate(sample, 1):
        filename = paper['path'].name
        print(f"\n[{i}/{len(sample)}] Processing: {filename[:40]}...")
        text = paper['text']
        
        try:
            # --- PASS 1: METADATA ---
            print("   [1/2] extracting metadata...", end=" ", flush=True)
            # Use first 3000 chars (approx 1 page) for header extraction
            header_text = text[:4000]
            
            metadata = metadata_extractor.extract(
                text=header_text,
                schema=StudyMetadataSchema,
                filename=filename
            )
            print("✓")
            
            # --- PASS 2: CLINICAL ---
            print("   [2/2] extracting clinical data...", end=" ", flush=True)
            narrative = clinical_extractor.extract(
                text=text,
                schema=DPMNarrativeExtractionSchema,
                filename=filename
            )
            print("✓")
            
            # --- MERGE & DERIVE ---
            meta_dict = metadata.model_dump()
            narrative_dict = narrative.model_dump()
            
            # Combine - metadata schema overwrites narrative schema for shared Metadata fields
            # But DPMNarrativeExtractionSchema doesn't have title/authors, so no conflict usually.
            combined_data = {**narrative_dict, **meta_dict}
            
            # Ensure filename is preserved
            combined_data['filename'] = filename
            
            final_data = process_extraction(combined_data)
            
            results.append({
                'filename': filename,
                'status': 'success',
                'data': final_data
            })
            print(f"   ✓ Success (Extracted {len(final_data)} fields)")
            
        except Exception as e:
            print(f"\n   ✗ Error: {e}")
            results.append({
                'filename': filename,
                'status': 'error',
                'error': str(e)
            })

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"pilot_hybrid_{timestamp}.json"
    
    final_output = {
        'metadata': {
            'timestamp': timestamp,
            'metadata_model': metadata_model,
            'clinical_model': clinical_model,
            'sample_size': len(sample)
        },
        'results': results
    }
    
    with open(output_file, 'w') as f:
        json.dump(final_output, f, indent=2, default=str)
        
    print("\n" + "="*70)
    print("HYBRID PILOT COMPLETE")
    print(f"📁 Saved to: {output_file}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--papers-dir", type=Path, default=Path("/Users/thomaslandry/Projects/research-projects/DPM-systematic-review/papers"))
    parser.add_argument("--output-dir", type=Path, default=Path("/Users/thomaslandry/Projects/research-projects/DPM-systematic-review/extraction_results"))
    parser.add_argument("--sample-size", type=int, default=3)
    
    parser.add_argument("--metadata-model", type=str, default="llama3.1:8b")
    parser.add_argument("--clinical-model", type=str, default="anthropic/claude-3.5-sonnet")
    
    parser.add_argument("--metadata-provider", type=str, default="ollama")
    parser.add_argument("--clinical-provider", type=str, default="openrouter")
    
    parser.add_argument("--dry-run", action="store_true")
    
    args = parser.parse_args()
    
    run_pilot(
        papers_dir=args.papers_dir,
        output_dir=args.output_dir,
        sample_size=args.sample_size,
        metadata_model=args.metadata_model,
        clinical_model=args.clinical_model,
        metadata_provider=args.metadata_provider,
        clinical_provider=args.clinical_provider,
        dry_run=args.dry_run
    )
