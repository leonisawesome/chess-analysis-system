# PGN tooling cheat sheet

## What “dedupe” means (two different levels)

### 1) File-level dedupe (dedupe folders of `.pgn` files)

Use this when you have many `.pgn` files and want to combine them into one master PGN while eliminating duplicate *files* (same content, different paths).

- Script: `scripts/pgn/combine_pgn_corpus.py`
- Method: MD5 hash of each PGN file’s bytes (fast, content-based)
- Output: one combined `*.pgn` plus CSV reports

### 1b) No-dedupe concat (combine folders of `.pgn` files as-is)

Use this when you want a single “giant PGN” built from many `.pgn` files and you **do not** want any dedupe or filtering.

- Script: `scripts/pgn/concat_pgn_corpus.py`
- Method: binary concatenation with a blank-line separator between files
- Notes: ignores macOS `._*` AppleDouble sidecars (never deletes anything)

### 2) Game-level dedupe (dedupe games inside one massive PGN)

Use this when you have one huge PGN and need to remove duplicate *games* within it (or across runs).

- Script: `scripts/pgn/dedupe_massive_pgn.py` (wrapper)
- Implementation: `chess_rag_system/dedupe_massive_pgn.py`
- Storage: disk-backed hash table (`chess_rag_system/deduplication.py`)
- Output: chunked PGNs under `--output-dir` (default `deduplicated_chunks/`) so it can resume and avoid rewriting huge files.

Notes:
- This tool currently hashes a normalized PGN text representation (whitespace-normalized), so it primarily removes byte-equivalent duplicates.
- By default it uses Postgres if available (requires Postgres + `psycopg2` and a reachable DB configured in `chess_rag_system/db_config.py`).
- If you don’t have Postgres, it can run with a local SQLite file (no server install):
  - `CHESS_DEDUP_BACKEND=sqlite`
  - `CHESS_DEDUP_SQLITE_PATH=/path/to/dedup_hashes.sqlite3` (optional; default: `dedup_hashes.sqlite3` in the current working directory)
  - `CHESS_DEDUP_SQLITE_COMMIT_EVERY=5000` (optional; commit cadence for speed)
- For accurate progress/ETA, either pass a known game count (`--total-games 9222501`) or do an exact pre-scan (`--count-games-first`).
- To dump duplicates as a PGN: `--duplicates-out /path/to/duplicates.pgn` (optionally cap with `--duplicates-limit N`).

## Language cleanup (ChessBase English+German comments)

Use this when a PGN has duplicated German prose inside `{ ... }` comments.

- Script: `scripts/pgn/clean_pgn_language.py`
- Method: parses games via `python-chess`, keeps English sentences + token metadata, drops German tails/sentences

## EVS filtering (keep medium/high quality games)

Use these after you have a combined master PGN and want to keep only the better games:

- Single file → keep medium/high: `scripts/pgn/filter_pgn_by_evs.py`
- Directory → stream medium/high across many files: `scripts/pgn/filter_directory_by_evs.py`
- Keep top N%: `scripts/pgn/sample_top_evs.py`

Notes:
- By default, EVS filtering keeps games that python-chess cannot parse (so nothing is lost); pass `--drop-unparseable` to discard them.
- By default, EVS filtering also keeps games that parse but cannot be scored (e.g., python-chess stricter than ChessBase); pass `--drop-unscorable` to discard them.
- To only report counts (no filtering / no output): add `--report-only` (use `--stats-json` if you want machine-readable totals).

### Interpreting EVS < 40 vs “zero verbal annotations”

- EVS is not a pure “has prose” detector. A game can score above 40 with good headers/structure and length even with no `{...}` prose comments.
- If your real goal is “drop games with zero verbal annotations”, use a direct heuristic:
  - “verbal annotation” = at least one `{ ... }` comment with at least one word.
  - In reports, this is tracked as `zero_verbal_total`.

## Verbal-only filtering (drop games with zero verbal annotations)

Use this if your goal is specifically “remove games with no prose comments”:

- Script: `scripts/pgn/filter_pgn_by_zero_verbal.py`
- Method: scans `{...}` comments for word-like tokens; drops games with zero verbal words
- Benefit: does not parse moves, so it won't drop games due to "illegal san"

## Dedupe-only + zero-verbal report (recommended first pass)

Use this when you want to:
- remove exact duplicates, and
- get a count of how many games *would* be dropped by the zero-verbal rule,
without actually dropping them yet.

- Script: `scripts/pgn/dedupe_only_report_zero_verbal.sh`

## Dedupe + verbal ranges (15–29 / 30–44 / 45+)

Use this when you want to inspect what different “RAG prose density” thresholds look like.
It deduplicates first (exact duplicates only), then partitions games into non-overlapping
commentary word-count ranges:

- Script: `scripts/pgn/dedupe_and_partition_verbal_ranges.sh`
- Word token rule: `[A-Za-zÀ-ÖØ-öø-ÿ]{2,}` counted in `{...}` and `;...` comments after stripping `[%... ]`
- Outputs (written into a timestamped job directory under your chosen OUT_DIR):
  - `0-14_range.pgn`
  - `15-29_range.pgn`
  - `30-44_range.pgn`
  - `45plus_range.pgn`

## Verbal slicing with arbitrary buckets

Use this when you want custom score slices (e.g., `40-49` and `50+`) without editing code.

- Script: `scripts/pgn/partition_pgn_by_verbal_ranges.py`
- Verbal score: word-token count in `{...}` and `;...` comments after stripping `[%... ]`
- Word token regex: `[A-Za-zÀ-ÖØ-öø-ÿ]{2,}`
- Bucket syntax (repeatable): `--bucket "RANGE=/path/to/out.pgn"`
  - `RANGE` formats: `A-B` (inclusive), `A+` (no upper bound), or `N` (exact)
  - Buckets are evaluated in order; by default each game goes to the first matching bucket

Example: split a PGN into `40-49.pgn` and `50plus.pgn`:

```bash
python3 -u scripts/pgn/partition_pgn_by_verbal_ranges.py \
  --input "/Users/leon/Downloads/chess/mas_de_45.pgn" \
  --bucket "40-49=/Users/leon/Downloads/chess/40-49.pgn" \
  --bucket "50+=/Users/leon/Downloads/chess/50plus.pgn" \
  --log-every 50000
```
