"""
LLM-IE Benchmark Script

Compares LLM-IE's SentenceFrameExtractor against SR-architect's baseline
on the golden dataset (10 DPM case reports).

Usage:
    python3 benchmarks/llm_ie_benchmark.py --limit 3
"""

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import sys

# Add parent to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.parser import DocumentParser
from core.token_tracker import TokenTracker

# LLM-IE imports
from llm_ie import (
    SentenceFrameExtractor,
    BasicFrameExtractor,  # For comparison - whole doc approach
    LLMInformationExtractionDocument,
)
from llm_inference_engine import OllamaInferenceEngine, BasicLLMConfig

# Schema fields to extract (matching our case_report schema)
# Schema fields to extract (matching our case_report schema)
CASE_REPORT_SCHEMA = """
### Task description
Extract clinical case details from the sentence. Focus on specific entity types defined below.

### Schema definition
Your output should contain "entity_text" (the exact quote) and "attr" dictionary containing:
    "entity_type": one of ["case_count", "patient_age", "patient_sex", "presenting_symptoms", "diagnostic_method", "imaging_findings", "histopathology", "immunohistochemistry", "treatment", "outcome"].

### Output format definition
Your output should follow JSON format:
[
    {"entity_text": "<exact quote from text>", "attr": {"entity_type": "<field_name>"}},
    {"entity_text": "<exact quote from text>", "attr": {"entity_type": "<field_name>"}}
]

If no relevant entities are found in the sentence, output: []

### Examples
Input: A 45-year-old male presented with chronic cough.
Output: [
    {"entity_text": "45-year-old", "attr": {"entity_type": "patient_age"}},
    {"entity_text": "male", "attr": {"entity_type": "patient_sex"}},
    {"entity_text": "chronic cough", "attr": {"entity_type": "presenting_symptoms"}}
]

### Context
The sentence to extract from:
"{{input}}"
"""


def load_golden_baseline(baseline_path: Path) -> Dict[str, Dict]:
    """Load golden dataset baseline for comparison."""
    baseline = {}
    with open(baseline_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row.get('filename', '')
            if filename:
                baseline[filename] = row
    return baseline


def run_sentence_extractor(
    text: str,
    engine: OllamaInferenceEngine,
) -> tuple[List[Any], float, int]:
    """Run LLM-IE SentenceFrameExtractor and return frames, time, tokens."""
    extractor = SentenceFrameExtractor(
        inference_engine=engine,
        prompt_template=CASE_REPORT_SCHEMA,
        context_sentences=1  # ±1 sentences around focus
    )
    
    start_time = time.time()
    frames = extractor.extract_frames(
        text,
        concurrent=False,  # Sequential for accurate timing
        fuzzy_match=True,
        fuzzy_score_cutoff=0.7
    )
    elapsed = time.time() - start_time
    
    return frames, elapsed, len(frames)


def run_basic_extractor(
    text: str,
    engine: OllamaInferenceEngine,
) -> tuple[List[Any], float, int]:
    """Run LLM-IE BasicFrameExtractor (whole doc) for comparison."""
    extractor = BasicFrameExtractor(
        inference_engine=engine,
        prompt_template=CASE_REPORT_SCHEMA,
    )
    
    start_time = time.time()
    frames = extractor.extract_frames(
        text,
        fuzzy_match=True,
        fuzzy_score_cutoff=0.7
    )
    elapsed = time.time() - start_time
    
    return frames, elapsed, len(frames)


def compare_extractions(
    frames: List[Any],
    baseline: Dict[str, str],
    fields: List[str]
) -> Dict[str, Any]:
    """Compare extracted frames against baseline."""
    results = {
        'fields_found': 0,
        'fields_total': len(fields),
        'fields_matched': 0,
        'details': {}
    }
    
    # Group frames by field
    extracted_by_field = {}
    for frame in frames:
        if hasattr(frame, 'attr') and 'entity_type' in frame.attr:
            field = frame.attr['entity_type']
            if field not in extracted_by_field:
                extracted_by_field[field] = []
            extracted_by_field[field].append(frame.entity_text)
    
    for field in fields:
        baseline_value = baseline.get(field, '')
        extracted_values = extracted_by_field.get(field, [])
        
        if extracted_values:
            results['fields_found'] += 1
            # Simple substring match for now
            if any(ev.lower() in baseline_value.lower() or 
                   baseline_value.lower() in ev.lower() 
                   for ev in extracted_values):
                results['fields_matched'] += 1
                results['details'][field] = 'MATCH'
            else:
                results['details'][field] = 'MISMATCH'
        else:
            results['details'][field] = 'MISSING'
    
    return results


def main():
    parser = argparse.ArgumentParser(description='LLM-IE Benchmark')
    parser.add_argument('--limit', type=int, default=3, help='Limit papers to process')
    parser.add_argument('--model', default='qwen3:14b', help='Ollama model to use')
    parser.add_argument('--output', default='benchmarks/llm_ie_benchmark_results.json')
    args = parser.parse_args()
    
    # Paths
    papers_dir = Path('papers_benchmark')
    baseline_path = Path('benchmarks/golden_dataset/baseline.csv')
    cache_dir = Path('.cache/parsed_docs')
    
    # Load baseline
    print(f"Loading baseline from {baseline_path}...")
    baseline = load_golden_baseline(baseline_path)
    print(f"  Found {len(baseline)} baseline entries")
    
    # Initialize Ollama engine
    print(f"\nInitializing Ollama engine with model: {args.model}")
    try:
        engine = OllamaInferenceEngine(
            model_name=args.model,
            num_ctx=4096,
            keep_alive=300,
            config=BasicLLMConfig(temperature=0.1, max_new_tokens=2048)
        )
    except Exception as e:
        print(f"ERROR: Could not initialize Ollama: {e}")
        print("Make sure Ollama is running: ollama serve")
        return 1
    
    # Get papers to process
    pdf_files = sorted(papers_dir.glob('*.pdf'))[:args.limit]
    print(f"\nProcessing {len(pdf_files)} papers...")
    
    results = {
        'config': {
            'model': args.model,
            'limit': args.limit,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        },
        'papers': [],
        'summary': {
            'sentence_extractor': {'total_time': 0, 'total_frames': 0},
            'basic_extractor': {'total_time': 0, 'total_frames': 0}
        }
    }
    
    fields_to_check = [
        'case_count', 'patient_age', 'patient_sex', 'presenting_symptoms',
        'diagnostic_method', 'imaging_findings', 'histopathology'
    ]
    
    for i, pdf_path in enumerate(pdf_files):
        print(f"\n[{i+1}/{len(pdf_files)}] {pdf_path.name}")
        
        # Parse PDF (use cached if available)
        cache_file = cache_dir / f"{pdf_path.stem}.json"
        if cache_file.exists():
            print("  Using cached parse...")
            with open(cache_file) as f:
                parsed = json.load(f)
                text = parsed.get('full_text', '')
        else:
            print("  Parsing PDF...")
            pdf_parser = DocumentParser()
            doc = pdf_parser.parse_pdf(str(pdf_path))
            text = doc.full_text if hasattr(doc, 'full_text') else str(doc)
        
        # Truncate for initial test
        text = text[:15000]  # First 15K chars
        print(f"  Text length: {len(text)} chars")
        
        paper_result = {
            'filename': pdf_path.name,
            'text_length': len(text)
        }
        
        # Run SentenceFrameExtractor
        print("  Running SentenceFrameExtractor...")
        try:
            frames, elapsed, count = run_sentence_extractor(text, engine)
            paper_result['sentence_extractor'] = {
                'frames': count,
                'time_seconds': round(elapsed, 2),
                'frames_data': [f.to_dict() if hasattr(f, 'to_dict') else str(f) for f in frames[:10]]
            }
            results['summary']['sentence_extractor']['total_time'] += elapsed
            results['summary']['sentence_extractor']['total_frames'] += count
            print(f"    → {count} frames in {elapsed:.1f}s")
        except Exception as e:
            print(f"    ERROR: {e}")
            paper_result['sentence_extractor'] = {'error': str(e)}
        
        # Run BasicFrameExtractor (whole doc)
        print("  Running BasicFrameExtractor (whole doc)...")
        try:
            frames, elapsed, count = run_basic_extractor(text, engine)
            paper_result['basic_extractor'] = {
                'frames': count,
                'time_seconds': round(elapsed, 2),
                'frames_data': [f.to_dict() if hasattr(f, 'to_dict') else str(f) for f in frames[:10]]
            }
            results['summary']['basic_extractor']['total_time'] += elapsed
            results['summary']['basic_extractor']['total_frames'] += count
            print(f"    → {count} frames in {elapsed:.1f}s")
        except Exception as e:
            print(f"    ERROR: {e}")
            paper_result['basic_extractor'] = {'error': str(e)}
        
        results['papers'].append(paper_result)
    
    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")
    print(f"Papers processed: {len(results['papers'])}")
    print(f"\nSentenceFrameExtractor (unit-context):")
    print(f"  Total frames: {results['summary']['sentence_extractor']['total_frames']}")
    print(f"  Total time: {results['summary']['sentence_extractor']['total_time']:.1f}s")
    print(f"\nBasicFrameExtractor (whole doc):")
    print(f"  Total frames: {results['summary']['basic_extractor']['total_frames']}")
    print(f"  Total time: {results['summary']['basic_extractor']['total_time']:.1f}s")
    print(f"\nResults saved to: {output_path}")
    
    return 0


if __name__ == '__main__':
    exit(main())
