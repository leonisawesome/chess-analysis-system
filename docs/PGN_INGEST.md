# PGN Ingestion Process (Rigorous)

This document outlines the mandatory steps for adding games to the Chess Analysis System Knowledge Bank.

## 🏁 The "Gold Standard" Rules
1.  **Zero Textless Games**: Games consisting only of move notation without human commentary are REJECTED. They add noise to the LLM and offer no coaching value. (Relaxed for high-prose density games like "Logical Chess").
2.  **100% Deduplication**: Games are fingerprinted using a **Full Normalized Move Hash** (ignoring comments/whitespace/headers) to prevent duplicates.
3.  **Educational Value Score (EVS)**: Every game is scored. Only games with an EVS > 0.5 (indicating meaningful commentary or variations) are ingested.
4.  **Source Integrity**: Preserve the "Source" metadata (e.g., Chessable Course Name or Book Title) to allow for source-restricted searching.

## 🛠 Ingestion Pipeline
1.  **Stage 1: Quality Analysis** (`pgn_quality_analyzer.py`)
    - Scans raw PGNs.
    - Filters out games with no `{}` comments (unless WPM > 3.5).
    - Calculates the "Educational Value Score".
    - **Deduplication Check (Composite Key)**:
        *   **Move Hash**: MD5 of the normalized move sequence (mechanics).
        *   **Player Hash**: Normalized strings of White and Black player names.
        *   **Result Hash**: Normalized result (e.g., "1-0").
        *   **Logic**: A game is a duplicate ONLY if `MoveHash + White + Black + Result` matches an existing entry.
        *   **Conflict Resolution**: If a conflict exists, keep the version with the **Higher EVS** (better commentary).

2.  **Stage 2: SQLite Ingestion** (`analyze_pgn_games.py`)
    - Inserts validated games into `knowledge_docs` and `knowledge_fts`.
    - Cleans PGN headers to reduce context noise.

## 🚦 Verification Gates
- **Pre-Ingest**: Log showing exactly how many games were rejected and why.
- **Post-Ingest**: Query the DB for `source_type='pgn_game'` and ensure `content` is not empty.
- **Search Test**: Verify that a search for a thematic game (e.g., "Kasparov immortal") returns the game with its commentary.
