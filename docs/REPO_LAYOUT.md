# Repository layout

This repo has accumulated a lot of one-off scripts and session artifacts over time. The goal of this layout is to keep the **day-to-day operational scripts** easy to find without breaking existing commands.

## Key entrypoints (repo root)

- `app.py` — Flask server
- `add_books_to_corpus.py` — ingest EPUBs into Qdrant (requires `OPENAI_API_KEY`)
- `add_pgn_to_corpus.py` — ingest PGN chunks into Qdrant (requires `OPENAI_API_KEY`)
- `pgn_quality_analyzer.py` — score staged PGNs into SQLite before ingest
- `analyze_pgn_games.py` — parse PGNs into RAG chunks

## `scripts/`

Canonical operational scripts are grouped by domain:

- `scripts/books/` — EPUB staging, scoring, and removal helpers
- `scripts/pgn/` — PGN merge/dedupe/clean/filter/diagram helpers
- `scripts/diag/` — diagram debugging utilities
- `scripts/ops/` — operational utilities (misc tooling)

### Backward compatibility wrappers

The previous paths under `scripts/` (for example `python scripts/merge_pgn_sources.py`) are preserved as thin wrappers that forward to the canonical subfolder scripts.

## `chess_rag_system/`

Library code and heavier tooling that may have additional dependencies (e.g. the Postgres-backed game deduper).

