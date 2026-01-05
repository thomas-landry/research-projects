#!/usr/bin/env python3
"""
Phase 2 Test: Content Filter
Tests token optimization and section filtering.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.parser import DocumentParser
from core.content_filter import ContentFilter

def test_content_filter():
    """Test content filtering on a successfully parsed PDF."""
   
    papers_dir = Path(__file__).parent.parent.parent / "DPM-systematic-review" / "papers"
    
    # Use a PDF we know works from Phase 1
    test_pdf = papers_dir / "Luvison et al. - 2013 - Pulmonary meningothelial-like nodules are of donor origin in lung allografts.pdf"
    
    print(f"Testing content filter on: {test_pdf.name[:60]}...\n")
    
    try:
        # Parse PDF
        parser = DocumentParser()
        print("📄 Parsing PDF...")
        doc = parser.parse_pdf(str(test_pdf))
        print(f"  ✅ Parsed: {len(doc.chunks)} chunks\n")
        
        # Test content filter
        filter = ContentFilter()
        print("🔍 Applying content filter...")
        result = filter.filter_chunks(doc.chunks)
        
        # Display results
        stats = result.token_stats
        print(f"  Original chunks: {stats['original_chunks']}")
        print(f"  Filtered chunks: {stats['filtered_chunks']}")
        print(f"  Removed chunks: {stats['removed_chunks']}")
        print(f"  Token reduction: {stats['reduction_percentage']}%")
        print(f"  Est. tokens saved: {stats['estimated_tokens_saved']}")
        
        # Check if any sections were removed
        if result.removed_chunks:
            print(f"\n📋 Removed sections:")
            removed_sections = set(c.section for c in result.removed_chunks if c.section)
            for section in list(removed_sections)[:5]:
                print(f"  - {section}")
        
        # Validate results
        assert stats['filtered_chunks'] > 0, "All chunks were filtered out!"
        assert stats['original_chunks'] >= stats['filtered_chunks'], "Logic error: more filtered than original"
        
        print("\n✅ Content filter test PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ Content filter test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_content_filter()
    sys.exit(0 if success else 1)
