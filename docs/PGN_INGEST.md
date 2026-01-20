# PGN Ingestion Process (Rigorous)

This document outlines the mandatory steps for adding games to the Chess Analysis System Knowledge Bank.

## 🏁 The "Gold Standard" Rules
1.  **Zero Textless Games**: Games consisting only of move notation without human commentary are REJECTED. They add noise to the LLM and offer no coaching value.
2.  **100% Deduplication**: Games are fingerprinted based on the **Initial Move Sequence** (ignoring comments) to prevent the same game from appearing multipe times.
3.  **Educational Value Score (EVS)**: Every game is scored. Only games with an EVS > 0.5 (indicating meaningful commentary or variations) are ingested.
4.  **Source Integrity**: Preserve the "Source" metadata (e.g., Chessable Course Name or Book Title) to allow for source-restricted searching.

## 🛠 Ingestion Pipeline
1.  **Stage 1: Quality Analysis** (`pgn_quality_analyzer.py`)
    - Scans raw PGNs.
    - Filters out games with no `{}` comments.
    - Calculates the "Educational Value Score".
2.  **Stage 2: Deduplication**
    - Generates a hash for the starting 20 moves.
    - Checks against the existing `knowledge_docs` table in SQLite.
3.  **Stage 3: SQLite Ingestion** (`analyze_pgn_games.py`)
    - Inserts validated games into `knowledge_docs` and `knowledge_fts`.
    - Cleans PGN headers to reduce context noise.

## 🚦 Verification Gates
- **Pre-Ingest**: Log showing exactly how many games were rejected and why.
- **Post-Ingest**: Query the DB for `source_type='pgn_game'` and ensure `content` is not empty.
- **Search Test**: Verify that a search for a thematic game (e.g., "Kasparov immortal") returns the game with its commentary.
