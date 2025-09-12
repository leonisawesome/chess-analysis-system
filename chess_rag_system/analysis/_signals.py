import re
from typing import Iterable

# Rough SAN tokens (KQRBN optional, square, promotions), move numbers like "12." or "12..."
_SAN_MOVE = re.compile(r"\b(?:[KQRBN])?[a-h][1-8](?:=[QRBN])?[+#]?\b")
_MOVE_NUM = re.compile(r"\b\d{1,3}\.(?:\.\.)?\b")  # 1.  or 1... (black to move)
_RESULT = re.compile(r"\b1-0|0-1|1/2-1/2\b")

_DIDACTIC = {
    # keep small and obvious; expand later
    "plan",
    "plans",
    "idea",
    "ideas",
    "key",
    "typical",
    "principle",
    "principles",
    "aim",
    "aims",
    "avoid",
    "mistake",
    "mistakes",
    "strategy",
    "strategic",
    "structure",
    "structures",
    "improve",
    "manoeuvre",
    "manuever",
    "manoeuvres",
    "remember",
    "explain",
    "explains",
    "explained",
    "theme",
    "themes",
    "concepts",
}


def tokens(text: str) -> Iterable[str]:
    return re.findall(r"[A-Za-z0-9\.\+\#=/\-]+", text)


def pgn_ratio(text: str) -> float:
    """Share of tokens that look like SAN moves or move numbers/results."""
    toks = list(tokens(text))
    if not toks:
        return 0.0
    pgnish = 0
    for t in toks:
        if _SAN_MOVE.fullmatch(t) or _MOVE_NUM.fullmatch(t) or _RESULT.fullmatch(t):
            pgnish += 1
    return pgnish / max(1, len(toks))


def didactic_hits_per_1k(text: str) -> int:
    """Count of didactic words per ~1000 tokens, rounded down."""
    toks = [t.lower() for t in tokens(text)]
    if not toks:
        return 0
    hits = sum(1 for t in toks if t in _DIDACTIC)
    return int(1000 * hits / max(1, len(toks)))

