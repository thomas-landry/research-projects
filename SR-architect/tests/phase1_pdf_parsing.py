#!/usr/bin/env python3
"""
Phase 1 Test: PDF Parsing
Tests if Docling can successfully parse PDFs from the DPM collection.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.parser import DocumentParser

def test_pdf_parsing():
    """Test parsing multiple PDFs to find which ones work."""
    
    papers_dir = Path(__file__).parent.parent.parent / "DPM-systematic-review" / "papers"
    
    if not papers_dir.exists():
        print(f"❌ Papers directory not found: {papers_dir}")
        return
    
    pdf_files = list(papers_dir.glob("*.pdf"))[:5]  # Test first 5
    
    print(f"Testing {len(pdf_files)} PDFs...\n")
    
    parser = DocumentParser()
    successful = []
    failed = []
    
    for pdf_path in pdf_files:
        print(f"📄 Testing: {pdf_path.name[:60]}...")
        
        try:
            doc = parser.parse_pdf(str(pdf_path))
            chunks = len(doc.chunks)
            text_len = len(doc.full_text)
            
            if chunks > 0 and text_len > 100:
                print(f"  ✅ SUCCESS: {chunks} chunks, {text_len} chars")
                successful.append(pdf_path.name)
            else:
                print(f"  ⚠️  PARSED BUT EMPTY: {chunks} chunks, {text_len} chars")
                failed.append((pdf_path.name, "Empty content"))
                
        except Exception as e:
            print(f"  ❌ FAILED: {str(e)[:100]}")
            failed.append((pdf_path.name, str(e)[:100]))
        
        print()
    
    # Summary
    print("=" * 70)
    print(f"\n✅ Successful: {len(successful)}/{len(pdf_files)}")
    for name in successful:
        print(f"  - {name[:60]}")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(pdf_files)}")
        for name, error in failed:
            print(f"  - {name[:40]}: {error[:30]}")
    
    return successful, failed


if __name__ == "__main__":
    successful, failed = test_pdf_parsing()
    
    if not successful:
        print("\n⚠️  WARNING: No PDFs parsed successfully!")
        print("This indicates a problem with Docling or the PDF files themselves.")
        sys.exit(1)
    else:
        print(f"\n✅ {len(successful)} PDFs ready for extraction testing")
        sys.exit(0)
