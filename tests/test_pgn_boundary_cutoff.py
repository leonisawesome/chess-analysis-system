import glob, pathlib
import sys
sys.path.insert(0, '.')
from chess_rag_system.analysis._signals import pgn_ratio

def measure(P):
    text = P.read_text(encoding='utf-8', errors='ignore')
    return pgn_ratio(text)

def test_boundary_fixtures_exist_and_span():
    files = sorted(glob.glob("tests/fixtures/pgn_boundary/*.txt"))
    assert files, "Generate boundary fixtures first: scripts/gen_pgn_boundary_oracle.py"
    vals = [measure(pathlib.Path(f)) for f in files]
    assert any(0.33 <= v < 0.35 for v in vals), f"No fixture in (0.33,0.35): {vals}"
    assert any(v < 0.33 for v in vals) and any(v >= 0.35 for v in vals), f"Need both sides of cutoff: {vals}"