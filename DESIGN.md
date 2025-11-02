# Chess Tutor – System Design (v0.1)

Purpose: A single, adaptive training system that “speaks to your data”, produces reliable diagrams and drills, analyzes your games, and plans a curriculum to reach OTB ~2400 strength over ~10 years.

## Goals
- Reliable: diagrams and drills are deterministic and validated (no hallucinations).
- Personalized: adapts to your mistakes; dynamic curriculum and SRS scheduling.
- Explainable: cites your books/courses and shows engine‑checked evaluations.
- Private: runs locally; cloud only where explicitly configured.

## High‑Level Architecture
- Text RAG (Explanations)
  - Ingest books/courses → chunk with metadata → Qdrant/ES. LLM stitches explanations with citations.
- Positions Index (Diagrams & Drills)
  - ETL from PGNs → FENs every N plies → tactic labels via python‑chess + heuristics (+ optional engine verification). Stored in SQLite/Parquet. This is the primary source for diagrams/drills.
- Engine Analysis
  - Stockfish for difficulty scoring, game review, and hint generation.
- Tutor Planner
  - Skill model per motif/opening, SRS queue (FSRS/SM‑2), daily curriculum generator (tactics/endgames/openings/play+analysis).
- Web App / API
  - Chat (ask anything, plans, source citations), Drills UI (FEN→board + feedback), Dashboards.

## Provenance & Traceability (RAG Hygiene)
- Chunk metadata (stored in Qdrant payloads and manifests):
  - Core: `source_type` (book|course|pgn), `source_id` (stable), `source_title`, `author`, `year`, `edition`
  - File: `file_path` (relative), `sha256_file`, `ingest_version`, `ingest_time`
  - Chunk: `doc_id` (stable), `chunk_id` (uuid), `content_sha256`, `char_start`/`char_end` (or page/chapter), `collection`
  - PGN (when ready): `game_id` (hash), `headers` (event/site/date/players/eco), `ply_start`/`ply_end`, `phase`
- Manifests & audit:
  - `data/manifest/*.json` (one per source) + `data/manifest/index.json`
  - `data/audit/purges-YYYYMMDD.json` for removals
- Dirty‑data removal flow:
  - `data/denylist.yaml` supports keys by `source_id|file_path|sha256|doc_id|game_id`
  - Admin CLI (rag_admin.py): list-sources, find-chunks, purge, reindex
- Indexing for filters: payload indexes on `source_id`, `doc_id`, `collection` in Qdrant
- Answer provenance: UI shows title/chapter/source_id and links back to manifest

## Data Model (Positions Index)
- Core columns: `id, game_id, ply, fen, side_to_move, tactic_labels(set), opening_tag, phase, source`.
- Engine fields: `eval_cp, best_move_san, alt_move_penalty_cp, depth`.
- Quality: `duplicate_group(hash), diversity_score`.

## Key Flows
1) Ask‑Explain: Query → RAG → LLM explanation (citations). Diagrams pulled from positions index by motif/opening filters.
2) Drill: Planner pulls K positions by weakest motifs/difficulty → SRS scheduling → immediate engine feedback and short explanation.
3) Game Review: Import PGN → engine detect errors → tag motifs/openings → inject similar positions into next plan; show trendlines.

## Roadmap (Incremental)
1) Now: Solidify RAG Q&A and chat; finalize index schema & validators (code skeletons); planner + SRS scaffolding.
2) PGNs ready: Build Positions Index MVP on a subset; wire diagrams via index‑backed backfill; ship reliable tactical diagrams.
3) Expand: more motifs, endgames, difficulty bands; integrate game review and daily curriculum.
4) Infra: Move Qdrant to Docker/Cloud; lazy init & startup health checks.

## Success Metrics
- Tactical accuracy per motif ↑ week‑over‑week; time‑to‑solve ↓.
- Advantage conversion in won positions; reduced blunder rate under time pressure.
- Query satisfaction (explanations with citations) ≥ target.

## Notes on OTB ~2400 Target
- Requires regular classical tournaments, disciplined study, and feedback loops. System prioritizes deliberate practice (not generic puzzles), personalized drills, and engine‑checked review to accelerate learning.
