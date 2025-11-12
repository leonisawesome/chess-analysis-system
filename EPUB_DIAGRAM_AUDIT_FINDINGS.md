# EPUB Diagram Audit Findings
**Date:** November 9, 2025
**Books Audited:** 3 sample books from 1,055 total

---

## 🎯 Executive Summary

**FINDING:** Chess EPUB files contain **HUNDREDS OF THOUSANDS** of diagram images ready for extraction.

- **3 sample books:** 1,720 total diagrams (587, 797, 336 per book)
- **Projected total (1,055 books):** **~600,000 diagrams** (conservative estimate)
- **Formats:** Standard PNG/JPG images (easy to extract)
- **Structure:** Well-organized, predictable HTML layout

---

## 📊 Sample Data

### Book 1: kotronias_0000_the_safest_scandinavian_reloaded.epub
- **Images:** 587 (586 PNG, 1 JPEG cover)
- **HTML chunks with images:** 29
- **Image sizes:** ~15-16 KB per diagram

### Book 2: john_2012_play_the_french_everyman_chess.epub
- **Images:** 797 (796 JPG, 1 JPEG cover)
- **HTML chunks with images:** 18
- **Image sizes:** ~29-30 KB per diagram

### Book 3: simeonidis_2020_carlsens_neo_moller_nic.epub
- **Images:** 336 (335 JPG, 1 JPEG cover)
- **HTML chunks with images:** 256
- **Image sizes:** ~47-130 KB per diagram

### Aggregate Stats
- **Total diagrams (3 books):** 1,720
- **Average per book:** 573 diagrams
- **Formats:** 68% JPG, 32% PNG (both standard, widely supported)

---

## 🏗️ HTML Structure Pattern

### Typical Layout
```html
<!-- Chapter/section heading -->
<p><b>White's critical reply: 8.dxe5</b></p>

<!-- Chess moves leading to diagram -->
<p><b>1.e4 e5 2.Nf3 Nc6 3.Bb5 a6 4.Ba4 Nf6 5.0-0 Bc5 6.c3 0-0 7.d4 Ba7 8.dxe5</b></p>

<!-- DIAGRAM (in its own paragraph) -->
<p><img src="index-23_1.jpg"/></p>

<!-- Strategic explanation of the position -->
<p>In this chapter we will examine 8.dxe5, one of the most critical lines
against the Neo-Møller. The main feature in this line is Black's isolated pawn
which is created on d6...</p>
```

### Key Observations
1. **Diagrams are standalone:** Each `<img>` tag is in its own `<p>` element
2. **Move notation precedes diagrams:** Text before usually shows chess moves
3. **Strategic text follows:** Explanation/analysis comes after diagram
4. **No alt text:** Images typically have empty `alt=""` attributes
5. **Simple filenames:** e.g., `index-23_1.jpg`, `4_intro_converted_2.png`

---

## 💡 Extraction Strategy

### Phase 1: Image Extraction
1. **Iterate through all EPUB files** in `/Volumes/T7 Shield/rag/books/epub/` (1,055 books)
2. **Extract all images** (skip covers, keep diagrams)
3. **Store with unique IDs:** `{book_id}_{image_name}`
4. **Save to:** `/Volumes/T7 Shield/rag/books/images/{book_id}/`

### Phase 2: Text-Image Linking
1. **Parse HTML documents** in each EPUB
2. **Find `<img>` tags** and their positions in text flow
3. **Identify surrounding text:**
   - **Before:** Previous sibling `<p>` elements (chess moves)
   - **After:** Next sibling `<p>` elements (strategic discussion)
4. **Create linkage mapping:** `{diagram_id: chunk_id}`

### Phase 3: Qdrant Integration
1. **Add metadata fields** to existing chunks:
   ```python
   {
       "diagram_ids": ["book123_diagram_045", "book123_diagram_046"],
       "diagram_count": 2
   }
   ```
2. **Re-upload chunks** with diagram metadata (or update in-place)

### Phase 4: Frontend Display
1. **Modify search results** to check for `diagram_ids`
2. **Display diagrams inline** with chunk text
3. **Image serving:** Static files from `static/diagrams/{book_id}/{image_name}`

---

## 📏 Storage Estimates

### Conservative Estimate
- **Books:** 1,055
- **Avg diagrams/book:** 400 (lower bound from samples)
- **Avg size/diagram:** 30 KB
- **Total diagrams:** ~420,000
- **Total storage:** ~12.6 GB

### Realistic Estimate
- **Books:** 1,055
- **Avg diagrams/book:** 573 (actual sample average)
- **Avg size/diagram:** 35 KB
- **Total diagrams:** ~604,000
- **Total storage:** ~21 GB

### Upper Bound
- **Books:** 1,055
- **Avg diagrams/book:** 750 (some books are very diagram-heavy)
- **Avg size/diagram:** 40 KB
- **Total diagrams:** ~791,000
- **Total storage:** ~31.6 GB

**RECOMMENDATION:** Budget **25-30 GB** for diagram storage

---

## ⚠️ Technical Considerations

### Challenges
1. **File path variations:** Some use `images/00001.jpg`, others use `4_intro_converted_1.png`
2. **Cover images:** Need to filter out (typically named `cover.jpeg`)
3. **Chunking alignment:** Must match existing Qdrant chunk boundaries
4. **Encoding issues:** Some EPUB HTML has UTF-8 encoding quirks

### Solutions
1. **Path normalization:** Handle different directory structures
2. **Cover detection:** Skip images named `cover.*` or in `Cover` directories
3. **Chunk matching:** Use book_name + position heuristics to link diagrams to chunks
4. **Robust parsing:** Use `errors='ignore'` for encoding issues

---

## 🎯 Success Criteria

### Extraction Success
- ✅ **>90% of diagrams extracted** from all 1,055 books
- ✅ **Storage within budget** (< 30 GB)
- ✅ **All images properly named** and accessible

### Linking Success
- ✅ **>85% of diagrams linked** to correct text chunks
- ✅ **Metadata added** to Qdrant chunks
- ✅ **No duplicate diagrams** across books

### Display Success
- ✅ **Diagrams render** correctly in web interface
- ✅ **Relevant to search results** (shown with correct chunks)
- ✅ **Fast loading** (< 2s for page with 5 diagrams)

---

## 📝 Next Steps

1. **Build extraction script** - Process all EPUBs, extract images
2. **Test on 10 books** - Validate extraction logic
3. **Design Qdrant schema update** - Add diagram metadata fields
4. **Implement frontend display** - Show diagrams in search results
5. **Full corpus run** - Extract from all 1,055 books
6. **Validation testing** - Verify diagram-chunk linkage quality

---

**Status:** Audit complete, ready to proceed with extraction pipeline ✅
