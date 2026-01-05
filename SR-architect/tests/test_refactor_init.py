#!/usr/bin/env python3
"""
Verification script for SR-Architect refactoring.
Tests initialization of core components using the new shared utils.
"""
import sys
import os
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from core.extractor import StructuredExtractor
    from core.extraction_checker import ExtractionChecker
    from agents.screener import ScreenerAgent, PICOCriteria
    print("✅ Imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

def test_initialization():
    print("\nTesting Component Initialization:")
    
    # 1. Extractor
    try:
        extractor = StructuredExtractor(api_key="test-key")
        # Trigger client init (which uses core.utils)
        # We expect this to work (create the object) but maybe fail 
        # actual API calls if we don't have a real key, but here we just want to see
        # if the import and property access logic holds up without crashing on imports.
        _ = extractor.client 
        print("✅ StructuredExtractor initialized")
    except Exception as e:
        print(f"❌ StructuredExtractor failed: {e}")

    # 2. Checker
    try:
        checker = ExtractionChecker(api_key="test-key")
        _ = checker.client
        print("✅ ExtractionChecker initialized")
    except Exception as e:
        print(f"❌ ExtractionChecker failed: {e}")

    # 3. Screener
    try:
        pico = PICOCriteria(
            population="A", intervention="B", comparator="C", outcome="D", 
            study_design="RCT", language="en", date_range="2000+", excluded_types=[]
        )
        screener = ScreenerAgent(pico_criteria=pico)
        # Screener doesn't take api_key in init, uses env. 
        # We might need to mock env for this test to pass get_llm_client validation
        os.environ["OPENROUTER_API_KEY"] = "test-env-key"
        _ = screener.client
        print("✅ ScreenerAgent initialized")
    except Exception as e:
        print(f"❌ ScreenerAgent failed: {e}")

if __name__ == "__main__":
    test_initialization()
