# Database Schema: Chess Knowledge Bank

The system uses two primary SQLite databases to store processed chess content.

## 1. `pgn_analysis.db`
Managed by `pgn_quality_analyzer.py`. Focuses on game deduplication and quality scoring.

### Table: `game_hashes`
Stores unique content fingerprints and links them to canonical Game IDs (UCI moves).

| Column | Type | Description |
| :--- | :--- | :--- |
| `fingerprint` | TEXT (PK) | SHA-256 of normalized PGN text. Unique identifier for the educational content. |
| `game_id` | TEXT | MD5 of UCI moves. Groups different versions of the same game. |
| `evs` | REAL | Educational Value Score (0-100). |
| `source_file` | TEXT | Filename where this version was found. |
| `source_index` | INTEGER | Index within the source file. |

---

## 2. `chess_text.db`
Managed by `epub_ingester.py`. Structured as a position-aware knowledge graph.

### Table: `books`
Metadata for processed EPUBs.

| Column | Type | Description |
| :--- | :--- | :--- |
| `book_id` | INTEGER (PK) | Internal ID. |
| `title` | TEXT | Book title. |
| `author` | TEXT | Author name. |
| `quality_score` | REAL | Average quality score (0-100) across all chunks. |
| `processed_date` | TEXT | ISO timestamp of ingestion. |

### Table: `chunks`
Semantic segments of book text, linked to board positions.

| Column | Type | Description |
| :--- | :--- | :--- |
| `chunk_id` | INTEGER (PK) | Internal ID. |
| `book_id` | INTEGER | FK to `books`. |
| `text_content` | TEXT | The raw educational prose. |
| `fen` | TEXT | The FEN (Forsyth-Edwards Notation) state at the *start* of this chunk. |
| `quality_score` | REAL | Instructionality score based on vocabulary density. |
| `is_instructional` | BOOLEAN | Flag for RAG prioritization (> 50 score). |

### Table: `diagrams`
Visual anchors found within the text.

| Column | Type | Description |
| :--- | :--- | :--- |
| `diagram_id` | INTEGER (PK) | Internal ID. |
| `chunk_id` | INTEGER | FK to `chunks`. |
| `image_path` | TEXT | Path/Source of the diagram image. |
| `fen` | TEXT | The *exact* FEN for this diagram. |
| `is_ocr_based` | BOOLEAN | True if the FEN was derived via OCR fallback (orphaned diagram). |

---

## 3. Full-Text Search (FTS5)
Both databases utilize FTS5 virtual tables (`chunks_fts`) to enable fast semantic and keyword search across the `text_content` and `content` fields.
