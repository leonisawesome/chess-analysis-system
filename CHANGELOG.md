# Changelog - Completed Items

**Recent first, oldest at bottom**

---

## ITEM-033: Inline Diagram Rendering Fix (November 10-11, 2025) 🔄

**Problem:** Diagrams not displaying inline - HTML showing as plain text, markers not replaced
- Raw HTML `<div class="inline-diagram"...>` appearing literally in browser
- `[FEATURED_DIAGRAM_X]` markers visible as plain text (not replaced with images)
- Only 3 diagrams instead of 5-10 requested by user
- Wrong diagrams appearing (app store metadata, crossed arrows - not chess positions)

**Evidence:**
- PDF test: "Explain the Italian Game opening" showed literal HTML and unreplaced markers
- Second PDF test: "Nimzo-Indian Defense key concepts" showed wrong diagrams

**Root Cause (Partner AI Consensus):**
1. **Primary:** Frontend using `textContent` instead of `innerHTML` in renderAnswerWithDiagrams
2. **Secondary:** Marker replacement using fragile `replace()` method (only replaces first occurrence)
3. **Contributing:** Inconsistent marker formatting (newlines, whitespace variations)

**Partner Consultation:** Gemini, ChatGPT, Grok all identified same root cause and solution

**Solution (Implementing):**
1. Change `container.textContent = answer` → `container.innerHTML = processedAnswer` (line ~505)
2. Replace marker replacement with robust `split().join()` method
3. Add validation logging for debugging
4. Verify diagram URLs include file extensions

**Branch:** fix/inline-diagram-rendering

### Update (Nov 11, 2025)
- Added backend guard `enforce_featured_diagram_markers()` so the synthesized answer always has the same number of `[FEATURED_DIAGRAM_X]` markers as the `featured_diagrams` payload (and strips them entirely when no diagrams exist).
- `/query` legacy endpoint sanitizes outputs the same way, preventing stale markers in archived flows.
- Frontend now removes any leftover markers after attempting replacements, so literal `[FEATURED_DIAGRAM_X]` text can’t leak into the UI even if data drifts.
- Verified via `curl /query_merged` that 6 featured diagrams → exactly 6 markers before rendering.

**Status:** 🔄 IN PROGRESS (frontend visual verification still pending)

---

## ITEM-032: Phase 6.1a Debugging (November 10, 2025) ✅

**Problem:** All 3 diagram features broken after Phase 6.1a deployment
- GPT-5 writing `[DIAGRAM: ...]` placeholders (6 found)
- Featured diagrams returning 0 items
- 0/10 relevance sources appearing (10 found)

**Root Cause:** Flask module caching + data flow timing issues

**4 Fixes Implemented:**
1. **Code Loading Verification**: Added canary prints, cleared `__pycache__`
2. **Featured Diagrams**: Fixed data flow timing (diagrams attach at line 536, not 472)
3. **0/10 Filter**: Verified already correctly placed after GPT reranking
4. **GPT Placeholders**: Strengthened prompt + added regex strip fallback

**Test Results:**
- Italian Game query: 4 featured diagrams ✅
- epub_diagrams properly attached to results
- Defense in depth: prompt engineering + post-processing

**Files Modified:**
- app.py: Removed premature epub_diagrams copy, kept canary
- synthesis_pipeline.py: Strengthened prompt (line 188), added regex strip (line 338)

**Partner Consultation:** Gemini, Grok, ChatGPT identified caching as root cause

**Commit:** 72252f8

---

## ITEM-031: Book Ingestion (November 10, 2025) ✅

**Books Added:** 2
- Dvoretsky's Endgame Manual 6th Ed (1,053 chunks, 1,275 diagrams)
- Under the Surface 2nd Ed by Markos (346 chunks, 501 diagrams)

**Stats Change:** 920 → 922 books, 309,867 → 311,266 EPUB chunks, 534,467 → 536,243 diagrams

**Bugs Fixed:**
- add_books_to_corpus.py: Fixed hardcoded wrong path
- batch_process_epubs.py: Fixed crash on summary report

**Documentation:** Corrected inflated stats from previous sessions

---

## ITEM-030: Duplicate Book Cleanup (Previous session) ✅

- Removed 4 duplicate books
- macOS `._*` metadata files properly ignored (not deleted)
- Tool created: `find_current_duplicates_fixed.py`

---

## ITEM-029: Static EPUB Diagram Integration (November 9, 2025) ✅

- Extracted 536,243 diagrams from 922 books
- Created `diagram_service.py` with in-memory index
- Flask `/diagrams/<diagram_id>` endpoint
- Frontend rendering with lazy loading
- Ranking: Text similarity + keywords + quality boost

---

## ITEM-028: RRF Multi-Collection Merge (Complete) ✅

**Phase 5.1:**
- Query router with intent classification (8/8 tests passed)
- RRF merger with k=60 and collection weights
- Parallel multi-collection search with asyncio
- `/query_merged` endpoint with complete pipeline
- UI integration with dual scores and collection badges

**Phase 5.2:** On hold (waiting for PGN corpus expansion to 1M games)

---

## ITEM-027: PGN Ingestion System ✅

- All 1,778 games validated
- 1,791 chunks in `chess_pgn_repertoire` collection
- 100% query success rate
- Variation splitting for oversized games

---

## ITEM-024.7: JavaScript Rendering Architecture ✅

- Restored clean separation between backend and frontend
- Path B implementation (chessboard.js)

---

## ITEM-011: Monolithic Refactoring (October 2025) ✅

### Problem
`app.py` was 1,474 lines - unmaintainable monolith with synthesis, chess parsing, and diagram generation all mixed together.

### Solution
Extracted into 9 specialized modules:
- `rag_engine.py` - Vector search (105 lines)
- `reranker.py` - GPT-5 reranking (88 lines)
- `synthesis_pipeline.py` - 3-stage synthesis (179 lines)
- `chess_positions.py` - FEN/PGN parsing (122 lines)
- `diagram_generator.py` - SVG generation (145 lines)
- `content_formatter.py` - Markdown formatting (89 lines)
- `validation.py` - Quality checks (67 lines)
- `query_router.py` - Intent classification (71 lines)
- `rrf_merger.py` - Multi-collection merge (92 lines)

**Result:** `app.py` reduced to 262 lines (Flask routes only)
**Reduction:** 82.2% code reduction in main file
**Architecture:** Clean modular design with single responsibilities

---

## ITEM-008: Sicilian Contamination Bug (October 2025) ✅

### Problem
Querying "King's Indian Defense" contaminated with Sicilian Defense results:
- 70% of results were Sicilian instead of King's Indian
- Root cause: Regeneration feedback loop in 3-stage synthesis
- Stage 2 would regenerate Stage 1's correct results with wrong opening

### Solution
**Removed regeneration entirely** - each stage runs once:
- Stage 1: Generate outline
- Stage 2: Expand sections (no regeneration)
- Stage 3: Add diagrams (no regeneration)

### Results
- **Before:** 30% success rate (7/23 queries succeeded)
- **After:** 100% success rate (23/23 queries succeeded)
- No contamination across 50+ validation queries

---

## Earlier Items (2024)

- **ITEM-001:** Initial bug identification (September 2024)
- **ITEM-002-007:** Various features and fixes
- See git history for details

---

**Note:** For current status, see [README.md](README.md). This file contains historical completed items only.
