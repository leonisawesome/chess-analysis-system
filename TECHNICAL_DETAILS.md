# Technical Details - Chess Analysis System

## SYSTEM ARCHITECTURE

### Data Flow
```
User Query
    ↓
Flask /query_merged Endpoint
    ↓
OpenAI Embeddings API (query vectorization)
    ↓
Qdrant Parallel Search (EPUB + PGN collections)
    ↓
Optional LLM Reranking
    ↓
RRF Merge (k=60)
    ↓
FEN Parsing (chess.pgn library)
    ↓
Diagram Matching (FEN → diagram_metadata)
    ↓
Response with diagram URLs
```

### Collections & Data

**Qdrant Collections:**
- `chess_production` - 309,867 vectors (EPUB text chunks, 358,529 chunks from 1,055 books)
- `chess_pgn_repertoire` - PGN game database (1,778 games)

**Qdrant Connection:**
- URL: `http://localhost:6333`
- Running in Docker container
- No restart needed after reboot (persistent storage)

**Diagram Storage:**
- Location: `/Volumes/T7 Shield/rag/books/images/`
- Format: `book_{hash}/book_{hash}_{index}.{ext}`
- Total: 534,466 diagrams from 920 books
- Metadata: `diagram_metadata_full.json` (385MB JSON file)

---

## FILE CHANGES THIS SESSION

### app.py Line 106 (CRITICAL CHANGE)
**Before:**
```python
diagram_index.load('diagram_metadata_full.json', min_size_bytes=12000)
```

**After:**
```python
diagram_index.load('diagram_metadata_full.json', min_size_bytes=2000)
```

**Impact:**
- OLD: 462,147 diagrams loaded (8.3% filtered = 44,257 diagrams lost)
- NEW: 526,463 diagrams loaded (1.5% filtered = 8,003 diagrams lost)
- GAINED: 64,316 valid chess diagrams

**Rationale:**
- Size analysis showed 2-10KB range contains valid diagrams
- 12KB threshold was filtering out small but valid chess diagrams
- 2KB threshold properly filters icons/ribbons while keeping diagrams

---

## DIAGRAM SYSTEM DEEP DIVE

### Diagram Service (diagram_service.py)

**DiagramIndex Class:**
- Loads all diagram metadata into memory on startup
- Provides fast lookup by diagram_id or book_id
- Maintains whitelist of valid diagram IDs

**Key Methods:**
```python
def load(metadata_path: str, min_size_bytes: int = 12000) -> 'DiagramIndex':
    # Loads JSON, filters by size, indexes by ID and book
    # Returns self for chaining

def get_by_id(diagram_id: str) -> dict:
    # O(1) lookup by diagram_id
    # Returns diagram metadata dict or None

def get_by_book(book_id: str) -> list[dict]:
    # Returns all diagrams for a book
    # Sorted by index
```

**Metadata Structure:**
```json
{
  "diagram_id": "book_00448974a7ea_0000",
  "book_id": "book_00448974a7ea",
  "file_path": "/Volumes/T7 Shield/rag/books/images/book_00448974a7ea/book_00448974a7ea_0000.gif",
  "size_bytes": 2680,
  "format": ".gif",
  "width": 200,
  "height": 200,
  "context": "Some surrounding text from EPUB"
}
```

### Diagram Endpoint (app.py line 129-151)

```python
@app.route('/diagrams/<diagram_id>', methods=['GET', 'HEAD'])
def serve_diagram(diagram_id):
    """Serve diagram image by ID"""
    diagram = diagram_index.get_by_id(diagram_id)
    
    if not diagram:
        logger.warning(f"Invalid diagram ID requested: {diagram_id}")
        return jsonify({"error": "Diagram not found"}), 404
    
    return send_file(
        diagram['file_path'],
        mimetype=f'image/{diagram["format"][1:]}',  # Remove leading dot
        as_attachment=False
    )
```

**URL Format:**
- Pattern: `http://localhost:5001/diagrams/{diagram_id}`
- Example: `http://localhost:5001/diagrams/book_00448974a7ea_0000`
- Response: Binary image data (gif/png/jpg)

### Diagram Matching in Query Results

**FEN Parsing:**
- Extracts chess moves from text chunks
- Parses moves using python-chess library
- Converts positions to FEN notation
- Matches FENs to diagram metadata (future enhancement)

**Current Implementation:**
- Diagrams included in response JSON
- Frontend can display inline with results
- Lazy loading supported for performance

---

## DEPENDENCIES

### Python Packages (requirements.txt)
- `flask` - Web server
- `qdrant-client` - Vector database client
- `openai` - Embeddings and LLM API
- `python-chess` - Chess move parsing and FEN generation
- `spacy` - NLP for text processing
- `Pillow` - Image processing
- `ebooklib` - EPUB parsing

### External Services
- **Qdrant:** Vector database (localhost:6333)
- **OpenAI:** Embeddings API (text-embedding-3-small)
- **External Drive:** Diagram storage (/Volumes/T7 Shield)

### macOS Requirements
- Python 3.11+
- Virtual environment: `.venv/`
- Minimum 16GB RAM (for in-memory diagram index)
- External drive mounted for diagram access

---

## PERFORMANCE CHARACTERISTICS

### Startup Time
- Flask initialization: ~2-3 seconds
- Diagram metadata loading: ~3-5 seconds (385MB JSON)
- Qdrant connection: ~1 second
- spaCy model loading: ~2-3 seconds
- **Total startup:** ~10-15 seconds

### Query Performance
- Embedding generation: 5-6 seconds (OpenAI API)
- Parallel search: 1-2 seconds (Qdrant)
- Optional reranking: 15-20 seconds (LLM API)
- FEN parsing: Variable (depends on results)
- **Total query:** 20-30 seconds typical

### Memory Usage
- Flask app: ~500MB base
- Diagram metadata: ~400MB (in-memory index)
- spaCy model: ~200MB
- **Total:** ~1.1GB RAM

### Disk Usage
- Diagrams: ~15GB (/Volumes/T7 Shield/rag/books/images/)
- EPUBs: ~8GB (/Volumes/T7 Shield/rag/books/epub/)
- Qdrant data: ~2GB (vector storage)
- Metadata: ~400MB (JSON files)

---

## ERROR HANDLING

### Common Errors and Solutions

**1. Diagram 404 Errors**
```
WARNING:app:Invalid diagram ID requested: book_xxxxx_xxxx
```
**Cause:** Size filtering, missing metadata, or wrong ID
**Fix:** Check `min_size_bytes` in app.py line 106 (should be 2000)

**2. External Drive Not Mounted**
```
FileNotFoundError: /Volumes/T7 Shield/rag/books/images/book_xxx/book_xxx_xxx.gif
```
**Cause:** External drive disconnected or unmounted
**Fix:** Reconnect drive, restart Flask

**3. Qdrant Connection Failed**
```
ERROR: Could not connect to Qdrant at http://localhost:6333
```
**Cause:** Qdrant Docker container not running
**Fix:** `docker start qdrant-container-name`

**4. OpenAI API Timeout**
```
openai.APITimeoutError: Request timed out.
```
**Cause:** Slow network or API overload
**Fix:** Retry query, check internet connection

**5. Port Already in Use**
```
Address already in use
Port 5001 is in use by another program.
```
**Cause:** Previous Flask instance still running
**Fix:** `lsof -ti:5001 | xargs kill -9`

---

## TESTING & VERIFICATION

### Unit Tests
- None currently implemented
- Recommended: pytest for diagram service, FEN parsing

### Integration Tests
```bash
# Test diagram endpoint
curl -I http://localhost:5001/diagrams/book_00448974a7ea_0000
# Expected: HTTP/1.1 200 OK

# Test query endpoint
curl -X POST http://localhost:5001/query_merged \
  -H "Content-Type: application/json" \
  -d '{"query": "Najdorf Sicilian", "top_k": 5}'
# Expected: JSON with results array

# Test health check
curl http://localhost:5001/health
# Expected: {"status": "ok"}
```

### Load Tests
- Not yet performed
- Recommended: Apache Bench or Locust for concurrent queries

### Diagram Quality Checks
```bash
# Count diagrams by size
jq '.diagrams[] | .size_bytes' diagram_metadata_full.json | \
  awk '{if($1<2000) s++; else if($1<5000) xs++; else if($1<10000) s++; else if($1<20000) m++; else l++} END {print "XS:",xs,"S:",s,"M:",m,"L:",l}'

# Find diagrams by book
jq '.diagrams[] | select(.book_id == "book_00448974a7ea") | {diagram_id, size_bytes, format}' diagram_metadata_full.json

# Check for missing files
jq -r '.diagrams[] | .file_path' diagram_metadata_full.json | \
  while read f; do [ -f "$f" ] || echo "Missing: $f"; done
```

---

## LOGGING

### Log Files
- `flask_final.log` - Current Flask server output
- `flask_startup.log` - Previous startup attempt
- `flask_restart.log` - Restart after metadata fix
- `extraction_clean.log` - Diagram extraction output

### Log Levels
- INFO: Normal operations, query processing
- WARNING: Non-critical issues (404s, retries)
- ERROR: Critical failures (DB connection, API errors)

### Key Log Patterns
```bash
# Successful startup
grep "Loaded.*diagrams" flask_final.log

# Query processing
grep "QUERY_MERGED ENDPOINT" flask_final.log

# Diagram access
grep "diagrams" flask_final.log | grep "HTTP"

# Errors only
grep "ERROR" flask_final.log
```

---

## FUTURE ENHANCEMENTS

### Phase 6.1b: Dynamic Diagram Generation
- Generate diagrams from FEN positions on-the-fly
- Use chess.js or python-chess for rendering
- Cache generated diagrams

### Phase 6.2: Advanced Diagram Features
- Interactive diagrams (move pieces, show variations)
- Diagram annotations (arrows, highlights)
- Export diagrams (PNG, SVG, PGN)

### PGN Corpus Expansion
- Current: 1,778 games
- Target: 1,000,000 games
- Source: Lichess database, Chess.com

### Performance Optimizations
- Redis cache for frequent queries
- Diagram thumbnail generation
- CDN for diagram serving
- Async query processing
