"""
Text processing utilities for SR-Architect.

Includes fuzzy matching logic adapted from LLM-IE (JAMIA Open 2025)
to improve quote validation robustness.
"""

import re
from typing import List, Tuple, Optional, Set

def tokenize(text: str) -> List[str]:
    """
    Simple word tokenization.
    Splits on non-alphanumeric characters and converts to lowercase.
    """
    return re.findall(r'\b\w+\b', text.lower())

def jaccard_score(tokens1: Set[str], tokens2: Set[str]) -> float:
    """
    Compute Jaccard similarity score between two sets of tokens.
    J(A,B) = |A ∩ B| / |A ∪ B|
    """
    if not tokens1 or not tokens2:
        return 0.0
    
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    
    return intersection / union if union > 0 else 0.0

def find_best_substring_match(
    text: str, 
    pattern: str, 
    threshold: float = 0.8,
    window_slack: float = 0.5
) -> Tuple[Optional[str], float, Optional[Tuple[int, int]]]:
    """
    Find the best fuzzy match for a pattern within a text using Jaccard similarity.
    
    Adapted from llm-ie project.
    
    Args:
        text: The source text to search in.
        pattern: The substring pattern to look for (e.g. LLM extracted quote).
        threshold: Minimum Jaccard score to consider a match.
        window_slack: How much larger to make the search window compared to pattern length.
                      0.2 means window can be 20% larger than pattern (in tokens).
                      
    Returns:
        Tuple of (matched_text, score, (start_index, end_index))
        Returns (None, 0.0, None) if no match found above threshold.
    """
    if not pattern or not text:
        return None, 0.0, None
        
    # Quick exact match check
    exact_idx = text.find(pattern)
    if exact_idx != -1:
        return pattern, 1.0, (exact_idx, exact_idx + len(pattern))
        
    # Fuzzy match logic
    text_tokens = tokenize(text)
    pattern_tokens = tokenize(pattern)
    pattern_set = set(pattern_tokens)
    
    if not pattern_tokens:
        return None, 0.0, None
        
    n_pattern = len(pattern_tokens)
    n_text = len(text_tokens)
    
    # Define window size limits
    min_window = max(1, int(n_pattern * (1 - window_slack)))
    max_window = int(n_pattern * (1 + window_slack)) + 1
    
    best_score = 0.0
    best_window_indices = None
    
    # Sliding window over tokens
    # Note: iterating tokens is faster than characters but requires mapping back to char indices
    # To map back, we need token positions.
    
    # Build token map: (token, start_char, end_char)
    token_map = []
    for match in re.finditer(r'\b\w+\b', text):
        token_map.append((match.group().lower(), match.start(), match.end()))
        
    if not token_map:
        return None, 0.0, None

    for i in range(len(token_map)):
        # Optimization: Early exit if remaining text is too short for pattern
        if i + min_window > len(token_map):
            break
            
        for w_len in range(min_window, min(max_window, len(token_map) - i + 1)):
            window_slice = token_map[i : i + w_len]
            window_tokens = set(t[0] for t in window_slice)
            
            # Simple heuristic: First word must allow match (optional, but speeds up)
            # if window_slice[0][0] not in pattern_set:
            #     continue
            
            score = jaccard_score(window_tokens, pattern_set)
            
            if score > best_score:
                best_score = score
                best_window_indices = (i, i + w_len)
    
    if best_score >= threshold and best_window_indices:
        start_idx = best_window_indices[0]
        end_idx = best_window_indices[1] - 1  # Inclusive of last token
        
        start_char = token_map[start_idx][1]
        end_char = token_map[end_idx][2]
        
        # Extend to cover full captured text (including spaces between first/last token)
        matched_text = text[start_char:end_char]
        
        return matched_text, best_score, (start_char, end_char)
        
    return None, best_score, None
