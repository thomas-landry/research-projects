"""
Document parser manager that orchestrates parsing strategies and caching.
"""
import json
import hashlib
from pathlib import Path
from typing import Optional

from ..config import settings
from ..utils import get_logger
from .base import ParsedDocument
from .docling import DoclingParser
from .fallbacks import PyMuPDFParser, PDFPlumberParser, TextParser, simple_chunk
from ..complexity_classifier import ComplexityClassifier

logger = get_logger("DocumentParser")

class DocumentParser:
    """Parse academic documents with caching and fallback strategies."""
    
    # Simplified parser chain: Docling → PyMuPDF only (preferred)
    PARSER_CHAIN = ["docling", "pymupdf"]
    
    def __init__(
        self, 
        use_ocr: bool = False, 
        cache_dir: str = ".cache/parsed_docs",
        use_imrad: bool = False,
        extract_tables: bool = True,
        max_cache_size: int = None,
    ):
        """
        Initialize the parser manager.
        """
        self.use_ocr = use_ocr
        self.cache_dir = Path(cache_dir)
        self.use_imrad = use_imrad
        self.extract_tables = extract_tables
        if max_cache_size is None:
            max_cache_size = settings.PARSER_CACHE_MAX_SIZE
        self.max_cache_size = max_cache_size
        self.logger = logger
        
        self._docling_parser = DoclingParser()
        self._pymupdf_parser = PyMuPDFParser()
        self._pdfplumber_parser = PDFPlumberParser(extract_tables=extract_tables)
        self._text_parser = TextParser()
        self._imrad_parser = None
        self.classifier = ComplexityClassifier()
        
        # Ensure cache directory exists
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Evict old cache entries if over limit
        self._evict_cache_if_needed()
        
        # Lazy-load IMRAD parser if enabled
        if self.use_imrad:
            try:
                from ..imrad_parser import IMRADParser
                self._imrad_parser = IMRADParser()
            except ImportError:
                self.logger.warning("IMRADParser not available")
    
    def _evict_cache_if_needed(self):
        """Evict oldest cache entries if over max_cache_size limit."""
        if not self.cache_dir.exists():
            return
            
        cache_files = list(self.cache_dir.glob("*.json"))
        if len(cache_files) <= self.max_cache_size:
            return
            
        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda f: f.stat().st_mtime)
        
        # Evict oldest entries
        to_evict = len(cache_files) - self.max_cache_size
        for cache_file in cache_files[:to_evict]:
            try:
                cache_file.unlink()
                self.logger.debug(f"Evicted cache entry: {cache_file.name}")
            except Exception as e:
                self.logger.warning(f"Failed to evict cache {cache_file}: {e}")
    
    def _get_cache_path(self, file_path: Path) -> Path:
        """Generate a unique cache path based on file content hash."""
        stat = file_path.stat()
        key = f"{str(file_path)}_{stat.st_mtime}_{stat.st_size}"
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.json"
        
    def _load_cached(self, file_path: Path) -> Optional[ParsedDocument]:
        """Try to load parsed document from cache (JSON)."""
        cache_path = self._get_cache_path(file_path)
        if cache_path.exists():
            try:
                self.logger.debug(f"Loading cached parse for {file_path.name}")
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return ParsedDocument(**data)
            except Exception as e:
                self.logger.warning(f"Cache load failed for {file_path}: {e}")
        return None
        
    def _save_to_cache(self, doc: ParsedDocument, file_path: Path):
        """Save parsed document to cache as JSON."""
        try:
            cache_path = self._get_cache_path(file_path)
            # Use atomic write via temp file
            temp_path = cache_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(doc.model_dump(), f, indent=2)
            temp_path.replace(cache_path)
            self.logger.debug(f"Saved parse for {file_path.name} to cache")
        except Exception as e:
            self.logger.error(f"Cache save failed for {file_path}: {e}")

    def parse_pdf(self, pdf_path: str) -> ParsedDocument:
        """Parse a single PDF file with fallbacks."""
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
        # Check cache first
        cached_doc = self._load_cached(path)
        if cached_doc:
            return cached_doc
        
        # 1. Fast Path: Always try PyMuPDF first (Scanner)
        try:
            parsed_doc = self._pymupdf_parser.parse(path)
            self.logger.debug(f"Initial scan with PyMuPDF successful for {path.name}")
        except (ImportError, Exception) as e:
            self.logger.warning(f"PyMuPDF scan failed: {e}. Defaulting to Docling.")
            parsed_doc = None

        # 2. Check Complexity & Upgrade if needed
        used_docling = False
        if parsed_doc:
            try:
                # Classify complexity
                strategy = self.classifier.get_parser_strategy(parsed_doc)
                primary_parser = strategy.get("primary", "pymupdf")
                
                # Upgrade to Docling if recommended
                if primary_parser == "docling":
                    self.logger.info(f"Complexity Upgrade: Re-parsing {path.name} with Docling (Strategy: {strategy})")
                    try:
                        parsed_doc = self._docling_parser.parse(path)
                        used_docling = True
                    except Exception as e:
                        self.logger.error(f"Docling upgrade failed: {e}. Keeping PyMuPDF result.")
            except Exception as e:
                self.logger.warning(f"Complexity classification failed: {e}")

        # 3. Fallback: If PyMuPDF failed initially or we haven't succeeded yet
        if not parsed_doc and not used_docling:
            try:
                parsed_doc = self._docling_parser.parse(path)
            except Exception as e:
                self.logger.error(f"Docling fallback failed: {e}")
                
                # Ultimate fallback if we haven't tried PyMuPDF yet (e.g. init failure)
                # But logic above guarantees we tried PyMuPDF first.
                # Just raise error if nothing worked.
                raise RuntimeError(f"Failed to parse {pdf_path}: all strategies failed")
        
        # Post-processing: IMRAD parsing
        if parsed_doc and self._imrad_parser and self.use_imrad:
            try:
                imrad_sections = self._imrad_parser.parse(parsed_doc.full_text)
                parsed_doc.metadata["imrad_sections"] = imrad_sections
                self.logger.debug("Applied IMRAD section parsing")
            except Exception as e:
                self.logger.warning(f"IMRAD parsing failed: {e}")
            
        # Save to cache
        if parsed_doc:
            self._save_to_cache(parsed_doc, path)
            
        return parsed_doc

    def parse_file(self, file_path: str) -> ParsedDocument:
        """Parse a file based on its extension."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        ext = path.suffix.lower()
        
        if ext == ".pdf":
            return self.parse_pdf(file_path)
        elif ext == ".txt":
            parsed_doc = self._text_parser.parse(path)
            # Save to cache also for txt files?
            self._save_to_cache(parsed_doc, path)
            return parsed_doc
            
        raise ValueError(f"Unsupported file extension: {ext}")
