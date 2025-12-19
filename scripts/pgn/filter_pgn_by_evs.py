#!/usr/bin/env python3
"""
Filter massive PGN files by EVS (Educational Value Score).

Modes
-----
1. single (default): keep every game with EVS >= medium threshold, write to --output.
2. split: route EVS >= high threshold to --high-output and medium-range EVS
   (medium_threshold <= EVS < high_threshold) to --medium-output.
   Lower EVS games are discarded.

Examples
--------
python scripts/filter_pgn_by_evs.py \\
    --input "/Volumes/T7 Shield/Deets/master_unknown.pgn" \\
    --output "/Volumes/T7 Shield/Deets/purged.pgn" \\
    --mode single --medium-threshold 45

python scripts/filter_pgn_by_evs.py \\
    --input "/Volumes/T7 Shield/Deets/master_unknown.pgn" \\
    --mode split \\
    --medium-output "/Volumes/T7 Shield/Deets/purged_mediums.pgn" \\
    --high-output "/Volumes/T7 Shield/Deets/purged_highs.pgn" \\
    --medium-threshold 45 --high-threshold 70
"""

from __future__ import annotations

import argparse
import io
import json
import re
from pathlib import Path
from typing import Iterable, Optional

import chess.pgn

from pgn_quality_analyzer import PGNQualityAnalyzer


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


_RAW_COMMENT_RE = re.compile(r"\{([^}]*)\}")


def _raw_comment_words(raw_game: str) -> int:
    comments = _RAW_COMMENT_RE.findall(raw_game)
    if not comments:
        return 0
    return sum(len(c.strip().split()) for c in comments if c.strip())


def filter_pgn(
    input_path: Path,
    *,
    mode: str,
    output_path: Optional[Path],
    medium_output: Optional[Path],
    high_output: Optional[Path],
    medium_threshold: float,
    high_threshold: float,
    log_every: int,
    drop_unparseable: bool,
    drop_unscorable: bool,
    verbose_errors: bool,
    report_only: bool,
) -> dict[str, int]:
    analyzer = PGNQualityAnalyzer(Path(":memory:"))
    stats = {
        "total": 0,
        "kept_single": 0,
        "kept_medium": 0,
        "kept_high": 0,
        "kept_unparseable": 0,
        "kept_unscorable": 0,
        "dropped_below_threshold": 0,
        "skipped": 0,
        "unparseable": 0,
        "unscorable": 0,
        "scorable": 0,
        "below_threshold": 0,
        "at_or_above_threshold": 0,
        "zero_verbal_total": 0,
        "zero_verbal_scorable": 0,
    }

    single_handle = None
    medium_handle = None
    high_handle = None

    if not report_only:
        if mode == "single":
            assert output_path is not None
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.exists():
                output_path.unlink()
            single_handle = output_path.open("w", encoding="utf-8")
        elif mode == "split":
            assert medium_output and high_output
            medium_output.parent.mkdir(parents=True, exist_ok=True)
            high_output.parent.mkdir(parents=True, exist_ok=True)
            for path in (medium_output, high_output):
                if path.exists():
                    path.unlink()
            medium_handle = medium_output.open("w", encoding="utf-8")
            high_handle = high_output.open("w", encoding="utf-8")
        else:  # range mode
            assert output_path is not None
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.exists():
                output_path.unlink()
            single_handle = output_path.open("w", encoding="utf-8")

    try:
        for stats["total"], raw_game in enumerate(iter_raw_games(input_path), start=1):
            if _raw_comment_words(raw_game) == 0:
                stats["zero_verbal_total"] += 1

            if log_every and stats["total"] % log_every == 0:
                print(
                    f"[heartbeat] {stats['total']:,} games | "
                    f"single={stats['kept_single']:,} | "
                    f"medium={stats['kept_medium']:,} | "
                    f"high={stats['kept_high']:,} | "
                    f"unparseable_kept={stats['kept_unparseable']:,} | "
                    f"unscorable_kept={stats['kept_unscorable']:,} | "
                    f"below_thr={stats['below_threshold']:,} | "
                    f"skipped={stats['skipped']:,}"
                )

            if not raw_game:
                stats["skipped"] += 1
                continue

            try:
                game = chess.pgn.read_game(io.StringIO(raw_game + "\n\n"))
            except Exception as exc:  # noqa: BLE001
                stats["unparseable"] += 1
                if drop_unparseable:
                    stats["skipped"] += 1
                    if verbose_errors:
                        print(f"   ⚠️  Failed to parse game #{stats['total']}: {exc}")
                    continue
                # Keep unparseable games to avoid losing ChessBase-readable content.
                if report_only:
                    stats["kept_unparseable"] += 1
                    continue
                if mode == "single":
                    if stats["kept_single"] > 0 or stats["kept_unparseable"] > 0:
                        single_handle.write("\n\n")
                    single_handle.write(raw_game.strip())
                    stats["kept_unparseable"] += 1
                elif mode == "split":
                    if stats["kept_medium"] > 0 or stats["kept_unparseable"] > 0:
                        medium_handle.write("\n\n")
                    medium_handle.write(raw_game.strip())
                    stats["kept_unparseable"] += 1
                else:  # range -> single output
                    if stats["kept_single"] > 0 or stats["kept_unparseable"] > 0:
                        single_handle.write("\n\n")
                    single_handle.write(raw_game.strip())
                    stats["kept_unparseable"] += 1
                if verbose_errors:
                    print(f"   ⚠️  Unparseable game kept #{stats['total']}: {exc}")
                continue

            scored = analyzer.score_game(game, file_name=input_path.name, game_index=stats["total"])
            if not scored:
                stats["unscorable"] += 1
                if drop_unscorable:
                    stats["skipped"] += 1
                    continue
                # Keep games we can't score (python-chess stricter than ChessBase).
                if report_only:
                    stats["kept_unscorable"] += 1
                    continue
                if mode == "single":
                    if stats["kept_single"] > 0 or stats["kept_unparseable"] > 0 or stats["kept_unscorable"] > 0:
                        single_handle.write("\n\n")
                    single_handle.write(raw_game.strip())
                    stats["kept_unscorable"] += 1
                elif mode == "split":
                    if stats["kept_medium"] > 0 or stats["kept_unparseable"] > 0 or stats["kept_unscorable"] > 0:
                        medium_handle.write("\n\n")
                    medium_handle.write(raw_game.strip())
                    stats["kept_unscorable"] += 1
                else:  # range -> single output
                    if stats["kept_single"] > 0 or stats["kept_unparseable"] > 0 or stats["kept_unscorable"] > 0:
                        single_handle.write("\n\n")
                    single_handle.write(raw_game.strip())
                    stats["kept_unscorable"] += 1
                continue

            evs = scored.evs
            stats["scorable"] += 1
            if scored.comment_words == 0:
                stats["zero_verbal_scorable"] += 1
            if evs < medium_threshold:
                stats["below_threshold"] += 1
            else:
                stats["at_or_above_threshold"] += 1

            if report_only:
                continue
            serialized = raw_game.strip()

            if mode == "single":
                if evs >= medium_threshold:
                    if stats["kept_single"] > 0 or stats["kept_unparseable"] > 0:
                        single_handle.write("\n\n")
                    single_handle.write(serialized)
                    stats["kept_single"] += 1
                else:
                    stats["dropped_below_threshold"] += 1
                    stats["skipped"] += 1
            elif mode == "split":
                if evs >= high_threshold:
                    if stats["kept_high"] > 0:
                        high_handle.write("\n\n")
                    high_handle.write(serialized)
                    stats["kept_high"] += 1
                elif evs >= medium_threshold:
                    if stats["kept_medium"] > 0 or stats["kept_unparseable"] > 0:
                        medium_handle.write("\n\n")
                    medium_handle.write(serialized)
                    stats["kept_medium"] += 1
                else:
                    stats["dropped_below_threshold"] += 1
                    stats["skipped"] += 1
            else:  # range
                low = medium_threshold
                high = high_threshold
                if low <= evs < high:
                    if stats["kept_single"] > 0 or stats["kept_unparseable"] > 0:
                        single_handle.write("\n\n")
                    single_handle.write(serialized)
                    stats["kept_single"] += 1
                else:
                    # Range mode: anything outside [low, high) is "dropped by threshold".
                    stats["dropped_below_threshold"] += 1
                    stats["skipped"] += 1
    finally:
        if single_handle:
            single_handle.close()
        if medium_handle:
            medium_handle.close()
        if high_handle:
            high_handle.close()

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter PGN games by EVS thresholds.")
    parser.add_argument("--input", required=True, help="Input PGN path.")
    parser.add_argument(
        "--mode",
        choices=["single", "split", "range"],
        default="single",
        help="single: >= medium threshold; split: separate medium/high; range: keep low<=EVS<high to a single file.",
    )
    parser.add_argument("--output", help="Output PGN path for single or range mode.")
    parser.add_argument("--medium-output", help="PGN path for medium games (split mode).")
    parser.add_argument("--high-output", help="PGN path for high games (split mode).")
    parser.add_argument("--medium-threshold", type=float, default=45.0, help="Minimum EVS for medium bucket.")
    parser.add_argument("--high-threshold", type=float, default=70.0, help="Minimum EVS for high bucket.")
    parser.add_argument("--log-every", type=int, default=1000, help="Heartbeat interval (games).")
    parser.add_argument(
        "--drop-unparseable",
        action="store_true",
        help="Drop games that python-chess cannot parse (default keeps them so nothing is lost).",
    )
    parser.add_argument(
        "--drop-unscorable",
        action="store_true",
        help="Drop games that parse but cannot be EVS-scored (default keeps them so nothing is lost).",
    )
    parser.add_argument(
        "--verbose-errors",
        action="store_true",
        help="Print per-game parse/score failures (default: quiet, just counts).",
    )
    parser.add_argument(
        "--stats-json",
        help="Write a JSON stats file for this run (useful for aggregating chunk runs).",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only compute stats; do not write any PGN output and do not drop anything.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input PGN not found: {input_path}")

    if args.mode == "single":
        if not args.report_only and not args.output:
            raise ValueError("--output is required in single mode")
        stats = filter_pgn(
            input_path,
            mode="single",
            output_path=(Path(args.output) if args.output else None),
            medium_output=None,
            high_output=None,
            medium_threshold=args.medium_threshold,
            high_threshold=args.high_threshold,
            log_every=args.log_every,
            drop_unparseable=args.drop_unparseable,
            drop_unscorable=args.drop_unscorable,
            verbose_errors=args.verbose_errors,
            report_only=args.report_only,
        )
        if args.stats_json:
            Path(args.stats_json).parent.mkdir(parents=True, exist_ok=True)
            Path(args.stats_json).write_text(json.dumps(stats, indent=2), encoding="utf-8")
        below_pct = (stats["below_threshold"] / stats["scorable"] * 100.0) if stats["scorable"] else 0.0
        below_total_pct = (stats["below_threshold"] / stats["total"] * 100.0) if stats["total"] else 0.0
        zv_pct = (stats["zero_verbal_total"] / stats["total"] * 100.0) if stats["total"] else 0.0
        print(
            f"Done. Total={stats['total']:,} | scorable={stats['scorable']:,} | below_thr={stats['below_threshold']:,} "
            f"({below_pct:.2f}% of scorable, {below_total_pct:.2f}% of total) | "
            f"zero_verbal={stats['zero_verbal_total']:,} ({zv_pct:.2f}% of total) | "
            f"kept_unparseable={stats['kept_unparseable']:,} | kept_unscorable={stats['kept_unscorable']:,} "
            f"| threshold={args.medium_threshold}"
        )
    elif args.mode == "split":
        if not args.medium_output or not args.high_output:
            raise ValueError("--medium-output and --high-output are required in split mode")
        stats = filter_pgn(
            input_path,
            mode="split",
            output_path=None,
            medium_output=Path(args.medium_output),
            high_output=Path(args.high_output),
            medium_threshold=args.medium_threshold,
            high_threshold=args.high_threshold,
            log_every=args.log_every,
            drop_unparseable=args.drop_unparseable,
            drop_unscorable=args.drop_unscorable,
            verbose_errors=args.verbose_errors,
            report_only=args.report_only,
        )
        if args.stats_json:
            Path(args.stats_json).parent.mkdir(parents=True, exist_ok=True)
            Path(args.stats_json).write_text(json.dumps(stats, indent=2), encoding="utf-8")
        print(
            f"Done. Total={stats['total']:,} | medium-kept={stats['kept_medium']:,} "
            f"| high-kept={stats['kept_high']:,} | kept_unparseable={stats['kept_unparseable']:,} "
            f"| kept_unscorable={stats['kept_unscorable']:,} "
            f"| dropped_by_score={stats['dropped_below_threshold']:,} | skipped={stats['skipped']:,} "
            f"| thresholds=({args.medium_threshold}, {args.high_threshold})"
        )
    else:  # range mode
        if not args.report_only and not args.output:
            raise ValueError("--output is required in range mode")
        low = args.medium_threshold
        high = args.high_threshold
        stats = filter_pgn(
            input_path,
            mode="range",
            output_path=(Path(args.output) if args.output else None),
            medium_output=None,
            high_output=None,
            medium_threshold=low,
            high_threshold=high,
            log_every=args.log_every,
            drop_unparseable=args.drop_unparseable,
            drop_unscorable=args.drop_unscorable,
            verbose_errors=args.verbose_errors,
            report_only=args.report_only,
        )
        if args.stats_json:
            Path(args.stats_json).parent.mkdir(parents=True, exist_ok=True)
            Path(args.stats_json).write_text(json.dumps(stats, indent=2), encoding="utf-8")
        print(
            f"Done. Total={stats['total']:,} | kept={stats['kept_single']:,} "
            f"| kept_unparseable={stats['kept_unparseable']:,} | kept_unscorable={stats['kept_unscorable']:,} "
            f"| dropped_by_score={stats['dropped_below_threshold']:,} | skipped={stats['skipped']:,} "
            f"| EVS range [{low}, {high})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
