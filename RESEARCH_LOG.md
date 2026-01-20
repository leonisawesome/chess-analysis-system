# Research & Implementation Log

## Context Overview
**System:** RAG-based Chess analysis using Gemini 2.0.
**Primary Storage:** SQLite (`chess_text.db`) with 210,330 chunks across ~1000 books and ~144k PGN games.
**Frontend:** `app_lite.py` (Flask) with `index.html`.

## Key Findings & Overhauls (Jan 19, 2026)

### 1. RAG Depth Fix (The "Snippet" Problem)
- **Discovery:** Retrieval was only providing 64-word snippets to Gemini.
- **Fix:** Overhauled `content_surfacing_agent.py` to retrieve the **full content** (up to 8,000 chars) per result.
- **Result:** Context window per query increased from ~1,000 words to ~100,000+ characters.

### 2. Search Precision Overhaul
- **Discovery:** Search was stripping quotes, making phrase matching impossible. Stopwords like "tell me about" were skewing results.
- **Fix:** 
  - Preserved quotes in `search_library`.
  - Added a filter to exclude index, bibliography, and copyright pages from context.
  - Added "instructional" words to the stopword list.

### 3. Answer Synthesis Quality
- **Discovery:** Default synthesis was factual but brief/encyclopedic.
- **Fix:** Updated Gemini 2.0 system instructions to act as a "Grandmaster Coach," demanding 600-1000+ word deep-dive lessons with move-by-move explanations.

## Ongoing Work: Interactive Diagrams
- **Current State:** Diagrams are static SVG/IMG or static `chessboard.js` (draggable: false).
- **Goal:** Enable "Play through variations" by integrating a PGN player or interactive move stack.

## Stale Configuration Notes
- `TROUBLESHOOTING.md` and `ARCHITECTURE.md` still contain legacy references to OpenAI/GPT-5.
- **Correction:** The system is officially transitioned to **Gemini 2.0**.
