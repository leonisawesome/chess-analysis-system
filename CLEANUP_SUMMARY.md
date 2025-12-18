# Collection Cleanup Summary

## Current Stats (as of 2025-11-09)
- **EPUB files:** 920
- **Image directories:** 938 (18 orphaned from deleted books)
- **Qdrant chunks:** 309,867

## Major Changes This Session

### 1. Bug Fix: Duplicate Image Extraction
**File:** `extract_epub_diagrams.py`

**Issue:** When the same diagram image was referenced multiple times across different HTML documents (navigation, TOC, multiple chapters), the extractor would save it multiple times.

**Example:** Fischer 2008 book had 258 unique images but extracted 13,032 total (50x duplication)

**Fix:** Added `extracted_images` set to track processed images and skip duplicates (lines 171-222)

### 2. Books Deleted

#### Beginner Books (20 total)
- 14 books deleted in first batch
- 5 books deleted in second batch
- 1 memoir book (lubomir_2022)
- **Total chunks removed:** 2,602

#### Duplicate Books (3 total)
- alexander_1908 (duplicate of alekhine_2013) - 713 chunks, 623 images
- fischer_2008 (duplicate of bobby_2009, corrupted extraction) - 298 chunks, 13,032 corrupted images
- cyrus_0000 (duplicate of lakdawala_2015) - 397 chunks, 420 images
- **Total chunks removed:** 1,408

#### Timeout Cleanup
Fixed sloppy Qdrant cleanup from previous timed-out deletions:
- pavlovic_2017: 239 chunks
- moskalenko (no_dg version): 511 chunks
- **Total chunks removed:** 750

### 3. Total Cleanup This Session
- **Books deleted:** 23
- **Qdrant chunks removed:** 4,760
- **Corrupted images removed:** 13,032

## Remaining Considerations

### Puzzle Books
Currently have 44 puzzle/exercise books flagged. These typically:
- Contain only positions without instructional text
- Don't help with RAG queries about openings or tactics explanations
- Take up space but provide minimal value for semantic search

**Recommendation:** Remove puzzle books unless you want positional pattern recognition queries.

### Other Non-RAG Categories Still Present
- Autobiographical/game collections: 9 books
- Biography: 35 books
- Historical: 31 books
- General interest: 24 books
- Low diagram books: 2 books

Total flagged for potential removal: 145 books

## Scripts Created
All cleanup scripts use the 3-location deletion pattern:
1. Delete EPUB file
2. Delete image directory
3. Delete Qdrant chunks with verification

Key scripts:
- `cleanup_qdrant_timeouts.py` - Fixed timed-out deletions
- `delete_beginner_books.py` - Batch delete beginner books
- `delete_*_duplicate.py` - Individual duplicate removals
- `scan_non_rag_worthy_books_clean.py` - Generate clean reports
