# Partner Consult: RRF Multi-Collection Merge (Phase 5)

**Date:** November 8, 2025
**Topic:** Reciprocal Rank Fusion for EPUB + PGN collections
**Consulting Partners:** ChatGPT, Gemini, Grok
**Status:** Awaiting partner input

---

## Introduction

We've successfully completed Phase 4 of our PGN variation splitting project. We now have two Qdrant collections with different content types:

- **EPUB Collection** (`chess_production`): 358,529 chunks from 1,052 chess books
- **PGN Collection** (`chess_pgn_repertoire`): 1,791 chunks from 1,778 PGN game files

Both collections are working independently with good retrieval quality. Now we need to implement Phase 5: merge results from both collections so users get the best content regardless of source format.

---

## What We Are Doing (Phase 5 Goal)

**Objective:** Implement Reciprocal Rank Fusion (RRF) to combine search results from both EPUB and PGN collections into a unified ranked list.

**Use Case Example:**
- User queries: "Benko Gambit opening repertoire"
- System should return:
  - EPUB chunks: Book chapters explaining Benko Gambit strategy
  - PGN chunks: Actual Benko Gambit game variations with annotations
  - Merged result: Best content from both sources, properly ranked

**Key Requirements:**
1. Search both collections with same query embedding
2. Merge results using RRF algorithm
3. Maintain retrieval quality (no degradation)
4. Preserve source attribution (user knows if result is from book or PGN)
5. Handle different metadata structures (EPUB vs PGN)
6. Keep existing single-collection endpoints working (`/query` for EPUB, `/query_pgn` for PGN)

---

## What We Have Done (Context)

### Phase 1-4 Completion Summary

**Phase 1:** Variation splitting implementation (718 lines)
- Split oversized PGN games into semantically coherent chunks
- Implemented eval compression, context headers, small chunk merging
- All 35 unit tests passing

**Phase 2:** Full corpus testing (1,779 games)
- 1,791 chunks created (only 5 games needed splitting)
- 0% chunks over 7,800 token limit
- 100% success rate

**Phase 3:** Qdrant ingestion
- Created separate `chess_pgn_repertoire` collection
- 1,791 points uploaded successfully
- Fixed hierarchical chunk ID bug
- Full corpus ingested ($0.0303 embedding cost)

**Phase 4:** Retrieval testing & web interface
- Created `/test_pgn` endpoint with web UI
- Validated similarity scores (0.70-0.74 normal range)
- Content preview optimization (skip PGN headers, show annotations)
- Example queries feature with randomization
- Backported improvements to EPUB interface

### Current System Architecture

```
User Query → OpenAI Embedding → Qdrant Search → Results

Currently TWO separate paths:
1. /query → chess_production (EPUB books)
2. /query_pgn → chess_pgn_repertoire (PGN games)

Proposed Phase 5:
User Query → OpenAI Embedding → [EPUB Search] + [PGN Search] → RRF Merge → Unified Results
```

### Existing Code Structure

**app.py:**
- `/query` endpoint (lines 112-388): EPUB-only search
  - Calls `search_qdrant()` with collection="chess_production"
  - Returns top 100 candidates
  - GPT-5 reranks to top 30
  - Synthesis pipeline generates answer

- `/query_pgn` endpoint (lines 392-459): PGN-only search
  - Calls `search_qdrant()` with collection="chess_pgn_repertoire"
  - Returns top 10 results
  - No synthesis (direct retrieval testing)

**rag_engine.py:**
- `search_qdrant()` function: Currently takes single collection name
- Returns list of scored results with metadata

---

## My Initial Ideas (Claude's Proposal)

### Option A: Create New RRF Module + New Endpoint

**Approach:**
1. Create `rrf_merger.py` module with RRF algorithm implementation
2. Create new `/query_merged` endpoint for cross-collection queries
3. Keep existing endpoints unchanged (backward compatibility)

**RRF Algorithm:**
```python
def reciprocal_rank_fusion(results_lists, k=60):
    """
    results_lists: List of ranked result lists from different sources
    k: Constant for RRF formula (default 60, commonly used)

    RRF Score = Σ(1 / (k + rank)) for each result across all lists
    """
    fused_scores = {}

    for results in results_lists:
        for rank, result in enumerate(results, start=1):
            result_id = result['id']
            score = 1 / (k + rank)

            if result_id in fused_scores:
                fused_scores[result_id]['rrf_score'] += score
            else:
                fused_scores[result_id] = {
                    'rrf_score': score,
                    'result': result,
                    'sources': []
                }

            fused_scores[result_id]['sources'].append({
                'collection': result['collection'],
                'rank': rank,
                'similarity': result.get('score', 0)
            })

    # Sort by RRF score descending
    merged = sorted(fused_scores.values(), key=lambda x: x['rrf_score'], reverse=True)
    return merged
```

**Implementation Steps:**
1. Modify `search_qdrant()` to add collection name to each result
2. Create `search_multi_collection()` function that calls search twice
3. Apply RRF to merge results
4. Return top N merged results (e.g., top 30 for synthesis)

**Advantages:**
- Clean separation: RRF in dedicated module
- Backward compatible: Existing endpoints unchanged
- Easy to test: Compare `/query` vs `/query_merged`
- Future-proof: Can add more collections later

**Questions/Concerns:**
- What should k value be? (60 is common, but should we tune it?)
- How many results to retrieve from each collection? (100 EPUB + 10 PGN = imbalanced)
- Should we normalize similarity scores before RRF?
- Do we need collection-specific weights? (e.g., boost EPUB 1.2x, PGN 1.0x)

### Option B: Modify Existing /query Endpoint

**Approach:**
1. Add `include_pgn=true` query parameter to `/query`
2. When enabled, search both collections and merge with RRF
3. Default to EPUB-only for backward compatibility

**Advantages:**
- Single endpoint for all queries
- No UI changes needed
- Progressive enhancement (opt-in multi-collection)

**Disadvantages:**
- More complex endpoint logic
- Harder to A/B test
- Potential for breaking existing behavior

---

## Questions for Our AI Partners

### For ChatGPT, Gemini, and Grok:

**1. RRF Algorithm Design:**
- Is the RRF formula above correct? Any modifications needed?
- What k value should we use? (default 60, or tune for our use case?)
- Should we normalize similarity scores before applying RRF?
- Do we need collection-specific weights? (EPUB vs PGN importance)

**2. Retrieval Strategy:**
- How many results to fetch from each collection?
  - EPUB: 100 candidates (current approach)
  - PGN: 10 candidates (current approach)
  - Should these be equal? (e.g., 50 + 50)
- Does imbalanced retrieval (100 EPUB + 10 PGN) bias RRF results?
- Should we use percentile-based retrieval? (e.g., top 5% of each collection)

**3. Architecture Decision:**
- **Option A:** New `/query_merged` endpoint (my preference)
- **Option B:** Modify existing `/query` with parameter
- **Option C:** Something else we're missing?

**4. Metadata Handling:**
- EPUB metadata: book_title, author, chapter, page_range, content_type
- PGN metadata: source_file, game_number, opening, eco, chapter
- How to present mixed results in UI? Show source type badge?
- Should metadata affect RRF ranking? (e.g., boost opening-tagged PGN for opening queries)

**5. Quality Validation:**
- How to test if RRF improves or degrades retrieval quality?
- Should we create test queries with known "ground truth" results?
- What metrics to track? (precision, recall, user satisfaction)

**6. Edge Cases:**
- What if PGN collection returns 0 results but EPUB returns 100?
- What if same content exists in both collections? (deduplication needed?)
- How to handle vastly different collection sizes? (358K EPUB vs 1.8K PGN)

**7. Performance:**
- Will searching two collections 2x the latency?
- Should we parallelize collection searches?
- Cache embeddings? (query embedding used for both searches)

**8. User Experience:**
- Should user control which collections to search? (checkboxes: EPUB, PGN)
- Or always search both by default?
- How to display mixed results? Show source type? Icons?

---

## What Are We Missing?

**Technical Gaps I'm Aware Of:**
1. Don't know if RRF is the best fusion method (vs. CombSUM, CombMNZ, Borda Count)
2. Unsure about optimal k value for our domain
3. No experience with collection weighting strategies
4. Unknown if our similarity scores need normalization

**Potential Issues:**
1. Collection size imbalance (358K vs 1.8K) might bias results
2. Different content granularities (EPUB chapters vs PGN game variations)
3. User might expect PGN content but get EPUB-heavy results (or vice versa)
4. Latency could increase with two searches
5. Synthesis pipeline expects EPUB-style content - will PGN chunks work?

**Questions for Partner Guidance:**
- Are there better fusion algorithms than RRF for our use case?
- Should we use a hybrid approach? (RRF + learned weights)
- Do we need query classification? (opening queries → boost PGN, strategy queries → boost EPUB)
- Should we implement collection-specific boosting based on query type?

---

## What We Need From Partners

**Please provide:**

1. **Your assessment of Option A vs Option B** (or propose Option C)
2. **RRF parameter recommendations** (k value, normalization, weights)
3. **Retrieval strategy** (how many from each collection, balancing approach)
4. **Metadata handling approach** (UI presentation, ranking influence)
5. **Quality validation strategy** (how to test if RRF is working well)
6. **Edge case handling** (empty results, size imbalance, deduplication)
7. **Any critical issues we're missing** (blind spots, risks)
8. **Implementation priorities** (what to build first, what can wait)

**After all partners respond, we'll synthesize:**
- Common recommendations (consensus)
- Divergent opinions (evaluate trade-offs)
- Best path forward (implementation plan)

---

## Partner Response Section

### ChatGPT Response:

**Summary:** Comprehensive implementation-ready plan with drop-in code

**Key Recommendations:**

1. **Architecture: Option A** - New `/query_merged` endpoint
   - Keep existing endpoints stable
   - Enables A/B testing and fallbacks
   - Clean separation: `rrf_merger.py`, `router.py`, `diversify.py`

2. **RRF Algorithm:**
   - Formula: `RRF = Σ w × (1/(k + rank))` - **CORRECT**
   - k value: **k = 60** (standard, tune 40-120 later)
   - **NO normalization** - RRF uses ranks, not raw scores
   - **YES collection weights** via intent router

3. **Intent Router (Light-weight):**
   - Opening/line queries (ECO, SAN, FEN, "mainline", "repertoire") → **w_PGN = 1.3, w_EPUB = 1.0**
   - Concept queries ("explain", "plans", "strategy", "why") → **w_EPUB = 1.3, w_PGN = 1.0**
   - Ambiguous → **w_EPUB = w_PGN = 1.0**

4. **Retrieval Strategy:**
   - **Balanced**: **50 EPUB + 50 PGN** (or 32+32 if latency-sensitive)
   - Avoids drowning PGN in large-collection noise
   - **Parallelize** with `asyncio.gather`
   - **Share query embedding** (compute once)
   - Per-store timeout: 150-250ms

5. **Metadata Handling:**
   - UI: Show **type badge** (Book / PGN)
   - Display: source name, ECO/opening for PGN, book title+chapter for EPUB
   - **Light ranking influence**: ECO/FEN/SAN in query → +0.3 PGN bias, "explain/why/plan" → +0.3 EPUB bias

6. **Quality Validation:**
   - Build offline eval: **100-150 labeled queries** (Opening-line, Concept, Mixed)
   - Ground truth: 3-5 "should appear" doc ids per query
   - Metrics: **NDCG@10, Recall@20, MRR@10, Source coverage@10**
   - Compare: EPUB-only vs PGN-only vs Merged
   - Log online: click-through, dwell, "kept in final answer" rate

7. **Edge Cases:**
   - PGN 0 results → RRF sums EPUB only (fine), show "No PGN hits" UI hint
   - Cross-source dupes → Use **MMR (λ=0.7)** + type-aware diversity (prefer 1 Book + 1 PGN in top-N)
   - Within-PGN dupes → Dedupe by canonical FEN or line_hash
   - Within-EPUB dupes → Dedupe by (book_id, section_path)

8. **Performance:**
   - Parallel searches, share embedding, 150-250ms timeout per store
   - Circuit breaker: if one store errors, return the other + UI hint
   - LRU cache for query embeddings

9. **User Experience:**
   - Default to **Both**, show **pills** to filter: All | Books | PGN
   - Each card: badge, source, tiny reason ("Matched FEN", "Matched ECO B20")
   - Answer composer: PGN-dominant → line-forward template, Book-dominant → explanatory bullets + model line

**Provided Drop-in Code:**
- Intent router (regex-based pattern matching)
- RRF merge with source weights + tie-breakers
- MMR diversity + type-aware dedupe
- Endpoint sketch for `/query_merged`
- Synthesis considerations for normalizing PGN chunks

**Implementation Priorities (1-week sprint):**
1. `/query_merged` endpoint + router + RRF (balanced k, weights)
2. Type-aware dedupe + MMR (FEN, line_hash, section_path)
3. UI badges + filter pills
4. Light PGN normalizer for synthesis (context header, tail compression)
5. Offline eval set (100 queries) + NDCG@10/MRR@10 harness
6. Logging: weights, per-source top-k, fusion ranks, clicks, citations

**Sensible Defaults:**
- RRF k: 60
- Top-k per store: 50 (or 32 if latency-sensitive)
- Router weights: 1.3 vs 1.0
- MMR λ: 0.7
- Rerank α (combine with rrf): 0.7
- Timeout per store: 200ms

**Alternative Fusions:**
- RRF robust for heterogeneous scales
- Could add **tiny CombMNZ bonus** (+0.05 if item appears in both lists) to reward cross-source agreement

**Final Checks:**
- A/B bucket: `/query` vs `/query_merged` for 10% traffic
- Fail-open: proceed with one store if other times out
- Coverage guardrail: opening queries need ≥1 PGN in top-10, concept queries need ≥1 Book in top-10

### Gemini Response:

**Summary:** Comprehensive, methodical recommendation with phased approach

**Key Recommendations:**

1. **Architecture: Option A** - New `/query_merged` endpoint
   - Single Responsibility Principle: Each endpoint has one job
   - Testability is the killer feature - can A/B compare all three endpoints
   - Future-proofing: Easy to add chess_tactics or chess_video_transcripts collections
   - Final step: Point main UI at `/query_merged` after validation

2. **RRF Algorithm & Parameters:**
   - Your code is **100% correct** - standard robust implementation
   - **k = 60**: Start here, don't try to tune yet (famously insensitive parameter)
   - **NO normalization**: RRF is rank-based by design, that's its advantage
   - **NO collection weights in RRF formula**: Apply via retrieval strategy instead

3. **Retrieval Strategy (MOST IMPORTANT):**
   - **CRITICAL FIX**: Fetch equal number of candidates (100+100, not 100+10)
   - Your 100 EPUB vs 10 PGN imbalance would heavily bias RRF
   - **Magic of RRF**: 358K vs 1.8K size imbalance doesn't matter!
     * Fetching 100 PGN = ~5.5% of entire collection (highly relevant)
     * Fetching 100 EPUB = ~0.03% of collection
     * PGN top-10 competes directly with EPUB top-10 in scoring
     * This imbalance is GOOD - gives PGN's "voice" equal volume

   **Advanced Strategy (Phase 6 - Query Classification):**
   - If "strategy" queries too PGN-heavy (or vice versa), classify queries
   - Opening-line queries: epub_limit=50, pgn_limit=150
   - Concept queries: epub_limit=100, pgn_limit=100
   - Start with 100+100, likely works 90% of time

4. **Metadata Handling & UI:**
   - **Must have source badge**: 📖 Book or ♟️ PGN icons
   - Metadata in RRF: Only care about result['id'], metadata comes along for ride
   - **No ranking influence from metadata**: Keep it simple, let query classification handle boosting

5. **Quality Validation:**
   - Create "golden set" of 25-50 test queries
     * Opening-specific: "Benko Gambit opening repertoire"
     * Strategy-general: "How to play against isolated queen pawn?"
     * Mixed: "Main plans in King's Indian Defense?"
   - Manually find "perfect" chunk IDs (top 3 results that SHOULD appear)
   - Measure **Mean Reciprocal Rank (MRR)**
   - **Goal**: /query_merged has higher average MRR than single-collection endpoints

6. **Edge Cases:**
   - Empty results: Your RRF code already handles perfectly (no special logic needed)
   - Deduplication: result_id (Qdrant UUID) IS the deduplication
     * If same ID in both lists, RRF correctly sums score (feature not bug)
   - Collection size imbalance: As said in #3, this is a FEATURE with equal retrieval

7. **CRITICAL BLIND SPOT: Synthesis Pipeline**
   - **#1 Risk you are missing**: Synthesis prompt engineered for book prose
   - Will now be fed PGN chunks: `1. e4 c5 2. Nf3 {Notes...}`
   - **LLM will get confused** by mixed-format context
   - **SOLUTION - Structured Prompting (NOT OPTIONAL):**

```
[Old Prompt]
Context:
{chunk 1}
{chunk 2}
---
Question: {query}

[NEW REQUIRED Prompt]
You are a world-class chess expert. Answer by synthesizing the following sources.
Some are from books (prose), others from PGN files (annotated move lists).
Use PGNs for specific lines and books for general strategy.

---
[Source 1: Book - "Mastering the King's Indian"]
{epub chunk text...}
---
[Source 2: PGN - "King's Indian Repertoire"]
{pgn chunk text... 1. d4 Nf6 2. c4 g6 ...}
---
User Question: {query}
```

   **This change is NOT OPTIONAL. Critical for high-quality synthesis.**

8. **Performance:**
   - Latency: max(search_epub, search_pgn) with parallelization
   - **Must parallelize** with asyncio.gather (non-negotiable)
   - Cache embeddings with Redis/LRU (hit rate high for repeated queries)

9. **User Experience:**
   - Default to both (merged)
   - Add checkboxes/toggles for power users
   - Source icons + color-coding (blue EPUB, green PGN)
   - Tailor preview snippets by type

**Implementation Plan (Gemini's Summary):**

1. **Architecture:** Option A
2. **Parallelism:** Refactor with asyncio.gather for both collections
3. **Retrieval:** Fetch limit=100 (or N=50) from BOTH collections
4. **RRF Module:** Use existing code as-is, k=60, no weights/normalization
5. **Synthesis:** **MODIFY PROMPTS** for mixed-media context (Book vs PGN)
6. **Validation:** Build golden set of 50 queries, use MRR to prove superiority
7. **UX:** Add source badges/icons
8. **Phase 6 (Future):** Query classification for dynamic retrieval balancing

**Final Assessment:** "This is a fantastic project. RRF merger + PGN splitter = truly state-of-the-art system."

### Grok Response:

**Summary:** Comprehensive best practices for RAG fusion with specific chess domain tuning

**Key Recommendations:**

1. **Architecture: Option A** (Strongly recommended)
   - Clean separation of concerns
   - Backward compatible
   - Testing capability (A/B compare)
   - **Option C Hybrid Suggestion**: Implement Option A, but add redirect/proxy in /query
     * If merge=true parameter set, internally call /query_merged
     * Single-endpoint UX without mutating core logic
     * Future-proof: Make search_qdrant() accept list of collections

2. **RRF Algorithm Design:**
   - Formula: **Correct** - standard RRF
   - Minor tweaks:
     * Use unique global result_id (hash of content or collection+chunk_id)
     * Store sources as array for traceability
     * Add fallback: If result in only one list, fine (RRF handles naturally)
   - **k value**: Start k=60, tune empirically
     * Test k=30 (aggressive fusion) vs k=100 (smoother)
     * Chess queries might benefit from **k=40** (boost rare but precise PGN hits)
   - **Normalize scores?** No for pure RRF (rank-based advantage)
     * If want score influence, hybridize: multiply RRF by normalized similarity
     * Keep pure RRF for simplicity unless tests show bias
   - **Collection weights?** Yes, lightly - apply multiplier to 1/(k+rank) per collection
     * weight EPUB=1.0, PGN=1.2 for opening-heavy queries
     * Make dynamic: Use query classification (move notation/repertoire → boost PGN 1.1-1.5)

3. **Retrieval Strategy:**
   - **Balanced 50 EPUB + 50 PGN** (down from 100+10)
   - Total 100 candidates pre-fusion, RRF to top 30 for reranking
   - **Imbalance bias**: Yes, 100+10 skews toward EPUB (more ranks contributing)
   - Balancing mitigates this; alternative: proportional fetching
   - **Percentile-based**: Optional but good for future scale
     * Retrieve top X% (0.1% EPUB, 5% PGN) to normalize density
     * Start without it, add if PGNs buried

4. **Metadata Handling:**
   - **UI**: Source badges/icons (📕 EPUB, ♟ PGN) + color-coding
   - Group metadata: Shared fields first (opening/ECO), then type-specific
   - **Affect ranking?** Lightly post-RRF
     * Secondary boost (+0.1 if PGN has matching opening tag for "opening" queries)
     * Detect query type via regex (gambit/repertoire → boost PGN)

5. **Quality Validation:**
   - **Benchmark set**: 50 test queries with ground truth
     * Manually ranked ideal EPUB+PGN mixes
   - **Metrics**: NDCG@30, Precision@10, Recall@30
   - **Ground truth categories**: 20 opening (PGN heavy), 20 strategy (EPUB heavy), 10 mixed
   - Use human eval (1-5 rating for "usefulness")
   - **Track**: Diversity (EPUB/PGN ratio in top 30), Latency, User Satisfaction

6. **Edge Cases:**
   - **0 results from one**: RRF degrades gracefully (just uses non-empty)
     * Add threshold: If <5 total, fallback to single-collection with warning
   - **Duplicate content**: Rare (EPUB prose vs PGN moves)
     * Dedupe post-fusion: If content similarity >0.9, keep higher RRF + merge metadata
   - **Size imbalance**: Mitigated by balanced fetching
     * For extreme skew, cap max contributions (no more than 60% from EPUB in top 30)

7. **Performance:**
   - **Latency**: ~1.5-2x if sequential, parallelize to minimize
   - **Parallelize**: Absolutely - asyncio.gather (negligible overhead)
   - **Cache embeddings**: Yes - Redis/LRU (high hit rate for repeated queries)
   - Expected: <200ms total

8. **User Experience:**
   - **Default to both** (merged)
   - Add checkboxes: "Include Books/PGNs" for power users
   - **Display**: Source icons + color (blue EPUB, green PGN)
   - Preview snippets: Tailor by type (EPUB: first para; PGN: key variation + annotation)
   - **Explainability**: Hover for "Why this rank? (RRF score + sources)" - builds trust

**Summary Recommendations:**

- **Assessment**: Strongly Option A, with Option C hybrid for UX polish
- **RRF Parameters**: k=60 start, no pre-normalization, dynamic weights via query classification (PGN 1.1-1.5 boost)
- **Retrieval**: Balanced 50+50, proportional if scaling
- **Metadata**: Shared fields + type-specific, light post-RRF boosts
- **Validation**: Benchmark with ground truth, track NDCG/Precision/Recall/Diversity
- **Edge Cases**: Graceful fallbacks, dedupe via similarity, cap per-collection in top ranks
- **Missing**:
  1. Query classification is key blind spot (implement basic regex/LLM to auto-boost)
  2. Synthesis adaptation: Tune GPT-5 prompt for mixed chunks
  3. Over-reliance on RRF without tuning could favor verbose EPUBs
- **Implementation Priorities**:
  1. Build/test RRF module standalone
  2. Add parallel multi-search
  3. New /query_merged endpoint
  4. Benchmark validation
  5. UI tweaks (badges/toggles)
  6. Advanced weights/classification after basics validated

**Final Note:** "This should get you to a robust merged system without over-engineering. Share sample query results or rrf_merger.py draft for refinements."

---

## Synthesis & Decision

[To be completed after all partners respond]

**Consensus Points:**
- [TBD]

**Divergent Opinions:**
- [TBD]

**Recommended Approach:**
- [TBD]

**Implementation Plan:**
- [TBD]

---

## Next Steps

After partner consult and synthesis:
1. Implement agreed-upon RRF approach
2. Create test queries for validation
3. Build RRF module
4. Modify endpoints as decided
5. Test retrieval quality
6. Update documentation
7. Commit to GitHub
