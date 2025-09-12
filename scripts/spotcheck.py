#!/usr/bin/env python3
import argparse, sys, json, pathlib
from chess_rag_system.analysis.instructional_detector import (
    detect_instructional,
    _PGN_CUTOFF, _DIDACTIC_BOOST, _HEADINGS_BOOST, _ENGINE_NEG_HITS, _TOC_NEG_HITS, _ANNOT_POS_HITS,
)
from chess_rag_system.analysis._signals import (
    pgn_ratio, didactic_hits_per_1k, heading_hits, engine_dump_hits, annotation_hits, toc_like_hits
)


def analyze(label: str, text: str):
    metrics = {
        "pgn_ratio": round(pgn_ratio(text), 3),
        "engine_hits": engine_dump_hits(text),
        "toc_hits": toc_like_hits(text),
        "didactic_per_1k": didactic_hits_per_1k(text),
        "heading_hits": heading_hits(text),
        "annot_hits": annotation_hits(text),
    }
    triggers = []
    if metrics["pgn_ratio"] >= _PGN_CUTOFF:
        triggers.append(f"PGN_NEG(≥{_PGN_CUTOFF})")
    if metrics["engine_hits"] >= _ENGINE_NEG_HITS:
        triggers.append(f"ENGINE_NEG(≥{_ENGINE_NEG_HITS})")
    if metrics["toc_hits"] >= _TOC_NEG_HITS:
        triggers.append(f"TOC_NEG(≥{_TOC_NEG_HITS})")
    if metrics["didactic_per_1k"] >= _DIDACTIC_BOOST:
        triggers.append(f"DIDACTIC_POS(≥{_DIDACTIC_BOOST})")
    if metrics["heading_hits"] >= _HEADINGS_BOOST:
        triggers.append(f"HEADINGS_POS(≥{_HEADINGS_BOOST})")
    if metrics["annot_hits"] >= _ANNOT_POS_HITS:
        triggers.append(f"ANNOT_POS(≥{_ANNOT_POS_HITS})")

    decision = bool(detect_instructional(text))
    return {
        "label": label,
        "decision": decision,
        "triggers": triggers,
        "metrics": metrics,
        "thresholds": {
            "PGN_CUTOFF": _PGN_CUTOFF,
            "ENGINE_NEG_HITS": _ENGINE_NEG_HITS,
            "TOC_NEG_HITS": _TOC_NEG_HITS,
            "DIDACTIC_BOOST": _DIDACTIC_BOOST,
            "HEADINGS_BOOST": _HEADINGS_BOOST,
            "ANNOT_POS_HITS": _ANNOT_POS_HITS,
        },
    }


def read_text(path: pathlib.Path) -> str:
    # Simple, robust read (for .txt/.pgn/.md). For PDFs, just paste text via --text.
    return path.read_text(encoding="utf-8", errors="ignore")


def main():
    ap = argparse.ArgumentParser(description="Quick spot-check for instructional detector")
    ap.add_argument("paths", nargs="*", help="Files to check (txt/pgn/md).")
    ap.add_argument("--text", help="Inline text sample to check.")
    args = ap.parse_args()

    items = []
    if args.text:
        items.append(("INLINE", args.text))
    for p in args.paths:
        path = pathlib.Path(p)
        if path.is_file():
            items.append((str(path), read_text(path)))
        else:
            print(f"warn: not a file: {p}", file=sys.stderr)

    if not items:
        print("No input. Use --text 'your text' or pass file paths.", file=sys.stderr)
        sys.exit(2)

    results = [analyze(label, text) for label, text in items]
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

