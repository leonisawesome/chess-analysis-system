#!/usr/bin/env python3
"""
Sample top X% of games by EVS from a PGN file.

Usage:
    python scripts/sample_top_evs.py \\
        --input "/path/to/input.pgn" \\
        --output "/path/to/output.pgn" \\
        --percent 10
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import List, Tuple

import chess.pgn

from pgn_quality_analyzer import PGNQualityAnalyzer


def iter_raw_games(filepath: Path) -> List[str]:
    """Load all raw PGN strings from file."""
    games = []
    with filepath.open("r", encoding="utf-8", errors="ignore") as handle:
        buffer: list[str] = []
        for line in handle:
            stripped = line.lstrip()
            if stripped.startswith("[Event "):
                if buffer:
                    games.append("".join(buffer).strip())
                    buffer = [line]
                else:
                    buffer.append(line)
            else:
                buffer.append(line)
        if buffer:
            games.append("".join(buffer).strip())
    return games


def sample_top_evs(
    input_path: Path,
    output_path: Path,
    percent: float,
) -> dict[str, int]:
    """Sample top X% of games by EVS score."""

    print(f"Loading games from: {input_path}")
    raw_games = iter_raw_games(input_path)
    total = len(raw_games)
    print(f"Found {total:,} games.")

    # Calculate EVS for each game
    print("Calculating EVS scores...")
    analyzer = PGNQualityAnalyzer(Path(":memory:"))
    game_scores: List[Tuple[float, str]] = []

    for idx, raw_game in enumerate(raw_games, 1):
        if idx % 10000 == 0:
            print(f"  [progress] Scored {idx:,}/{total:,} games")

        try:
            game = chess.pgn.read_game(io.StringIO(raw_game))
            if game is None:
                continue

            evs = analyzer.compute_evs(game)
            game_scores.append((evs, raw_game))
        except Exception:
            # Skip games that fail to parse
            continue

    print(f"Successfully scored {len(game_scores):,} games.")

    # Sort by EVS descending
    print("Sorting by EVS...")
    game_scores.sort(key=lambda x: x[0], reverse=True)

    # Take top X%
    keep_count = int(len(game_scores) * (percent / 100.0))
    top_games = game_scores[:keep_count]

    print(f"Keeping top {percent}% = {keep_count:,} games")

    # Write output
    print(f"Writing to: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    with output_path.open("w", encoding="utf-8") as handle:
        for idx, (evs, raw_game) in enumerate(top_games, 1):
            if idx > 1:
                handle.write("\n\n")
            handle.write(raw_game)

    print(f"✓ Done! Wrote {keep_count:,} games to {output_path}")

    return {
        "total": total,
        "scored": len(game_scores),
        "kept": keep_count,
    }


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample top X% of games by EVS.")
    parser.add_argument("--input", required=True, help="Input PGN file.")
    parser.add_argument("--output", required=True, help="Output PGN file.")
    parser.add_argument("--percent", type=float, default=10.0, help="Percentage to keep (default: 10).")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    input_path = Path(args.input).expanduser()
    output_path = Path(args.output).expanduser()

    print("=" * 80)
    print("PGN EVS SAMPLER")
    print("=" * 80)
    print(f"Input  : {input_path}")
    print(f"Output : {output_path}")
    print(f"Percent: {args.percent}%")
    print("=" * 80)

    stats = sample_top_evs(input_path, output_path, args.percent)

    print()
    print("=" * 80)
    print("FINAL STATISTICS")
    print("=" * 80)
    print(f"Total games     : {stats['total']:,}")
    print(f"Successfully scored: {stats['scored']:,}")
    print(f"Kept (top {args.percent}%) : {stats['kept']:,}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
