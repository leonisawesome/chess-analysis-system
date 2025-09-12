"""
Empirically-derived instructional vocabulary from 5-AI partner consultation
Based on consensus from Gemini, Grok (2x), ChatGPT (2x), Perplexity analysis
Replacing synthetic patterns with chess-specific empirical vocabulary

Option A hotfix: env-gated EN/ES regex
- Controlled by env var DETECTOR_LANGS (comma-separated), default: "en"
- Supported values: "en", "es", "en,es" (or "all")
"""

from __future__ import annotations

import os
from typing import Dict, List

def _env_langs() -> List[str]:
    raw = os.getenv("DETECTOR_LANGS", "en").strip().lower()
    if raw in ("all", "*", "any"):
        return ["en", "es"]
    # split on comma/space
    parts = [p for p in (x.strip() for x in raw.replace(" ", ",").split(",")) if p]
    # keep only supported
    out = []
    for p in parts:
        if p in ("en", "es") and p not in out:
            out.append(p)
    return out or ["en"]

# ChatGPT's 9-category framework with empirically-derived chess patterns
_EN_LEXICON: Dict[str, List[str]] = {
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

# Spanish equivalents (focused, minimal coverage for precision)
_ES_LEXICON: Dict[str, List[str]] = {
    "intent_patterns": [
        "la idea es",
        "apunta a",
        "pretende",
        "evita",
        "con la idea de",
        "el plan es",
        "diseñado para",
        "intenta",
        "sirve para",
        "ayuda a",
        "permite",
        "hace posible"
    ],
    "opening_principle": [
        "desarrolla con tiempo",
        "lucha por el centro",
        "controla el centro",
        "desarrolla rápido",
        "enroca temprano",
        "evita debilidades",
        "mantiene la tensión",
        "igualar cómodamente",
        "seguridad del rey"
    ],
    "planning_patterns": [
        "mejorar la peor pieza",
        "reubicar el caballo",
        "sobreproteger la debilidad",
        "doblar en la columna",
        "crear puestos avanzados",
        "construir presión",
        "coordinar piezas",
        "centralizar las piezas",
        "maximizar la actividad",
        "crear amenazas",
        "mantener la iniciativa"
    ],
    "tactical_patterns": [
        "eliminar al defensor",
        "desviación",
        "clavada",
        "tenedor",
        "rayos x",
        "ataque descubierto",
        "doble ataque",
        "zwischenzug",
        "despeje",
        "interferencia",
        "señuelo"
    ],
    "endgame_patterns": [
        "torre detrás del peón pasado",
        "oposición",
        "triangulación",
        "zugzwang",
        "ruptura",
        "promoción",
        "final de rey y peones",
        "técnica de finales de torre",
        "final de damas",
        "final de piezas menores",
        "fortaleza",
        "trucos de ahogado"
    ],
    "evaluation_patterns": [
        "única",
        "mantiene la ventaja",
        "igualado",
        "ligera ventaja",
        "posición ganadora",
        "posición perdedora",
        "incierto",
        "compensación",
        "iniciativa",
        "presión",
        "contrajuego",
        "la defensa aguanta"
    ],
    "structure_patterns": [
        "estructura de peones",
        "cadena de peones",
        "peón aislado",
        "peones doblados",
        "peón pasado",
        "casilla débil",
        "casilla fuerte",
        "agujero en la posición",
        "mayoría de peones",
        "minoría de peones",
        "tormenta de peones",
        "ruptura de peones"
    ],
    "teaching_method": [
        "paso a paso",
        "enfoque sistemático",
        "principios clave",
        "conceptos fundamentales",
        "ejemplos prácticos",
        "explicación clara",
        "análisis detallado",
        "partida instructiva",
        "objetivos de aprendizaje",
        "método de mejora"
    ],
    "strategic_concepts": [
        "ventaja de espacio",
        "factor tiempo",
        "balance material",
        "compensación posicional",
        "planificación a largo plazo",
        "temas estratégicos",
        "juego posicional",
        "coordinación de piezas",
        "factores dinámicos",
        "ventajas estáticas"
    ],
}

def _merge_lexicons(langs: List[str]) -> Dict[str, List[str]]:
    """Combine language lexicons per category without duplicates."""
    out: Dict[str, List[str]] = {}
    def add_from(src: Dict[str, List[str]]):
        for cat, phrases in src.items():
            bucket = out.setdefault(cat, [])
            for p in phrases:
                pl = p.lower()
                # avoid dups preserving order
                if all(pl != q.lower() for q in bucket):
                    bucket.append(p)
    if "en" in langs:
        add_from(_EN_LEXICON)
    if "es" in langs:
        add_from(_ES_LEXICON)
    return out

INSTRUCTIONAL_LEXICON = _merge_lexicons(_env_langs())

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
# >>> ENHANCED_VOCAB_PATTERNS BEGIN
try:
    import os
    if (lambda v: v.strip().lower() in ('1','true','yes','on'))(os.getenv('ENHANCED_VOCAB_PATTERNS','')):
        _EN_AUG={'planning_patterns':(r'\b(the\s+idea\s+is|the\s+plan\s+is)\b',),
                 'teaching_method':(r'\b(exercise|practice|study|analys[ei]s|example|solution)s?\b',r'\b(see\s+the\s+diagram)\b',r'\b(explains?|demonstrates?|teaches?|shows\s+how)\b',),
                 'strategic_concepts':(r'\b(strategy|strategic|structure|typical)\b',),
                 'intent_patterns':(r'\b(find\s+the\s+(?:best\s+)?move)\b',)}
        _ES_AUG={'planning_patterns':(r'\b(la\s+idea\s+es|el\s+plan\s+es)\b',r'\b(estrategia|estrat[eé]gico|principio|principios)\b',),
                 'teaching_method':(r'\b(ejercicio|ejemplos?|soluci[oó]n(?:es)?)\b',r'\b(ver\s+el\s+diagrama)\b',r'\b(explica|demuestra|enseña|muestra\s+c[oó]mo)\b',),
                 'strategic_concepts':(r'\b(t[aá]ctica|apertura|final(?:es)?|variante\s+principal|plan\s+estrat[eé]gico)\b',r'\b(idea|ideas|tema|temas|conceptos?)\b',),
                 'intent_patterns':(r'\b(juegan\s+(?:las\s+)?(?:blancas|negras)|mueven\s+(?:las\s+)?(?:blancas|negras))\b',r'\b(encuentr[ea]\s+la\s+(?:mejor\s+)?jugada)\b',r'\b(observa|considera|recuerda|nota\s+que)\b',)}
        g=globals()
        if isinstance(g.get('INSTRUCTIONAL_LEXICON'),dict):
            try:
                langs = set(_env_langs())
            except Exception:
                langs = set((os.getenv('DETECTOR_LANGS','en') or 'en').replace(' ','').lower().split(','))
            combined = {}
            if 'en' in langs:
                combined.update(_EN_AUG)
            if 'es' in langs:
                for k,v in _ES_AUG.items():
                    combined[k] = tuple(list(combined.get(k, ())) + list(v))
            for k,v in combined.items():
                if k in g['INSTRUCTIONAL_LEXICON']:
                    old=tuple(g['INSTRUCTIONAL_LEXICON'][k])
                    g['INSTRUCTIONAL_LEXICON'][k]=old+tuple(v)
except Exception:
    pass
# >>> ENHANCED_VOCAB_PATTERNS END
# >>> ENHANCED_VOCAB_PATTERNS v2 BEGIN
try:
    import os
    if (lambda v: v.strip().lower() in ('1','true','yes','on'))(os.getenv('ENHANCED_VOCAB_PATTERNS','')):
        EXTRA_EN = {
            'planning_patterns': (
                r'(key\s+idea|main\s+idea)',
                r'(typical\s+plan|common\s+plan)',
            ),
            'teaching_method': (
                r'(in\s+this\s+position)',
                r"(let'?s\s+(?:see|examine|look))",
                r'(remember\s+that|note\s+that)',
            ),
            'intent_patterns': (
                r'(white|black)\s+to\s+play',
            ),
        }
        EXTRA_ES = {
            'planning_patterns': (
                r'(idea\s+clave|idea\s+principal)',
                r'(plan\s+t[íi]pico)',
            ),
            'teaching_method': (
                r'(en\s+esta\s+posici[oó]n)',
                r'(veamos|miremos)',
                r'(recuerda\s+que|ten\s+en\s+cuenta)',
            ),
            'intent_patterns': (
                r'(blancas|negras)\s+juegan',
            ),
        }
        g=globals()
        if isinstance(g.get('INSTRUCTIONAL_LEXICON'), dict):
            try:
                langs = set(_env_langs())
            except Exception:
                langs = set((os.getenv('DETECTOR_LANGS','en') or 'en').replace(' ','').lower().split(','))
            combined = {}
            if 'en' in langs:
                combined.update(EXTRA_EN)
            if 'es' in langs:
                for k,v in EXTRA_ES.items():
                    combined[k] = tuple(list(combined.get(k, ())) + list(v))
            for k, v in combined.items():
                if k in g['INSTRUCTIONAL_LEXICON']:
                    seq = list(g['INSTRUCTIONAL_LEXICON'][k])
                    for pat in v:
                        if pat not in seq:
                            seq.append(pat)
                    g['INSTRUCTIONAL_LEXICON'][k] = seq
except Exception:
    pass
# >>> ENHANCED_VOCAB_PATTERNS v2 END

# >>> ENHANCED_VOCAB_PATTERNS_B BEGIN
try:
    import os, re
    _truthy = lambda v: str(v or '').strip().lower() in ('1','true','yes','on')
    if _truthy(os.getenv('ENHANCED_VOCAB_PATTERNS','')):
        _AUG_EN = {
            'teaching_method': (
                r"\b(?:Exercise)\b",
                r"\b(?:Solution)\b",
                r"\b(?:In this lesson)\b",
                r"\b(?:Chapter|Part|Lesson)\s+\d+\b",
            ),
            'intent_patterns': (
                r"\b(?:Find the best move)\b",
            ),
            'planning_patterns': (
                r"\b(?:The idea is)\b",
            ),
        }
        _AUG_ES = {
            'teaching_method': (
                r"\b(?:Ejercicio)\b",
                r"\b(?:Soluci[oó]n)\b",
                r"\b(?:En esta lecci[oó]n)\b",
                r"\b(?:Cap[íi]tulo|Parte|Lecci[oó]n)\s+\d+\b",
            ),
            'intent_patterns': (
                r"\b(?:Encuentra la mejor jugada)\b",
            ),
            'planning_patterns': (
                r"\b(?:La idea es|El plan es)\b",
            ),
        }
        g = globals()
        lex = g.get('INSTRUCTIONAL_LEXICON')
        if isinstance(lex, dict):
            try:
                langs = set(_env_langs())
            except Exception:
                langs = set((os.getenv('DETECTOR_LANGS','en') or 'en').replace(' ','').lower().split(','))
            combined = {}
            if 'en' in langs:
                combined.update(_AUG_EN)
            if 'es' in langs:
                for k,v in _AUG_ES.items():
                    combined[k] = tuple(list(combined.get(k, ())) + list(v))
            for cat, pats in combined.items():
                if cat in lex:
                    cur = tuple(lex[cat])
                    # dedupe while preserving order
                    seen = set(cur)
                    merged = list(cur)
                    for ptn in pats:
                        if ptn not in seen:
                            merged.append(ptn)
                            seen.add(ptn)
                    lex[cat] = tuple(merged)
except Exception:
    pass
# >>> ENHANCED_VOCAB_PATTERNS_B END
