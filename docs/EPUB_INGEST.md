# EPUB Ingestion (Books) — Operational Checklist

This repo’s “book” pipeline is **EPUB-only**. PDFs are not used/ingested here.

## 1) Stage

- Copy new EPUBs into `/Volumes/T7 Shield/rag/books/epub/1new/`.
- Do **not** delete macOS `._*` files; scripts filter them out.

## 2) Dedupe gate (before scoring)

- Confirm staged titles are not duplicates of existing corpus books (same title/edition under a different filename).
- If a staged EPUB is a duplicate you want to remove, use `python scripts/remove_books.py "<filename>.epub"` (never manually delete `. _*`).

## 3) Score staged EPUBs (SQLite)

- Run the analyzer wrapper:
  - `scripts/analyze_staged_books.sh`
- Results are written to `epub_analysis.db` (table: `epub_analysis`), with `score`, `tier`, `word_count`, and any `error`.

## 4) Approve / reject

- Review scores (example):
  - `sqlite3 epub_analysis.db "SELECT filename, score, tier, word_count, error FROM epub_analysis WHERE full_path LIKE '/Volumes/T7 Shield/rag/books/epub/1new/%' ORDER BY score DESC;"`
- Only approved titles continue.

## 5) Move approved EPUBs into corpus + fix paths

- Move approved files to `/Volumes/T7 Shield/rag/books/epub/`.
- Ensure `epub_analysis.full_path` is updated to the new corpus path (not `/1new/`), or ingestion can fail.

## 6) Ingest into Qdrant

- Prereqs: Qdrant running + `OPENAI_API_KEY` set.
- Run: `python add_books_to_corpus.py "Book.epub" ...`

## 7) Extract diagrams + update metadata

- Extract diagrams for new EPUBs and append to `diagram_metadata_full.json` (see `DEVELOPMENT.md` for the incremental snippet).

## 8) Verify + update UI counts

- Run: `python verify_system_stats.py`
- Update homepage counts in `templates/index.html`.

