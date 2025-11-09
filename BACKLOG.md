# Chess Analysis System - Development Backlog

**Philosophy:** Ship working features incrementally. Partner review at each milestone.

---

## MUST-HAVE FEATURES (Priority Order)

### Phase 6.1a: Client-Side Interactive Diagrams ✅ COMPLETE
**Goal:** Render FEN positions as interactive chessboards

**Status:** SHIPPED (November 9, 2025)

**What We Shipped:**
- ✅ FEN extraction already existed in diagram_processor.py (extract_fen_from_marker)
- ✅ Modified diagram-renderer.js to detect FEN and render with chessboard.js
- ✅ Interactive chessboards for all diagrams with FEN positions
- ✅ SVG fallback preserved for static diagrams
- ✅ Chessboard.js + Chess.js libraries already loaded in index.html

**Technical Details:**
- Backend: diagram_processor.py extracts FEN, includes in diagram_positions response
- Frontend: diagram-renderer.js checks for `diagram.fen` field, renders Chessboard() if present
- Board config: 400px width, centered, non-draggable (display only)
- Fallback: SVG rendering if no FEN available

**Time:** 1 hour (much faster than estimated - FEN extraction already existed!)

---

### Phase 6.1b: Fix Static Diagrams ⭐ CRITICAL
**Goal:** EPUB diagrams render correctly and are contextually relevant

**The Problem (Honest Assessment):**
1. Diagrams extracted from EPUBs are often:
   - Missing entirely (image extraction fails)
   - Present but unlinked to relevant text (chunking issue)
   - Irrelevant to the query (reranking doesn't consider diagrams)
2. Some EPUBs encode diagrams as:
   - Base64 images → may work
   - SVG chess notation → probably broken
   - External image files → likely missing

**Tasks:**
- [ ] Audit 20 random EPUBs to see HOW diagrams are encoded
- [ ] Fix image extraction in `epub_ingestion.py`
- [ ] Add `has_diagram: boolean` to chunk metadata
- [ ] Add `diagram_count: int` to chunk metadata
- [ ] Store diagram images in `./diagrams/{book_id}/{chunk_id}.png`
- [ ] Update GPT-5 reranking prompt to boost chunks with diagrams when relevant
- [ ] Test with 10 diagram-heavy books (Silman, Dvoretsky)

**Estimated Time:** 5-7 days
**Risk Level:** MEDIUM
- May discover EPUBs use unsupported diagram formats
- Image storage could grow large (budget 5-10GB)
- Some diagrams may be unsalvageable from source

**Partner Consult Topics:**
- Is increased storage acceptable?
- Which books MUST have working diagrams? (test priority)
- Acceptable failure rate? (90% working? 95%?)

**Definition of Done:**
- 90% of diagrams from top 100 books render correctly
- Diagram relevance improved (user testing)
- Documented list of books with broken diagrams

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
- ✅ Phase 5.1: RRF multi-collection merge
- ✅ Phase 5.2: Validation framework (IN PROGRESS: 11/50 queries)

**Active:**
- 🔄 Phase 5.2 validation running (~90 minutes remaining)

**Next Up:**
- ⏸️ Wait for validation results
- ⏸️ Analyze validation findings
- ⏸️ **Partner consult:** Review Phase 5 results, plan Phase 6

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
**Validation Status:** Phase 5.2 in progress (11/50 queries complete)
