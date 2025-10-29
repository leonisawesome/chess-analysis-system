#!/usr/bin/env python3
import os, pathlib, random, tempfile
import sys
sys.path.insert(0, '.')
from chess_rag_system.analysis._signals import pgn_ratio

OUT = pathlib.Path("tests/fixtures/pgn_boundary")
OUT.mkdir(parents=True, exist_ok=True)

# Candidate PGN-ish lines (diverse; the analyzer will be the judge)
PGN_CANDIDATES = [
    '[Event "Boundary Test"]',
    '[Site "Somewhere"]', '[Date "2022.01.01"]', '[Round "1"]',
    '[White "A"]', '[Black "B"]', '[Result "1-0"]',
    '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6', '1... c5 2. Nf3 d6 3. d4 cxd4',
    '23... Qg5 24. g3 Qh5 25. Qe2 Qxh2+', '12. Bb5+ c6 13. dxc6'
]
FILLER = "This is filler prose; not PGN."

def pgn_ratio_of_text(text: str) -> float:
    return pgn_ratio(text)

def filter_recognized_pgn_lines():
    ok=[]
    # Keep lines the analyzer actually counts toward pgn_ratio
    for line in PGN_CANDIDATES:
        pr = pgn_ratio_of_text(line + "\n" + FILLER + "\n")
        if pr > 0.0:
            ok.append(line)
    # Fallback: if none recognized, we still proceed (ratio tuning will show failure)
    return ok if ok else PGN_CANDIDATES[:1]

def build_target(target: float, total_lines: int, ok_lines):
    # Start with a guess; then adjust using the analyzer as oracle
    lo, hi = 0, total_lines
    best_text, best_err = "", 1.0
    for _ in range(14):  # few iterations suffice
        n_pgn = int(round((lo+hi)/2))
        # Assemble text with n_pgn lines sampled from ok_lines
        lines = [random.choice(ok_lines) for _ in range(n_pgn)]
        lines += [FILLER] * (total_lines - n_pgn)
        random.Random(42).shuffle(lines)
        text = "\n".join(lines) + "\n"
        pr = pgn_ratio_of_text(text)
        err = abs(pr - target)
        if err < best_err:
            best_text, best_err = text, err
        if pr < target: lo = n_pgn + 1
        else:           hi = max(0, n_pgn - 1)
    return best_text, best_err

def main():
    ok_lines = filter_recognized_pgn_lines()
    targets = [0.320, 0.335, 0.345, 0.355, 0.370]
    total = 300  # keeps files small and stable

    for t in targets:
        txt, err = build_target(t, total, ok_lines)
        pr = pgn_ratio_of_text(txt)
        name = OUT / f"pgn_ratio_target_{t:.3f}_actual_{pr:.3f}.txt"
        name.write_text(txt)
        print(f"Wrote {name} (|err|={err:.4f})")

if __name__ == "__main__":
    main()