"""
PubMed Fetcher for metadata enrichment.
Fetches article metadata from PubMed/NCBI APIs.
"""
import time
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

import requests

from core.utils import get_logger

logger = get_logger("PubMedFetcher")

# API endpoints
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


@dataclass
class PubMedArticle:
    """PubMed article metadata."""
    pmid: str
    title: str = ""
    authors: str = ""
    journal: str = ""
    pub_date: str = ""
    doi: str = ""
    abstract: str = ""
    mesh_terms: list = None
    
    def __post_init__(self):
        if self.mesh_terms is None:
            self.mesh_terms = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pmid": self.pmid,
            "title": self.title,
            "authors": self.authors,
            "journal": self.journal,
            "pub_date": self.pub_date,
            "doi": self.doi,
            "abstract": self.abstract,
            "mesh_terms": self.mesh_terms,
        }


class PubMedFetcher:
    """
    Fetches metadata from PubMed for enriching parsed documents.
    Includes rate limiting and caching.
    """
    
    def __init__(
        self, 
        cache_dir: str = ".cache/pubmed",
        rate_limit_delay: float = 0.34,  # ~3 requests/second (NCBI guideline)
        api_key: Optional[str] = None,  # Optional NCBI API key for higher limits
    ):
        """
        Initialize fetcher.
        
        Args:
            cache_dir: Directory for caching responses
            rate_limit_delay: Seconds between requests
            api_key: Optional NCBI API key
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit_delay = rate_limit_delay
        self.api_key = api_key
        self._last_request_time = 0.0
        
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()
    
    def _get_cache_path(self, pmid: str) -> Path:
        """Get cache file path for a PMID."""
        return self.cache_dir / f"{pmid}.json"
    
    def _load_from_cache(self, pmid: str) -> Optional[PubMedArticle]:
        """Load article from cache if available."""
        cache_path = self._get_cache_path(pmid)
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    return PubMedArticle(**data)
            except Exception as e:
                logger.warning(f"Cache load failed for PMID {pmid}: {e}")
        return None
    
    def _save_to_cache(self, article: PubMedArticle):
        """Save article to cache."""
        cache_path = self._get_cache_path(article.pmid)
        try:
            with open(cache_path, 'w') as f:
                json.dump(article.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Cache save failed for PMID {article.pmid}: {e}")
    
    def fetch_by_pmid(self, pmid: str) -> Optional[PubMedArticle]:
        """
        Fetch article metadata by PMID.
        
        Args:
            pmid: PubMed ID
            
        Returns:
            PubMedArticle or None if not found
        """
        # Check cache first
        cached = self._load_from_cache(pmid)
        if cached:
            logger.debug(f"Loaded PMID {pmid} from cache")
            return cached
        
        # Rate limit
        self._rate_limit()
        
        try:
            # Fetch summary
            params = {
                "db": "pubmed",
                "id": pmid,
                "retmode": "json",
            }
            if self.api_key:
                params["api_key"] = self.api_key
                
            response = requests.get(PUBMED_SUMMARY_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response
            result = data.get("result", {})
            article_data = result.get(pmid, {})
            
            if not article_data or "error" in article_data:
                logger.warning(f"PMID {pmid} not found")
                return None
            
            # Extract fields
            authors_list = article_data.get("authors", [])
            authors = ", ".join([a.get("name", "") for a in authors_list[:5]])
            if len(authors_list) > 5:
                authors += " et al."
            
            article = PubMedArticle(
                pmid=pmid,
                title=article_data.get("title", ""),
                authors=authors,
                journal=article_data.get("source", ""),
                pub_date=article_data.get("pubdate", ""),
                doi=next((id_obj.get("value", "") for id_obj in article_data.get("articleids", []) 
                         if id_obj.get("idtype") == "doi"), ""),
            )
            
            # Cache result
            self._save_to_cache(article)
            logger.info(f"Fetched PMID {pmid}: {article.title[:50]}...")
            
            return article
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch PMID {pmid}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing PMID {pmid}: {e}")
            return None
    
    def search_by_title(self, title: str, max_results: int = 5) -> list:
        """
        Search PubMed by title.
        
        Args:
            title: Article title to search
            max_results: Maximum results to return
            
        Returns:
            List of PMIDs
        """
        self._rate_limit()
        
        try:
            params = {
                "db": "pubmed",
                "term": f"{title}[Title]",
                "retmax": max_results,
                "retmode": "json",
            }
            if self.api_key:
                params["api_key"] = self.api_key
                
            response = requests.get(PUBMED_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            pmids = data.get("esearchresult", {}).get("idlist", [])
            
            logger.debug(f"Search '{title[:30]}...' returned {len(pmids)} results")
            return pmids
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def enrich_document(self, doc: "ParsedDocument", pmid: Optional[str] = None) -> "ParsedDocument":
        """
        Enrich a parsed document with PubMed metadata.
        
        Args:
            doc: ParsedDocument to enrich
            pmid: Optional PMID. If not provided, will search by filename.
            
        Returns:
            Enriched ParsedDocument (modifies metadata in place)
        """
        # Try to find PMID
        if not pmid:
            # Search by filename (often contains author/year)
            search_term = doc.filename.replace(".pdf", "").replace("_", " ")
            pmids = self.search_by_title(search_term, max_results=1)
            if pmids:
                pmid = pmids[0]
        
        if not pmid:
            logger.debug(f"No PMID found for {doc.filename}")
            return doc
        
        # Fetch metadata
        article = self.fetch_by_pmid(pmid)
        if article:
            doc.metadata["pubmed"] = article.to_dict()
            logger.info(f"Enriched {doc.filename} with PubMed metadata")
        
        return doc
