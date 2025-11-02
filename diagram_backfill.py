"""
Diagram Backfill Helpers

Backfill tactical diagrams from RAG results when synthesized markers are
insufficient or invalid. Keeps output dynamic by mining positions from
retrieved content and validating them.
"""

from typing import List, Dict, Optional, Tuple
import uuid

from diagram_validator import validate_diagram
from diagram_processor import generate_svg_from_fen
from chess_positions import extract_chess_positions


TACTICAL_KEYWORDS = {
    'pin': {'pin','pins','pinned','pinning'},
    'fork': {'fork','forks','double attack','double-attack'},
    'skewer': {'skewer','skewers'},
}


def infer_tactic_from_query(query: str) -> Optional[str]:
    q = (query or '').lower()
    for tactic, keys in TACTICAL_KEYWORDS.items():
        if any(k in q for k in keys):
            return tactic
    return None


def backfill_tactical_diagrams_from_results(
    results: List[Dict],
    tactic: str,
    needed: int,
    max_total: int = 5,
) -> List[Dict]:
    """
    Mine positions from RAG results and validate for the given tactic.

    Args:
        results: formatted RAG results (as returned by format_rag_results)
        tactic: one of ('pin','fork','skewer', ...)
        needed: number of diagrams to add
        max_total: upper bound to avoid flooding

    Returns:
        A list of diagram dicts: {id, fen, svg, caption, tactic, validated=True}
    """
    if not results or not tactic or needed <= 0:
        return []

    seen_fens = set()
    backfilled: List[Dict] = []

    for res in results:
        positions = res.get('positions') or []
        # Fallback: mine positions from raw text if struct positions missing
        if not positions:
            text = res.get('text') or ''
            try:
                mined = extract_chess_positions(text) or []
            except Exception:
                mined = []
            # Normalize mined format: list of dicts with 'fen' and optional 'caption'
            norm = []
            for m in mined:
                if isinstance(m, dict) and m.get('fen'):
                    norm.append({'fen': m.get('fen'), 'caption': m.get('caption') or ''})
                elif isinstance(m, tuple) and len(m) >= 1:
                    norm.append({'fen': m[0], 'caption': ''})
            positions = norm
        if not positions:
            continue
        for pos in positions:
            fen = pos.get('fen') or ''
            if not fen or fen in seen_fens:
                continue

            # Caption preference: existing caption -> book/chapter context -> generic
            caption = pos.get('caption') or ''
            if not caption:
                book = res.get('book') or res.get('book_name') or 'Source'
                chapter = res.get('chapter') or res.get('chapter_title') or ''
                caption = f"From {book}{(': ' + chapter) if chapter else ''}"

            ok, reason = validate_diagram(fen, caption, tactic)
            if not ok:
                continue

            svg = generate_svg_from_fen(fen)
            if not svg:
                continue

            d = {
                'id': str(uuid.uuid4()),
                'fen': fen,
                'svg': svg,
                'caption': caption,
                'tactic': tactic,
                'validated': True,
                'validation_reason': reason,
            }
            seen_fens.add(fen)
            backfilled.append(d)

            if len(backfilled) >= min(max_total, needed):
                return backfilled

    return backfilled

