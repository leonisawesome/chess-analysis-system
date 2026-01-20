# Chess Analysis System: Core Algorithms

This document details the logic used to score and filter chess content before it enters the Knowledge Bank. The goal is to ensure the system acts as a **Masterclass Coach**, not a move-list generator.

## 1. Educational Value Score (EVS)
The EVS is a 0-100 score calculated in `pgn_quality_analyzer.py`. A score of **80+** is considered "Gold" instructional content.

### The "Hygiene" Gates (Mandatory)
A game is immediately score **0** (dropped) if it fails these Masterclass thresholds:
- **Words Per Move (WPM) > 1.5**: If a 40-move game has fewer than 60 human-written words, it is considered "low density" and rejected.
- **Variation Required**: A game with zero variations (sidelines) is rejected, as coaching requires exploring alternatives.

### Scoring Components
| Component | Weight | Criteria |
| :--- | :--- | :--- |
| **Annotations** | Up to 45 pts | Density of `!` and `?` symbols + raw comment word count. |
| **Educational** | Up to 15 pts | Presence of coaching keywords (e.g., "plan", "strategy", "concept"). |
| **Explanatory** | Multiplier | Tiered rewards for specific chess-theory words (Outpost, Prophylaxis, etc.). |
| **Humanness** | Up to 20 pts | Checks for Elo ratings, Event history, and Modern dates (Post-1980). |
| **Structure** | Up to 20 pts | Completeness of PGN headers (Site, Date, Result). |

### Penalties
- **Engine Noise**: Substantial penalties for excessive `%eval` lines or mentions of engine names (Stockfish, Komodo).
- **Variation Overload**: Penalties for games that have deep move trees but sparse human commentary.

---

## 2. Language Detection Logic
The system uses a two-stage detection process to ensure the LLM receives high-quality prose.

### Stage 1: Library Detection
Uses the `langdetect` library on a concatenated blob of all game comments and headers.

### Stage 2: Stopword Fallback (Deterministic)
If libraries are unavailable or the text is short, the system counts hits against language-specific stopword lists:
- **English**: the, that, with, etc.
- **Spanish**: el, que, por, etc.
- **German**: der, die, das, etc.

**Allowed Status**:
- **Supported**: English (`en`), Spanish (`es`).
- **Blends**: English/German blends are allowed (common in old Masters' databases).
- **Rejected**: All other languages are filtered out to prevent "hallucinated" translations in the synthesis.

---

## 3. PGN Fingerprinting (Deduplication)
To achieve **100% deduplication**, the system does not rely on headers (which are often inconsistent).

**The Algorithm**:
1.  **Strip** all comments `{...}` and move numbers.
2.  **Extract** the first 20 mainline moves.
3.  **Hash** the move string (e.g., `e4e5Nf3Nc6...`).
4.  **Lookup**: If the hash exists in the SQLite `knowledge_docs` table, the new game is rejected as a duplicate.
