# System Architecture

## Overview

**Type:** Retrieval-Augmented Generation (RAG) system for chess knowledge

**Core Flow:**
```
User Query
  ↓
Vector Search (Qdrant)
  ↓
GPT-5 Reranking
  ↓
3-Stage Synthesis
  ↓
Response + Diagrams
```

---

## System Components

### 1. Data Layer
- **EPUB Books:** 937 books (last verified Nov 11, 2025), ~311k chunks — always run `python verify_system_stats.py` before quoting numbers
- **PGN Games:** 1,778 games, 1,791 chunks
- **Diagrams:** 536,243 images from EPUBs
- **Storage:** External drive `/Volumes/T7 Shield/books/`

### 2. Vector Database (Qdrant)
- **Collections:**
  - `chess_production`: 311,266 EPUB chunks
  - `chess_pgn_repertoire`: 1,791 PGN chunks
  - `chess_pgn_test`: 13,010 test chunks
- **Model:** text-embedding-3-small (1536 dimensions)
- **Distance:** Cosine similarity

### 3. Backend (Flask)
- **Port:** 5001
- **Main routes:**
  - `/query` - Single collection search
  - `/query_merged` - RRF multi-collection merge
  - `/diagrams/<id>` - Serve diagram images
- **Modules:** 9 specialized modules (see below)

### 4. Frontend
- **HTML/JS:** Vanilla JavaScript + chessboard.js
- **Features:** Lazy-loaded diagrams, dual scores, collection badges
- **Location:** `templates/index.html`

---

## Module Architecture

After ITEM-011 refactoring, app.py reduced from 1,474 → 262 lines.

### Core Modules

**rag_engine.py** (105 lines)
- Vector search via Qdrant
- Retrieves top-k chunks

**reranker.py** (88 lines)
- GPT-5 reranking by relevance
- Filters to top results

**synthesis_pipeline.py** (179 lines)
- 3-stage synthesis (outline → expand → diagrams)
- No regeneration (ITEM-008 fix)

**chess_positions.py** (122 lines)
- FEN/PGN parsing
- Board visualization

**diagram_generator.py** (145 lines)
- SVG chess diagram generation
- Dynamic position rendering

**content_formatter.py** (89 lines)
- Markdown formatting
- Code block handling

**validation.py** (67 lines)
- Quality checks
- Opening signature validation

**query_router.py** (71 lines)
- Intent classification (opening/concept/game)
- Routes to appropriate collection

**rrf_merger.py** (92 lines)
- Reciprocal Rank Fusion
- Merges EPUB + PGN results

**diagram_service.py** (242 lines)
- In-memory diagram index
- Relevance ranking (Jaccard + keywords)
- Quality filtering (size, format)

---

## Data Flow: Query to Response

### 1. User submits query
```
POST /query_merged
{
  "query": "Najdorf Sicilian",
  "top_k": 5
}
```

### 2. Intent Classification
```python
router = QueryRouter()
intent = router.classify_query("Najdorf Sicilian")
# Result: "opening" → search both EPUB + PGN
```

### 3. Parallel Vector Search
```python
# Search both collections in parallel
epub_results = qdrant.search("chess_production", ...)
pgn_results = qdrant.search("chess_pgn_repertoire", ...)
```

### 4. RRF Merge
```python
# Reciprocal Rank Fusion with k=60
merged = rrf_merge(epub_results, pgn_results, k=60)
# Weights: EPUB=0.6, PGN=0.4
```

### 5. GPT-5 Reranking
```python
# Rerank top 50 by relevance
reranked = reranker.rerank(merged[:50], query)
top_10 = reranked[:10]
```

### 6. Three-Stage Synthesis
```python
# Stage 1: Generate outline
outline = generate_outline(chunks, query)

# Stage 2: Expand sections
content = expand_sections(outline, chunks)

# Stage 3: Add diagrams (static only)
diagrams = attach_diagrams(content, query)
```

### 7. Return Response
```json
{
  "answer": "markdown content",
  "results": [
    {
      "text": "...",
      "book_name": "...",
      "score": 0.95,
      "collection": "EPUB",
      "diagrams": [...]
    }
  ]
}
```

---

## File Structure

```
/Users/leon/Downloads/python/chess-analysis-system/
├── app.py                    # Flask server (262 lines)
├── rag_engine.py             # Vector search
├── reranker.py               # GPT-5 reranking
├── synthesis_pipeline.py     # 3-stage synthesis
├── chess_positions.py        # FEN/PGN parsing
├── diagram_generator.py      # SVG generation
├── diagram_service.py        # Diagram index
├── query_router.py           # Intent classification
├── rrf_merger.py             # RRF merge
├── analyze_chess_books.py    # Quality scoring
├── add_books_to_corpus.py    # Incremental ingestion
├── extract_epub_diagrams.py  # Diagram extraction
├── verify_system_stats.py    # Stats verification
├── templates/
│   └── index.html            # Frontend UI
└── /Volumes/T7 Shield/books/
    ├── epub/                 # 937 EPUB files (current as of Nov 11, 2025)
    └── images/               # 536,243 diagrams
```

---

## Technologies

- **Python 3.11**
- **Flask** - Web server
- **Qdrant** - Vector database (Docker)
- **OpenAI** - Embeddings + GPT-5
- **python-chess** - Chess logic
- **ebooklib** - EPUB parsing
- **chessboard.js** - Frontend boards

---

## Configuration

### Environment Variables
```bash
export OPENAI_API_KEY='sk-proj-...'
export QDRANT_MODE='docker'  # or 'local'
export QDRANT_URL='http://localhost:6333'
```

### Constants
- **Chunk size:** 512 tokens
- **Chunk overlap:** 64 tokens
- **Embedding model:** text-embedding-3-small
- **RRF k-value:** 60
- **Collection weights:** EPUB=0.6, PGN=0.4

---

## Performance

- **Query latency:** 20-30 seconds
  - Embedding: 5-6s
  - Search: 1-2s
  - Reranking: 15-20s
- **Diagram loading:** Lazy (on-demand)
- **Cache:** 24-hour browser cache for diagrams

---

**For development workflow, see [DEVELOPMENT.md](DEVELOPMENT.md)**
**For troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)**
