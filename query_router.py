"""
Query Router Module - Intent Classification

Handles:
- Query classification (opening vs concept vs mixed)
- Collection weight determination based on query type
- Regex-based pattern matching for chess terminology

Phase 5.1 Implementation
"""

import re
from typing import Dict, Tuple


# Patterns for query classification
OPENING_PATTERN = re.compile(
    r'\b([A-E][0-9]{2})\b|'  # ECO codes (A00-E99)
    r'([KQRBN]x?[a-h][1-8])|'  # SAN notation (Nf3, Bxc6)
    r'(^|\s)\d+\.\s|'  # Move numbers (1. e4)
    r'\bFEN\b|'  # FEN string reference
    r'\bECO\b|'  # ECO reference
    r'\bmainline\b|'
    r'\brepertoire\b|'
    r'\bafter\s+\d+\.{0,3}|'  # "after 10...d5"
    r'\bvariation\b|'
    r'\bline\b|'
    r'\bopening\b|'
    r'\bgambit\b|'
    r'\bdefense\b|'
    r'\bdefence\b',  # British spelling
    re.IGNORECASE
)

CONCEPT_PATTERN = re.compile(
    r'\bexplain\b|'
    r'\bplans?\b|'
    r'\bstrateg(y|ies)\b|'
    r'\bideas?\b|'
    r'\bwhy\b|'
    r'\bmodel game\b|'
    r'\bprinciples?\b|'
    r'\bconcepts?\b|'
    r'\bhow to\b|'
    r'\bwhat is\b|'
    r'\bunderstand\b',
    re.IGNORECASE
)


def classify_query(query: str) -> str:
    """
    Classify query type based on content.

    Args:
        query: User's query string

    Returns:
        'opening' - Query about specific lines/repertoires
        'concept' - Query about strategy/ideas
        'mixed' - Ambiguous or contains both types

    Examples:
        "Explain the Italian Game" → 'mixed' (has both "explain" and "Italian Game")
        "Benko Gambit repertoire" → 'opening' (repertoire keyword)
        "What is a fork?" → 'concept' (strategic concept)
        "After 1.e4 c5 what should I play?" → 'opening' (move notation)
    """
    is_opening = bool(OPENING_PATTERN.search(query))
    is_concept = bool(CONCEPT_PATTERN.search(query))

    if is_opening and not is_concept:
        return 'opening'
    elif is_concept and not is_opening:
        return 'concept'
    else:
        # Both patterns match or neither matches
        return 'mixed'


def get_collection_weights(query: str) -> Dict[str, float]:
    """
    Get collection weights based on query classification.

    Args:
        query: User's query string

    Returns:
        Dict with keys for collection names, values are weight multipliers

    Weight Strategy:
        - Opening queries: PGN gets 1.3x boost (concrete variations)
        - Concept queries: EPUB gets 1.3x boost (strategic explanations)
        - Mixed queries: No bias (1.0 for both)
    """
    query_type = classify_query(query)

    if query_type == 'opening':
        # Opening queries favor PGN (specific lines and games)
        return {
            'chess_production': 1.0,
            'chess_pgn_repertoire': 1.3
        }
    elif query_type == 'concept':
        # Concept queries favor EPUB (explanatory prose)
        return {
            'chess_production': 1.3,
            'chess_pgn_repertoire': 1.0
        }
    else:
        # Mixed or ambiguous - no bias
        return {
            'chess_production': 1.0,
            'chess_pgn_repertoire': 1.0
        }


def get_query_info(query: str) -> Tuple[str, Dict[str, float]]:
    """
    Convenience function to get both classification and weights.

    Args:
        query: User's query string

    Returns:
        Tuple of (query_type, collection_weights)

    Example:
        >>> query_type, weights = get_query_info("Benko Gambit repertoire")
        >>> print(query_type)  # 'opening'
        >>> print(weights)     # {'chess_production': 1.0, 'chess_pgn_repertoire': 1.3}
    """
    query_type = classify_query(query)
    weights = get_collection_weights(query)
    return query_type, weights
