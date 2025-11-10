# Chess Analysis System - Development Backlog

**Philosophy:** Ship working features incrementally. Partner review at each milestone.

---

## MUST-HAVE FEATURES (Priority Order)

### Phase 6.1a: Static EPUB Diagram Integration ✅ COMPLETE
**Goal:** Extract diagrams from EPUB files and display them in search results

**Status:** COMPLETE (November 9, 2025)

**What Was Built:**
1. ✅ Extract PNG/SVG diagrams from EPUB files → 724,062 diagrams extracted
2. ✅ Store diagrams in `/Volumes/T7 Shield/books/images/{book_id}/`
3. ✅ Link diagrams to text chunks via book-level matching + relevance ranking
4. ✅ Display diagrams in search results with responsive UI

**UI Integration Completion (November 9, 2025):**
- **diagram_service.py** (242 lines): In-memory index with quality filtering and relevance ranking
  - Book-level linking with reverse lookup (book_name → book_id)
  - Multi-factor ranking: Text similarity (Jaccard) + opening keywords + sequential proximity + quality boost
  - Quality filtering: min 12KB (removes icons/ribbons)
  - Loaded: 26,876 diagrams from 41 books indexed
- **app.py**: Secure diagram serving and attachment to results
  - `/diagrams/<diagram_id>` endpoint: Metadata whitelist validation, trusted file paths only
  - `/query_merged` integration: Top 5 diagrams per result
  - 24-hour cache headers for performance
- **index.html**: Frontend rendering with responsive grid
  - JavaScript diagram rendering (lines 756-790)
  - CSS styling with mobile support (lines 206-256)
  - Lazy loading, graceful error handling (onerror)
  - 2-column grid on mobile (<600px)
- **Partner Consultation**: Synthesized feedback from Gemini, Grok, ChatGPT
  - Consensus: Book-level + ranking (chapter-level blocked by missing `html_document` field)
  - Security: diagram_id endpoint to prevent path traversal
  - Architecture: In-memory index (200 MB acceptable)

**Final Statistics (Updated November 10, 2025):**
- **Books:** 946 total (after duplicate cleanup - removed 33 books)
- **Diagrams:** 724,062 extracted (~16.5 GB)
- **Qdrant:** 315,554 chunks (cleaned up from 327,779)
- **Data Cleaning:** Removed 17 low-quality books + 16 duplicate editions + 913 MacOS metadata files

**Time Taken:** 7 days (extraction + integration)
**Risk Level:** LOW (well-solved with partner consultation)

---

### Phase 6.1b: Dynamic Diagram Generation (FUTURE)
**Goal:** Generate diagrams on-the-fly for queries where no EPUB diagrams exist

**Status:** PENDING (awaiting 6.1a completion + partner consult required)

**The Problem (Honest Assessment):**
- GPT-5 diagram generation has **NEVER worked properly**
- Previous attempts were "band-aiding individual queries" instead of architectural fix
- Documented solutions (Enhancement 4.1, 4.2) in README not actually working
- Need partner consult for proper architecture

**Why This is Hard:**
- GPT-5 generates positions that don't match the concepts
- "Forks and pins" queries return positions without actual forks/pins
- Validation/enforcement approaches tried but failed
- Canonical position library exists (73 positions) but integration doesn't work

**Approach (TBD - Partner Consult Required):**
- Option A: Fix GPT-5 prompt engineering + validation
- Option B: Expand canonical library to thousands of positions
- Option C: Different architecture entirely
- **Decision:** Requires partner consultation after 6.1a complete

**Estimated Time:** 7-14 days (after partner consult)
**Risk Level:** HIGH (multiple failed attempts already)

**Definition of Done:**
- Dynamic diagrams actually render correctly in browser
- Positions match the concepts being discussed
- Works for common opening/tactical queries
- Acceptable failure rate determined through testing

---

### Phase 6.2: Interactive PGN Diagrams ⭐ MUST HAVE
**Goal:** PGN results show playable chessboard to step through moves

**The Reality:**
- This is actually straightforward (libraries exist)
- Main risk: UI clutter if showing 10 boards per query

**Tasks:**
- [ ] Add `chessboard.js` + `chess.js` libraries to UI
- [ ] Create `PgnBoard` component for each PGN result
- [ ] Parse PGN text to extract moves
- [ ] Add prev/next/reset buttons
- [ ] Add "copy PGN" button
- [ ] Add "analyze on Lichess" button (generates URL)
- [ ] Test with mobile devices (boards must be touch-friendly)
- [ ] Add collapse/expand for boards (show 1, hide others by default)

**Estimated Time:** 3-4 days
**Risk Level:** LOW
- Well-solved problem with good libraries
- Main work is UI polish

**Partner Consult Topics:**
- How many boards to show expanded by default?
- Desktop vs mobile layout preferences
- Should boards autoplay through the line?

**Definition of Done:**
- All PGN results have interactive boards
- Boards work on mobile
- "Analyze on Lichess" links work correctly
- No performance issues with 10 boards on page

---

### Phase 7: Conversational Interface ⭐ MUST HAVE
**Goal:** Multi-turn conversation like ChatGPT, not isolated queries

**The Reality (Brutal Honesty):**
- This is HARD and will have bugs
- Follow-up detection is fuzzy (AI will misunderstand sometimes)
- Context windows get expensive (storing conversation history)
- Users will expect ChatGPT-level intelligence (won't get it)

**Minimum Viable Conversation:**
```
User: "Najdorf Sicilian"
[Results]
User: "Tell me more about move 6"
System: [Searches corpus with context: "Najdorf Sicilian, move 6"]
User: "Show me GM games"
System: [Searches PGN collection with context]
```

**Tasks:**
- [ ] Add session storage (Redis or in-memory dict)
- [ ] Track last 5 messages + last results per session
- [ ] Build "intent classifier" to detect:
  - New query (search fresh)
  - Refinement ("more on X", "narrow to Y")
  - Follow-up question ("why?", "explain Z")
  - Show more ("next page")
- [ ] Update search to accept conversation context
- [ ] Add "Clear conversation" button
- [ ] Test with 50 multi-turn conversations
- [ ] Handle failures gracefully ("I didn't understand, can you rephrase?")

**Estimated Time:** 10-14 days
**Risk Level:** HIGH
- Intent classification will fail sometimes (users will be frustrated)
- Context management is complex
- Expensive (GPT-4 calls for every follow-up)
- May need multiple iterations to get UX right

**GOTCHAS TO WATCH FOR:**
1. User says "show me more" but we don't know "more" of WHAT
2. Conversation drifts off-topic, context becomes useless
3. Users expect memory beyond last 5 turns (won't have it)
4. Ambiguous pronouns ("tell me more about IT" - what is "it"?)

**Partner Consult Topics:**
- Acceptable failure rate for understanding? (70%? 80%?)
- How to handle "I don't understand" scenarios?
- Budget for GPT-4 API costs (could be $$$ with lots of users)
- Should we start with simple keyword-based follow-ups first?

**Definition of Done:**
- 80% of follow-ups correctly understood in testing
- Sessions persist for 1 hour
- Clear error messages when system doesn't understand
- Cost per conversation < $0.10 on average

---

## BACKLOG (Nice-to-Have, Future)

### Game Database Integration
**Goal:** Link opening theory to actual GM games from corpus

**Reality:** This is doable but requires position matching
- Search by FEN not just PGN text
- Index games by opening ECO codes
- **Time:** 5-7 days | **Risk:** MEDIUM

### Stockfish.js Engine Integration
**Goal:** Show engine evaluation for positions

**Reality:** CPU-intensive, may hang browser
- Stockfish WASM works but is slow
- May need web workers to avoid UI freeze
- **Time:** 7-10 days | **Risk:** MEDIUM-HIGH

### Full Agent Mode (Tool-Calling)
**Goal:** GPT-4 agent with tools like search_opening(), get_games(), etc.

**Reality:** This is the holy grail but very expensive
- Each interaction uses multiple GPT-4 calls
- Tool calling adds latency
- Users will push it to limits (cost explosion)
- **Time:** 14-21 days | **Risk:** HIGH

### Repertoire Builder
**Goal:** Save and organize personal opening lines

**Reality:** Requires authentication + database + UI
- User accounts = security + privacy concerns
- Database schema for saved lines
- **Time:** 10-14 days | **Risk:** MEDIUM

### Position Search (FEN Upload)
**Goal:** Upload a position, get book content

**Reality:** Requires FEN indexing (not implemented)
- Would need to re-index entire corpus with position FENs
- Similarity search on positions is hard (which FENs are "similar"?)
- **Time:** 14-21 days | **Risk:** HIGH

### Annotation Mode
**Goal:** Upload your game, get it annotated from corpus

**Reality:** Cool idea but very complex
- Requires position matching at every move
- Critical moment detection (where to annotate?)
- May not have corpus coverage for your specific position
- **Time:** 21-30 days | **Risk:** VERY HIGH

---

## CURRENT STATUS

**Completed:**
- ✅ Phase 1-4: EPUB ingestion, search, GPT-5 reranking
- ✅ Phase 5.1: RRF multi-collection merge (UI integrated, production-ready)
- ✅ Phase 5.2: Validation framework created (early termination after 28/50 queries)
- ✅ **Phase 6.1a: Static EPUB Diagram Extraction** (COMPLETE - November 9, 2025)
  - **Pipeline:** `extract_epub_diagrams.py` (350+ lines)
  - **Test:** 2,046 diagrams from 3 books (100% success)
  - **Full Extraction:** COMPLETE (979 books total after all processing)
  - **Final Stats:** 724,062 diagrams extracted, ~16.5 GB total disk usage
  - **Output:** `/Volumes/T7 Shield/books/images/{book_id}/`
  - **Data Cleaning:** Removed 17 low-quality books (9 batch 1, 8 batch 2 including 1 duplicate)
    - Batch 1: 9 books with <30 diagrams (7-29 range)
    - Batch 2: 7 books with 30-63 diagrams + 1 Silman duplicate (875 diagrams)
  - **.mobi Conversion:** 41 books converted from .mobi → EPUB using Calibre
    - Total: 31,875 diagrams extracted (avg 777/book, range 75-5,014)
    - All books passed quality check (no removals needed)
  - **Qdrant Cleanup:** Removed 32,150 duplicate .mobi chunks (collection: 359,929 → 327,779)
  - **Evaluation Enhancement:** Added deletion prompts to `analyze_chess_books.py` for books scoring <40/100

**On Hold:**
- ⏸️ **Phase 5.2 Validation:** Paused pending larger PGN corpus
  - **Reason:** Current 1,778 PGN games too small for meaningful validation
  - **Findings:** EPUB won 28/28 queries (100%), PGN scored 0.000 on 25% of openings
  - **Target:** Scale to 1M games before re-validating RRF merge
  - **Status:** RRF system working correctly, just needs more PGN data

**Future Work:**
- ✅ **Bug Fix Complete:** Added `book_title` field to Qdrant ingestion (November 9, 2025)
  - **Issue:** Pipeline only saved `book_name` (filename), not human-readable title
  - **Fix:** Extract title from EPUB metadata using `ebooklib`, fallback to filename
  - **Location:** `build_production_corpus.py` lines 138-156, 200, 294
  - **Note:** Existing Qdrant data still has missing titles (re-ingestion required for historical data)
- 🎯 **Phase 6.1b:** Test static diagram display in UI, then dynamic diagram generation (after partner consult)
- 📦 **PGN Corpus Expansion:** Scale from 1,778 → 1M games
- 🔄 **Phase 5.2 Resume:** Re-validate RRF after PGN corpus expansion

---

## RISK MITIGATION STRATEGY

1. **Ship small, test early**
   - Each phase ships a working feature
   - No "big bang" releases

2. **Partner checkpoints**
   - Review after each phase before starting next
   - Show working demo, discuss gotchas
   - Adjust priorities based on feedback

3. **Honest time estimates**
   - These estimates assume things will go wrong
   - Built-in buffer for debugging
   - If estimate was 5 days and it takes 7, that's normal

4. **Cost awareness**
   - Track OpenAI API costs per feature
   - Set budget limits before implementing
   - Have killswitch if costs spike

5. **Graceful degradation**
   - Features should fail gracefully
   - Always have fallback behavior
   - Clear error messages, not crashes

---

## NOTES ON AI OVERPROMISING

Things that SOUND easy but are HARD in practice:
- ❌ "Natural language understanding" → Fails 20-30% of the time
- ❌ "Context-aware responses" → Context window limits are real
- ❌ "Intelligent search" → Still needs good old-fashioned engineering
- ❌ "It'll just work" → No, it won't. Debugging is 80% of the work.

Things that ARE actually easy:
- ✅ Rendering interactive chess boards (solved problem)
- ✅ Linking to Lichess (just URL generation)
- ✅ Storing conversation history (basic session management)
- ✅ Keyword-based follow-ups ("show me more" = same query, next page)

**The Pattern:**
- If open-source library exists → probably easy
- If requires "AI understanding" → probably hard
- If requires "just" → definitely hard

---

**Last Updated:** 2025-11-09
**Phase 5.2 Status:** ON HOLD - Awaiting PGN corpus expansion (1,778 → 1M games)
