# Chess Coach Roadmap & Strategic Vision

This document outlines the long-term vision for the Chess Analysis System, designed to guide a player from a 1300 to a 2300 rating.

## Core Principles
1.  **System Integrity over Velocity**: Every component must be verified and documented before moving to the next phase.
2.  **Resilience**: The system must handle API failures (429s) gracefully with fallback strategies.
3.  **Actionable Knowledge**: The goal is not just to provide engine evaluations, but to connect them to human-readable explanations in your library.

## Architectural Suggestions (Backlog)

### 1. The "Theme-Aware" Search (Semantic + Keyword)
- **Problem**: Search can be too literal.
- **Suggestion**: Implement **Keyword Expansion** based on chess theory. If you search for "Isolated Queen Pawn", the system should also look for "IQP", "hanging pawns", and "pawn centers".
- **Impact**: Better retrieval from your 942 EPUBs.

### 2. Position-to-Prose Mapping (FEN FTS)
- **Problem**: You often have a position but don't know which book explains it.
- **Suggestion**: Create a specialized SQLite table that maps **FEN substrings** (representing structures like the Carlsbad or the French Center) to book chapters.
- **Impact**: You can paste a FEN from a game, and the system immediately gives you the 3 best chapters in your library to read.

### 3. Error-Correcting Study Drills
- **Problem**: Reading is passive; study must be active.
- **Suggestion**: Use the Stockfish agent to find your most frequent mistake patterns (e.g., "blunders into pins"). Have the LLM generate **custom puzzles** from your library specifically about pins in the openings you play.
- **Impact**: Direct remediation of your weaknesses.

### 4. Progress Dashboard (The 2300 Tracker)
- **Problem**: It's hard to see progress over 10 years.
- **Suggestion**: Track which "Manuals" or "Courses" you have completed and cross-reference them with your engine evaluation trends in those specific openings.
- **Impact**: Visual proof of growth and identifying "stale" knowledge.

## Current Backlog

| Priority | Feature | Description |
| :--- | :--- | :--- |
| **P0** | API Resilience | OpenAI Fallback for Gemini 429 errors. |
| **P0** | SQLite Foundation | Migrating all RAG data from Qdrant to robust FTS5 SQLite. |
| **P1** | Diagram Sync | Ensuring every diagram in the library can be rendered interactively. |
| **P1** | PGN Fingerprinting | 100% accurate deduplication of your 96k+ games. |
| **P2** | Weakness Agent | Stockfish agent that maps game errors to RAG content. |
| **P3** | Training UI | Flashcards or drills based on retrieved book content. |

## Documentation Strategy
- **README.md**: Updated after every phase with current API status and ingestion counts.
- **ARCHITECTURE.md**: Maintains the "System Map" for future agents.
- **VERIFICATION_LOG.md**: A dedicated record of what was tested and when (no system moves without a log entry).
