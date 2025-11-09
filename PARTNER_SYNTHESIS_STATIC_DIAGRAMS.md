# Partner Synthesis: Static EPUB Diagram Integration

**Date:** November 9, 2025
**Participants:** Claude (original), Gemini (xAI), Grok (xAI), ChatGPT (OpenAI)

---

## 🎯 Critical Finding

**Qdrant Payload Inspection Results:**
```json
{
  "text": "...",
  "book_name": "unknown_author_0000_study_chess_with_tal.epub",
  "book_tier": "HIGH",
  "book_score": 88,
  "chapter_title": "unknown_author_0000_study_chess_with_tal.epub",  ← NOT actual chapter, just book_name
  "chapter_index": 0,
  "chunk_index": 0
}
```

**⚠️ KEY ISSUE:** No `html_document` field exists in Qdrant chunks. The `chapter_title` field is just the book filename, NOT the source HTML document name.

**Impact:** Gemini's recommended chapter-level matching (via `html_document`) **cannot be implemented** without re-ingesting all 327,779 chunks into Qdrant.

---

## 📊 Partner Responses Summary

### Gemini (xAI) - "Chapter-Level is Critical"

**Key Recommendations:**
1. ❌ **Chapter-level matching** via `html_document` - *BLOCKED* (field missing)
2. ✅ **Reverse lookup dict** (`book_name` → `book_id`) - Adopt
3. ✅ **Security hardening** - Change to `/diagrams/<diagram_id>` endpoint - Adopt
4. ✅ **Error handling** - Use `onerror="this.style.display='none'"` - Adopt
5. ✅ **Symlink option** - Consider for cleaner URLs

**Critical Insight:** "Book-level linking will show Chapter 10 diagrams for Chapter 1 content - this destroys user trust."

**Status:** Chapter-level recommendation blocked by missing metadata, but security/error handling advice is excellent.

### Grok (xAI) - "Hybrid Book-Level + Ranking"

**Key Recommendations:**
1. ✅ **Book-level + ranking** (Option D hybrid) - Adopt
2. ✅ **In-memory metadata** (200 MB is fine) - Adopt
3. ✅ **Quality filtering** (size-based) - Adopt
4. ✅ **Drive health check** on startup - Adopt
5. ✅ **Cache-Control headers** (`max-age=86400`) - Adopt
6. ✅ **Mobile responsive grid** - Adopt

**Ranking Suggestions:**
- `position_in_document` sort (sequential relevance)
- Quick string similarity (cosine on context vs. chunk text)
- Filter images <10KB (icons/ribbons)

**Critical Insight:** "Overload (889 diagrams) and irrelevance (random sidelines) require ranking, not just limits."

### ChatGPT (OpenAI) - "Lightweight Ranking + Drop-In Code"

**Key Recommendations:**
1. ✅ **Chapter-biased book-level** with ranking - Adopt
2. ✅ **Metadata whitelist validation** (not regex alone) - Adopt
3. ✅ **Quality filter** (<12KB images) - Adopt
4. ✅ **Jaccard text similarity** for ranking - Adopt
5. ✅ **Opening keyword matching** (ECO codes, "Najdorf", etc.) - Adopt
6. ✅ **Concrete ranking algorithm** with code samples - Adopt

**Ranking Algorithm:**
```python
score = 2.0 * same_html_doc  # N/A for us (no html_document)
      + 0.8 * token_overlap(chunk_text, context_before+after)
      + 0.4 * has_opening_keyword(chunk_topic, context_text)
      + 0.2 * position_proximity(chunk_index, position_in_document)
      + 0.1 * size_quality_boost
```

**Critical Insight:** "Provides drop-in code for DiagramIndex, ranking function, and endpoint security."

---

## 🏗️ Unified Architecture (Synthesis)

### Core Consensus (All 3 Partners Agree)

1. **In-Memory Metadata** (200 MB acceptable)
   - Load `diagram_metadata_full.json` on startup
   - Quality filter: Skip images <12KB
   - Index by `book_id` for fast lookup

2. **Secure Endpoint** (`/diagrams/<diagram_id>`)
   - NOT `/diagrams/<book_id>/<filename>` (user-controlled paths)
   - Validate `diagram_id` against metadata whitelist
   - Use metadata to resolve trusted file path
   - Add Cache-Control headers

3. **Lightweight Ranking** (Limit to 5 per result)
   - Text similarity (Jaccard/cosine)
   - Keyword matching (ECO, opening names)
   - Sequential proximity (position_in_document)
   - Quality boost (size-based)

4. **Embed URLs in API Response**
   - No separate `/diagrams_for_results` endpoint
   - Include `id`, `url`, `caption`, `book_title`
   - Frontend uses `<img loading="lazy">`

5. **Error Handling**
   - Server: Return 410 Gone if drive unmounted
   - Frontend: `onerror="this.style.display='none'"`
   - Graceful degradation (no crashes)

### Divergences & Resolution

| Question | Gemini | Grok | ChatGPT | **Decision** |
|----------|--------|------|---------|--------------|
| **Linking Strategy** | Chapter-level (html_document) | Book-level + ranking | Chapter-biased book-level | **Book-level + ranking** (chapter-level blocked) |
| **Endpoint Security** | diagram_id only | book_id + sanitization | Metadata whitelist | **diagram_id + whitelist** (Gemini/ChatGPT) |
| **Ranking Algorithm** | First 5 by index | position_in_document sort | Jaccard + keywords | **ChatGPT's full algorithm** (most comprehensive) |
| **Serving Method** | Symlink | Custom endpoint | Custom endpoint | **Custom endpoint** (more portable) |

---

## 🎯 Final MVP Architecture

### Phase 6.1a - Static Diagram Integration (3-4 hours)

#### 1. Startup: Load Diagram Metadata
```python
# app.py or diagram_service.py
from collections import defaultdict
import json

class DiagramIndex:
    def __init__(self):
        self.by_book = defaultdict(list)  # book_id -> [diagram_info]
        self.by_id = {}                   # diagram_id -> diagram_info
        self.whitelist = set()            # (diagram_id)
        self.book_name_to_id = {}         # book_name -> book_id (reverse lookup)

    def load(self, metadata_path):
        with open(metadata_path, 'r') as f:
            data = json.load(f)

        for d in data['diagrams']:
            # Quality filter: Skip small images (likely icons/ribbons)
            if d.get('size_bytes', 0) < 12000:
                continue

            book_id = d['book_id']
            diagram_id = d['diagram_id']

            # Store diagram
            self.by_book[book_id].append(d)
            self.by_id[diagram_id] = d
            self.whitelist.add(diagram_id)

            # Build reverse lookup (book_name -> book_id)
            book_name = d['epub_filename']
            if book_name not in self.book_name_to_id:
                self.book_name_to_id[book_name] = book_id

        # Sort diagrams by position_in_document for sequential relevance
        for book_id in self.by_book:
            self.by_book[book_id].sort(key=lambda x: x.get('position_in_document', 1e9))

        logger.info(f"Loaded {len(self.by_id):,} diagrams from {len(self.by_book)} books")
        logger.info(f"Quality filtered {data['stats']['total_diagrams'] - len(self.by_id):,} small images")

diagram_index = DiagramIndex()
diagram_index.load('diagram_metadata_full.json')
```

#### 2. Diagram Serving Endpoint (Secure)
```python
from flask import send_file, abort, Response
import os

DIAGRAM_ROOT = '/Volumes/T7 Shield/books/images'

@app.route('/diagrams/<diagram_id>')
def serve_diagram(diagram_id):
    """
    Serve diagram by ID (secure - no user-controlled paths).
    """
    # Validate against whitelist
    if diagram_id not in diagram_index.whitelist:
        logger.warning(f"Invalid diagram ID requested: {diagram_id}")
        abort(404)

    # Get trusted file path from metadata
    diagram_info = diagram_index.by_id.get(diagram_id)
    if not diagram_info:
        abort(404)

    file_path = diagram_info['file_path']

    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"Diagram file missing: {file_path}")
        return Response("Diagram file unavailable", status=410)  # Gone

    # Serve with caching headers
    response = send_file(file_path, conditional=True)  # Adds ETag/Last-Modified
    response.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours
    return response
```

#### 3. Lightweight Ranking Function
```python
import math
import re

# Stopwords for text similarity
STOP = set("""the a an and or of to in for on with from this that these those is are was were
              be as by after before during white black move moves plan plans strategy lines
              mainline variation position positions""".split())

# Opening keyword pattern
OPENING_HINT = re.compile(
    r'\b([A-E][0-9]{2}|najdorf|benko|hedgehog|caro-kann|sicilian|french|grunfeld|'
    r'king.?indian|...e5|...c5|ruy.?lopez|queens.?gambit)\b',
    re.IGNORECASE
)

def tokenize(text):
    """Extract meaningful tokens (no stopwords)."""
    tokens = re.findall(r"[A-Za-z0-9+.#=/-]+", (text or "").lower())
    return [t for t in tokens if t not in STOP]

def jaccard_similarity(text1, text2):
    """Compute Jaccard similarity between two texts."""
    set1, set2 = set(tokenize(text1)), set(tokenize(text2))
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)

def rank_diagrams_for_chunk(diagrams, chunk, max_k=5):
    """
    Rank diagrams by relevance to chunk.

    Returns: Top k diagrams sorted by score.
    """
    chunk_text = chunk.get('text', '')[:2000]  # First 2K chars
    chunk_index = chunk.get('chunk_index', 0)

    scores = []
    for d in diagrams:
        # 1. Text overlap (Jaccard similarity)
        diagram_context = f"{d.get('context_before', '')} {d.get('context_after', '')}"
        score_overlap = 0.8 * jaccard_similarity(chunk_text, diagram_context)

        # 2. Opening keyword match
        score_keyword = 0.0
        if OPENING_HINT.search(chunk_text) and OPENING_HINT.search(diagram_context):
            score_keyword = 0.4

        # 3. Sequential proximity (position in book)
        score_proximity = 0.0
        if 'position_in_document' in d:
            delta = abs((d['position_in_document'] or 0) - chunk_index)
            score_proximity = 0.2 * math.exp(-delta / 10.0)

        # 4. Quality boost (larger images prioritized)
        score_quality = 0.1 if d.get('size_bytes', 0) >= 25000 else 0.0

        # Total score
        total_score = score_overlap + score_keyword + score_proximity + score_quality
        scores.append((total_score, d))

    # Sort by score (descending)
    scores.sort(key=lambda x: x[0], reverse=True)

    # Return top k
    top_diagrams = [d for _, d in scores[:max_k]]

    # Fallback: Ensure at least 2 diagrams if available (even if low score)
    if len(top_diagrams) < min(2, len(diagrams)):
        top_diagrams = top_diagrams + [d for _, d in scores[len(top_diagrams):2]]
        top_diagrams = top_diagrams[:max_k]

    return top_diagrams
```

#### 4. Attach Diagrams to Search Results
```python
def attach_diagrams_to_results(results, max_per_result=5):
    """
    Attach top-ranked diagrams to each search result.
    """
    for result in results:
        payload = result['payload']
        book_name = payload.get('book_name', '')

        # Map book_name to book_id
        book_id = diagram_index.book_name_to_id.get(book_name)

        if not book_id:
            result['diagrams'] = []
            continue

        # Get all diagrams for this book
        all_diagrams = diagram_index.by_book.get(book_id, [])

        if not all_diagrams:
            result['diagrams'] = []
            continue

        # Rank diagrams by relevance
        ranked_diagrams = rank_diagrams_for_chunk(all_diagrams, payload, max_k=max_per_result)

        # Format for frontend
        result['diagrams'] = [
            {
                'id': d['diagram_id'],
                'url': f"/diagrams/{d['diagram_id']}",
                'caption': (d.get('context_before') or d.get('context_after') or 'Chess diagram')[:120],
                'book_title': d.get('book_title', 'Unknown'),
                'position': d.get('position_in_document', 0)
            }
            for d in ranked_diagrams
        ]

    return results

# In /query or /query_merged endpoint:
results = attach_diagrams_to_results(results, max_per_result=5)
```

#### 5. Frontend Integration (templates/index.html)
```javascript
// In displayResults() function
results.forEach(result => {
    // ... existing code to display text ...

    // Display diagrams if available
    if (result.diagrams && result.diagrams.length > 0) {
        const diagramsHtml = `
            <div class="diagrams-section">
                <h4>📷 ${result.diagrams.length} diagram(s) from "${result.diagrams[0].book_title}"</h4>
                <div class="diagram-grid">
                    ${result.diagrams.map(d => `
                        <div class="diagram-item">
                            <img
                                src="${d.url}"
                                alt="${d.caption}"
                                loading="lazy"
                                onerror="this.style.display='none'"
                            />
                            <p class="diagram-caption">${d.caption}</p>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        resultElement.innerHTML += diagramsHtml;
    }
});
```

#### 6. CSS Styling
```css
.diagram-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 15px;
    margin: 15px 0;
}

.diagram-item {
    text-align: center;
}

.diagram-item img {
    width: 100%;
    height: auto;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: #f8f9fa;
}

.diagram-caption {
    font-size: 12px;
    color: #666;
    margin-top: 5px;
    font-style: italic;
}

/* Mobile responsive */
@media (max-width: 600px) {
    .diagram-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}
```

---

## ✅ Improvements Over Original Plan

### Security Enhancements
- ✅ Changed from `/diagrams/<book_id>/<filename>` to `/diagrams/<diagram_id>`
- ✅ Metadata whitelist validation (not regex guessing)
- ✅ Trusted file paths from metadata only (no user-controlled paths)

### UX Improvements
- ✅ Quality filtering (skip images <12KB)
- ✅ Lightweight ranking (relevance-based, not random)
- ✅ Graceful error handling (`onerror` + 410 Gone)
- ✅ Mobile responsive grid (2 columns under 600px)

### Performance Enhancements
- ✅ Cache-Control headers (24-hour cache)
- ✅ Lazy loading images (`loading="lazy"`)
- ✅ Limited to 5 diagrams per result (prevents overload)

### Future Enhancements (Phase 6.1b)
- Generate thumbnails (256px WEBP)
- Drive health check on startup
- "View all diagrams" pagination
- Re-ingest Qdrant with `book_id` and `html_document` fields

---

## 📋 Implementation Checklist

### Phase 6.1a MVP (This Session)
- [ ] Create `diagram_service.py` with `DiagramIndex` class
- [ ] Add `load_diagram_metadata()` to app.py startup
- [ ] Implement secure `/diagrams/<diagram_id>` endpoint
- [ ] Implement `rank_diagrams_for_chunk()` function
- [ ] Modify `/query_merged` to call `attach_diagrams_to_results()`
- [ ] Update frontend JavaScript to render diagrams
- [ ] Add CSS styling for diagram grid
- [ ] Test with multiple queries (opening, tactical, endgame)
- [ ] Verify error handling (missing drive, invalid IDs)
- [ ] Update Big 3 documentation
- [ ] Commit to GitHub

---

## 🎓 Key Lessons from Partner Consultation

1. **Chapter-level matching is ideal but blocked** - Would require Qdrant re-ingestion
2. **Book-level + ranking is the pragmatic MVP** - Good enough UX without infrastructure changes
3. **Security must use metadata as source of truth** - Never trust user-provided file paths
4. **Quality filtering prevents UI pollution** - Skip small icons/ribbons
5. **Lightweight ranking beats random selection** - Text similarity + keywords + position
6. **Error handling must be graceful** - Silent failures better than crashes
7. **Partner consensus is strong** - All three agree on core architecture

---

## 🚀 Next Steps

1. **Implement** diagram service (3-4 hours estimated)
2. **Test** in browser with various queries
3. **Iterate** based on user feedback
4. **Document** in Big 3 + session notes
5. **Commit** to GitHub
6. **Plan** Phase 6.1b (thumbnails, health checks, pagination)

---

**Status:** Ready to implement ✅
**Confidence Level:** 95% (strong partner consensus)
**Risk Level:** LOW (no Qdrant changes, proven patterns)
