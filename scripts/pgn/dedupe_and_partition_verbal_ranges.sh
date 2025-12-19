#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Deduplicate a big PGN (exact duplicates only), then partition the deduped games
into NON-overlapping verbal-score ranges:
  - 15-29_range.pgn
  - 30-44_range.pgn
  - 45plus_range.pgn

"Verbal score" = count of word tokens in comments ({...} and ;...),
after stripping [%... ] control codes. Word token regex:
  [A-Za-zÀ-ÖØ-öø-ÿ]{2,}

Games with score < 15 are NOT written to any range file.
Nothing is deleted: deduped chunks remain in the job directory.

Usage:
  bash scripts/pgn/dedupe_and_partition_verbal_ranges.sh INPUT.pgn OUT_DIR

Example:
  bash scripts/pgn/dedupe_and_partition_verbal_ranges.sh \
    "/Users/leon/Downloads/chess/New Database.pgn" \
    "/Users/leon/Downloads/chess"

Optional env vars:
  TOTAL_GAMES_HINT=9222501
  GAMES_PER_CHUNK=50000
  CHESS_DEDUP_SQLITE_COMMIT_EVERY=5000
  DUMP_DUPES=1           # write duplicates to duplicates.pgn
  DUPES_LIMIT=0          # 0 = unlimited
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 2 ]]; then
  usage
  exit 2
fi

IN_PGN="$1"
BASE_OUT_DIR="$2"

if [[ ! -f "$IN_PGN" ]]; then
  echo "ERROR: input PGN not found: $IN_PGN" >&2
  exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ ! -f "$REPO_DIR/scripts/pgn/dedupe_massive_pgn.py" ]]; then
  echo "ERROR: repo root not found from script path: $REPO_DIR" >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! "$PYTHON_BIN" -c "import chess, chess.pgn" >/dev/null 2>&1; then
  echo "ERROR: python-chess is not importable from $PYTHON_BIN." >&2
  echo "Install it for that Python: $PYTHON_BIN -m pip install python-chess" >&2
  exit 1
fi

mkdir -p "$BASE_OUT_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
JOB_DIR="$BASE_OUT_DIR/_jobs/verbal_ranges_${STAMP}"

mkdir -p "$JOB_DIR"/{logs,dedup_chunks}

export PYTHONPATH="$REPO_DIR"
export PYTHONUNBUFFERED=1

# Always use SQLite for the hash store (no Postgres required).
export CHESS_DEDUP_BACKEND=sqlite
export CHESS_DEDUP_SQLITE_PATH="$JOB_DIR/dedup_hashes.sqlite3"
export CHESS_DEDUP_SQLITE_COMMIT_EVERY="${CHESS_DEDUP_SQLITE_COMMIT_EVERY:-5000}"

TOTAL_GAMES_HINT="${TOTAL_GAMES_HINT:-}"
GAMES_PER_CHUNK="${GAMES_PER_CHUNK:-50000}"
DUMP_DUPES="${DUMP_DUPES:-0}"
DUPES_LIMIT="${DUPES_LIMIT:-0}"

filter_console_noise() {
  awk '
    /illegal san:/ { next }
    /Failed to parse game/ { next }
    /Unparseable game kept/ { next }
    /⚠️/ { next }
    { print }
  '
}

echo "Job dir: $JOB_DIR"
echo "Input:   $IN_PGN"
echo "Outputs: $JOB_DIR/0-14_range.pgn  $JOB_DIR/15-29_range.pgn  $JOB_DIR/30-44_range.pgn  $JOB_DIR/45plus_range.pgn"
echo

echo "Stage 1/2: DEDUPE (exact duplicates only)"
(
  cd "$JOB_DIR"
  args=( "$IN_PGN" "--output-dir" "$JOB_DIR/dedup_chunks" "--games-per-chunk" "$GAMES_PER_CHUNK" )
  if [[ -n "$TOTAL_GAMES_HINT" ]]; then
    args+=( "--total-games" "$TOTAL_GAMES_HINT" )
  fi
  if [[ "$DUMP_DUPES" == "1" ]]; then
    args+=( "--duplicates-out" "$JOB_DIR/duplicates.pgn" "--duplicates-limit" "$DUPES_LIMIT" )
  fi
  "$PYTHON_BIN" -u "$REPO_DIR/scripts/pgn/dedupe_massive_pgn.py" "${args[@]}" \
    2>&1 | tee "$JOB_DIR/logs/dedupe.log" | filter_console_noise
)

echo
echo "Stage 2/2: PARTITION VERBAL RANGES (no chess parsing)"
rm -f "$JOB_DIR/0-14_range.pgn" "$JOB_DIR/15-29_range.pgn" "$JOB_DIR/30-44_range.pgn" "$JOB_DIR/45plus_range.pgn" 2>/dev/null || true
for f in "$JOB_DIR"/dedup_chunks/chunk_*.pgn; do
  b="$(basename "$f")"
  "$PYTHON_BIN" -u "$REPO_DIR/scripts/pgn/partition_pgn_by_verbal_ranges.py" \
    --input "$f" \
    --out-0-14 "$JOB_DIR/0-14_range.pgn" \
    --out-15-29 "$JOB_DIR/15-29_range.pgn" \
    --out-30-44 "$JOB_DIR/30-44_range.pgn" \
    --out-45-plus "$JOB_DIR/45plus_range.pgn" \
    --log-every 5000 \
    --append \
    2>&1 | tee "$JOB_DIR/logs/partition_${b%.pgn}.log" | filter_console_noise
done

echo
echo "PARTITION SUMMARY (aggregate across all chunks)"
JOB_DIR="$JOB_DIR" "$PYTHON_BIN" - <<'PY'
from __future__ import annotations

import glob
import os
import re
from pathlib import Path

job_dir = Path(os.environ["JOB_DIR"])
log_paths = sorted(glob.glob(str(job_dir / "logs" / "partition_chunk_*.log")))

line_re = re.compile(
    r"^Done\. Total=(?P<total>[\d,]+) \| 15-29=(?P<r15>[\d,]+).*?\| 30-44=(?P<r30>[\d,]+).*?\| 45\+=(?P<r45>[\d,]+).*?\| <15=(?P<lt15>[\d,]+)"
)

agg = {"total": 0, "r15": 0, "r30": 0, "r45": 0, "lt15": 0}
parsed = 0

for path in log_paths:
    last_done = None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("Done. Total="):
                    last_done = line.strip()
    except OSError:
        continue

    if not last_done:
        continue

    m = line_re.match(last_done)
    if not m:
        continue

    parsed += 1
    for k, g in (("total", "total"), ("r15", "r15"), ("r30", "r30"), ("r45", "r45"), ("lt15", "lt15")):
        agg[k] += int(m.group(g).replace(",", ""))

def pct(n: int, d: int) -> float:
    return (100.0 * n / d) if d else 0.0

total = agg["total"]
r15 = agg["r15"]
r30 = agg["r30"]
r45 = agg["r45"]
lt15 = agg["lt15"]

print(f"Chunks parsed: {parsed:,} / {len(log_paths):,}")
print(
    f"Total={total:,} | "
    f"15-29={r15:,} ({pct(r15,total):.2f}%) | "
    f"30-44={r30:,} ({pct(r30,total):.2f}%) | "
    f"45+={r45:,} ({pct(r45,total):.2f}%) | "
    f"<15={lt15:,} ({pct(lt15,total):.2f}%)"
)
print(f"Written total (>=15): {(r15+r30+r45):,} ({pct(r15+r30+r45,total):.2f}%)")
PY

echo "DONE"
echo "  0-14:    $JOB_DIR/0-14_range.pgn"
echo "  15-29:   $JOB_DIR/15-29_range.pgn"
echo "  30-44:   $JOB_DIR/30-44_range.pgn"
echo "  45plus:  $JOB_DIR/45plus_range.pgn"
echo "  logs:    $JOB_DIR/logs"
echo "  chunks:  $JOB_DIR/dedup_chunks"
if [[ "$DUMP_DUPES" == "1" ]]; then
  echo "  dupes:   $JOB_DIR/duplicates.pgn"
fi
