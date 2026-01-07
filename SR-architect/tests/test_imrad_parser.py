
import unittest
from core.imrad_parser import IMRADParser

class TestIMRADParser(unittest.TestCase):
    def setUp(self):
        self.parser = IMRADParser()

    def test_standard_headers(self):
        text = """
        ABSTRACT
        This is the abstract.
        
        1. INTRODUCTION
        Background info here.
        
        2. METHODS
        We used X and Y.
        
        3. RESULTS
        We found Z.
        
        4. DISCUSSION
        This means A.
        
        5. REFERENCES
        Ref 1.
        """
        sections = self.parser.parse(text)
        
        self.assertIn("This is the abstract", sections["abstract"])
        self.assertIn("Background info here", sections["introduction"])
        self.assertIn("We used X and Y", sections["methods"])
        self.assertIn("We found Z", sections["results"])
        self.assertIn("This means A", sections["discussion"])

    def test_varied_headers(self):
        text = """
        Background
        Some context.
        
        Materials and Methods
        Study design details.
        
        Findings
        Data points.
        
        Conclusion
        Final thoughts.
        """
        sections = self.parser.parse(text)
        
        self.assertIn("Some context", sections["introduction"])
        self.assertIn("Study design details", sections["methods"])
        self.assertIn("Data points", sections["results"])
        self.assertIn("Final thoughts", sections["discussion"])

    def test_clinical_case_report_mapping(self):
        # Case reports often use "Case Presentation" which maps to Results
        text = """
        Introduction
        Rare disease.
        
        Case Presentation
        A 52-year-old female...
        
        Discussion
        Rare case indeed.
        """
        sections = self.parser.parse(text)
        self.assertIn("A 52-year-old female", sections["results"])

    def test_fallback_uncategorized(self):
        text = """
        Just some text without headers.
        More text.
        """
        sections = self.parser.parse(text)
        self.assertIn("Just some text", sections["uncategorized"])
        self.assertEqual(sections["results"], "")

    def test_context_construction(self):
        sections = {
            "abstract": "Abs",
            "introduction": "Intro",
            "methods": "Meth",
            "results": "Res",
            "discussion": "Disc",
            "uncategorized": ""
        }
        context = self.parser.get_extraction_context(sections)
        # Order should be Abs -> Res -> Meth -> Disc
        self.assertTrue(context.index("ABSTRACT") < context.index("RESULTS"))
        self.assertTrue(context.index("RESULTS") < context.index("METHODS"))
        self.assertTrue(context.index("METHODS") < context.index("DISCUSSION"))
