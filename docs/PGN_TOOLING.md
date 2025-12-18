# PGN tooling cheat sheet

## What “dedupe” means (two different levels)

### 1) File-level dedupe (dedupe folders of `.pgn` files)

Use this when you have many `.pgn` files and want to combine them into one master PGN while eliminating duplicate *files* (same content, different paths).

- Script: `scripts/pgn/combine_pgn_corpus.py`
- Method: MD5 hash of each PGN file’s bytes (fast, content-based)
- Output: one combined `*.pgn` plus CSV reports

### 2) Game-level dedupe (dedupe games inside one massive PGN)

Use this when you have one huge PGN and need to remove duplicate *games* within it (or across runs).

- Script: `scripts/pgn/dedupe_massive_pgn.py` (wrapper)
- Implementation: `chess_rag_system/dedupe_massive_pgn.py`
- Storage: Postgres-backed hash table (`chess_rag_system/deduplication.py`)
- Output: chunked PGNs under `--output-dir` (default `deduplicated_chunks/`) so it can resume and avoid rewriting huge files.

Notes:
- This tool currently hashes a normalized PGN text representation (whitespace-normalized), so it primarily removes byte-equivalent duplicates.
- It requires Postgres + `psycopg2` and a reachable DB configured in `chess_rag_system/db_config.py`.

## Language cleanup (ChessBase English+German comments)

Use this when a PGN has duplicated German prose inside `{ ... }` comments.

- Script: `scripts/pgn/clean_pgn_language.py`
- Method: parses games via `python-chess`, keeps English sentences + token metadata, drops German tails/sentences

## EVS filtering (keep medium/high quality games)

Use these after you have a combined master PGN and want to keep only the better games:

- Single file → keep medium/high: `scripts/pgn/filter_pgn_by_evs.py`
- Directory → stream medium/high across many files: `scripts/pgn/filter_directory_by_evs.py`
- Keep top N%: `scripts/pgn/sample_top_evs.py`

