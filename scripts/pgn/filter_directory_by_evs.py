#!/usr/bin/env python3
"""
Walk a directory tree, score every PGN game by EVS (Educational Value Score),
and stream medium/high-quality games into two master PGNs.

Example:
    python scripts/filter_directory_by_evs.py \
        --root "/Users/leon/Downloads/3unknown" \
        --medium-output "/Volumes/T7 Shield/rag/databases/pgn/1new/medium_value.pgn" \
        --high-output "/Volumes/T7 Shield/rag/databases/pgn/1new/high_value.pgn" \
        --medium-threshold 45 --high-threshold 70 \
        --log-every 2000
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path
from typing import Iterable

import chess.pgn

from pgn_quality_analyzer import PGNQualityAnalyzer


def iter_raw_games(filepath: Path) -> Iterable[str]:
    """Yield raw PGN strings from a file."""
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


def score_directory(
    root: Path,
    medium_handle,
    high_handle,
    medium_threshold: float,
    high_threshold: float,
    log_every: int,
) -> dict[str, int]:
    analyzer = PGNQualityAnalyzer(Path(":memory:"))
    stats = {"total": 0, "kept_medium": 0, "kept_high": 0, "skipped": 0}

    pgn_files = sorted(
        p for p in root.rglob("*.pgn") if p.is_file() and not p.name.startswith("._")
    )
    for file_idx, file_path in enumerate(pgn_files, start=1):
        print(f"[info] Processing ({file_idx}/{len(pgn_files)}): {file_path}")
        for raw_game in iter_raw_games(file_path):
            stats["total"] += 1
            if log_every and stats["total"] % log_every == 0:
                print(
                    f"[heartbeat] {stats['total']:,} games processed "
                    f"| medium={stats['kept_medium']:,} | high={stats['kept_high']:,} "
                    f"| skipped={stats['skipped']:,}"
                )
            if not raw_game:
                stats["skipped"] += 1
                continue
            try:
                game = chess.pgn.read_game(io.StringIO(raw_game + "\n\n"))
            except Exception as exc:  # noqa: BLE001
                stats["skipped"] += 1
                print(f"   ⚠️  Failed to parse game #{stats['total']}: {exc}")
                continue

            scored = analyzer.score_game(game, file_name=file_path.name, game_index=stats["total"])
            if not scored:
                stats["skipped"] += 1
                continue

            evs = scored.evs
            serialized = str(game).strip()
            if evs >= high_threshold:
                if stats["kept_high"] > 0:
                    high_handle.write("\n\n")
                high_handle.write(serialized)
                stats["kept_high"] += 1
            elif evs >= medium_threshold:
                if stats["kept_medium"] > 0:
                    medium_handle.write("\n\n")
                medium_handle.write(serialized)
                stats["kept_medium"] += 1
            else:
                stats["skipped"] += 1
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split high/medium EVS games into master PGNs.")
    parser.add_argument("--root", required=True, help="Root directory containing .pgn files.")
    parser.add_argument("--medium-output", required=True, help="Destination PGN for medium EVS games.")
    parser.add_argument("--high-output", required=True, help="Destination PGN for high EVS games.")
    parser.add_argument("--medium-threshold", type=float, default=45.0, help="Minimum EVS for medium bucket.")
    parser.add_argument("--high-threshold", type=float, default=70.0, help="Minimum EVS for high bucket.")
    parser.add_argument("--log-every", type=int, default=2000, help="Heartbeat interval (games).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    if not root.exists():
        raise FileNotFoundError(f"Root directory not found: {root}")

    medium_output = Path(args.medium_output)
    high_output = Path(args.high_output)
    medium_output.parent.mkdir(parents=True, exist_ok=True)
    high_output.parent.mkdir(parents=True, exist_ok=True)
    if medium_output.exists():
        medium_output.unlink()
    if high_output.exists():
        high_output.unlink()

    with medium_output.open("w", encoding="utf-8") as medium_handle, high_output.open(
        "w", encoding="utf-8"
    ) as high_handle:
        stats = score_directory(
            root,
            medium_handle,
            high_handle,
            args.medium_threshold,
            args.high_threshold,
            args.log_every,
        )

    print(
        f"Done. Total={stats['total']:,} | medium-kept={stats['kept_medium']:,} "
        f"| high-kept={stats['kept_high']:,} | skipped={stats['skipped']:,}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
