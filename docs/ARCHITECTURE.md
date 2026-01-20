# Chess Analysis System: Unified Architecture

## Core Philosophy
We treat chess content not as "text" or "games", but as **Instructional Position Graphs**.
*   **PGNs** are structured graphs of moves and commentary.
*   **EPUBs** are interleaved streams of prose, moves, and diagrams.

Our goal is to ingest both into a unified **Knowledge Bank** where queries can be semantic ("Greek Gift") OR positional (White Knight on d5).

---

## 1. PGN Ingestion Pipeline
**Goal**: High-quality, deduplicated game index.

### Deduplication Strategy: "Two-Layer Identity"
We solve the "Game vs. Document" conflict by modeling both explicitly.

| Layer | Component | Logic | Purpose |
| :--- | :--- | :--- | :--- |
| **Layer 1** | **Game ID** (Grouping) | `MD5(Normalized_UCI_Moves)` | Groups all versions of the same game (Raw, Annotated, etc.). |
| **Layer 2** | **Fingerprint** (Identity) | `SHA256(Normalized_PGN_Text)` | Identifies unique *educational artifacts*. Collapses whitespace/formatting but preserves comments. |
| **Layer 3** | **Value Score** (Ranking) | `EVS` (WPM, Variations, Etc.) | Decides which version to embed/retrieve. |

### Storage Schema
*   **`game_hashes` table**: Tracks `fingerprint` (PK), `game_id`, and `evs`.
*   **`knowledge_docs` table**: Stores the actual textual content for RAG.
*   **Policy**: Store **ALL** unique fingerprints. Embed only **High Value** versions.

---

## 2. EPUB Ingestion Pipeline
**Goal**: Context-aware chunks linked to board positions + Quality Filtering.

### Strategy: "Stateful Parsing with Hybrid Fallback"
We prioritize **Moves** as the source of truth but use **OCR** strictly as a fallback for diagram-only content.

### Parsing Logic
1.  **Stateful Parsing**: The parser maintains a real chess board (python-chess) state while reading.
2.  **Move Tracking**: Every SAN move found in text updates the internal board.
3.  **Diagram Anchors**:
    *   **Primary (Instructional)**: When an `<img>` tag is found, link it to the current board state (FEN) derived from moves.
    *   **Fallback (Tactics/Puzzles)**: If *no* moves precede the diagram, flag it as "Textless". These are candidates for OCR processing (Tier 2).

### Algorithmic Quality Scoring (EPUB EVS)
We score books/chunks based on **Explanatory Density** and **Vocabulary Richness** to distinguish "Coaching" from "Data".

**Metrics:**
*   **Prose Ratio**: `(Text Length) / (Prose + Moves)`
*   **Vocabulary Score**: Weighted sum of terms from `assets/coaching_vocab.json`.
    *   *High Value (5)*: "Prophylaxis", "Outpost", "Deep Strategy".
    *   *Mid Value (3)*: "Open file", "Advantage".
    *   *Low Value (1)*: "Capture", "Move".
*   **Diagram Context**: Words of prose surrounding a diagram (High = Teaching, Low = Test).

**Classification:**
*   **`INSTRUCTIONAL`**: High Vocab Score, High Prose Ratio. (Embed priority: High).
*   **`ANNOTATED_GAMES`**: Moderate prose, game structure. (Embed priority: Medium).
*   **`PUZZLE_BOOK`**: Low prose per diagram, "White to play" patterns. (Embed priority: Low/Specialized).
*   **`OPENING_REF`**: High move density, low prose, deep nesting. (Embed priority: Reference only).

---

## 3. Implementation Roadmap
1.  **PGN Deduplication**: Implement Two-Layer Hashing in `pgn_quality_analyzer.py` (Immediate Phase).
2.  **EPUB Parser**: Build `ChessBookParser` with stateful tracking and standard scoring.
