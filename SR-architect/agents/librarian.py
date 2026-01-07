#!/usr/bin/env python3
"""
Librarian Agent for Systematic Review - PubMed Search.

Fetches papers from PubMed and returns structured results for the Orchestrator.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import json
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.prisma_state import Paper, PaperStatus, SearchStrategy
from core.utils import load_env, make_request, get_logger


class LibrarianAgent:
    """
    Librarian Agent for fetching papers from PubMed.
    
    Uses the NCBI E-utilities API to search and fetch paper metadata.
    """
    
    PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    
    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Librarian agent.
        
        Args:
            email: Email for NCBI API (recommended)
            api_key: NCBI API key for higher rate limits
        """
        load_env()
        self.logger = get_logger("LibrarianAgent")
        
        self.email = email or os.getenv("NCBI_EMAIL", "researcher@example.com")
        self.api_key = api_key or os.getenv("NCBI_API_KEY")

        if not self.email:
             self.logger.warning("No email provided for NCBI API. Rate limits may be lower.")
    
    def search_pubmed(
        self,
        query: str,
        max_results: int = 100,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search PubMed and return PMIDs.
        
        Args:
            query: Boolean search string
            max_results: Maximum papers to retrieve
            date_from: Start date (YYYY/MM/DD)
            date_to: End date (YYYY/MM/DD)
            
        Returns:
            Dict with PMIDs and search metadata
        """
        try:
            import requests
        except ImportError:
            self.logger.error("requests not installed")
            raise ImportError("requests not installed. Run: pip install requests")
        
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        }
        
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        if date_from:
            params["mindate"] = date_from
        if date_to:
            params["maxdate"] = date_to
            params["datetype"] = "pdat"  # Publication date
        
        response = make_request(self.PUBMED_ESEARCH, params=params)
        
        data = response.json()
        result = data.get("esearchresult", {})
        
        count = int(result.get("count", 0))
        pmids = result.get("idlist", [])
        
        self.logger.info(f"PubMed search yielded {count} total results. Retrieving top {len(pmids)}.")
        
        return {
            "pmids": pmids,
            "count": count,
            "query_translation": result.get("querytranslation", query),
            "search_date": datetime.now().isoformat(),
        }
    
    def fetch_paper_details(self, pmids: List[str]) -> List[Paper]:
        """
        Fetch detailed metadata for papers by PMID.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of Paper objects
        """
        if not pmids:
            return []
        
        papers = []
        
        # Process in batches of 100
        batch_size = 100
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            
            params = {
                "db": "pubmed",
                "id": ",".join(batch),
                "retmode": "xml",
            }
            
            if self.email:
                params["email"] = self.email
            if self.api_key:
                params["api_key"] = self.api_key
            
            try:
                response = make_request(self.PUBMED_EFETCH, params=params)
                
                # Parse XML
                root = ET.fromstring(response.text)
                
                for article in root.findall(".//PubmedArticle"):
                    paper = self._parse_article(article)
                    if paper:
                        papers.append(paper)
            except Exception as e:
                self.logger.error(f"Failed to fetch batch details: {e}")
        
        return papers
    
    def _parse_article(self, article: ET.Element) -> Optional[Paper]:
        """Parse a single PubmedArticle XML element."""
        try:
            # Get PMID
            pmid_elem = article.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else None
            if not pmid:
                return None
            
            # Get title
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else "No title"
            
            # Get abstract
            abstract_parts = article.findall(".//AbstractText")
            abstract = " ".join(
                (a.text or "") for a in abstract_parts
            ) if abstract_parts else ""
            
            # Get authors
            authors = []
            for author in article.findall(".//Author"):
                last = author.find("LastName")
                fore = author.find("ForeName")
                if last is not None:
                    name = last.text
                    if fore is not None:
                        name = f"{last.text} {fore.text[0]}"
                    authors.append(name)
            
            # Get journal
            journal_elem = article.find(".//Journal/Title")
            journal = journal_elem.text if journal_elem is not None else "Unknown"
            
            # Get year
            year_elem = article.find(".//PubDate/Year")
            try:
                year = int(year_elem.text) if year_elem is not None else 0
            except ValueError:
                # Fallback for dates like "2023 Dec"
                year = 0
                if year_elem and year_elem.text:
                    parts = year_elem.text.split()
                    if parts and parts[0].isdigit():
                        year = int(parts[0])
            
            # Get DOI
            doi = None
            for artid in article.findall(".//ArticleId"):
                if artid.get("IdType") == "doi":
                    doi = artid.text
                    break
            
            # Sanitization
            if abstract == "No abstract available":
                abstract = ""

            return Paper(
                pmid=pmid,
                doi=doi,
                title=title,
                authors=", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""),
                journal=journal,
                year=year,
                abstract=abstract,
                status=PaperStatus.PENDING.value,
                exclusion_reason=None,
                exclusion_notes=None,
                source_database="PubMed",
                retrieved_date=datetime.now().strftime("%Y-%m-%d"),
            )
        
        except Exception as e:
            self.logger.warning(f"Failed to parse article: {e}")
            return None
    
    def run_search(
        self,
        query: str,
        max_results: int = 100,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Tuple[List[Paper], SearchStrategy]:
        """
        Complete search workflow: search + fetch details.
        
        Args:
            query: Boolean search string
            max_results: Maximum papers
            date_from: Start date
            date_to: End date
            
        Returns:
            Tuple of (papers list, search strategy log)
        """
        # Search
        self.logger.info(f"Searching PubMed: {query[:50]}...")
        search_result = self.search_pubmed(query, max_results, date_from, date_to)
        
        pmids = search_result["pmids"]
        self.logger.info(f"Found {len(pmids)} papers")
        
        # Fetch details
        papers = self.fetch_paper_details(pmids)
        self.logger.info(f"Retrieved metadata for {len(papers)} papers")
        
        # Create search strategy log
        strategy = SearchStrategy(
            database="PubMed",
            search_date=search_result["search_date"],
            search_string=search_result["query_translation"],
            filters_applied=[],
            results_count=len(papers),
        )
        
        return papers, strategy


def build_pico_query(
    population: str,
    intervention: str,
    outcome: str,
    comparator: Optional[str] = None,
) -> str:
    """
    Build a PubMed Boolean query from PICO elements.
    """
    parts = []
    
    # Population
    pop_terms = population.split(",")
    pop_query = " OR ".join(f'"{t.strip()}"[MeSH] OR "{t.strip()}"[tiab]' for t in pop_terms)
    parts.append(f"({pop_query})")
    
    # Intervention
    int_terms = intervention.split(",")
    int_query = " OR ".join(f'"{t.strip()}"[MeSH] OR "{t.strip()}"[tiab]' for t in int_terms)
    parts.append(f"({int_query})")
    
    # Outcome
    out_terms = outcome.split(",")
    out_query = " OR ".join(f'"{t.strip()}"[tiab]' for t in out_terms)
    parts.append(f"({out_query})")
    
    return " AND ".join(parts)


if __name__ == "__main__":
    # Demo search
    librarian = LibrarianAgent()
    
    # Build query
    query = build_pico_query(
        population="ICU patients, critical care",
        intervention="bowel protocol, laxative, prophylactic",
        outcome="constipation, bowel movement",
    )
    
    print(f"Query: {query}\n")
    
    # Run search (limited for demo)
    try:
        papers, strategy = librarian.run_search(query, max_results=10)
        
        print(f"\nSearch Strategy:")
        print(f"  Database: {strategy['database']}")
        print(f"  Date: {strategy['search_date']}")
        print(f"  Results: {strategy['results_count']}")
        
        print(f"\nFirst 3 papers:")
        for p in papers[:3]:
            # Simple print for CLI demo output, agent uses logging internally
            print(f"  - PMID:{p['pmid']}: {p['title'][:60]}...")
            print(f"    {p['authors']}, {p['journal']} ({p['year']})")
    
    except Exception as e:
        print(f"Demo search failed (expected if no internet): {e}")
