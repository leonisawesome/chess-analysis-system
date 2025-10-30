"""
Chess Opening Data with ECO Codes
Phase 1: Top 20 most common openings
"""
from typing import Optional, Tuple

opening_eco_map = {
    # Italian Game and variants
    "italian game": {"eco": "C50", "parent": "Italian Game", "signature": "1.e4 e5 2.Nf3 Nc6 3.Bc4"},
    "giuoco piano": {"eco": "C50", "parent": "Italian Game", "signature": "1.e4 e5 2.Nf3 Nc6 3.Bc4"},

    # Sicilian Defense and variants
    "sicilian defense": {"eco": "B20", "parent": "Sicilian Defense", "signature": "1.e4 c5"},
    "sicilian": {"eco": "B20", "parent": "Sicilian Defense", "signature": "1.e4 c5"},
    "najdorf variation": {"eco": "B90", "parent": "Sicilian Defense", "signature": "1.e4 c5"},
    "najdorf": {"eco": "B90", "parent": "Sicilian Defense", "signature": "1.e4 c5"},
    "dragon variation": {"eco": "B70", "parent": "Sicilian Defense", "signature": "1.e4 c5"},
    "dragon": {"eco": "B70", "parent": "Sicilian Defense", "signature": "1.e4 c5"},
    "sveshnikov variation": {"eco": "B33", "parent": "Sicilian Defense", "signature": "1.e4 c5"},
    "sveshnikov": {"eco": "B33", "parent": "Sicilian Defense", "signature": "1.e4 c5"},

    # French Defense
    "french defense": {"eco": "C00", "parent": "French Defense", "signature": "1.e4 e6"},
    "french": {"eco": "C00", "parent": "French Defense", "signature": "1.e4 e6"},
    "winawer variation": {"eco": "C15", "parent": "French Defense", "signature": "1.e4 e6"},
    "winawer": {"eco": "C15", "parent": "French Defense", "signature": "1.e4 e6"},

    # Caro-Kann Defense
    "caro kann defense": {"eco": "B10", "parent": "Caro-Kann Defense", "signature": "1.e4 c6"},
    "carokann defense": {"eco": "B10", "parent": "Caro-Kann Defense", "signature": "1.e4 c6"},
    "caro kann": {"eco": "B10", "parent": "Caro-Kann Defense", "signature": "1.e4 c6"},
    "carokann": {"eco": "B10", "parent": "Caro-Kann Defense", "signature": "1.e4 c6"},

    # Ruy Lopez
    "ruy lopez": {"eco": "C60", "parent": "Ruy Lopez", "signature": "1.e4 e5 2.Nf3 Nc6 3.Bb5"},
    "spanish opening": {"eco": "C60", "parent": "Ruy Lopez", "signature": "1.e4 e5 2.Nf3 Nc6 3.Bb5"},
    "spanish game": {"eco": "C60", "parent": "Ruy Lopez", "signature": "1.e4 e5 2.Nf3 Nc6 3.Bb5"},

    # Queen's Gambit
    "queens gambit": {"eco": "D06", "parent": "Queen's Gambit", "signature": "1.d4 d5 2.c4"},
    "queen's gambit": {"eco": "D06", "parent": "Queen's Gambit", "signature": "1.d4 d5 2.c4"},
    "queens gambit declined": {"eco": "D30", "parent": "Queen's Gambit", "signature": "1.d4 d5 2.c4"},
    "queens gambit accepted": {"eco": "D20", "parent": "Queen's Gambit", "signature": "1.d4 d5 2.c4"},

    # King's Indian Defense
    "kings indian defense": {"eco": "E60", "parent": "King's Indian Defense", "signature": "1.d4 Nf6 2.c4 g6"},
    "king's indian defense": {"eco": "E60", "parent": "King's Indian Defense", "signature": "1.d4 Nf6 2.c4 g6"},
    "kings indian": {"eco": "E60", "parent": "King's Indian Defense", "signature": "1.d4 Nf6 2.c4 g6"},

    # Nimzo-Indian Defense
    "nimzoindian defense": {"eco": "E20", "parent": "Nimzo-Indian Defense", "signature": "1.d4 Nf6 2.c4 e6 3.Nc3 Bb4"},
    "nimzo indian defense": {"eco": "E20", "parent": "Nimzo-Indian Defense", "signature": "1.d4 Nf6 2.c4 e6 3.Nc3 Bb4"},
    "nimzo-indian defense": {"eco": "E20", "parent": "Nimzo-Indian Defense", "signature": "1.d4 Nf6 2.c4 e6 3.Nc3 Bb4"},
    "nimzoindian": {"eco": "E20", "parent": "Nimzo-Indian Defense", "signature": "1.d4 Nf6 2.c4 e6 3.Nc3 Bb4"},

    # English Opening
    "english opening": {"eco": "A10", "parent": "English Opening", "signature": "1.c4"},
    "english": {"eco": "A10", "parent": "English Opening", "signature": "1.c4"},

    # Catalan Opening
    "catalan opening": {"eco": "E00", "parent": "Catalan Opening", "signature": "1.d4 Nf6 2.c4 e6 3.g3"},
    "catalan": {"eco": "E00", "parent": "Catalan Opening", "signature": "1.d4 Nf6 2.c4 e6 3.g3"},

    # Grünfeld Defense
    "grunfeld defense": {"eco": "D70", "parent": "Grünfeld Defense", "signature": "1.d4 Nf6 2.c4 g6 3.Nc3 d5"},
    "gruenfeld defense": {"eco": "D70", "parent": "Grünfeld Defense", "signature": "1.d4 Nf6 2.c4 g6 3.Nc3 d5"},
    "grunfeld": {"eco": "D70", "parent": "Grünfeld Defense", "signature": "1.d4 Nf6 2.c4 g6 3.Nc3 d5"},

    # Pirc Defense
    "pirc defense": {"eco": "B07", "parent": "Pirc Defense", "signature": "1.e4 d6"},
    "pirc": {"eco": "B07", "parent": "Pirc Defense", "signature": "1.e4 d6"},

    # Scotch Game
    "scotch game": {"eco": "C44", "parent": "Scotch Game", "signature": "1.e4 e5 2.Nf3 Nc6 3.d4"},
    "scotch opening": {"eco": "C44", "parent": "Scotch Game", "signature": "1.e4 e5 2.Nf3 Nc6 3.d4"},
    "scotch": {"eco": "C44", "parent": "Scotch Game", "signature": "1.e4 e5 2.Nf3 Nc6 3.d4"},
}


def detect_opening(query: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Detect chess opening from query using ECO-based lookup.

    Args:
        query: User query string

    Returns:
        Tuple of (parent_opening, signature, eco_code) or (None, None, None) if not found
    """
    # Normalize query: lowercase, remove apostrophes/hyphens, collapse spaces
    query_normalized = query.lower().replace("'", "").replace("-", " ").replace("  ", " ").strip()

    # Try to find opening in the map
    for variant, data in opening_eco_map.items():
        if variant in query_normalized:
            return data["parent"], data["signature"], data["eco"]

    return None, None, None
