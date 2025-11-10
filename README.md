# Chess Knowledge RAG System

**A retrieval-augmented generation system for chess opening knowledge, powered by GPT-5 and 313,057 chunks from 922 chess books (536,243 extracted diagrams) + 1,778 PGN games.**

---

## 🎯 Quick Context for New Claude Sessions

### What This System Does
- **User asks:** "Explain the Italian Game opening"
- **System retrieves:** Relevant chunks from 1,055 chess books via Qdrant vector search
- **GPT-5 reranks:** Results by relevance
- **3-stage synthesis:** Creates coherent answer with chess diagrams
- **Output:** Professional article with interactive chess positions

### Current Status (November 10, 2025)
- ✅ **ITEM-008 Complete:** Sicilian contamination bug eliminated (100% success rate)
- ✅ **ITEM-011 Complete:** Monolithic refactoring (1,474 → 262 lines, -82.2%)
- ✅ **ITEM-024.7 Complete:** JavaScript rendering architecture (Path B) - Restored clean separation between backend and frontend
- ✅ **ITEM-027 Complete:** PGN ingestion system - All 1,778 games validated, 1,791 chunks in `chess_pgn_repertoire`, 100% query success
- ✅ **ITEM-028 Phase 5.1 COMPLETE:** RRF Multi-Collection Merge - Production-ready with UI integration
  - ✅ Query router with intent classification (8/8 tests passed)
  - ✅ RRF merger with k=60 and collection weights (8/8 tests passed)
  - ✅ Parallel multi-collection search with asyncio
  - ✅ /query_merged endpoint with complete pipeline (237 lines)
  - ✅ Mixed-media synthesis context (EPUB+PGN integration)
  - ✅ Module integration validated (5/5 tests passed)
  - ✅ **UI Integration Complete:** Main page uses /query_merged with dual scores, collection badges, corpus stats
- ⏸️ **ITEM-028 Phase 5.2 ON HOLD:** Validation paused pending PGN corpus expansion
  - ✅ Test suite: 50 curated queries (20 opening, 20 concept, 10 mixed)
  - ✅ Metrics: MRR, NDCG@5/10, Precision@5/10, Recall@5/10, F1@5/10
  - ✅ Framework: A/B testing script (EPUB vs PGN vs RRF comparison)
  - ✅ **Results:** Early termination after 28/50 queries - EPUB wins 28/28 (100%)
  - ⚠️ **Findings:** PGN corpus too small (1,778 vs 1M target), scored 0.000 on 25% of openings
  - 📊 **Status:** RRF system working correctly, validation paused until PGN corpus scaled to 1M games
- ✅ **ITEM-029 Phase 6.1a COMPLETE:** Static EPUB Diagram Integration (November 9, 2025)
  - **Extraction Pipeline:** COMPLETE ✅ (`extract_epub_diagrams.py` - 350+ lines)
  - **Test Results:** 2,046 diagrams from 3 books (100% success rate)
  - **Full Extraction:** COMPLETE ✅ (924 books total after all processing)
  - **Final Stats:** 536,243 diagrams extracted, ~12 GB total disk usage
  - **Data Cleaning:** Removed 17 low-quality books (9 batch 1, 8 batch 2 including 1 duplicate)
  - **.mobi Conversion:** 41 books converted from .mobi → EPUB, 31,875 diagrams extracted (avg 777/book)
  - **Qdrant Cleanup:** Removed 32,150 duplicate .mobi chunks (collection: 359,929 → 327,779)
  - **Output:** `/Volumes/T7 Shield/books/images/{book_id}/`
  - **Evaluation Enhancement:** Added deletion prompts to `analyze_chess_books.py` for books scoring <40/100
  - ✅ **UI Integration COMPLETE:** Static diagrams now displayed in search results
    - **diagram_service.py:** In-memory index with quality filtering and relevance ranking (242 lines)
    - **app.py:** Secure `/diagrams/<diagram_id>` endpoint + diagram attachment to results
    - **index.html:** Frontend rendering with responsive grid, lazy loading, graceful error handling
    - **Ranking Algorithm:** Text similarity (Jaccard) + opening keywords + sequential proximity + quality boost
    - **Security:** Metadata whitelist validation, trusted file paths only, 24-hour cache headers
    - **Partner Consultation:** Synthesized feedback from Gemini, Grok, ChatGPT
- ✅ **ITEM-030 Complete:** Duplicate Book Cleanup (Previous session)
  - **Duplicates Removed:** 4 duplicate books (herman_2014, rozentalis_0000, moskalenko_no_dg, plus 1 other)
  - **Note on `._*` files:** macOS metadata files are properly IGNORED in counts, not deleted (Mac needs them!)
  - **Qdrant Status:** Duplicates removed from vector database
  - **Tool Created:** `find_current_duplicates_fixed.py` for future duplicate detection
- ✅ **Bug Fix Complete:** Added `book_title` field to Qdrant ingestion
  - **Issue:** Ingestion pipeline only saved `book_name` (filename), not human-readable title
  - **Fix:** Extract title from EPUB metadata using `ebooklib`, fallback to filename if missing
  - **Location:** `build_production_corpus.py` lines 138-156 (extraction), 200 (chunk metadata), 294 (Qdrant payload)
  - **Impact:** Future ingestion will include human-readable titles for better UX
- ✅ **Dynamic Diagram Removal Complete** (November 10, 2025)
  - **Reason:** GPT-5/ChatGPT diagram generation never worked reliably - positions didn't match concepts
  - **Removed:** 7 files (diagram_processor.py, opening_validator.py, tactical_query_detector.py, diagram_validator.py, canonical_positions.json, canonical_fens.json, validate_canonical_library.py)
  - **Code Cleanup:** ~200 lines removed from app.py + 326 lines from README.md
  - **Bug Fix:** Fixed `diagram_time` variable reference → `diagram_attach_time`
  - **Current Solution:** Static EPUB diagrams only (Phase 6.1a - 536,243 diagrams)
- ✅ **ITEM-031 Complete:** Book Ingestion (November 10, 2025)
  - **Books Added:** 2 (Dvoretsky Endgame Manual 6th Ed, Markos Under the Surface 2nd Ed)
  - **Stats Change:** 920 → 922 books, 309,867 → 311,266 EPUB chunks, 534,467 → 536,243 diagrams
  - **New Content:** +1,399 chunks, +1,776 diagrams
  - **Cost:** $0.0143
  - **Bugs Fixed:** 2 (add_books_to_corpus.py wrong path, batch_process_epubs.py crash)
  - **Documentation:** Corrected inflated stats from previous sessions (946 books → 920 actual before today)
- 🎯 **Active Priority:** Test static diagram display in UI with 536,243 extracted diagrams
- 📦 **Future Work:** PGN corpus expansion to 1M games, then resume Phase 5.2 validation
- 🔧 **Architecture:** Clean modular design across 9 specialized modules
- 🔧 **System:** Fully synced with GitHub, Flask operational at port 5001

### Critical System Facts
- **Model:** GPT-5 (\`gpt-chatgpt-4o-latest-20250514\`)
- **Corpus:** 313,057 total chunks (311,266 EPUB + 1,791 PGN) across 2 Qdrant collections
- **Books:** 922 EPUB books, 1,778 PGN games
- **Diagrams:** 536,243 extracted from EPUBs
- **Success Rate:** 100% on Phase 1 & Phase 2 validation queries
- **Port:** Flask runs on port 5001
- **Auth:** GitHub SSH (no token expiration issues)

### Data Storage Structure
```
/Volumes/T7 Shield/books/
├── epub/                      # 946 chess books in EPUB format (after duplicate cleanup)
│   ├── kotronias_0000_the_safest_scandinavian_reloaded.epub
│   ├── john_2012_play_the_french_everyman_chess.epub
│   └── ... (944 more books)
│
└── images/                    # Extracted diagram images (Phase 6.1a COMPLETE)
    ├── book_{hash}/           # Organized by book ID
    │   ├── book_{hash}_0000.png
    │   ├── book_{hash}_0001.png
    │   └── ... (536,243 total diagrams across 922 books)
    └── ...
```

**Note:** Directory structure as of November 10, 2025. Count excludes macOS `._*` metadata files (Mac needs these - they are ignored, not deleted).

---

## 📦 System Architecture

### Module Overview (Post-Phase 5.1)
\`\`\`
chess-analysis-system/
├── app.py (499 lines)
│   ├── Flask routes, initialization
│   ├── /query endpoint - EPUB-only queries
│   ├── /query_pgn endpoint - PGN-only queries
│   └── /query_merged endpoint - RRF multi-collection merge (NEW Phase 5.1)
│
├── rag_engine.py (305 lines)
│   ├── execute_rag_query() - Main RAG pipeline (embed → search → rerank)
│   ├── format_rag_results() - Format search results for web display
│   ├── prepare_synthesis_context() - Context prep with source attribution (UPDATED)
│   ├── collect_answer_positions() - Collect positions from top sources
│   ├── search_multi_collection_async() - Parallel multi-collection search (NEW)
│   └── debug_position_extraction() - Debug helper
│
├── synthesis_pipeline.py (292 lines)
│   ├── stage1_generate_outline() - Create structured outline (JSON)
│   ├── stage2_expand_sections() - Expand with diagrams (UPDATED for mixed-media)
│   ├── stage3_final_assembly() - Assemble with smooth transitions
│   └── synthesize_answer() - Main orchestrator
│
├── rrf_merger.py (152 lines) - NEW Phase 5.1
│   ├── reciprocal_rank_fusion() - Core RRF algorithm with k=60
│   └── merge_collections() - Convenience wrapper for EPUB+PGN merge
│
├── query_router.py (136 lines) - NEW Phase 5.1
│   ├── classify_query() - Intent classification (opening/concept/mixed)
│   ├── get_collection_weights() - Collection-specific weights
│   └── get_query_info() - Convenience function
│
├── opening_validator.py (390 lines)
│   ├── extract_contamination_details() - ITEM-008 feedback generation
│   ├── generate_section_with_retry() - ITEM-008 automatic retry (max 2)
│   ├── validate_stage2_diagrams() - Opening signature validation
│   └── validate_and_fix_diagrams() - Diagram existence validation
│
├── diagram_processor.py (187 lines)
│   ├── extract_moves_from_description() - Parse moves from [DIAGRAM: ...] markers
│   ├── extract_diagram_markers() - Find all diagram markers in text
│   └── replace_markers_with_ids() - Replace markers with UUID placeholders
│
├── chess_positions.py (295 lines)
│   ├── detect_fen() - Find FEN strings in text
│   ├── parse_moves_to_fen() - Convert move notation to FEN
│   ├── extract_chess_positions() - Extract positions from chunks
│   ├── filter_relevant_positions() - Opening-specific filtering
│   └── create_lichess_url() - Generate Lichess analysis URLs
│
└── query_classifier.py (existing, not refactored)
    └── get_canonical_fen_for_query() - Classify query type & get canonical FEN
\`\`\`

**Total Code:** ~2,256 lines across 9 focused modules
**Phase 5.1 Additions:** +288 lines (rrf_merger.py, query_router.py), +237 lines (/query_merged endpoint)

---

## 🔄 Data Flow: How a Query Works

### Complete Pipeline
\`\`\`
1. USER REQUEST
   ├── POST /query {"query": "Explain the Italian Game"}
   └── app.py receives request

2. QUERY CLASSIFICATION
   ├── query_classifier.get_canonical_fen_for_query()
   ├── Determines: opening/middlegame/general
   └── Returns: canonical FEN if available

3. RAG PIPELINE (rag_engine.py)
   ├── execute_rag_query()
   │   ├── embed_query() → OpenAI embedding (3072-dim)
   │   ├── semantic_search() → Qdrant top-k=100
   │   └── gpt5_rerank() → GPT-5 rerank to top-n=10
   └── format_rag_results() → Web-ready format

4. SYNTHESIS PIPELINE (synthesis_pipeline.py)
   ├── synthesize_answer()
   │   ├── stage1_generate_outline() → JSON outline (3-5 sections)
   │   ├── stage2_expand_sections() → Expand with [DIAGRAM: ...] markers
   │   │   └── Uses ITEM-008 validation & retry if needed
   │   └── stage3_final_assembly() → Cohesive article
   └── Returns: Synthesized text with diagram markers

5. DIAGRAM PROCESSING (diagram_processor.py)
   ├── extract_diagram_markers() → Parse [DIAGRAM: 1.e4 e5 ...]
   ├── Convert moves → FEN → SVG boards
   └── replace_markers_with_ids() → Replace with UUIDs

6. RESPONSE
   └── JSON with answer, positions, sources, timing
\`\`\`

### Key Integration Points

**app.py \`/query\` endpoint:**
\`\`\`python
# Step 1: Classify query
query_type, concept_key, canonical_fen = query_classifier.get_canonical_fen_for_query(...)

# Step 2: Execute RAG
ranked_results, timing = execute_rag_query(...)
results = format_rag_results(ranked_results, ...)

# Step 3: Synthesize
context_chunks = prepare_synthesis_context(results, canonical_fen)
answer = synthesize_answer(OPENAI_CLIENT, query_text, context_chunks)

# Step 4: Process diagrams
diagram_positions = extract_diagram_markers(answer)
answer = replace_markers_with_ids(answer, diagram_positions)
\`\`\`

---

## 🐛 ITEM-008: The Sicilian Contamination Bug (RESOLVED)

### Problem (Discovered September 2024)
GPT-4o contaminated non-Sicilian 1.e4 openings with Sicilian Defense diagrams:
- **Italian Game** query → Generated Sicilian diagrams (1.e4 c5)
- **Ruy Lopez** query → Generated Sicilian diagrams
- **Caro-Kann** query → Generated Sicilian diagrams
- **Failure rate:** 40% on critical opening queries

### Root Cause
Deep training data bias in OpenAI models toward the Sicilian Defense (most popular e4 opening). Model swapping (GPT-4o → GPT-4-Turbo → GPT-5) didn't fix it.

### Solution (Implemented October 2025)
**Regeneration Feedback Loop** in \`opening_validator.py\`:

1. \`generate_section_with_retry()\` generates section content
2. \`extract_contamination_details()\` detects wrong opening signatures
3. If contaminated: Regenerate with specific feedback:
\`\`\`
   "Your previous response included Sicilian Defense (1.e4 c5). 
   This query is about Italian Game (1.e4 e5 2.Nf3 Nc6 3.Bc4). 
   Regenerate with ONLY Italian Game diagrams."
\`\`\`
4. Max 2 retries per section
5. Tracks attempts in \`expanded_sections\`

### Results
- **Before:** 0% pass rate on contaminated queries (4/4 failed)
- **After:** 100% pass rate (10/10 passed)
- **Sicilian contamination:** Eliminated completely

### Technical Implementation
\`\`\`python
# opening_validator.py
def generate_section_with_retry(
    openai_client, section, query, context, 
    opening_name, expected_signature, max_retries=2
):
    for attempt in range(max_retries + 1):
        content = generate_section(...)  # Call GPT-5
        
        # Validate diagrams
        if not has_contamination(content, expected_signature):
            return content, attempt + 1
        
        # Extract specific contamination details
        feedback = extract_contamination_details(content, expected_signature)
        
        # Regenerate with feedback
        context += f"\\n\\nFEEDBACK: {feedback}"
    
    return content, max_retries + 1
\`\`\`

---

## 🏗️ ITEM-011: Monolithic Refactoring (COMPLETED)

### Problem
\`app.py\` grew to 1,474 lines - impossible to reason about, test, or maintain.

### Solution: 5-Phase Extraction

| Phase | Module | Lines | Description | Status |
|-------|--------|-------|-------------|--------|
| 1 | \`chess_positions.py\` | 295 | Chess utilities | ✅ Complete |
| 2 | \`diagram_processor.py\` | 187 | Diagram markers | ✅ Complete |
| 3 | \`opening_validator.py\` | 390 | ITEM-008 validation | ✅ Complete |
| 4 | \`synthesis_pipeline.py\` | 292 | 3-stage synthesis | ✅ Complete |
| 5 | \`rag_engine.py\` | 215 | RAG orchestration | ✅ Complete |

### Results
- **Starting:** 1,474 lines (monolithic)
- **Ending:** 262 lines (Flask routes + init)
- **Reduction:** -82.2% (1,212 lines extracted)
- **Modules:** 6 focused, independently testable modules
- **Status:** All validated, on GitHub

### Validation Process (Master Prompt Standard)
Each phase required:
1. ✅ Git version control checkpoint
2. ✅ Backup creation
3. ✅ Module extraction with proper imports
4. ✅ Syntax validation
5. ✅ Functional testing (Flask + test query)
6. ✅ Log file review (never trust "complete" messages)
7. ✅ GitHub push

---

## 🔧 Development Setup

### Prerequisites
\`\`\`bash
# Python 3.11+
python3 --version

# Virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Mac/Linux

# Dependencies
pip install flask openai qdrant-client python-chess spacy
python -m spacy download en_core_web_sm
\`\`\`

### Environment Variables
\`\`\`bash
# Required
export OPENAI_API_KEY='your-api-key-here'

# Optional (defaults in code)
export QDRANT_PATH='./qdrant_production_db'
export COLLECTION_NAME='chess_production'
\`\`\`

### Running the System

**Docker Qdrant (Recommended - 15x faster startup)**

The system now uses Docker Qdrant for better performance:

```bash
# 1. Start Qdrant container (if not already running)
docker-compose up -d

# 2. Start Flask with Docker Qdrant
export OPENAI_API_KEY='your-openai-key-here'
export QDRANT_MODE=docker
export QDRANT_URL=http://localhost:6333
source .venv/bin/activate
python app.py

# Server starts in ~3 seconds (vs 45s with local mode)
# ✅ You'll see: "Using Docker Qdrant at http://localhost:6333"
# ✅ Flask: "Running on http://127.0.0.1:5001"
```

**Qdrant Dashboard:** http://localhost:6333/dashboard

**Local Qdrant (Legacy - slower)**

```bash
# Start Flask server with local Qdrant
export QDRANT_MODE=local  # or omit (defaults to local)
python3 app.py

# Server will start in ~45 seconds (loads 5.5GB into memory)
# ⚠️  Warning: "Not recommended for collections with >20,000 points"
```

**Performance Comparison:**
- **Docker:** 3s startup, persistent, production-ready
- **Local:** 45s startup, reloads on every restart, dev only

### Accessing the Application

**Option 1: Web Interface (Recommended)**
```bash
# Open your browser and visit:
http://localhost:5001

# Interactive UI with:
# - Query input form
# - Chess diagram visualization
# - Source attribution
# - Interactive Lichess boards
```

**Option 2: REST API (For programmatic access)**
```bash
# Query via curl
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain the Italian Game opening"}' \
  | jq '.answer' -r

# Response includes:
# - answer: Synthesized article text
# - diagram_positions: Array of chess diagrams with FENs & SVGs
# - sources: Top 10 source chunks from RAG
# - timing: Performance metrics
```

---

## 🎮 PGN Game Collection Pipeline (In Development)

**Status:** Design phase - pipeline under development

### Overview
Adding PGN game collections (1M+ games from Chessable, ChessBase, Modern Chess, etc.) to the RAG corpus for game-based queries.

**Sources:**
- Chessable course PGNs
- ChessBase mega database
- Modern Chess publications
- Publisher-specific collections
- Currently: 288K games in master ChessBase file (cleaning in progress)
- Target: 1M+ games total

### Design Questions (To Be Resolved)

**1. Chunking Strategy:**
- **Option A:** Each game = 1 chunk (simple, ~500-2000 tokens/game)
- **Option B:** Per-game with rich metadata (players, opening, ECO, annotations)
- **Option C:** Split by phase (opening/middlegame/endgame for annotated games)
- **Option D:** Critical positions only (extract key moments + annotations)

**2. Quality Filtering:**
- Master games only (2000+ rating)?
- Annotated games only?
- Exclude blitz/bullet games?
- Minimum game length (moves)?
- Deduplication strategy (transpositions, same games from different sources)?

**3. Metadata to Preserve:**
- White/Black players + ratings
- ECO code, Opening name
- Event, Site, Date, Round
- Result
- Annotations/comments
- Time control
- Source (Chessable/ChessBase/etc)

**4. Use Cases to Support:**
- "Show games where Carlsen played the Najdorf"
- "Rook endgame technique examples"
- "How to play against the London System"
- "Typical middlegame plans in the King's Indian"
- "Sacrificial attacks in the Sicilian Dragon"

**5. Scale Considerations:**
- Current corpus: 358K chunks from 1,134 books
- Adding 1M games could add 1-3M chunks (depending on chunking strategy)
- Estimate: Each game → 1-3 chunks (game + variations)
- Storage: ~10-30GB additional Qdrant storage
- Embedding cost: ~$5-15 for 1M games

**6. Development Plan:**
- Phase 1: Test with 100-1,000 sample games
- Phase 2: Build chunking + quality filtering
- Phase 3: Test retrieval quality
- Phase 4: Scale to full 1M+ dataset

### Sample Games Needed
For pipeline development: **100-1,000 representative PGN games**
- Mix of annotated and unannotated
- Mix of openings
- Mix of master/amateur games
- Mix of sources (Chessable, ChessBase, etc.)

### Future Scripts (Not Yet Created)
- `analyze_pgn_games.py` - Quality scoring for PGN collections
- `add_pgn_to_corpus.py` - Ingest PGN games to Qdrant
- `batch_process_pgns.py` - Batch PGN processing

---

## 📚 Adding New Books to the Corpus

### Overview
The system has **two separate workflows** for processing chess books:
1. **RAG Corpus Building** - EPUB/MOBI extraction and vectorization (what you need for adding books)
2. **File Analysis/Renaming** - PGN/PDF quality analysis (uses `chess_rag_system` module)

**Supported Formats for RAG Corpus:**
- ✅ **EPUB** (1,023 books) - via `ebooklib`
- ✅ **MOBI** (111 books) - via `mobi` library
- ❌ **PGN** - Analysis only, not added to RAG corpus
- ❌ **PDF** - Intentionally excluded to avoid contaminating RAG with low-quality extractions

**Why no PDF?**
PDF text extraction is unreliable for chess books due to:
- Diagram/notation corruption during extraction
- Inconsistent formatting across different PDF sources
- High risk of introducing noisy, malformed text into the corpus
- Decision: Only ingest high-quality EPUB/MOBI with clean text extraction

### Prerequisites
```bash
# Activate the virtual environment (CRITICAL!)
source .venv/bin/activate

# Verify ebooklib is available
python -c "import ebooklib; print('✓ ebooklib available')"
```

### Quick Start: Analyze New Books (EPUB/MOBI)

**Single Book Analysis:**
```bash
# Activate venv first
source .venv/bin/activate

# Analyze one book (works with both .epub and .mobi)
python analyze_chess_books.py "/path/to/book.epub"
python analyze_chess_books.py "/path/to/book.mobi"

# Output shows:
# - EVS Score (Educational Value Score)
# - Tier (TIER_1: 85+, TIER_2: 80-84, TIER_3: 70-79)
# - Author reputation score
# - Instructional content percentage
# - Tactical/strategic content analysis
```

**Batch Analysis (Multiple Books):**
```bash
# Activate venv
source .venv/bin/activate

# Analyze all books in a directory
python batch_process_epubs.py "/Volumes/T7 Shield/books/epub/1new"

# Results stored in: epub_analysis.db
# Query results:
sqlite3 epub_analysis.db "SELECT file, score, tier FROM epub_analysis ORDER BY score DESC LIMIT 10;"
```

### Understanding EPUB Analysis Results

**EVS Score Tiers:**
- **TIER_1 (85+):** Elite instructional content - High priority for RAG
- **TIER_2 (80-84):** Premium educational material - Good for RAG
- **TIER_3 (70-79):** Quality supplementary content - Include if space allows
- **Below 70:** Low instructional value - Consider excluding

**Key Metrics:**
- `score`: Overall educational value (0-100)
- `author_score`: Reputation bonus for GM/elite authors
- `instructional_pct`: % of text with teaching patterns
- `tactical_content`: Tactical concept density
- `strategic_content`: Strategic concept density

### Adding Books to Qdrant Vector Database

**Current Corpus:** 357,957 chunks from 1,052 books in `qdrant_production_db`

#### Complete Pipeline for Adding New Books

**Step 1: Analyze Book Quality**
```bash
source .venv/bin/activate
python batch_process_epubs.py "/path/to/new/books"

# Review scores
sqlite3 epub_analysis.db "SELECT filename, score, tier FROM epub_analysis WHERE full_path LIKE '%new%' ORDER BY score DESC;"
```

**Step 2: Select Books (Quality Threshold)**
- Option A: Add all books scoring 70+ (HIGH tier)
- Option B: Add books scoring 55+ (top MEDIUM tier)
- Option C: Add books scoring 45+ (all MEDIUM tier)

**Step 3: Rename to Standard Pattern**
```bash
# Pattern: lastname_year_title_publisher.{epub|mobi}
# Examples:
mv "Author, Name - Title [Publisher, Year].epub" \
   "lastname_year_title_publisher.epub"

mv "Author, Name - Title [Publisher, Year].mobi" \
   "lastname_year_title_publisher.mobi"
```

**Step 4: Choose Indexing Method**

**Method A: Incremental Addition (Recommended for <10 books)**
```bash
source .venv/bin/activate

# Set environment variables
export OPENAI_API_KEY='your-key-here'
export QDRANT_MODE=docker  # Use Docker Qdrant (recommended)
export QDRANT_URL=http://localhost:6333

# Add specific books to existing Qdrant database
python add_books_to_corpus.py book1.epub book2.epub book3.epub

# Alternative syntax:
python add_books_to_corpus.py --books "book1.epub" "book2.epub" "book3.epub"

# Add all books not yet in Qdrant:
python add_books_to_corpus.py --all-new

# Cost: ~$0.02-0.05 per book
# Time: ~30-60 seconds per book
# Result: Adds ~300-500 chunks per book to existing Docker Qdrant index
```

**Method B: Full Corpus Rebuild (For major updates)**
```bash
source .venv/bin/activate
export OPENAI_API_KEY='your-key-here'

# Rebuild entire corpus from scratch
python build_production_corpus.py

# Cost: ~$2-3 for 1,000+ books
# Time: ~2-4 hours
# Result: Fresh index with all books (ensures consistency)
```

**Step 5: Verify Addition**
```bash
# Check Qdrant collection size
python -c "
from qdrant_client import QdrantClient
client = QdrantClient(path='./qdrant_production_db')
info = client.get_collection('chess_production')
print(f'Total chunks: {info.points_count}')
"

# Test query on new content
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "topics from your new books"}' \
  | jq '.sources[0].metadata.book_title'
```

**Step 6: Restart Flask Server**
```bash
# Restart to ensure Qdrant changes are loaded
pkill -f "python.*app.py"
python app.py
```

### Extracting Diagrams from EPUBs

After adding books to the RAG corpus, you should extract chess diagrams from the EPUB files for static diagram display in the UI.

**Overview:**
- **Script:** `extract_epub_diagrams.py` (427 lines)
- **Purpose:** Extract all chess diagram images from EPUB files with metadata
- **Output:** `/Volumes/T7 Shield/books/images/{book_id}/` directories
- **Features:** Duplicate prevention, context extraction, metadata generation

**Extract Diagrams for All Books:**
```bash
# Activate environment
source .venv/bin/activate

# Extract diagrams from all EPUBs
python extract_epub_diagrams.py \
  --epub-dir "/Volumes/T7 Shield/books/epub" \
  --output-dir "/Volumes/T7 Shield/books/images" \
  --metadata-file diagram_metadata.json

# The script will:
# - Process all 920 EPUB files
# - Skip books with existing image directories (incremental)
# - Extract diagrams with surrounding text context
# - Generate metadata JSON with diagram info
# - Time: ~15-20 minutes for full collection
# - Output: ~920 book directories with extracted diagrams
```

**Extract Diagrams for Specific Books:**
```bash
# Test mode: process only 3 books
python extract_epub_diagrams.py --test-mode

# Custom limit: process first N books
python extract_epub_diagrams.py --limit 10
```

**How It Works:**
1. **Book ID Generation:** Each book gets unique ID: `book_{md5(filename)[:12]}`
2. **Image Extraction:** Extracts all images from EPUB (skips covers)
3. **Duplicate Prevention:** Tracks processed images to avoid re-extraction when same image appears in multiple HTML documents
4. **Context Extraction:** Captures surrounding text before/after each diagram
5. **Metadata Creation:** Generates JSON with diagram locations, context, and book info
6. **Output Structure:**
   ```
   /Volumes/T7 Shield/books/images/
   ├── book_a857fac20ce3/
   │   ├── book_a857fac20ce3_0000.png
   │   ├── book_a857fac20ce3_0001.png
   │   └── ...
   ├── book_910a140220d4/
   └── ...
   ```

**Verification:**
```bash
# Count total image directories (should match EPUB count)
cd "/Volumes/T7 Shield/books/images"
find . -maxdepth 1 -type d -name "book_*" | wc -l

# Expected: 920 (one per EPUB file)

# Check specific book extraction
ls -lh book_a857fac20ce3/
# Should show extracted diagram files
```

**Metadata File:**
The `diagram_metadata.json` contains:
- **stats:** Extraction statistics (total books, diagrams, formats)
- **diagrams:** Array of diagram metadata objects with:
  - `diagram_id`: Unique identifier
  - `book_id`, `book_title`, `epub_filename`: Book information
  - `file_path`: Path to extracted image
  - `html_document`: Source HTML file in EPUB
  - `context_before`, `context_after`: Surrounding text (up to 300 chars each)
  - `position_in_document`: Diagram index within HTML document

**Bug Fix (November 2025):**
The duplicate prevention bug was fixed in lines 171-222 of `extract_epub_diagrams.py`:
- **Problem:** Same diagram extracted multiple times when referenced across different HTML documents (navigation, TOC, chapters)
- **Example:** Fischer 2008 book extracted 13,032 files for 258 unique images (50x duplication)
- **Solution:** Added `extracted_images` set to track processed images and skip duplicates
- **Result:** Proper 1:1 mapping between unique images and extracted files

**macOS File System Gotcha (November 2025):**
The verification logic was updated in line 273 of `extract_epub_diagrams.py` to handle macOS metadata files:
- **Problem:** macOS automatically creates `._*` metadata files for every image file written to external drives
- **Symptom:** Verification reported "Expected 889 files, found 1778" (exactly 2x the expected count)
- **Root Cause:** macOS creates hidden `._book_a857fac20ce3_0000.jpg` files alongside actual `book_a857fac20ce3_0000.jpg` images
- **Solution:** Updated file count verification to exclude `._*` files: `len([f for f in dir.glob("*") if not f.name.startswith('._')])`
- **Impact:** This only affects macOS systems with external drives; the metadata files are harmless but were causing false verification failures
- **Note:** These `._` files store extended attributes and resource forks - they're created automatically by macOS and should be excluded from file counts

**When to Re-extract:**
- After adding new EPUB files to the collection
- After fixing corrupted image directories
- After deleting books (orphaned directories remain until cleanup)
- Script automatically skips books with existing directories (incremental mode)

#### Cost Estimation

**OpenAI Embedding Costs:**
- Model: `text-embedding-3-small` ($0.02 per 1M tokens)
- Average book: ~30,000 words = ~40,000 tokens
- Chunks per book: ~300-500 (512 tokens each with overlap)

**Per Book:**
- Embedding cost: ~$0.001-0.002
- Processing time: 30-60 seconds

**Example Scenarios:**
- 3 books (incremental): ~$0.05, 2-3 minutes
- 10 books (incremental): ~$0.15, 8-10 minutes
- 1,055 books (full rebuild): ~$2.50, 2-4 hours

#### Important Notes

**Incremental vs Rebuild:**
- **Incremental:** Fast, cheap, preserves existing index
  - Use for: Adding 1-10 books
  - Limitation: Can't remove old books or change chunk strategy

- **Full Rebuild:** Slower, comprehensive, fresh start
  - Use for: Major updates, corpus cleanup, strategy changes
  - Benefit: Ensures complete consistency

**Current Status (Nov 2025):**
- ✅ Incremental addition script (`add_books_to_corpus.py`) - Ready to use
- ✅ Full rebuild script (`build_production_corpus.py`) - Tested and working
- 📝 3 books prepared (Nov 6): simeonidis_2020, dreev_2019, dreev_2018 (not yet indexed)

### File Naming Convention

**CRITICAL:** All EPUB files must follow the standardized naming pattern for corpus consistency.

**Pattern:** `lastname_year_title_publisher.epub`

**Rules:**
- All lowercase letters
- Underscores instead of spaces
- Remove special characters (commas, apostrophes, brackets, etc.)
- Format: `author_year_description_publisher.epub`

**Examples:**
```
Original: Aagaard, Jacob - GM Preparation Strategic Play [Quality Chess, 2013].epub
Renamed:  aagaard_2013_gm_preparation_strategic_play_quality_chess.epub

Original: Dreev, Alexey - Improve Your Practical Play in the Endgame [Thinkers, 2019].epub
Renamed:  dreev_2019_improve_your_practical_play_in_the_endgame_thinkers.epub

Original: Soltis, Andrew - 500 Chess Questions Answered [Batsford, 2021].epub
Renamed:  soltis_2021_500_chess_questions_answered_batsford.epub
```

**Renaming Command:**
```bash
# Template
mv "/path/to/Original Name [Publisher, Year].epub" \
   "/path/to/lastname_year_title_publisher.epub"
```

### File Locations
- **Book Analyzer:** `analyze_chess_books.py` - Single EPUB/MOBI file analysis
- **Batch Processor:** `batch_process_epubs.py` - Multiple files
- **Analysis DB:** `epub_analysis.db` - SQLite results storage
- **Qdrant DB:** `./qdrant_production_db/` - Vector database (6GB)

### Example: Adding 7 New Books

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Analyze new books
python batch_process_epubs.py "/Volumes/T7 Shield/books/epub/1new"

# 3. Check results
sqlite3 epub_analysis.db <<EOF
SELECT
  SUBSTR(file, -60) as book,
  score,
  tier,
  author_score
FROM epub_analysis
WHERE file LIKE '%1new%'
ORDER BY score DESC;
EOF

# 4. Identify high-quality books (TIER_1 and TIER_2)
# These are candidates for corpus addition
```

### Troubleshooting

**Issue: "ModuleNotFoundError: No module named 'ebooklib'"**
- **Solution:** Activate the virtual environment: `source .venv/bin/activate`

**Issue: "No text content found in EPUB"**
- **Cause:** Corrupted or image-only EPUB
- **Solution:** Check `remove_corrupt_files.txt` for known bad files

**Issue: Low EVS scores for known good books**
- **Cause:** Puzzle books, game collections (not instructional)
- **Expected:** Only annotated games and teaching content score high

---

## 🎮 PGN Game Collection Pipeline (In Development)

**Status:** Architecture design phase - NOT YET IMPLEMENTED

### Overview

The system is being designed to support 1M+ PGN games from professional chess course materials:
- **Chessable courses** (~40%) - Structured opening repertoires
- **ChessBase Mega Database** (~30%) - High-quality master games
- **ChessBase PowerBases** (~15%) - Thematic collections (opening/player/endgame specific)
- **Modern Chess courses** (~10%) - Professional training content
- **ChessBase Magazine** (significant) - Every monthly issue since 1987
- **Chess Publishing monthly** (remaining) - Latest opening theory updates

### Key Context

**These are NOT random game databases** - They are professional course materials:
- Already curated and cleaned (user removed low-quality games)
- Course games have hierarchical structure (Course → Chapter → Section → Game)
- Even "unannotated" games in courses are teaching examples (model repertoire lines)
- Different sources serve different purposes (courses vs databases vs magazines)

### Design Documents

**1. PGN_CHUNKING_QUESTIONS.md**
- Comprehensive design questions for AI consultation
- 6 key areas: chunking strategy, filtering, metadata, variations, use cases, cost/scale
- 4 chunking options analyzed (full game, game+metadata, by phase, critical positions)

**2. PGN_SOURCE_CLARIFICATION.md**
- Critical context about professional course materials (not random games)
- Explains course structure and hierarchical organization
- 5 re-evaluation questions for architecture decisions
- Sent to multiple AIs for consultation

**3. CLAUDE_PGN_RECOMMENDATION.md**
- Claude's detailed recommendation: Modified Option B
- **One game = one chunk** with rich, source-aware metadata
- Preserves course hierarchy (course name, author, chapter, section)
- Minimal filtering (user already curated collection)
- Includes all variations in game (part of teaching context)
- Estimated: 850K-900K unique games after deduplication
- Cost: ~$2.40 for embeddings, ~15GB storage

### Recommended Chunking Strategy

**Modified Option B: Full Game + Rich Metadata**

Each chunk contains:
```
Source Metadata:
  source_type: "chessable_course" (or mega_database, powerbase, magazine, etc.)
  course_name: "Lifetime Repertoire: 1.e4"
  course_author: "GM Boris Avrukh"
  chapter: "Open Sicilian - Najdorf"
  section: "6.Bg5 - Poisoned Pawn Variation"

Game Header:
  White: Magnus Carlsen (2863)
  Black: Hikaru Nakamura (2789)
  Event: World Championship 2023, Round 5
  ECO: B97 (Najdorf Sicilian, Poisoned Pawn)
  Result: 1-0

Full PGN:
  1. e4 c5 2. Nf3 d6... (all moves, annotations, variations)
```

**Rationale:**
- Similar to successful book chunking (keeps context intact)
- Course structure preserved (like book chapters)
- Rich metadata enables precise filtering
- Cost-effective: ~$2.40 for 1M games
- Manageable scale: 1M chunks (not 5M with position fragmentation)

### Implementation Plan (Not Yet Started)

**Phase 1: Sample Testing**
1. Get 1,000 sample PGNs from user (mixed sources)
2. Create `analyze_pgn_games.py` - parsing, metadata extraction
3. Test chunking strategy with samples
4. Validate retrieval precision

**Phase 2: Pilot Batch**
1. Process 60K games (10K from each source)
2. Cost: ~$0.15
3. Test cross-source queries
4. Refine deduplication logic

**Phase 3: Full Scale**
1. Process all 1M games
2. Cost: ~$2.40, Duration: 2-2.5 hours
3. Create `add_pgn_to_corpus.py` - batch ingestion
4. Upload to production Qdrant

**Phase 4: Integration**
1. Update Flask to query books + games
2. Add source filtering to UI
3. Display game diagrams
4. Production deployment

### Cost Estimates

**Embedding:**
- 1M games × 1,200 tokens average = 1.2B tokens
- Cost: $2.40 (at $0.02 per 1M tokens)

**Storage:**
- Current corpus: 358K chunks (5.5GB)
- PGN addition: 1M chunks (~15GB)
- Total: ~20.5GB (Docker Qdrant handles easily)

**Processing Time:**
- Parsing: 30-60 minutes
- Embedding: 40-50 minutes
- Upload: 20-30 minutes
- **Total: 2-2.5 hours**

### Query Examples (Future)

When implemented, the system will support:

**Course-specific queries:**
- "Show me Avrukh's Najdorf repertoire against 6.Bg5"
- Returns: Games from his Chessable course with chapter context

**Latest theory queries:**
- "Latest Poisoned Pawn theory from 2023"
- Returns: Recent ChessBase Magazine games, theory updates

**Player-specific queries:**
- "Magnus Carlsen Najdorf wins"
- Returns: Mega Database + PowerBase + Magazine games

**Technique queries:**
- "Rook endgame technique"
- Returns: PowerBase endgames, course sections, annotated games

### Implementation Status (November 2025)

**Phase 1: Architecture & Consultation** ✅ **COMPLETE**
- ✅ Design questions document created
- ✅ Source clarification document created
- ✅ Claude's recommendation written
- ✅ All 4 AI responses received (Gemini, Grok, ChatGPT, Claude)
- ✅ Complete synthesis and decision framework documented
- ✅ Unanimous baseline approach confirmed

**Phase 2: Sample Testing** ✅ **COMPLETE**
- ✅ Sample PGN games received (1,779 games from 25 files)
- ✅ `analyze_pgn_games.py` implemented and tested
- ✅ `add_pgn_to_corpus.py` implemented
- ✅ Parser validated: 1,779 games, ~1M tokens, $0.02 cost

**Sample Collection Details:**
- Source: `/Users/leon/Downloads/ZListo` (Modern Chess courses)
- Files: 25 PGN files
- Games: 1,779 total
- Content: Mostly Modern Chess course materials with hierarchical structure
- Metadata: Course names, chapters, sections detected successfully

**Scripts Created:**
1. **`analyze_pgn_games.py`** (570 lines)
   - Parses PGN files (handles multiple games per file)
   - Extracts course metadata (Event, White/Black as chapter/section)
   - Creates chunks with breadcrumb headers
   - Detects source type (Modern Chess, Chessable, etc.)
   - Includes full games with annotations and variations
   - Handles encoding errors gracefully

2. **`add_pgn_to_corpus.py`** (230 lines)
   - Generates OpenAI embeddings (text-embedding-3-small)
   - Uploads to Qdrant (Docker or local)
   - Batch processing (100 chunks/batch)
   - Progress tracking and cost estimation
   - Dry-run mode for testing

3. **`test_pgn_retrieval.py`** (206 lines)
   - Tests ONLY the PGN collection (isolated from book data)
   - Verifies retrieval works correctly
   - Confirms results are from PGN games, not books
   - Includes test suite with 5 diverse queries
   - Calculates purity metric (% of results from PGN collection)

**Audit Trail & Data Quality:**
- Every chunk includes `game_number` field for complete traceability
- Format: `source_file` + `game_number` + `chunk_id` → exact game in exact file
- Enables easy cleanup of dirty data by tracking back to specific game
- Example: "mcm_openings_game_42" → Game #42 in mcm_openings.pgn

**Testing Isolation:**
- Separate Qdrant collections: `chess_production` (books) vs `chess_pgn_test` (PGN games)
- Prevents contamination when testing new PGN data
- Dedicated test script validates PGN-only retrieval
- Can merge collections after validation

**Phase 3: Testing & Validation** ✅ **COMPLETE** (November 7-8, 2025)
- ✅ Generated embeddings: 1,400/1,779 chunks (78.7% success)
- ✅ Uploaded to `chess_pgn_test` collection
- ✅ Retrieval testing: **100% purity** (zero contamination)
- ✅ Audit trail verified (source_file + game_number working)
- ✅ **Oversized chunk analysis completed** (November 8, 2025)

**Test Results:**
```
Embeddings: 1,400 chunks, 1.2M tokens, $0.024, 35 seconds
Retrieval: 5/5 queries @ 100% precision (all PGN data)
  - Benko Gambit: 0.65 avg score
  - London System: 0.55 avg score
  - Rook endgame: 0.54 avg score
  - Middlegame plans: 0.50 avg score
```

**Oversized Chunk Analysis** (November 8, 2025):
Re-analysis with comprehensive logging revealed:
- **Total chunks:** 1,779 (one game = one chunk)
- **Oversized chunks:** 4 (0.2%)
- **Files affected:** 4 out of 25 PGN files

**Oversized Chunk Details:**
| File | Game # | Tokens | Over Limit | Reason |
|------|--------|--------|------------|--------|
| Rapport's Stonewall Dutch - All in One | 1 | 41,209 | 33,017 | Massive "all-in-one" file with all variations |
| The Correspondence Chess Today | 9 | 12,119 | 3,927 | Deep analysis with extensive variations |
| Queen's Gambit with h6 (MCM) | 15 | 9,540 | 1,348 | Theory-heavy game with many lines |
| EN - Elite Najdorf Repertoire | 3 | 8,406 | 214 | Detailed opening analysis |

**Analysis logs:**
- `pgn_analysis_20251108_125859.log` - Full processing log
- `oversized_chunks_20251108_125859.log` - Oversized chunk details
- `pgn_summary_20251108_125859.json` - Statistical summary

**Phase 4: Production Scale** 🔧 **IN PROGRESS** (variation splitting validated on full corpus!)
- ✅ **Chunking strategy implemented:** Variation splitting (Option A chosen after AI partner consultation)
- ✅ **Phase 1 Complete:** Core implementation + 4 oversized files tested (35 unit + 5 integration tests passing)
- ✅ **Phase 2 Complete:** Full corpus testing - **ALL 1,779 games validated!**
  - Total chunks: 1,805 (only 26 extra from splitting)
  - Split rate: 0.28% (5 games split)
  - Max chunk: 7,608 tokens (under 7,800 limit)
  - Failures: 0
  - Token distribution: 75% under 1,000 tokens
- ✅ **Phase 3 Complete:** Qdrant PGN Collection Setup (November 8, 2025)
  - ✅ **Hierarchical chunk ID bug fix:** Prevented duplicates in recursively split variations
  - ✅ **Collection created:** `chess_pgn_repertoire` (1536-dim vectors, COSINE distance)
  - ✅ **Ingestion script:** `ingest_pgn_to_qdrant.py` (374 lines)
    - OpenAI text-embedding-3-small embeddings
    - Batch processing (100 chunks/batch)
    - SHA-256 deterministic UUID conversion
    - Test mode: 4 split games (17 chunks, $0.0009)
  - ✅ **Bug fixed:** Duplicate chunk_ids in recursive splits
    - Problem: `variation_index` not passed to recursive calls → all defaulted to 0
    - Solution: Hierarchical IDs (e.g., `var_002_002`, `var_002_003`)
    - Result: 17/17 unique points uploaded (was 15/17 with duplicates)
  - ✅ **Test ingestion:** 17 chunks uploaded successfully to Qdrant
  - ✅ **Full corpus ingestion bugs discovered and fixed:**
    - Bug 1: FEN collection crashed on board state mismatches (411 failures)
    - Bug 2: Upload timeout with 1,380+ points in single batch
    - Solution 1: Error handling in `collect_fens_from_node()` (graceful degradation)
    - Solution 2: Batch upload (200 points/batch) prevents timeouts
  - ✅ **Full corpus ingestion complete:** 1,778 games → 1,791 chunks
    - Games processed: 1,778/1,778 (100%)
    - Games failed: 0 (0%)
    - Points uploaded: 1,791/1,791 (100%)
    - Embedding cost: $0.0303
    - Chess Strategy Simplified: 133 chunks (all valid, no transpositions)
  - ✅ **Committed to GitHub:** All bug fixes + full ingestion
- ✅ **Phase 4 Complete:** PGN Retrieval Testing & Web Interface (November 8, 2025)
  - ✅ **Web interface created:** `/test_pgn` endpoint with dedicated HTML interface
  - ✅ **Retrieval testing complete:** 100% successful queries against `chess_pgn_repertoire` collection
    - Collection size: 1,791 chunks from 1,778 PGN games
    - Test queries: 5/5 passed with semantic similarity scores 0.70-0.74 (normal range)
    - Content preview optimized: Shows instructional annotations instead of PGN headers
  - ✅ **Similarity score validation:** 0.70-0.74 range confirmed normal for semantic search
    - EPUB collection baseline: 0.7388 for same query
    - PGN collection: 0.7093 for same query
    - Semantic mismatch between conversational queries and chess notation expected
  - ✅ **Example queries feature:** Randomized clickable query suggestions
    - Implemented in PGN interface (5 random queries from 20 options)
    - Backported to EPUB interface (5 random queries from 20 options)
    - Improves user discovery and engagement
    - Bug fix: Replaced biased `sort()` with Fisher-Yates shuffle for true randomization
  - ✅ **Style consistency:** PGN interface matches EPUB light theme
    - Header: #2c3e50, Blue: #3498db, Background: #f5f5f5
    - Responsive design with metadata grids
    - 1000-character content previews with instructional focus
- ✅ **Phase 5.1 Complete:** RRF merge for cross-collection queries (production-ready)
  - ✅ Implemented RRF (Reciprocal Rank Fusion) for multi-collection queries
  - ✅ Cross-collection queries working (EPUB + PGN via /query_merged)
  - ✅ UI integration complete with dual scores and collection badges
- ⏸️ **Phase 5.2 On Hold:** Validation awaiting PGN corpus expansion
  - Framework complete, validation paused pending 1M game corpus
  - Current 1,778 games insufficient for meaningful A/B testing

**Production Estimates (1M PGNs):**
- Based on sample: 0.2% oversized rate (very low)
- Expected chunks: ~998K (if excluding oversized)
- Cost: ~$20 (at $0.02 per 1M tokens)
- Time: ~6-8 hours

---

## 🧪 Testing & Validation

### Phase 1 Test Queries (Opening-Specific)
Critical queries that exposed Sicilian contamination:
1. Italian Game
2. Ruy Lopez
3. King's Indian Defense
4. Caro-Kann Defense

**Expected:** Diagrams match the queried opening  
**Validation:** Check FEN first moves (1.e4 e5 vs 1.e4 c5)

### Phase 2 Test Queries (Regression)
Ensure working queries remain working:
1. Sicilian Defense
2. Najdorf Variation
3. Najdorf vs Dragon comparison
4. Queen's Gambit Accepted vs Declined
5. Winawer Variation (French Defense)
6. French Defense

**Expected:** 100% pass rate (no regressions)

### Validation Methodology
\`\`\`bash
# 1. Start Flask
python3 app.py

# 2. Run test query
curl -X POST http://localhost:5001/query \\
  -H "Content-Type: application/json" \\
  -d '{"query": "Explain the Italian Game"}' > response.json

# 3. Check for correct opening signature
grep "1.e4 e5 2.Nf3 Nc6 3.Bc4" response.json
# Should find matches

grep "1.e4 c5" response.json
# Should find ZERO matches (no Sicilian contamination)

# 4. Check logs
tail -100 flask_output.log
# Look for: "✓ Created X sections", "✓ Expanded X sections"
\`\`\`

---

## 📊 System Performance

### Typical Query Timing (Italian Game)
\`\`\`
⏱ Request parsing:     0.01s
⏱ Embedding:           0.50s
⏱ Qdrant search:       0.15s
⏱ GPT-5 reranking:     8.50s
⏱ Response formatting: 0.05s
⏱ 3-stage synthesis:  25.00s
  ├── Stage 1 (outline):    3.00s
  ├── Stage 2 (expand):    18.00s  (3-5 sections × 3-6s each)
  └── Stage 3 (assembly):   4.00s
⏱ Diagram extraction:  0.10s
─────────────────────────────
🎯 TOTAL:             ~34.31s
\`\`\`

### Resource Usage
- **Vector DB:** ~6GB on disk (qdrant_production_db/)
- **Memory:** ~500MB RAM during query
- **API Costs:** ~$0.15 per query (GPT-5 reranking + synthesis)
- **Budget Target:** <$100/month

---

## 🚨 Common Issues & Solutions

### Issue: "OPENAI_API_KEY not set"
**Solution:**
\`\`\`bash
export OPENAI_API_KEY='sk-...'
python3 app.py
\`\`\`

### Issue: Sicilian Contamination Detected
**Check:**
1. Is \`opening_validator.py\` imported? ✅
2. Is \`expected_signature\` passed to synthesis? ✅
3. Check logs for "ITEM-008 retry" messages
4. Verify \`generate_section_with_retry()\` is being called

**Debug:**
\`\`\`python
# In synthesis_pipeline.py stage2_expand_sections()
# Should see:
if generate_section_with_retry_func and expected_signature:
    content, attempts = generate_section_with_retry_func(...)
\`\`\`

### Issue: Import Errors After Refactoring
**Verify module structure:**
\`\`\`bash
ls -la *.py
# Should see all 6 modules

python3 -c "import rag_engine; import synthesis_pipeline; import opening_validator"
# Should import without errors
\`\`\`

### Issue: Git Push Fails
**Check authentication:**
\`\`\`bash
git remote -v
# Should show: git@github.com:leonisawesome/chess-analysis-system.git

ssh -T git@github.com
# Should show: "Hi username! You've successfully authenticated"
\`\`\`

**Fix if using HTTPS:**
\`\`\`bash
git remote set-url origin git@github.com:leonisawesome/chess-analysis-system.git
\`\`\`

---

## 🐛 Known Bugs & Required Fixes (November 10, 2025)

### Critical Bugs Found During ITEM-031 Ingestion

**1. add_books_to_corpus.py - Hardcoded Wrong Path**
- **File:** `add_books_to_corpus.py` line 62
- **Issue:** `EPUB_DIR = "/Volumes/T7 Shield/epub"` (WRONG)
- **Actual:** `/Volumes/T7 Shield/books/epub`
- **Impact:** Incremental book addition completely broken
- **Status:** ✅ **FIXED** (Nov 10, 2025 - 2:20 PM)
- **Fix Applied:** Updated line 62 to `/Volumes/T7 Shield/books/epub`
- **Note:** User specifically asked previous Claude to fix this during directory restructure, but it wasn't done

**2. batch_process_epubs.py - Summary Report Crash**
- **File:** `batch_process_epubs.py` line 273
- **Issue:** `TypeError: '<' not supported between instances of 'str' and 'NoneType'`
- **Root Cause:** Trying to sort `format_stats` keys containing `None` values
- **Impact:** Crash at end of batch processing (after analysis completes)
- **Status:** ✅ **FIXED** (Nov 10, 2025 - 2:20 PM)
- **Fix Applied:** Added None filtering before sorting: `valid_formats = [k for k in summary['format_stats'].keys() if k is not None]`

**3. extract_epub_diagrams.py - No Specific File Support**
- **File:** `extract_epub_diagrams.py`
- **Issue:** Only supports `--epub-dir` (processes all files), no `--files` argument
- **Impact:** Wasteful - must process entire directory to extract from 2 new books
- **Status:** ❌ NOT FIXED YET (designed workaround used)
- **Fix Required:** Add `--files` argument to accept specific EPUB paths
- **Workaround:** Created inline extraction script for 2 specific books

### Learnings from ITEM-031

**Technical Discoveries:**
1. `extract_epub_text()` returns a **tuple** (text, None), not a string - must use `result[0]`
2. OpenAI embedding API limit: 300k tokens per request - batch at 100 chunks
3. Qdrant upload timeout: ~1400 points - batch at 200 points (learned from PGN ingestion Phase 3.5)
4. Documentation drift: README stats were ~40% inflated (724K → 536K diagrams)

**Process Failures:**
1. Previous Claude sessions claimed "complete" without validating actual state
2. Bug fixes requested by user were not implemented
3. Stats not updated after significant changes
4. Master Prompt principle violated: "Never trust status messages - Always validate with log files"

**Action Items for Future Claude Sessions:**
- Always verify stats with actual queries, not documentation
- Fix bugs when discovered, don't defer
- Update README/SESSION_NOTES/BACKLOG immediately after changes
- Check for hardcoded paths when directory structure changes
- Add specific file arguments to batch processing scripts

---

## 🔄 Common Development Tasks

### Adding a New Function to a Module

**Example:** Add \`validate_move_sequence()\` to \`chess_positions.py\`

1. **Add function to module:**
\`\`\`python
# chess_positions.py
def validate_move_sequence(moves: str) -> bool:
    """Validate chess move sequence is legal."""
    # Implementation here
    pass
\`\`\`

2. **Update imports in app.py:**
\`\`\`python
from chess_positions import detect_fen, parse_moves_to_fen, ..., validate_move_sequence
\`\`\`

3. **Use in app.py:**
\`\`\`python
if validate_move_sequence(moves):
    # Process moves
\`\`\`

4. **Test & Commit:**
\`\`\`bash
python3 -m py_compile chess_positions.py
git add chess_positions.py app.py
git commit -m "Add move sequence validation"
git push
\`\`\`

### Creating a New Module

**Example:** Create \`rating_analyzer.py\`

1. **Create module file:**
\`\`\`python
# rating_analyzer.py
"""
Rating Analysis Module
Analyzes player ratings from chess positions
"""

def analyze_position_complexity(fen: str) -> float:
    """Calculate position complexity score."""
    pass
\`\`\`

2. **Add to app.py imports:**
\`\`\`python
from rating_analyzer import analyze_position_complexity
\`\`\`

3. **Update this README:**
\`\`\`markdown
├── rating_analyzer.py (XX lines)
│   └── analyze_position_complexity() - Position complexity scoring
\`\`\`

### Debugging a Query

**Enable verbose logging:**
\`\`\`python
# In app.py, add at top of /query endpoint:
import logging
logging.basicConfig(level=logging.DEBUG)
\`\`\`

**Check each pipeline stage:**
\`\`\`python
print(f"DEBUG: Query type: {query_type}")
print(f"DEBUG: Ranked results count: {len(ranked_results)}")
print(f"DEBUG: Synthesis output length: {len(synthesized_answer)}")
\`\`\`

**Review logs:**
\`\`\`bash
tail -f flask_output.log | grep "DEBUG:"
\`\`\`

---

## 📚 Key Concepts for New Sessions

### Canonical FENs
**Purpose:** Pre-defined positions for middlegame concepts  
**File:** \`canonical_fens.json\`  
**Example:**
\`\`\`json
{
  "minority attack": "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 9",
  "isolated queen pawn": "..."
}
\`\`\`

**Usage:** Injected into synthesis context for accurate position generation

### Opening Signatures
**Purpose:** Validate diagram markers match the queried opening  
**Format:** First few moves (e.g., "1.e4 e5 2.Nf3 Nc6 3.Bc4")  
**Used in:** ITEM-008 contamination detection

### Diagram Markers
**Format:** \`[DIAGRAM: 1.e4 e5 2.Nf3 Nc6 3.Bc4]\`  
**Pipeline:**
1. GPT-5 generates text with markers
2. \`extract_diagram_markers()\` finds all markers
3. Converts moves → FEN → SVG chessboard
4. \`replace_markers_with_ids()\` replaces with UUID placeholders
5. Frontend renders interactive boards

### 3-Stage Synthesis
**Why 3 stages?** Better quality than single-shot generation:
1. **Stage 1 (Outline):** Structure with 3-5 sections - ensures complete coverage
2. **Stage 2 (Expand):** Detailed content per section - allows ITEM-008 validation per section
3. **Stage 3 (Assembly):** Smooth transitions - creates cohesive article

**Token savings:** Reuses outline, doesn't regenerate entire article

---

## 🎯 Project Status & Next Steps

### Completed Milestones
- ✅ **ITEM-001:** Initial Sicilian bug identification (Sept 2024)
- ✅ **ITEM-008:** Regeneration feedback loop solution (Oct 2025)
- ✅ **ITEM-011:** Monolithic refactoring (Oct 2025)
- ✅ **Phase 1-2 Validation:** 10/10 test queries passing
- ✅ **Git Infrastructure:** SSH auth, clean repo (899 KB)

### Current State
- **Branch:** \`main\` (merged from feature/hash-deduplication)
- **app.py:** 262 lines (target was <200, achieved 82% reduction)
- **System:** Production-ready, 100% success rate
- **Documentation:** This README

### Potential Future Work
1. **Further Optimization:** Reduce app.py by 62 more lines to hit <200 line target
2. **Unit Tests:** Add pytest tests for each module
3. **API Documentation:** OpenAPI/Swagger spec for /query endpoint
4. **Performance:** Cache embeddings, optimize reranking
5. **Features:** Add more canonical FENs, support tactics queries
6. **Deployment:** Docker containerization, production hosting

---

## 📖 References

### Important Files
- **Master Prompt:** Project operating manual (in chat history)
- **BACKLOG.txt:** ITEM-001, ITEM-008 history
- **refactoring_logs/:** Complete execution logs for all phases
- **canonical_fens.json:** Middlegame position library

### Key Chat Sessions (in Project)
- **"Monolith problem solution":** ITEM-011 phases 1-5
- **"Diagrams 4":** ITEM-008 implementation & validation
- **"PDF opening validation phase completion":** Testing & results

### External Resources
- **GPT-5 Docs:** https://platform.openai.com/docs/models
- **Qdrant Docs:** https://qdrant.tech/documentation/
- **python-chess:** https://python-chess.readthedocs.io/

---

## 🤝 Working with This System

### For New Claude Sessions

**First things to read:**
1. This README (you're reading it!)
2. Master Prompt (if provided)
3. Recent chat history for context

**Quick orientation:**
\`\`\`bash
# Check current state
git status
git log --oneline -10

# Review module structure
ls -lh *.py

# Check system health
python3 -c "import app; import rag_engine; import synthesis_pipeline"
\`\`\`

**Understanding user context:**
- User expects verbose explanations (not concise)
- User follows Master Prompt workflow (game plan → execution → validation)
- User values engineering discipline (fix root causes, test assumptions)
- User requires ONE copyable block for all Claude Code commands
- User validates with logs (never trust "complete" without logs)

### Master Prompt Principles

**CRITICAL RULES:**
1. **Never trust status messages** - Always validate with log files
2. **ONE block rule** - All commands in ONE pasteable block
3. **Always ask for approval** - Never assume permission to proceed
4. **Be verbose** - Show reasoning AND conclusions
5. **Git version control** - Checkpoint before every change
6. **Rollback plan** - Document before execution

**Bias Awareness:**
- Claude (Principal Architect): Action bias, shortcut tendency → AVOID
- ChatGPT/Grok (Partners): Over-engineering tendency → Balance

---

## 📊 System Metrics (As of October 2025)

### Code Metrics
- **Total Lines:** 1,641 (across 6 modules)
- **Reduction:** 82.2% from monolithic 1,474 lines
- **Modules:** 6 focused, independently testable
- **Functions:** ~30 well-documented functions

### Quality Metrics
- **Test Pass Rate:** 100% (10/10 validation queries)
- **Sicilian Contamination:** 0% (eliminated)
- **Syntax Errors:** 0
- **Git Health:** ✅ Clean, <1MB repo size

### Performance Metrics
- **Query Time:** ~34s average (end-to-end)
- **API Cost:** ~$0.15 per query
- **Success Rate:** 100% on opening queries
- **Uptime:** Development system (not monitored)

---

*README.md created as part of ITEM-011 completion - October 30, 2025*  
*Optimized for Claude context in new sessions*

---

## 🎨 Frontend Diagram Rendering

### Overview
Chess diagrams in answers are rendered client-side using secure SVG parsing to prevent XSS vulnerabilities.

### Architecture
```
Backend (/query endpoint):
  └─> Returns JSON with:
      ├─> answer: "Text with [DIAGRAM_ID:uuid] markers"
      └─> diagram_positions: [{id, fen, svg}, ...]

Frontend (diagram-renderer.js):
  1. Parse [DIAGRAM_ID:uuid] markers
  2. Use DOMParser to safely parse SVG strings
  3. Sanitize SVG (remove scripts, event handlers)
  4. Add accessibility features (ARIA, titles)
  5. Insert chess boards inline
```

### Files
- **static/js/diagram-renderer.js** - Main rendering logic (250+ lines)
  - `renderAnswerWithDiagrams()` - Parses markers and renders diagrams
  - `sanitizeSvgStringToElement()` - Security-focused SVG sanitizer
- **static/css/diagrams.css** - Diagram styling (responsive, accessible)

### Security Features
- **XSS Prevention:** DOMParser + attribute whitelisting
- **Sanitization:** Removes `<script>`, event handlers, `javascript:` URIs
- **Defense-in-depth:** Even backend-generated SVGs are sanitized

### Accessibility
- `role="img"` on diagram containers
- `<title>` elements in SVGs with FEN notation
- `aria-label` attributes for screen readers
- Keyboard navigation compatible

### Implementation (October 31, 2025)
Fixed diagram rendering bug where [DIAGRAM_ID:xxx] markers appeared as text instead of chess boards.

**Partner Consult:** ChatGPT, Gemini, Grok - unanimous recommendation for client-side DOMParser approach
**Security:** Production-grade sanitizer based on OWASP best practices
**Testing:** Validated with Italian Game query (3+ diagrams)
