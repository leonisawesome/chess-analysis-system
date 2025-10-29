"""
Query classification for chess knowledge system.
Determines if query is about openings or middlegame concepts.
"""

def classify_query(query: str) -> str:
    """
    Classifies query as OPENING or MIDDLEGAME based on keywords.

    Returns:
        "OPENING" if query is about chess openings
        "MIDDLEGAME" if query is about middlegame concepts
    """
    query_lower = query.lower()

    # Opening indicators
    opening_keywords = [
        'opening', 'defense', 'gambit', 'variation',
        'italian game', 'ruy lopez', 'sicilian', 'french', 'caro-kann',
        'king\'s indian', 'queen\'s gambit', 'najdorf', 'dragon', 'winawer'
    ]

    # Middlegame indicators
    middlegame_keywords = [
        'isolated queen pawn', 'isolated pawn', 'iqp',
        'good knight', 'bad bishop',
        'closed position', 'backward pawn',
        'minority attack', 'hanging pawns',
        'blocked center', 'kingside majority',
        'open file', 'rook on open file',
        'pawn structure', 'piece coordination',
        'prophylaxis', 'space advantage'
    ]

    # Check for middlegame keywords first (more specific)
    for keyword in middlegame_keywords:
        if keyword in query_lower:
            return "MIDDLEGAME"

    # Default to opening if opening keywords found
    for keyword in opening_keywords:
        if keyword in query_lower:
            return "OPENING"

    # Default to opening if unclear
    return "OPENING"


def extract_concept_from_query(query: str) -> str:
    """
    Maps query to canonical FEN concept key.

    Returns:
        Concept key from canonical_fens.json, or None if not found
    """
    query_lower = query.lower()

    # Mapping of query patterns to canonical FEN keys
    concept_map = {
        'isolated queen pawn': 'isolated_queen_pawn',
        'isolated pawn': 'isolated_queen_pawn',
        'iqp': 'isolated_queen_pawn',
        'good knight': 'good_knight_vs_bad_bishop',
        'bad bishop': 'bad_bishop',
        'closed position': 'closed_position',
        'backward pawn': 'backward_pawn_d_file',
        'minority attack': 'minority_attack',
        'hanging pawns': 'hanging_pawns',
        'hanging pawn': 'hanging_pawns',
        'blocked center': 'blocked_center',
        'kingside majority': 'kingside_majority',
        'open file': 'open_file_rook',
        'rook on open file': 'open_file_rook'
    }

    # Find matching concept
    for pattern, concept_key in concept_map.items():
        if pattern in query_lower:
            return concept_key

    return None


def get_canonical_fen_for_query(query: str, canonical_fens: dict) -> tuple:
    """
    High-level function to classify query and get canonical FEN if available.
    
    Args:
        query: User's chess query
        canonical_fens: Dict of concept_key -> FEN string
        
    Returns:
        Tuple of (query_type, concept_key, fen_string)
        - query_type: "OPENING" or "MIDDLEGAME"
        - concept_key: Extracted concept key (or None)
        - fen_string: Canonical FEN (or None if not found)
    """
    # Classify the query
    query_type = classify_query(query)
    
    # Only look for canonical FEN if it's a middlegame query
    if query_type != "MIDDLEGAME":
        return (query_type, None, None)
    
    # Extract the concept
    concept_key = extract_concept_from_query(query)
    
    # Look up canonical FEN
    fen_string = canonical_fens.get(concept_key)
    
    return (query_type, concept_key, fen_string)
