"""
Empirically-derived instructional vocabulary from 5-AI partner consultation
Based on consensus from Gemini, Grok (2x), ChatGPT (2x), Perplexity analysis
Replacing synthetic patterns with chess-specific empirical vocabulary
"""

# ChatGPT's 9-category framework with empirically-derived chess patterns
INSTRUCTIONAL_LEXICON = {
    "intent_patterns": [
        "the idea is",
        "aims to",
        "prepares to", 
        "prevents",
        "with the idea of",
        "the plan is",
        "the point behind",
        "designed to",
        "intended to",
        "serves to",
        "helps to",
        "allows us to",
        "enables",
        "makes it possible to"
    ],
    "opening_principle": [
        "develops with tempo",
        "challenges the center",
        "controls the center",
        "develops quickly",
        "castles early",
        "avoids weakening moves",
        "maintains flexibility",
        "keeps tension",
        "equalizes comfortably",
        "secures king safety"
    ],
    "planning_patterns": [
        "improve the worst piece",
        "reroute the knight",
        "overprotect the weakness",
        "double on the file",
        "create outposts",
        "establish dominance",
        "build pressure",
        "coordinate pieces",
        "centralize forces",
        "maximize piece activity",
        "create threats",
        "maintain initiative"
    ],
    "tactical_patterns": [
        "removal of the defender",
        "deflection",
        "pin",
        "fork",
        "skewer",
        "discovered attack",
        "double attack",
        "zwischenzug",
        "clearance",
        "interference",
        "decoy",
        "x-ray attack"
    ],
    "endgame_patterns": [
        "rook behind the passed pawn",
        "opposition",
        "triangulation",
        "zugzwang",
        "breakthrough",
        "promotion",
        "king and pawn endgame",
        "rook endgame technique",
        "queen endgame",
        "minor piece endgame",
        "fortress",
        "stalemate tricks"
    ],
    "evaluation_patterns": [
        "only move",
        "keeps the advantage",
        "equalizes",
        "slight edge",
        "winning position",
        "losing position",
        "unclear",
        "compensation",
        "initiative",
        "pressure",
        "counterplay",
        "defense holds"
    ],
    "structure_patterns": [
        "pawn structure",
        "pawn chain",
        "isolated pawn",
        "doubled pawns",
        "passed pawn",
        "weak square",
        "strong square",
        "hole in the position",
        "pawn majority",
        "pawn minority",
        "pawn storm",
        "pawn break"
    ],
    "teaching_method": [
        "step by step",
        "systematic approach",
        "key principles",
        "fundamental concepts",
        "practical examples",
        "clear explanation",
        "detailed analysis",
        "instructive game",
        "learning objectives",
        "improvement method"
    ],
    "strategic_concepts": [
        "space advantage",
        "time factor",
        "material balance",
        "positional compensation",
        "long-term planning",
        "strategic themes",
        "positional play",
        "piece coordination",
        "dynamic factors",
        "static advantages"
    ]
}

# Slot patterns for dynamic content (maintained from original)
SLOT_PATTERNS = [
    {
        "category": "template",
        "pattern": r"(?P<MOVE>[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?)\s+(?:aims to|prepares|prevents)",
        "slots": ["MOVE"],
        "weight": 1.0
    },
    {
        "category": "template", 
        "pattern": r"the idea (?:of|behind)\s+(?P<MOVE>[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?)",
        "slots": ["MOVE"], 
        "weight": 1.0
    },
    {
        "category": "planning_patterns",
        "pattern": r"reroute (?:the )?(?:knight|bishop)\s+(?:to )?(?P<SQ>[a-h][1-8])",
        "slots": ["SQ"],
        "weight": 0.8
    },
    {
        "category": "planning_patterns", 
        "pattern": r"overprotect\s+(?P<SQ>[a-h][1-8])",
        "slots": ["SQ"],
        "weight": 0.8
    },
    {
        "category": "planning_patterns",
        "pattern": r"double rooks on\s+(?P<FILE>[a-h]-file)",
        "slots": ["FILE"], 
        "weight": 0.8
    }
]

# Category weights from 5-AI partner consultation consensus
CATEGORY_WEIGHTS = {
    "intent_patterns": 1.0,
    "template": 1.0,
    "teaching_method": 0.95,
    "endgame_patterns": 0.9,
    "tactical_patterns": 0.9,
    "planning_patterns": 0.85,
    "evaluation_patterns": 0.85,
    "strategic_concepts": 0.8,
    "structure_patterns": 0.8,
    "opening_principle": 0.75
}

# Diminishing returns caps (maintained from original)
CATEGORY_CAPS = {k: 6 for k in CATEGORY_WEIGHTS}