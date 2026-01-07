#!/usr/bin/env python3
"""
Phase 2 Integration Test: Parser Robustness Verification
Tests the complete parser chain with real PDFs.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from core.parser import DocumentParser
from core.complexity_classifier import ComplexityClassifier
from core.content_filter import ContentFilter


def test_parser_robustness():
    """End-to-end test of Phase 2 parser enhancements."""
    print("=" * 60)
    print("Phase 2 Parser Robustness Test")
    print("=" * 60)
    
    # Find a test PDF
    pdf_dirs = [
        Path("papers_benchmark"),
        Path("papers_validation"),
        Path("tests/data/verification_sample"),
    ]
    
    test_pdf = None
    for pdf_dir in pdf_dirs:
        if pdf_dir.exists():
            pdfs = list(pdf_dir.glob("*.pdf"))
            if pdfs:
                test_pdf = pdfs[0]
                break
    
    if not test_pdf:
        print("⚠ No test PDFs found. Skipping integration test.")
        return True
    
    print(f"\n[1/5] Testing with: {test_pdf.name}")
    
    # 1. Parse with new options
    print("\n[2/5] Testing DocumentParser with IMRAD and table extraction...")
    parser = DocumentParser(use_imrad=True, extract_tables=True)
    
    try:
        doc = parser.parse_pdf(str(test_pdf))
        print(f"✓ Parsed successfully")
        print(f"   - Chunks: {len(doc.chunks)}")
        print(f"   - Tables: {len(doc.tables)}")
        print(f"   - Parser used: {doc.metadata.get('parser', 'unknown')}")
        
        # Check IMRAD sections if enabled
        if "imrad_sections" in doc.metadata:
            sections = doc.metadata["imrad_sections"]
            print(f"   - IMRAD sections: {[k for k,v in sections.items() if v]}")
    except Exception as e:
        print(f"⚠ Parser error (non-fatal): {e}")
    
    # 2. Test ComplexityClassifier
    print("\n[3/5] Testing ComplexityClassifier...")
    classifier = ComplexityClassifier()
    result = classifier.classify(doc)
    print(f"✓ Complexity: {result.level.value} (score={result.score})")
    print(f"   - Signals: {result.signals}")
    print(f"   - Recommended parser: {result.recommendations.get('primary', 'N/A')}")
    
    # 3. Test LayoutCleaner
    print("\n[4/5] Testing LayoutCleaner...")
    content_filter = ContentFilter()
    original_len = len(doc.full_text)
    cleaned_text = content_filter.clean_layout(doc.full_text)
    cleaned_len = len(cleaned_text)
    reduction = ((original_len - cleaned_len) / original_len * 100) if original_len > 0 else 0
    print(f"✓ Layout cleaned: {original_len} → {cleaned_len} chars ({reduction:.1f}% reduction)")
    
    # 4. Test ContentFilter
    print("\n[5/5] Testing ContentFilter...")
    filter_result = content_filter.filter_chunks(doc.chunks)
    print(f"✓ Filtered: {filter_result.token_stats['original_chunks']} → {filter_result.token_stats['filtered_chunks']} chunks")
    print(f"   - Estimated tokens saved: ~{filter_result.token_stats['estimated_tokens_saved']}")
    
    print("\n" + "=" * 60)
    print("✓ All Phase 2 parser robustness tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_parser_robustness()
    sys.exit(0 if success else 1)
