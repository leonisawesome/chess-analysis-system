#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Run the PGN "clean" pipeline with robust logging + resumability:
  1) Game-level exact dedupe (keeps different annotations as different games)
  2) EVS filter (keeps EVS>=threshold; unparseable/unscorable games are kept by default)
  3) Concatenate to final output

Usage:
  bash scripts/pgn/run_clean_pgn_pipeline.sh "/path/to/input.pgn" "/path/to/clean.pgn"

Optional env vars:
  REPO_DIR                  Repo root (auto-detected if run from repo); defaults to current dir.
  JOB_DIR                   Where to write logs/chunks/checkpoints (default: sibling _jobs folder near output)
  GAMES_PER_CHUNK           Dedupe chunk size (default: 50000)
  EVS_THRESHOLD             EVS threshold (default: 40)
  TOTAL_GAMES_HINT          Known total game count (improves progress/ETA without pre-scan)
  COUNT_GAMES_FIRST         Set to 1 to pre-scan and count games (exact denominator; adds one full read pass)
  EVS_REPORT_ONLY           Set to 1 to only report how many are < threshold (no filtering / no output write)
  DUMP_DUPES                Set to 1 to write duplicates PGN (default path: "$JOB_DIR/duplicates.pgn")
  DUPES_LIMIT               Max duplicates to write (default: 0 = unlimited)
  DROP_ZERO_VERBAL          Set to 1 to drop games with zero verbal annotations (recommended)

  CHESS_DEDUP_BACKEND       Set to "sqlite" to avoid Postgres (recommended if you don't have Postgres)
  CHESS_DEDUP_SQLITE_PATH   SQLite file path (default: "$JOB_DIR/dedup_hashes.sqlite3")
  CHESS_DEDUP_SQLITE_COMMIT_EVERY  Commit cadence (default: 5000)

Notes:
  - This script does NOT install Python dependencies. It expects python-chess to be importable.
  - Logs are written under "$JOB_DIR/logs/".
  - Console output is filtered to hide noisy per-game parse warnings; see logs for details.
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

if [[ ! -f "$IN_PGN" ]]; then
  echo "ERROR: input PGN not found: $IN_PGN" >&2
  exit 1
fi

REPO_DIR="${REPO_DIR:-$(pwd)}"
if [[ ! -f "$REPO_DIR/scripts/pgn/dedupe_massive_pgn.py" ]]; then
  echo "ERROR: REPO_DIR doesn't look like repo root: $REPO_DIR" >&2
  echo "Set REPO_DIR=/Users/leon/Downloads/python/chess-analysis-system and re-run." >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! "$PYTHON_BIN" -c "import chess, chess.pgn" >/dev/null 2>&1; then
  echo "ERROR: python-chess is not importable from $PYTHON_BIN." >&2
  echo "Install it in the Python you're using, e.g.: $PYTHON_BIN -m pip install python-chess" >&2
  exit 1
fi

GAMES_PER_CHUNK="${GAMES_PER_CHUNK:-50000}"
EVS_THRESHOLD="${EVS_THRESHOLD:-40}"
TOTAL_GAMES_HINT="${TOTAL_GAMES_HINT:-}"
COUNT_GAMES_FIRST="${COUNT_GAMES_FIRST:-0}"
EVS_REPORT_ONLY="${EVS_REPORT_ONLY:-0}"
DUMP_DUPES="${DUMP_DUPES:-0}"
DUPES_LIMIT="${DUPES_LIMIT:-0}"
DROP_ZERO_VERBAL="${DROP_ZERO_VERBAL:-0}"

OUT_DIR="$(cd "$(dirname "$OUT_PGN")" && pwd)"
OUT_BASE="$(basename "$OUT_PGN")"

DEFAULT_JOB_BASE="$OUT_DIR/_jobs"
STAMP="$(date +%Y%m%d_%H%M%S)"
JOB_DIR="${JOB_DIR:-$DEFAULT_JOB_BASE/clean_${OUT_BASE}_${STAMP}}"

mkdir -p "$JOB_DIR"/{logs,dedup_chunks,filtered_chunks}

export PYTHONPATH="$REPO_DIR"
export PYTHONUNBUFFERED=1

# Default to SQLite if caller hasn't specified a backend; avoids Postgres installs.
export CHESS_DEDUP_BACKEND="${CHESS_DEDUP_BACKEND:-sqlite}"
export CHESS_DEDUP_SQLITE_PATH="${CHESS_DEDUP_SQLITE_PATH:-$JOB_DIR/dedup_hashes.sqlite3}"
export CHESS_DEDUP_SQLITE_COMMIT_EVERY="${CHESS_DEDUP_SQLITE_COMMIT_EVERY:-5000}"

filter_console_noise() {
  # Keep progress + summary lines; hide noisy warnings like "illegal san".
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
echo "Dedupe:  games_per_chunk=$GAMES_PER_CHUNK backend=$CHESS_DEDUP_BACKEND"
echo "EVS:     threshold=$EVS_THRESHOLD (keeps unparseable/unscorable by default)"
echo "Count:   total_games_hint=${TOTAL_GAMES_HINT:-none} count_games_first=$COUNT_GAMES_FIRST"
echo "Mode:    drop_zero_verbal=$DROP_ZERO_VERBAL evs_report_only=$EVS_REPORT_ONLY dump_dupes=$DUMP_DUPES"
echo

echo "Stage 1/3: DEDUPE (this does not drop games by EVS score; it only removes exact duplicates)"
(
  cd "$JOB_DIR"
  dup_args=()
  if [[ "$DUMP_DUPES" == "1" ]]; then
    dup_args+=( "--duplicates-out" "$JOB_DIR/duplicates.pgn" "--duplicates-limit" "$DUPES_LIMIT" )
  fi

  "$PYTHON_BIN" -u "$REPO_DIR/scripts/pgn/dedupe_massive_pgn.py" "$IN_PGN" \
    --output-dir "$JOB_DIR/dedup_chunks" \
    --games-per-chunk "$GAMES_PER_CHUNK" \
    $( [[ -n "${TOTAL_GAMES_HINT}" ]] && printf "%s" "--total-games ${TOTAL_GAMES_HINT}" ) \
    $( [[ "$COUNT_GAMES_FIRST" == "1" ]] && printf "%s" "--count-games-first" ) \
    "${dup_args[@]}" \
    2>&1 | tee "$JOB_DIR/logs/dedupe.log" | filter_console_noise
)

echo
if [[ "$DROP_ZERO_VERBAL" == "1" ]]; then
  echo "Stage 2/3: VERBAL FILTER (drops games with zero verbal annotations)"
elif [[ "$EVS_REPORT_ONLY" == "1" ]]; then
  echo "Stage 2/3: EVS REPORT (no dropping; counts EVS < $EVS_THRESHOLD and zero-verbal games)"
else
  echo "Stage 2/3: EVS FILTER (drops only games with EVS < $EVS_THRESHOLD; keeps unparseable/unscorable games)"
fi
for chunk in "$JOB_DIR"/dedup_chunks/chunk_*.pgn; do
  b="$(basename "$chunk")"
  out_chunk="$JOB_DIR/filtered_chunks/$b"
  log="$JOB_DIR/logs/evs_${b%.pgn}.log"
  stats_json="$JOB_DIR/logs/evs_${b%.pgn}.stats.json"

  if [[ "$DROP_ZERO_VERBAL" == "1" ]]; then
    zlog="$JOB_DIR/logs/verbal_${b%.pgn}.log"
    zstats="$JOB_DIR/logs/verbal_${b%.pgn}.stats.json"
    if [[ -s "$out_chunk" ]]; then
      echo "[skip] $b (already filtered)"
      continue
    fi
    "$PYTHON_BIN" -u "$REPO_DIR/scripts/pgn/filter_pgn_by_zero_verbal.py" \
      --input "$chunk" \
      --output "$out_chunk" \
      --min-verbal-words 1 \
      --log-every 5000 \
      --stats-json "$zstats" \
      2>&1 | tee "$zlog" | filter_console_noise
    continue
  fi

  if [[ "$EVS_REPORT_ONLY" == "1" ]]; then
    if [[ -s "$stats_json" ]]; then
      echo "[skip] $b (already reported)"
      continue
    fi
    "$PYTHON_BIN" -u "$REPO_DIR/scripts/pgn/filter_pgn_by_evs.py" \
      --input "$chunk" \
      --mode single \
      --medium-threshold "$EVS_THRESHOLD" \
      --log-every 5000 \
      --stats-json "$stats_json" \
      --report-only \
      2>&1 | tee "$log" | filter_console_noise
    continue
  fi

  if [[ -s "$out_chunk" ]]; then
    echo "[skip] $b (already filtered)"
    continue
  fi

  "$PYTHON_BIN" -u "$REPO_DIR/scripts/pgn/filter_pgn_by_evs.py" \
    --input "$chunk" \
    --mode single \
    --output "$out_chunk" \
    --medium-threshold "$EVS_THRESHOLD" \
    --log-every 5000 \
    --stats-json "$stats_json" \
    2>&1 | tee "$log" | filter_console_noise
done

echo
if [[ "$EVS_REPORT_ONLY" == "1" ]]; then
  echo "Stage 3/3: REPORT (no output written)"
else
  echo "Stage 3/3: CONCATENATE (write final PGN)"
fi

mkdir -p "$OUT_DIR"
if [[ "$EVS_REPORT_ONLY" != "1" ]]; then
  TMP="$OUT_PGN.tmp"
  : > "$TMP"
  for f in "$JOB_DIR"/filtered_chunks/chunk_*.pgn; do
    cat "$f" >> "$TMP"
    printf "\n\n" >> "$TMP"
  done
  mv -f "$TMP" "$OUT_PGN"
fi

echo
if [[ "$DROP_ZERO_VERBAL" == "1" ]]; then
  echo "VERBAL stats (aggregate):"
  "$PYTHON_BIN" - <<PY
import json
import glob
import os

job_dir = ${JOB_DIR@Q}
paths = sorted(glob.glob(os.path.join(job_dir, "logs", "verbal_*.stats.json")))
tot = {"total": 0, "kept": 0, "dropped_zero_verbal": 0, "zero_verbal": 0}
for p in paths:
    with open(p, "r", encoding="utf-8") as f:
        s = json.load(f)
    for k in tot.keys():
        tot[k] += int(s.get(k, 0) or 0)

pct = (tot["dropped_zero_verbal"] / tot["total"] * 100.0) if tot["total"] else 0.0
print(f"  total_games:         {tot['total']:,}")
print(f"  kept_games:          {tot['kept']:,}")
print(f"  dropped_zero_verbal: {tot['dropped_zero_verbal']:,} ({pct:.2f}%)")
PY
else
  echo "EVS stats (aggregate):"
  "$PYTHON_BIN" - <<PY
import json
import glob
import os

job_dir = ${JOB_DIR@Q}
thr = int(${EVS_THRESHOLD})
paths = sorted(glob.glob(os.path.join(job_dir, "logs", "evs_chunk_*.stats.json")))
tot = {
    "total": 0,
    "scorable": 0,
    "below_threshold": 0,
    "at_or_above_threshold": 0,
    "zero_verbal_total": 0,
    "zero_verbal_scorable": 0,
    # present when actually filtering
    "kept_single": 0,
    "kept_medium": 0,
    "kept_high": 0,
    "kept_unparseable": 0,
    "kept_unscorable": 0,
    "skipped": 0,
    "dropped_below_threshold": 0,
}
for p in paths:
    with open(p, "r", encoding="utf-8") as f:
        s = json.load(f)
    for k in tot.keys():
        tot[k] += int(s.get(k, 0) or 0)

kept = tot["kept_single"] + tot["kept_medium"] + tot["kept_high"] + tot["kept_unparseable"] + tot["kept_unscorable"]
dropped_total = tot["total"] - kept
dropped_pct = (dropped_total / tot["total"] * 100.0) if tot["total"] else 0.0
drop_score = tot["dropped_below_threshold"]
drop_score_pct_total = (drop_score / tot["total"] * 100.0) if tot["total"] else 0.0
drop_score_pct_of_dropped = (drop_score / dropped_total * 100.0) if dropped_total else 0.0
below_pct_scorable = (tot["below_threshold"] / tot["scorable"] * 100.0) if tot["scorable"] else 0.0
below_pct_total = (tot["below_threshold"] / tot["total"] * 100.0) if tot["total"] else 0.0
zv_pct_total = (tot["zero_verbal_total"] / tot["total"] * 100.0) if tot["total"] else 0.0
zv_pct_scorable = (tot["zero_verbal_scorable"] / tot["scorable"] * 100.0) if tot["scorable"] else 0.0

print(f"  total_games:            {tot['total']:,}")
print(f"  scorable_games:         {tot['scorable']:,}")
print(f"  below_{thr}:              {tot['below_threshold']:,} ({below_pct_scorable:.2f}% of scorable, {below_pct_total:.2f}% of total)")
print(f"  zero_verbal:            {tot['zero_verbal_total']:,} ({zv_pct_total:.2f}% of total)")
print(f"  zero_verbal_scorable:   {tot['zero_verbal_scorable']:,} ({zv_pct_scorable:.2f}% of scorable)")
print(f"  kept_unparseable:       {tot['kept_unparseable']:,}")
print(f"  kept_unscorable:        {tot['kept_unscorable']:,}")
print(f"  skipped_other:          {tot['skipped']:,}")

filtered = (tot["kept_single"] + tot["kept_medium"] + tot["kept_high"] + tot["dropped_below_threshold"]) > 0
if filtered:
    print(f"  kept_games:             {kept:,}")
    print(f"  dropped_games:          {dropped_total:,} ({dropped_pct:.2f}%)")
    print(f"  dropped_by_score(<thr): {drop_score:,} ({drop_score_pct_total:.2f}% of total, {drop_score_pct_of_dropped:.2f}% of dropped)")
PY
fi

echo
if [[ "$EVS_REPORT_ONLY" == "1" ]]; then
  echo "DONE (report only; no clean PGN written)"
else
  echo "DONE: $OUT_PGN"
fi
echo "Logs: $JOB_DIR/logs"
