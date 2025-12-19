#!/usr/bin/env python3
"""
Partition a PGN into "verbal prose word count" slices without validating move
legality (ChessBase-friendly; parser-agnostic).

Verbal score = count of word tokens in PGN comments:
  - brace comments: { ... } (can span lines)
  - semicolon comments: ; ... (to end-of-line), only when not inside braces

Before word counting, strip control codes like:
  - [%eval ...] [%clk ...] [%csl ...] [%cal ...] ...

Word token definition (English/Spanish/German accents):
  - [A-Za-zÀ-ÖØ-öø-ÿ]{2,}

No de-duplication is performed. Buckets are provided by CLI as:
  --bucket "0-14=/path/to/0-14.pgn"
  --bucket "40-49=/path/to/40-49.pgn"
  --bucket "50+=/path/to/50plus.pgn"

Ranges are inclusive; "A+" means A..infinity.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


CONTROL_CODE_RE = re.compile(r"\[%[^\]]*\]")
WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]{2,}")


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


def extract_comment_texts(raw_game: str) -> list[str]:
    """
    Extract { ... } and ;... comments from a raw game.

    - Braces can span multiple lines.
    - Semicolons count only outside braces.
    - Nested braces are not standard PGN, but we tolerate them by tracking depth.
    """
    comments: list[str] = []
    brace_depth = 0
    buf: list[str] = []
    i = 0
    n = len(raw_game)
    while i < n:
        ch = raw_game[i]
        if ch == "{":
            if brace_depth == 0:
                buf = []
            brace_depth += 1
            i += 1
            continue

        if ch == "}" and brace_depth > 0:
            brace_depth -= 1
            if brace_depth == 0:
                comments.append("".join(buf))
                buf = []
            i += 1
            continue

        if brace_depth > 0:
            buf.append(ch)
            i += 1
            continue

        if ch == ";":
            j = i + 1
            while j < n and raw_game[j] not in "\r\n":
                j += 1
            comments.append(raw_game[i + 1 : j])
            i = j
            continue

        i += 1

    return comments


def verbal_score(raw_game: str) -> int:
    comments = extract_comment_texts(raw_game)
    if not comments:
        return 0
    text = " ".join(comments)
    text = CONTROL_CODE_RE.sub(" ", text)
    return len(WORD_RE.findall(text))


def _open_append(path: Path) -> tuple[Optional[object], bool]:
    """
    Open for append, returning (handle, needs_separator).
    needs_separator=True means file already has content and next write should
    start with a blank line separator.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_sep = path.exists() and path.stat().st_size > 0
    handle = path.open("a", encoding="utf-8")
    return handle, needs_sep


@dataclass(frozen=True)
class Bucket:
    label: str
    min_inclusive: int
    max_inclusive: Optional[int]  # None means "no upper bound"
    out_path: Path

    def matches(self, score: int) -> bool:
        if score < self.min_inclusive:
            return False
        if self.max_inclusive is None:
            return True
        return score <= self.max_inclusive


_RANGE_RE = re.compile(r"^(?P<a>\d+)\s*-\s*(?P<b>\d+)$")
_PLUS_RE = re.compile(r"^(?P<a>\d+)\s*\+$")
_SINGLE_RE = re.compile(r"^(?P<a>\d+)$")


def parse_bucket_spec(spec: str) -> Bucket:
    """
    Parse a bucket spec of the form:
      - "0-14=/path/to/0-14.pgn"
      - "40-49=/path/to/40-49.pgn"
      - "50+=/path/to/50plus.pgn"
      - "12=/path/to/exact_12.pgn"
    """
    if "=" not in spec:
        raise ValueError(f"Invalid --bucket (missing '='): {spec!r}")
    raw_range, raw_path = spec.split("=", 1)
    raw_range = raw_range.strip()
    raw_path = raw_path.strip()
    if not raw_range:
        raise ValueError(f"Invalid --bucket (empty range): {spec!r}")
    if not raw_path:
        raise ValueError(f"Invalid --bucket (empty output path): {spec!r}")

    m = _RANGE_RE.match(raw_range)
    if m:
        a = int(m.group("a"))
        b = int(m.group("b"))
        if b < a:
            raise ValueError(f"Invalid --bucket (max < min): {spec!r}")
        return Bucket(label=f"{a}-{b}", min_inclusive=a, max_inclusive=b, out_path=Path(raw_path))

    m = _PLUS_RE.match(raw_range)
    if m:
        a = int(m.group("a"))
        return Bucket(label=f"{a}+", min_inclusive=a, max_inclusive=None, out_path=Path(raw_path))

    m = _SINGLE_RE.match(raw_range)
    if m:
        a = int(m.group("a"))
        return Bucket(label=f"{a}", min_inclusive=a, max_inclusive=a, out_path=Path(raw_path))

    raise ValueError(f"Invalid --bucket range (expected A-B, A+, or N): {raw_range!r}")


def partition_ranges(
    input_path: Path,
    *,
    buckets: list[Bucket],
    log_every: int,
    append: bool,
    max_games: int,
    multi_match: bool,
) -> dict[str, int]:
    if not buckets:
        raise ValueError("No buckets provided")

    stats: dict[str, int] = {"total": 0}
    for b in buckets:
        stats[b.label] = 0

    if not append:
        for b in buckets:
            if b.out_path.exists():
                b.out_path.unlink()

    handles: dict[str, object] = {}
    needs_sep: dict[str, bool] = {}
    try:
        for b in buckets:
            handle, sep = _open_append(b.out_path)
            handles[b.label] = handle
            needs_sep[b.label] = sep

        for stats["total"], raw_game in enumerate(iter_raw_games(input_path), start=1):
            if max_games and stats["total"] > max_games:
                break

            if log_every and stats["total"] % log_every == 0:
                parts = [f"[heartbeat] {stats['total']:,} games"]
                for b in buckets:
                    parts.append(f"{b.label}={stats[b.label]:,}")
                print(" | ".join(parts))

            if not raw_game:
                score = 0
                serialized = ""
            else:
                score = verbal_score(raw_game)
                serialized = raw_game.strip()

            matched_any = False
            for b in buckets:
                if not b.matches(score):
                    continue
                matched_any = True

                if serialized:
                    if needs_sep[b.label]:
                        handles[b.label].write("\n\n")
                    handles[b.label].write(serialized)
                    needs_sep[b.label] = True

                stats[b.label] += 1
                if not multi_match:
                    break

            if not matched_any:
                continue
    finally:
        for h in handles.values():
            try:
                h.close()
            except Exception:
                pass

    return stats


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Partition PGN games into verbal-score ranges.")
    p.add_argument("--input", required=True, help="Input PGN path.")
    p.add_argument(
        "--bucket",
        action="append",
        default=[],
        help="Repeatable bucket spec: RANGE=OUTPUT (RANGE is A-B, A+, or N).",
    )
    p.add_argument("--out-0-14", default="", help="(legacy) Output PGN path for 0-14 range.")
    p.add_argument("--out-15-29", default="", help="(legacy) Output PGN path for 15-29 range.")
    p.add_argument("--out-30-44", default="", help="(legacy) Output PGN path for 30-44 range.")
    p.add_argument("--out-45-plus", default="", help="(legacy) Output PGN path for 45+ range.")
    p.add_argument("--log-every", type=int, default=5000, help="Heartbeat interval (games).")
    p.add_argument("--append", action="store_true", help="Append to outputs instead of overwriting.")
    p.add_argument("--max-games", type=int, default=0, help="Optional cap for testing (0 = no limit).")
    p.add_argument(
        "--multi-match",
        action="store_true",
        help="Write games to all matching buckets (default: first matching bucket only).",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input PGN not found: {input_path}")

    buckets: list[Bucket] = []
    for spec in args.bucket:
        buckets.append(parse_bucket_spec(spec))

    if not buckets:
        # Backwards compatible behavior (previous fixed bucket set).
        if not (args.out_0_14 and args.out_15_29 and args.out_30_44 and args.out_45_plus):
            raise SystemExit("ERROR: Provide at least one --bucket RANGE=OUTPUT (recommended).")
        buckets = [
            Bucket(label="0-14", min_inclusive=0, max_inclusive=14, out_path=Path(args.out_0_14)),
            Bucket(label="15-29", min_inclusive=15, max_inclusive=29, out_path=Path(args.out_15_29)),
            Bucket(label="30-44", min_inclusive=30, max_inclusive=44, out_path=Path(args.out_30_44)),
            Bucket(label="45+", min_inclusive=45, max_inclusive=None, out_path=Path(args.out_45_plus)),
        ]

    stats = partition_ranges(
        input_path,
        buckets=buckets,
        log_every=int(args.log_every),
        append=bool(args.append),
        max_games=int(args.max_games),
        multi_match=bool(args.multi_match),
    )

    total = stats["total"]
    def pct(x: int) -> str:
        return f"{(x / total * 100.0):.2f}%" if total else "0.00%"

    parts = [f"Done. Total={total:,}"]
    for b in buckets:
        parts.append(f"{b.label}={stats[b.label]:,} ({pct(stats[b.label])})")
    print(" | ".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
