#!/usr/bin/env python3
"""
Filter a PGN by "verbal annotations" without parsing moves.

Definition (default):
- A game is "verbal" if it contains at least 1 word-like token inside a `{...}` comment.
- Word-like token = letters (ASCII or common Latin-1 accented letters).

This is intentionally stricter than "has any comment", so comments like `{[%eval +0.23]}`
or `{!?}` count as zero-verbal and will be dropped.

This script does NOT use python-chess, so it won't drop games due to "illegal san".
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable, Optional


def iter_raw_games(filepath: Path) -> Iterable[str]:
    """Yield raw PGN strings without loading everything in memory."""
    with filepath.open("r", encoding="utf-8", errors="ignore") as handle:
        buffer: list[str] = []
        for line in handle:
            stripped = line.lstrip()
            if stripped.startswith("[Event "):
                if buffer:
                    yield "".join(buffer).strip()
                    buffer = [line]
                else:
                    buffer.append(line)
            else:
                buffer.append(line)
        if buffer:
            yield "".join(buffer).strip()


COMMENT_RE = re.compile(r"\{([^}]*)\}")
WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+")


def verbal_word_count(raw_game: str) -> int:
    comments = COMMENT_RE.findall(raw_game)
    if not comments:
        return 0
    return sum(len(WORD_RE.findall(c)) for c in comments)


def filter_zero_verbal(
    input_path: Path,
    *,
    output_path: Optional[Path],
    min_verbal_words: int,
    log_every: int,
    report_only: bool,
) -> dict[str, int]:
    stats = {
        "total": 0,
        "kept": 0,
        "dropped_zero_verbal": 0,
        "zero_verbal": 0,
    }

    out_handle = None
    if not report_only:
        assert output_path is not None
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            output_path.unlink()
        out_handle = output_path.open("w", encoding="utf-8")

    try:
        for stats["total"], raw_game in enumerate(iter_raw_games(input_path), start=1):
            if log_every and stats["total"] % log_every == 0:
                print(
                    f"[heartbeat] {stats['total']:,} games | kept={stats['kept']:,} | "
                    f"dropped_zero_verbal={stats['dropped_zero_verbal']:,}"
                )

            if not raw_game:
                continue

            words = verbal_word_count(raw_game)
            if words < min_verbal_words:
                stats["zero_verbal"] += 1
                stats["dropped_zero_verbal"] += 1
                continue

            stats["kept"] += 1
            if report_only:
                continue

            if stats["kept"] > 1:
                out_handle.write("\n\n")
            out_handle.write(raw_game.strip())
    finally:
        if out_handle:
            out_handle.close()

    return stats


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Drop games with zero verbal annotations.")
    p.add_argument("--input", required=True, help="Input PGN path.")
    p.add_argument("--output", help="Output PGN path (omitted in --report-only mode).")
    p.add_argument("--min-verbal-words", type=int, default=1, help="Minimum verbal words in comments to keep a game.")
    p.add_argument("--log-every", type=int, default=5000, help="Heartbeat interval (games).")
    p.add_argument("--report-only", action="store_true", help="Only report stats; do not write output.")
    p.add_argument("--stats-json", help="Write stats JSON to this path.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input PGN not found: {input_path}")

    if not args.report_only and not args.output:
        raise ValueError("--output is required unless --report-only is set")

    stats = filter_zero_verbal(
        input_path,
        output_path=(Path(args.output) if args.output else None),
        min_verbal_words=max(int(args.min_verbal_words), 1),
        log_every=int(args.log_every),
        report_only=bool(args.report_only),
    )

    if args.stats_json:
        out = Path(args.stats_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    pct = (stats["dropped_zero_verbal"] / stats["total"] * 100.0) if stats["total"] else 0.0
    print(
        f"Done. Total={stats['total']:,} | kept={stats['kept']:,} | "
        f"dropped_zero_verbal={stats['dropped_zero_verbal']:,} ({pct:.2f}%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

