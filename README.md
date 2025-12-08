# Chess Knowledge RAG System

**A retrieval-augmented generation system for chess opening knowledge, powered by GPT-5 and ~600k chunks from 988 chess books (559,406 extracted diagrams). Includes 233,211 PGN game chunks from 64,251 games (run `python verify_system_stats.py` for latest counts).**

---

## ⚠️ START HERE: READ [AGENT_START_HERE.md](AGENT_START_HERE.md) FIRST!

**This repo has 3-4 recurring issues across sessions. Start with the guide above.**

**Quick version:**
1. Run `python verify_system_stats.py` whenever you need fresh counts for docs or after touching data (not required for every coding session)
2. NEVER delete macOS `._*` files → Filter them out: `if not f.name.startswith('._')`
3. Test before claiming "fixed" → Previous assistants didn't actually fix things

---

## 📚 Documentation

- **[AGENT_START_HERE.md](AGENT_START_HERE.md)** - Read this first every session
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design & data flow
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Common tasks & workflow
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Issues & solutions
- **[CHANGELOG.md](CHANGELOG.md)** - Completed items history
- **[BACKLOG.md](BACKLOG.md)** - Planned work & items
- **[SESSION_NOTES.md](SESSION_NOTES.md)** - Daily session logs

---

## 🎯 Current Status (November 10, 2025)

### Recently Completed
- ✅ **ITEM-033:** Inline diagram rendering fix (marker/diagram sync + frontend cleanup)
- ✅ **ITEM-032:** Phase 6.1a debugging - Fixed 4 diagram issues (GPT placeholders, featured diagrams, 0/10 filter, code caching)
- ✅ **ITEM-031:** Added 2 books (Dvoretsky, Markos) + fixed 2 critical bugs
- ✅ **ITEM-030:** Duplicate book cleanup
- ✅ **ITEM-029:** Static EPUB diagram integration (536K diagrams)
- ✅ **ITEM-028:** RRF multi-collection merge (EPUB + PGN)

### Active Priority
🎯 **PGN Diagram QA Tooling:** Build/validate tooling that scores diagrams extracted from PGN chunks. The initial prototype highlighted issues when pointed at a single massive PGN (tens of thousands of games), so we’re temporarily blocked on a cleaned/split corpus. Once that file is ready, rerun the tool, confirm diagram quality, and wire the verified output into the synthesis pipeline.

### Diagram Updates
- ✅ Static EPUB coverage remains primary (542K+ diagrams tracked in `diagram_metadata_full.json`)
- ✅ **Dynamic fallback re-enabled (Nov 20, 2025):** When a top RAG result doesn’t have a matching static asset, we now extract the FEN from the chunk and render an SVG on the fly (`/dynamic_diagrams/<id>`). Toggle via `ENABLE_DYNAMIC_DIAGRAMS` (default `true`); cache stored under `static/dynamic_diagrams/`.

### PGN Refresh (November 13, 2025) ✅ COMPLETE
- ✅ `chess_publishing_2021_master.pgn` analyzed: **64,251 games → 234,251 chunks** written to `data/chess_publishing_2021_chunks.json` (598 MB).
- ⚠️ 2 malformed games were skipped (IDs #8944 and #9284); see `pgn_quality_analyzer` logs for exact headers/snippets.
- ✅ **Ingestion complete:** 233,211 chunks embedded and uploaded to `chess_pgn_repertoire` collection.
- 💰 **Cost:** $3.21 (160.6M tokens) | **Time:** 162.8 minutes (2.7 hours)
- 🔌 Ready for production: Set `ENABLE_PGN_COLLECTION = True` in `app.py` to enable PGN queries.

### System Stats (Verified Dec 4, 2025)

**Run `python verify_system_stats.py` to get latest numbers!**

- **Books:** 988 EPUB
- **PGN Games:** 64,251 games (from Chess Publishing 2021 master corpus)
- **Chunks:** 600,205 total production (366,994 EPUB + 233,211 PGN)
- **Diagrams:** 559,406 extracted from EPUBs
- **Collections:** chess_production (360,660 points), chess_pgn_repertoire (233,211 points)

### Architecture
- **Model:** GPT-5 (gpt-chatgpt-4o-latest-20250514)
- **Vector DB:** Qdrant (Docker, port 6333)
- **Server:** Flask (port 5001)
- **Embedding:** text-embedding-3-small (1536 dims)
- **Modules:** 9 specialized modules (262-line app.py)

---

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone git@github.com:leonisawesome/chess-analysis-system.git
cd chess-analysis-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start Qdrant
```bash
open -a Docker  # Start Docker Desktop
docker-compose up -d
```

### 3. Start Flask Server
```bash
export OPENAI_API_KEY='sk-proj-YOUR_KEY_HERE'
python app.py
```

### 4. Open UI
```bash
open http://localhost:5001
```

### Answer Length Control
- Use the **Answer Length** slider (Concise / Balanced / In-Depth) to tell the synthesis pipeline how much depth you want.
- Concise → 1 paragraph per section (~250 words) for quick spot checks.
- Balanced (default) → 3‑4 sections mixing strategy prose with one concrete PGN line per section.
- In-Depth → long-form explainer with multiple variations and extra diagrams; expect ~700+ words.

---

## 🔄 Common Tasks

### Verify System State
```bash
python verify_system_stats.py
```

### Dynamic Diagrams (FEN Rendering Fallback)
- Default-on fallback automatically renders SVG boards for results without static EPUB diagrams.
- Configure via environment variables:
  ```bash
  export ENABLE_DYNAMIC_DIAGRAMS=true        # disable with false/0/no/off
  export DYNAMIC_DIAGRAMS_TOTAL=6            # max diagrams created per response
  export DYNAMIC_DIAGRAMS_PER_RESULT=1       # max per individual source
  ```
- Generated assets live under `static/dynamic_diagrams/` with metadata in `static/dynamic_diagrams/manifest.json`.

### Add New Books
- Run the canonical analyzer wrapper (processes **everything** in `/Volumes/T7 Shield/rag/books/epub/1new/` and writes to `epub_analysis.db`):
  ```bash
  scripts/analyze_staged_books.sh
  ```
- Review `epub_analysis.db` (e.g. `sqlite3 epub_analysis.db "SELECT filename, score FROM epub_analysis ORDER BY score DESC;"`) and send the score report so the user can approve/reject each title.
- After approval, rename/move the approved files into `/Volumes/T7 Shield/rag/books/epub/` (assistant automates this step)
- Continue with ingestion/diagram extraction per [DEVELOPMENT.md#adding-a-new-book](DEVELOPMENT.md#adding-a-new-book)
- After running `python verify_system_stats.py`, update the hardcoded stats in `templates/index.html` (subtitle + loading message) so the landing page reflects the new counts.

### Add PGN Games
1. Score staged PGNs before anything touches Qdrant:
   ```bash
   python pgn_quality_analyzer.py "/path/to/pgn_dir" --db pgn_analysis.db --json pgn_scores.json
   ```
   This writes one summary row per PGN file (avg EVS, annotation density, etc.) into `pgn_analysis.db`.
2. Share the score report with the user for approval (same workflow as EPUBs). Only approved PGNs advance.
3. Convert approved PGNs into chunks and ingest:
   ```bash
   python analyze_pgn_games.py /Volumes/T7\ Shield/pgn/approved --output approved_pgn_chunks.json
   python add_pgn_to_corpus.py approved_pgn_chunks.json --collection chess_pgn
   ```
   Keep the EVS score in each chunk’s metadata so we can query/delete low-quality games later.

### Combine Raw PGN Drops
- Use `scripts/combine_pgn_corpus.py` to deduplicate massive PGN folders before analysis/ingest. This tool:
  - Walks the tree recursively and filters macOS ghost files (`._*`)
  - Eliminates duplicates via MD5 hash
  - Skips non-English/Spanish annotations **by default** (logged + copied to a `--foreign-dir`)
  - Copies skipped files (encoding/permission issues) into `--skipped-dir` for manual fixes
  - Emits CSV reports for duplicates, skipped files, and foreign-language files
- Example (Modern Chess corpus):
  ```bash
  pip install langdetect  # one-time dependency
  python scripts/combine_pgn_corpus.py \
      --root "/Volumes/chess/1Modern Chess" \
      --output "/Volumes/T7 Shield/rag/databases/pgn/1new/modern.pgn" \
      --duplicates "/Volumes/T7 Shield/rag/databases/pgn/1new/modern_duplicates.csv" \
      --skipped "/Volumes/T7 Shield/rag/databases/pgn/1new/modern_skipped.csv" \
      --foreign "/Volumes/T7 Shield/rag/databases/pgn/1new/modern_foreign.csv" \
      --skipped-dir "/Volumes/T7 Shield/rag/databases/pgn/1new/skipped_pgns" \
      --foreign-dir "/Volumes/T7 Shield/rag/databases/pgn/1new/foreign_pgns" \
      --log-every 200
  ```
  Add `--keep-foreign` if you intentionally want to keep non-English PGNs in the combined output.

### Filter PGNs by EVS (High/Medium Buckets)
- Use `scripts/filter_pgn_by_evs.py` to keep only medium/high-quality games (EVS ≥ 45 by default).
- Two modes:
  1. `--mode single` (default): write all EVS ≥ medium threshold to a single file.
  2. `--mode split`: send EVS ≥ high threshold to one file and medium-range EVS to another.
- Example (split mode on a 10 GB PGN dump):
  ```bash
python scripts/filter_pgn_by_evs.py \
    --input "/Volumes/T7 Shield/Deets/3unknown/master_unknown.pgn" \
    --mode split \
    --medium-output "/Volumes/T7 Shield/rag/databases/pgn/1new/purged_mediums.pgn" \
    --high-output "/Volumes/T7 Shield/rag/databases/pgn/1new/purged_highs.pgn" \
      --medium-threshold 45 --high-threshold 70 \
      --log-every 5000
  ```
  This streams the PGN game-by-game, reuses the analyzer’s EVS scoring, and discards low-value games.

### Pick the Top X% of a PGN
- Use `scripts/sample_top_evs.py` to extract, for example, the strongest 10% of `purged_mediums.pgn`:
  ```bash
  python scripts/sample_top_evs.py \
      --input "/Volumes/T7 Shield/rag/databases/pgn/1new/purged_mediums.pgn" \
      --output "/Volumes/T7 Shield/rag/databases/pgn/1new/purged_mediums_top_10.pgn" \
      --percent 10
  ```
- This pass reuses the EVS scorer, ranks every game by EVS, and writes only the top N-percent subset.

### Split an Entire Directory into Medium/High Buckets
- Use `scripts/filter_directory_by_evs.py` to walk a folder (recursively) and stream all medium/high EVS games into two master PGNs:
  ```bash
  python scripts/filter_directory_by_evs.py \
      --root "/Users/leon/Downloads/3unknown" \
      --medium-output "/Volumes/T7 Shield/rag/databases/pgn/1new/medium_value.pgn" \
      --high-output "/Volumes/T7 Shield/rag/databases/pgn/1new/high_value.pgn" \
      --medium-threshold 45 --high-threshold 70 \
      --log-every 2000
  ```
- This is ideal for “unknown” dumps when you want to keep everything that scores medium/high without merging files manually.

### PGN Diagram Roadmap
1. **Metadata-first ingestion:** `analyze_pgn_games.py` preserves every PGN header (Event/Site/Date/Openings/ECO) plus course hierarchy (`course_name`, `chapter`, `section`) and annotation density. These fields act as the lookup keys for openings (e.g., Italian Game) and structural themes (IQP, prophylaxis).
2. **Candidate selection:** During chunking we also persist per-game stats (EVS, comment density, has_variations). A follow-up job will parse each chunk, flag moves with high annotation density, comment keywords (e.g., “prophylaxis”, “IQP”), or large eval swings to identify diagram-worthy plies.
3. **Concept tagging:** Opening questions map via ECO/opening headers; concept questions map via a lightweight classifier that scans comments + move text for canonical lexicon entries (pins, IQP, blockade, prophylaxis, etc.) and links them to existing `canonical_positions` IDs when possible.
4. **Diagram generation:** For each tagged move we snapshot the FEN, feed it to `diagram_generator.py`, and store PNG/SVG plus metadata `{game_id, source_file, move_number, concept_tags}` in a new `pgn_diagrams` catalog. Each record also references the originating chunk so deletions stay clean.
5. **Serving flow:** When answering queries the backend will look up both EPUB and PGN diagram pools. Opening queries match via `opening`/`eco`; concept queries match via shared lexicon tags. Featured diagrams then mix EPUB illustrations (strategic art) with PGN-derived boards (concrete move sequences) using the same `[FEATURED_DIAGRAM_X]` marker pipeline.

### Generate PGN Diagrams (Static SVGs)
`scripts/generate_pgn_diagrams.py` turns annotated PGN files into SVG boards + metadata that the Flask app can serve alongside EPUB artwork.

```bash
python scripts/generate_pgn_diagrams.py \
    --input "/Volumes/T7 Shield/rag/databases/pgn/1new/high_value.pgn" \
    --image-dir "/Volumes/T7 Shield/rag/databases/pgn/images" \
    --metadata-output "diagram_metadata_pgn.json" \
    --limit-per-game 4
```

- Streams giant PGNs safely, reuses the EVS scoring from `pgn_quality_analyzer.py`, inspects comments/NAGs for instructional keywords (prophylaxis, IQP, exchange sac, etc.), and snapshots the FEN when a tag fires or the comment is detailed enough.
- SVGs live under `/Volumes/T7 Shield/rag/databases/pgn/images/pgn_<hash>/pgn_<hash>_<game>_<ply>.svg`; metadata entries carry `source_type="pgn"`, the originating PGN path, EVS bucket, opening/ECO tags, and a caption built from the comment.
- Drop the metadata JSON into the repo root (or point `PGN_DIAGRAM_METADATA=/absolute/path/to/file.json`) and `app.py` will automatically load it after the EPUB catalog via `diagram_index.load(..., allow_small_source_types={'pgn'})`.
- `diagram_service` normalizes both catalogs into the same in-memory index, so `/query_merged` can now mix EPUB PNG/JPGs and PGN SVGs inside the featured diagram carousel.
- Set `--shard-size` (default 25k) to emit incremental metadata shards under `<metadata-output>_shards/diagram_metadata_pgn_shard_XXXX.json`. This keeps partial progress if a run stalls; once the full script finishes it still writes the aggregated `diagram_metadata_pgn.json`.
- Override shard location with `--shard-dir /path/to/shards` if you prefer to store them on a faster disk. Set `--shard-size 0` to disable shard output entirely.
- **Staging convention:** Place any new PGN you want processed (including the in-progress large corpus) under `/Volumes/T7 Shield/rag/databases/pgn/1new/`. That directory is where we run EVS scoring, chunking, and the PGN diagram generator. Keeping everything there makes it easy to hand files off to Claude Code for long-running ingestion jobs.
- **Language cleanup:** Run `scripts/clean_pgn_language.py` to strip duplicated German prose from ChessBase Magazine annotations before handing PGNs to the pipeline.

> **Operational workflow:** Codex handles short, code-focused tasks and documentation updates. Whenever a command will run for minutes/hours or needs heartbeat logging (e.g., `scripts/generate_pgn_diagrams.py`, large `analyze_pgn_games.py` jobs, or `add_pgn_to_corpus.py` ingestion), launch it via Claude Code so you get live status updates. Document the results back in `SESSION_NOTES.md` once the job finishes.

### Daily PGN Merge
- Use `scripts/merge_pgn_sources.py` to crawl either `/Users/leon/Downloads/ZListo`, `/Volumes/chess/zTemp`, or any custom directory, deduplicate by MD5, and emit a dated master PGN in `/Volumes/T7 Shield/rag/databases/pgn/1new`.
  ```bash
  python scripts/merge_pgn_sources.py
  ```
- The script prompts for the source directory (enter `3` to type any absolute path), ignores `._*` ghost files, strips trailing whitespace, and writes to `<MM-DD-YY>_new.pgn` (e.g., `11-15-25_new.pgn`). Run it whenever you stage new PGNs for Claude Code to ingest.

### Remove German comments from PGNs
- ChessBase Magazine games often repeat every annotation in German. Clean those duplicates before chunking so the RAG output stays English-only:
  ```bash
  python scripts/clean_pgn_language.py \
      --source "/path/to/chessbase_raw.pgn" \
      --output "/path/to/chessbase_english.pgn"
  ```
- The script scans every `{ ... }` comment, keeps English sentences (plus ChessBase metadata tokens), and drops the German translation + `[%tqu ... "De", ...]` payloads. Stats are printed after the run so you know how many comments and sentences were modified.
- Long jobs log progress every 100 games so you can track status while Claude runs the cleaner on massive PGNs.

### Remove A Book (EPUB + Metadata)
Use the helper script whenever possible:
```bash
python scripts/remove_books.py <filename>.epub
```
- Deletes the EPUB from `/Volumes/T7 Shield/rag/books/epub/`
- Removes the associated image folder under `/Volumes/T7 Shield/rag/books/images/`
- Clears the row from `epub_analysis.db`
- Issues the Qdrant delete for that `book_name`

`--dry-run` prints the actions without deleting; `--qdrant-url` overrides the default endpoint.

Manual process (only if you can’t run the script):
1. Delete source files  
   `rm "/Volumes/T7 Shield/rag/books/epub/<file>.epub"`  
   `rm -rf "/Volumes/T7 Shield/rag/books/images/<book_id>"`
2. Purge analyzer records  
   `sqlite3 epub_analysis.db "DELETE FROM epub_analysis WHERE filename = '<file>.epub';"`
3. Delete Qdrant chunks (see script snippet above)
4. Run `python verify_all_deletions.py` to confirm the cleanup

### Fix a Bug
See [DEVELOPMENT.md#fixing-a-bug](DEVELOPMENT.md#fixing-a-bug)

### Troubleshoot Issues
See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 📁 Data Storage

```
/Volumes/T7 Shield/books/
├── epub/                    # Production-ready EPUB/MOBI books
│   ├── 1new/                # Staging area (pre-analysis files live here)
│   ├── author_year_title_publisher.epub
│   └── ...
│
└── images/                  # 536,243 diagrams
    ├── book_{hash}/         # Organized by book ID
    │   ├── book_{hash}_0000.png
    │   └── ...
    └── ...
```

**Note:** Count excludes macOS `._*` metadata files (ignored, not deleted).

---

## 🔧 System Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for full details.

### Query Flow
```
User Query → Intent Classification → Parallel Search (EPUB + PGN)
  → RRF Merge → GPT-5 Reranking → 3-Stage Synthesis → Response + Diagrams
```

### 9 Specialized Modules
- `rag_engine.py` - Vector search (105 lines)
- `reranker.py` - GPT-5 reranking (88 lines)
- `synthesis_pipeline.py` - 3-stage synthesis (179 lines)
- `chess_positions.py` - FEN/PGN parsing (122 lines)
- `diagram_generator.py` - SVG generation (145 lines)
- `diagram_service.py` - Diagram index (242 lines)
- `content_formatter.py` - Markdown formatting (89 lines)
- `validation.py` - Quality checks (67 lines)
- `query_router.py` - Intent classification (71 lines)
- `rrf_merger.py` - RRF merge (92 lines)

**Result:** app.py reduced from 1,474 → 262 lines (-82.2%)

---

## 🧪 Testing

### Verify Stats
```bash
python verify_system_stats.py
```

### Test Query
```bash
curl -X POST http://localhost:5001/query_merged \
  -H "Content-Type: application/json" \
  -d '{"query": "Najdorf Sicilian", "top_k": 5}'
```

### Test Diagram Endpoint
```bash
curl -I http://localhost:5001/diagrams/book_00448974a7ea_0000
```

---

## 📊 Performance

- **Query latency:** 20-30 seconds total
  - Embedding: 5-6s
  - Search: 1-2s
  - Reranking: 15-20s
- **Success rate:** 100% (Phase 1 & 2 validation)
- **Diagram loading:** Lazy-loaded on demand

---

## 🐛 Known Issues

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#known-bugs-november-10-2025) for current bugs.

**Recently Fixed (Nov 10, 2025):**
- ✅ add_books_to_corpus.py - Wrong hardcoded path
- ✅ batch_process_epubs.py - Summary crash on None values

**Design Limitations:**
- ❌ extract_epub_diagrams.py - No specific file support (only full directory)

---

## 📦 Future Work

- **Phase 5.2:** Resume validation after PGN corpus expansion to 1M games
- **Phase 6.2:** Interactive PGN diagrams with chessboard.js (playable boards)
- **Phase 7:** Conversational interface (multi-turn like ChatGPT)

See [BACKLOG.md](BACKLOG.md) for detailed planning.

---

## 🤝 Contributing

### Before Making Changes
1. Read [AGENT_START_HERE.md](AGENT_START_HERE.md)
2. Run `python verify_system_stats.py`
3. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for known issues

### Development Workflow
See [DEVELOPMENT.md](DEVELOPMENT.md) for full workflow.

### Commit Format
```
Type: Short description (50 chars)

Longer explanation:
- What changed
- Why it changed
- Side effects

Co-Authored-By: Assistant <noreply@example.com>
```

---

## 📖 References

### Key Concepts
- **RAG:** Retrieval-Augmented Generation
- **RRF:** Reciprocal Rank Fusion (k=60)
- **EVS:** Educational Value Score (book quality metric)
- **ITEM-008:** Sicilian contamination bug (fixed Oct 2025)
- **ITEM-011:** Monolithic refactoring (completed Oct 2025)

### External Docs
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [python-chess](https://python-chess.readthedocs.io/)

---

## 📞 Support

### Getting Help
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Run `python verify_system_stats.py`
3. Check [DEVELOPMENT.md](DEVELOPMENT.md) for tasks
4. Review [SESSION_NOTES.md](SESSION_NOTES.md) for recent changes

### Filing Issues
**For assistant sessions:**
- Always verify stats with `verify_system_stats.py`
- Never trust documentation - check actual state
- Never delete macOS `._*` files
- Test before claiming "fixed"

---

## 📝 License & Credits

**Author:** Leon (leonisawesome)
**AI Partner:** Multi-agent panel (Gemini, Grok, ChatGPT)
**Repository:** github.com/leonisawesome/chess-analysis-system

---

**Last Updated:** November 10, 2025
**Current Branch:** phase-5.1-ui-integration
**Auth:** GitHub SSH (no token expiration)

---

**🚨 Remember: Run `python verify_system_stats.py` before updating any stats!**
