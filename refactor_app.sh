#!/bin/bash

# ITEM-010 PHASE 2B: REFACTOR MONOLITHIC APP.PY

cd /Users/leon/Downloads/python/chess-analysis-system

echo "Starting refactoring..."

# Backup
cp app.py app.py.before_refactor_backup
echo "✓ Backed up app.py"

# Show current size
echo "Current app.py: $(wc -l < app.py) lines"
echo ""

# The query_classifier.py was already partially added to app.py
# Let's create the standalone version
cat > query_classifier.py << 'PYEOF'
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
PYEOF

echo "✓ Created query_classifier.py"

echo ""
echo "Refactoring complete. Files created:"
echo "  - query_classifier.py: $(wc -l < query_classifier.py) lines"
echo "  - fen_validator.py: $(wc -l < fen_validator.py) lines (already exists)"
echo ""
echo "Next: Update app.py to import from query_classifier module"

