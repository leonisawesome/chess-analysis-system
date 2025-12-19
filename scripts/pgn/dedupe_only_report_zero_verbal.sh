#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Deduplicate a single large PGN (exact duplicates only), then report how many games
have zero verbal annotations (would be dropped by a zero-verbal filter).

This script:
  1) Removes exact duplicate games (via scripts/pgn/dedupe_massive_pgn.py)
  2) Writes a single deduped PGN output (concatenated chunks)
  3) Reports "zero verbal" count across the deduped output (does NOT drop them)

Definition:
  - "zero verbal" = no word-like tokens inside any `{...}` comment.

Usage:
  bash scripts/pgn/dedupe_only_report_zero_verbal.sh INPUT.pgn OUTPUT.pgn

Optional env vars:
  TOTAL_GAMES_HINT=9222501   Known total games for accurate progress/ETA
  GAMES_PER_CHUNK=50000      Dedupe chunk size
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
OUT_PGN="$2"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ ! -f "$REPO_DIR/scripts/pgn/dedupe_massive_pgn.py" ]]; then
  echo "ERROR: could not locate repo root from script path: $REPO_DIR" >&2
  exit 1
fi

if [[ ! -f "$IN_PGN" ]]; then
  echo "ERROR: input PGN not found: $IN_PGN" >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! "$PYTHON_BIN" -c "import chess, chess.pgn" >/dev/null 2>&1; then
  echo "ERROR: python-chess is not importable from $PYTHON_BIN." >&2
  echo "Install it for that Python: $PYTHON_BIN -m pip install python-chess" >&2
  exit 1
fi

OUT_DIR="$(cd "$(dirname "$OUT_PGN")" && pwd)"
OUT_BASE="$(basename "$OUT_PGN")"
STAMP="$(date +%Y%m%d_%H%M%S)"
JOB_DIR="$OUT_DIR/_jobs/dedupe_${OUT_BASE}_${STAMP}"

mkdir -p "$JOB_DIR"/{logs,dedup_chunks,zero_verbal_stats}

export PYTHONPATH="$REPO_DIR"
export PYTHONUNBUFFERED=1

# Always use SQLite for the dedupe hash store (no Postgres required).
export CHESS_DEDUP_BACKEND=sqlite
export CHESS_DEDUP_SQLITE_PATH="$JOB_DIR/dedup_hashes.sqlite3"
export CHESS_DEDUP_SQLITE_COMMIT_EVERY="${CHESS_DEDUP_SQLITE_COMMIT_EVERY:-5000}"

GAMES_PER_CHUNK="${GAMES_PER_CHUNK:-50000}"
TOTAL_GAMES_HINT="${TOTAL_GAMES_HINT:-}"

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
echo "Output:  $OUT_PGN"
echo "Mode:    dedupe only + zero-verbal report"
echo

echo "Stage 1/3: DEDUPE (exact duplicates only)"
(
  cd "$JOB_DIR"
  args=( "$IN_PGN" "--output-dir" "$JOB_DIR/dedup_chunks" "--games-per-chunk" "$GAMES_PER_CHUNK" )
  if [[ -n "$TOTAL_GAMES_HINT" ]]; then
    args+=( "--total-games" "$TOTAL_GAMES_HINT" )
  fi
  "$PYTHON_BIN" -u "$REPO_DIR/scripts/pgn/dedupe_massive_pgn.py" "${args[@]}" \
    2>&1 | tee "$JOB_DIR/logs/dedupe.log" | filter_console_noise
)

echo
echo "Stage 2/3: WRITE DEDUPED OUTPUT (concatenate chunks)"
mkdir -p "$OUT_DIR"
TMP="$OUT_PGN.tmp"
: > "$TMP"
for f in "$JOB_DIR"/dedup_chunks/chunk_*.pgn; do
  cat "$f" >> "$TMP"
  printf "\n\n" >> "$TMP"
done
mv -f "$TMP" "$OUT_PGN"
echo "Wrote: $OUT_PGN"

echo
echo "Stage 3/3: ZERO-VERBAL REPORT (no dropping; counts only)"
for f in "$JOB_DIR"/dedup_chunks/chunk_*.pgn; do
  b="$(basename "$f")"
  stats_json="$JOB_DIR/zero_verbal_stats/${b%.pgn}.json"
  [[ -s "$stats_json" ]] && continue
  "$PYTHON_BIN" -u "$REPO_DIR/scripts/pgn/filter_pgn_by_zero_verbal.py" \
    --input "$f" \
    --report-only \
    --log-every 0 \
    --stats-json "$stats_json" \
    2>&1 | tee "$JOB_DIR/logs/zero_verbal_${b%.pgn}.log" | filter_console_noise
done

"$PYTHON_BIN" - <<PY
import glob
import json
import os

job_dir = ${JOB_DIR@Q}
paths = sorted(glob.glob(os.path.join(job_dir, "zero_verbal_stats", "*.json")))
tot = {"total": 0, "zero_verbal": 0, "dropped_zero_verbal": 0, "kept": 0}
for p in paths:
    with open(p, "r", encoding="utf-8") as f:
        s = json.load(f)
    for k in tot:
        tot[k] += int(s.get(k, 0) or 0)

z = tot["zero_verbal"]
t = tot["total"]
pct = (z / t * 100.0) if t else 0.0
print("")
print("Zero-verbal summary (deduped corpus):")
print(f"  total_games:        {t:,}")
print(f"  zero_verbal_games:  {z:,} ({pct:.2f}%)  <-- would be dropped by zero-verbal rule")
PY

echo
echo "DONE"
echo "Deduped PGN: $OUT_PGN"
echo "Logs: $JOB_DIR/logs"
