#!/usr/bin/env python3
"""
Extraction Evaluator - Comprehensive accuracy assessment for data extraction.

Provides multi-tier metrics:
- Tier 1: Exact match (normalized string equality)
- Tier 2: Key term match (domain-specific clinical terms)
- Tier 3: Semantic similarity (fuzzy matching)
- Tier 4: Presence check (non-empty content)

Also provides:
- Field-level breakdown
- Error classification (Missing, Wrong, Partial, Excess, Format)
- Clinical Accuracy Score (weighted by field importance)
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from difflib import SequenceMatcher


class ErrorType(Enum):
    """Classification of extraction errors."""
    NONE = "correct"
    MISSING = "missing"      # Field empty when gold has data
    WRONG = "wrong"          # Completely different value
    PARTIAL = "partial"      # Correct but incomplete
    EXCESS = "excess"        # Correct + extra incorrect info
    FORMAT = "format"        # Correct data, wrong presentation


@dataclass
class FieldEvaluation:
    """Evaluation result for a single field."""
    field_name: str
    gold_value: str
    extracted_value: str
    
    # Tier scores
    exact_match: bool = False
    key_term_match: bool = False
    semantic_match: bool = False
    is_present: bool = False
    
    # Scores
    similarity_score: float = 0.0
    key_term_score: float = 0.0
    
    # Error analysis
    error_type: ErrorType = ErrorType.NONE
    error_detail: str = ""
    
    # Metadata
    weight: float = 1.0
    matched_terms: List[str] = field(default_factory=list)
    missing_terms: List[str] = field(default_factory=list)


@dataclass
class DocumentEvaluation:
    """Evaluation result for a single document."""
    document_name: str
    field_evaluations: List[FieldEvaluation]
    
    @property
    def exact_match_rate(self) -> float:
        if not self.field_evaluations:
            return 0.0
        return sum(1 for f in self.field_evaluations if f.exact_match) / len(self.field_evaluations)
    
    @property
    def key_term_rate(self) -> float:
        if not self.field_evaluations:
            return 0.0
        return sum(1 for f in self.field_evaluations if f.key_term_match) / len(self.field_evaluations)
    
    @property
    def semantic_rate(self) -> float:
        if not self.field_evaluations:
            return 0.0
        return sum(1 for f in self.field_evaluations if f.semantic_match) / len(self.field_evaluations)
    
    @property
    def completeness_rate(self) -> float:
        if not self.field_evaluations:
            return 0.0
        return sum(1 for f in self.field_evaluations if f.is_present) / len(self.field_evaluations)
    
    @property
    def clinical_accuracy_score(self) -> float:
        """Weighted accuracy score based on field importance."""
        if not self.field_evaluations:
            return 0.0
        
        total_weight = sum(f.weight for f in self.field_evaluations)
        weighted_correct = sum(
            f.weight for f in self.field_evaluations 
            if f.semantic_match or f.key_term_match
        )
        return weighted_correct / total_weight if total_weight > 0 else 0.0


@dataclass
class ModelEvaluation:
    """Evaluation results for a model across all documents."""
    model_name: str
    document_evaluations: List[DocumentEvaluation]
    processing_time: float = 0.0
    
    @property
    def avg_exact_match(self) -> float:
        if not self.document_evaluations:
            return 0.0
        return sum(d.exact_match_rate for d in self.document_evaluations) / len(self.document_evaluations)
    
    @property  
    def avg_key_term_match(self) -> float:
        if not self.document_evaluations:
            return 0.0
        return sum(d.key_term_rate for d in self.document_evaluations) / len(self.document_evaluations)
    
    @property
    def avg_semantic_match(self) -> float:
        if not self.document_evaluations:
            return 0.0
        return sum(d.semantic_rate for d in self.document_evaluations) / len(self.document_evaluations)
    
    @property
    def avg_completeness(self) -> float:
        if not self.document_evaluations:
            return 0.0
        return sum(d.completeness_rate for d in self.document_evaluations) / len(self.document_evaluations)
    
    @property
    def avg_clinical_accuracy(self) -> float:
        if not self.document_evaluations:
            return 0.0
        return sum(d.clinical_accuracy_score for d in self.document_evaluations) / len(self.document_evaluations)
    
    def get_field_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get per-field statistics across all documents."""
        field_stats = {}
        
        for doc_eval in self.document_evaluations:
            for field_eval in doc_eval.field_evaluations:
                name = field_eval.field_name
                if name not in field_stats:
                    field_stats[name] = {
                        "exact": 0, "terms": 0, "semantic": 0, "present": 0, "total": 0,
                        "errors": {"missing": 0, "wrong": 0, "partial": 0, "excess": 0, "format": 0}
                    }
                
                stats = field_stats[name]
                stats["total"] += 1
                if field_eval.exact_match:
                    stats["exact"] += 1
                if field_eval.key_term_match:
                    stats["terms"] += 1
                if field_eval.semantic_match:
                    stats["semantic"] += 1
                if field_eval.is_present:
                    stats["present"] += 1
                
                if field_eval.error_type != ErrorType.NONE:
                    error_key = field_eval.error_type.value
                    if error_key in stats["errors"]:
                        stats["errors"][error_key] += 1
        
        return field_stats
    
    def get_error_examples(self, max_examples: int = 5) -> List[Dict[str, Any]]:
        """Get examples of extraction errors."""
        examples = []
        
        for doc_eval in self.document_evaluations:
            for field_eval in doc_eval.field_evaluations:
                if field_eval.error_type != ErrorType.NONE and len(examples) < max_examples:
                    examples.append({
                        "document": doc_eval.document_name,
                        "field": field_eval.field_name,
                        "error_type": field_eval.error_type.value.upper(),
                        "gold": field_eval.gold_value,
                        "extracted": field_eval.extracted_value,
                        "detail": field_eval.error_detail,
                    })
        
        return examples


class ExtractionEvaluator:
    """
    Evaluates extraction accuracy against gold standard data.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize evaluator.
        
        Args:
            config_path: Path to YAML config. Uses default if not provided.
        """
        self.config_path = config_path or Path(__file__).parent / "gold_standards" / "evaluation_config.yaml"
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load evaluation configuration."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        
        # Default config
        return {
            "field_weights": {},
            "key_terms": {},
            "aliases": {},
            "thresholds": {"semantic_similarity": 0.5, "key_term_ratio": 0.3},
            "error_patterns": {"missing": ["", "not reported", "NR", "N/A"]},
        }
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        text = str(text).lower().strip()
        text = re.sub(r'[^\w\s]', ' ', text)
        return ' '.join(text.split())
    
    def check_exact_match(self, gold: str, extracted: str) -> bool:
        """Check if normalized strings match exactly."""
        return self.normalize_text(gold) == self.normalize_text(extracted)
    
    def check_key_terms(self, gold: str, extracted: str, field_name: str) -> Tuple[bool, float, List[str], List[str]]:
        """
        Check if key clinical terms are present.
        
        Returns:
            (match, score, matched_terms, missing_terms)
        """
        key_terms = self.config.get("key_terms", {}).get(field_name, [])
        
        if not key_terms:
            # No key terms defined for this field, check if gold terms appear
            gold_tokens = set(self.normalize_text(gold).split())
            ext_tokens = set(self.normalize_text(extracted).split())
            
            if not gold_tokens:
                return True, 1.0, [], []
            
            matched = gold_tokens & ext_tokens
            score = len(matched) / len(gold_tokens) if gold_tokens else 1.0
            return score >= 0.5, score, list(matched), list(gold_tokens - matched)
        
        extracted_lower = self.normalize_text(extracted)
        gold_lower = self.normalize_text(gold)
        
        matched = []
        missing = []
        
        for term in key_terms:
            term_lower = term.lower()
            # Check if term appears in gold (only count terms that should be there)
            if term_lower in gold_lower:
                if term_lower in extracted_lower:
                    matched.append(term)
                else:
                    missing.append(term)
        
        # Calculate score based on terms that SHOULD be in extraction
        total_expected = len(matched) + len(missing)
        if total_expected == 0:
            return True, 1.0, [], []
        
        score = len(matched) / total_expected
        threshold = self.config.get("thresholds", {}).get("key_term_ratio", 0.3)
        
        return score >= threshold, score, matched, missing
    
    def calculate_semantic_similarity(self, gold: str, extracted: str) -> float:
        """Calculate semantic similarity using token overlap and sequence matching."""
        gold_norm = self.normalize_text(gold)
        ext_norm = self.normalize_text(extracted)
        
        if not gold_norm:
            return 1.0 if not ext_norm else 0.0
        if not ext_norm:
            return 0.0
        
        # Token overlap (Jaccard)
        gold_tokens = set(gold_norm.split())
        ext_tokens = set(ext_norm.split())
        
        intersection = gold_tokens & ext_tokens
        union = gold_tokens | ext_tokens
        jaccard = len(intersection) / len(union) if union else 0.0
        
        # Sequence matching
        seq_ratio = SequenceMatcher(None, gold_norm, ext_norm).ratio()
        
        # Containment boost for short gold values
        if len(gold_tokens) <= 3 and gold_norm in ext_norm:
            return 1.0
        
        return max(jaccard, seq_ratio)
    
    def classify_error(self, gold: str, extracted: str, similarity: float) -> Tuple[ErrorType, str]:
        """Classify the type of extraction error."""
        gold_norm = self.normalize_text(gold)
        ext_norm = self.normalize_text(extracted)
        
        # Check for missing patterns
        missing_patterns = self.config.get("error_patterns", {}).get("missing", [])
        is_missing = not ext_norm or ext_norm in [self.normalize_text(p) for p in missing_patterns]
        
        if is_missing and gold_norm:
            return ErrorType.MISSING, "No value extracted when gold has data"
        
        if not gold_norm and not ext_norm:
            return ErrorType.NONE, ""
        
        if not gold_norm and ext_norm:
            return ErrorType.EXCESS, "Extracted value when gold is empty"
        
        # Check for partial match
        gold_tokens = set(gold_norm.split())
        ext_tokens = set(ext_norm.split())
        
        if gold_tokens.issubset(ext_tokens) and ext_tokens != gold_tokens:
            return ErrorType.EXCESS, f"Contains extra: {ext_tokens - gold_tokens}"
        
        if ext_tokens.issubset(gold_tokens) and ext_tokens != gold_tokens:
            missing = gold_tokens - ext_tokens
            return ErrorType.PARTIAL, f"Missing: {missing}"
        
        # High similarity but not exact = format difference
        if similarity >= 0.7:
            return ErrorType.FORMAT, "Semantically correct but differently formatted"
        
        # Low similarity = wrong
        if similarity < 0.4:
            return ErrorType.WRONG, "Different value"
        
        # Medium similarity
        return ErrorType.PARTIAL, f"Partial match (similarity: {similarity:.2f})"
    
    def evaluate_field(
        self, 
        field_name: str, 
        gold_value: str, 
        extracted_value: str
    ) -> FieldEvaluation:
        """Evaluate a single field extraction."""
        
        weight = self.config.get("field_weights", {}).get(field_name, 1.0)
        
        # Tier 1: Exact match
        exact = self.check_exact_match(gold_value, extracted_value)
        
        # Tier 2: Key term match
        term_match, term_score, matched, missing = self.check_key_terms(
            gold_value, extracted_value, field_name
        )
        
        # Tier 3: Semantic similarity
        similarity = self.calculate_semantic_similarity(gold_value, extracted_value)
        threshold = self.config.get("thresholds", {}).get("semantic_similarity", 0.5)
        semantic = similarity >= threshold
        
        # Tier 4: Presence check
        ext_norm = self.normalize_text(extracted_value)
        missing_patterns = self.config.get("error_patterns", {}).get("missing", [])
        is_present = bool(ext_norm) and ext_norm not in [self.normalize_text(p) for p in missing_patterns]
        
        # Error classification
        if exact or semantic or term_match:
            error_type = ErrorType.NONE
            error_detail = ""
        else:
            error_type, error_detail = self.classify_error(gold_value, extracted_value, similarity)
        
        return FieldEvaluation(
            field_name=field_name,
            gold_value=gold_value,
            extracted_value=extracted_value,
            exact_match=exact,
            key_term_match=term_match,
            semantic_match=semantic,
            is_present=is_present,
            similarity_score=similarity,
            key_term_score=term_score,
            error_type=error_type,
            error_detail=error_detail,
            weight=weight,
            matched_terms=matched,
            missing_terms=missing,
        )
    
    def evaluate_document(
        self, 
        gold_standard: Dict[str, Any], 
        extracted: Dict[str, Any]
    ) -> DocumentEvaluation:
        """Evaluate extraction for a single document."""
        
        doc_name = gold_standard.get("source", "Unknown")
        
        # Fields to evaluate
        fields = [
            "case_count", "patient_age", "patient_sex", "presenting_symptoms",
            "diagnostic_method", "imaging_findings", "histopathology",
            "immunohistochemistry", "treatment", "outcome", "comorbidities"
        ]
        
        evaluations = []
        for field_name in fields:
            gold_value = str(gold_standard.get(field_name, ""))
            extracted_value = str(extracted.get(field_name, ""))
            
            eval_result = self.evaluate_field(field_name, gold_value, extracted_value)
            evaluations.append(eval_result)
        
        return DocumentEvaluation(
            document_name=doc_name,
            field_evaluations=evaluations,
        )
    
    def evaluate_model(
        self, 
        model_name: str,
        gold_standards: List[Dict[str, Any]],
        extractions: List[Dict[str, Any]],
        processing_time: float = 0.0,
    ) -> ModelEvaluation:
        """Evaluate a model across multiple documents."""
        
        doc_evaluations = []
        
        for gold in gold_standards:
            source = gold.get("source", "")
            
            # Find matching extraction
            matched_extraction = None
            for ext in extractions:
                if source in str(ext.values()):
                    matched_extraction = ext
                    break
            
            if matched_extraction:
                doc_eval = self.evaluate_document(gold, matched_extraction)
                doc_evaluations.append(doc_eval)
        
        return ModelEvaluation(
            model_name=model_name,
            document_evaluations=doc_evaluations,
            processing_time=processing_time,
        )


def generate_report(evaluations: List[ModelEvaluation], output_path: Path) -> str:
    """Generate a detailed markdown report comparing model evaluations."""
    
    lines = [
        "# Extraction Accuracy Report",
        "",
        f"Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Model | Time (s) | Exact | Key Terms | Semantic | Complete | CAS |",
        "|-------|----------|-------|-----------|----------|----------|-----|",
    ]
    
    for eval in evaluations:
        lines.append(
            f"| {eval.model_name} | {eval.processing_time:.1f} | "
            f"{eval.avg_exact_match:.0%} | {eval.avg_key_term_match:.0%} | "
            f"{eval.avg_semantic_match:.0%} | {eval.avg_completeness:.0%} | "
            f"**{eval.avg_clinical_accuracy:.2f}** |"
        )
    
    lines.extend([
        "",
        "> **CAS** = Clinical Accuracy Score (weighted by field importance)",
        "",
        "---",
        "",
    ])
    
    # Field-level breakdown for each model
    for eval in evaluations:
        lines.extend([
            f"## {eval.model_name}",
            "",
            "### Field-Level Breakdown",
            "",
            "| Field | Exact | Terms | Semantic | Present | Errors |",
            "|-------|-------|-------|----------|---------|--------|",
        ])
        
        field_stats = eval.get_field_stats()
        for field_name, stats in field_stats.items():
            total = stats["total"]
            errors = stats["errors"]
            error_summary = ", ".join(
                f"{count} {etype}" for etype, count in errors.items() if count > 0
            ) or "-"
            
            lines.append(
                f"| {field_name} | {stats['exact']}/{total} | "
                f"{stats['terms']}/{total} | {stats['semantic']}/{total} | "
                f"{stats['present']}/{total} | {error_summary} |"
            )
        
        # Error examples
        examples = eval.get_error_examples(3)
        if examples:
            lines.extend([
                "",
                "### Error Examples",
                "",
            ])
            
            for i, ex in enumerate(examples, 1):
                lines.extend([
                    f"**{i}. [{ex['error_type']}] {ex['field']}** ({ex['document'][:40]}...)",
                    f"- Gold: `{ex['gold'][:100]}{'...' if len(ex['gold']) > 100 else ''}`",
                    f"- Extracted: `{ex['extracted'][:100]}{'...' if len(ex['extracted']) > 100 else ''}`",
                    f"- Note: {ex['detail']}",
                    "",
                ])
        
        lines.extend(["", "---", ""])
    
    report = "\n".join(lines)
    
    # Save report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(report)
    
    return report


if __name__ == "__main__":
    # Quick test
    from tests.gold_standard_validation import ALL_GOLD_STANDARDS
    
    evaluator = ExtractionEvaluator()
    
    # Demo with mock extraction
    mock_extraction = {
        "case_count": "1",
        "patient_age": "61",
        "patient_sex": "female",
        "presenting_symptoms": "asymptomatic",
        "histopathology": "MPMNs",
    }
    
    doc_eval = evaluator.evaluate_document(ALL_GOLD_STANDARDS[0], mock_extraction)
    
    print(f"Document: {doc_eval.document_name[:50]}...")
    print(f"Exact Match Rate: {doc_eval.exact_match_rate:.0%}")
    print(f"Key Term Rate: {doc_eval.key_term_rate:.0%}")
    print(f"Semantic Rate: {doc_eval.semantic_rate:.0%}")
    print(f"Clinical Accuracy Score: {doc_eval.clinical_accuracy_score:.2f}")
