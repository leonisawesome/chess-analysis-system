# Chess Knowledge RAG System

**A retrieval-augmented generation system for chess opening knowledge, powered by GPT-5 and 313,057 chunks from 922 chess books (536,243 extracted diagrams) + 1,778 PGN games.**

---

## ⚠️ START HERE: READ [AGENT_START_HERE.md](AGENT_START_HERE.md) FIRST!

**This repo has 3-4 recurring issues across sessions. Start with the guide above.**

**Quick version:**
1. Run `python verify_system_stats.py` → Use those numbers, not docs
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
- ✅ **ITEM-032:** Phase 6.1a debugging - Fixed 4 diagram issues (GPT placeholders, featured diagrams, 0/10 filter, code caching)
- ✅ **ITEM-031:** Added 2 books (Dvoretsky, Markos) + fixed 2 critical bugs
- ✅ **ITEM-030:** Duplicate book cleanup
- ✅ **ITEM-029:** Static EPUB diagram integration (536K diagrams)
- ✅ **ITEM-028:** RRF multi-collection merge (EPUB + PGN)

### Active Priority
🎯 **ITEM-033:** Fixing inline diagram rendering (HTML displaying as plain text, markers not replaced)
- Branch: fix/inline-diagram-rendering
- Partner AI consultation complete (Gemini, ChatGPT, Grok consensus on root cause)
- Backend now enforces a 1:1 match between `featured_diagrams` and `[FEATURED_DIAGRAM_X]` markers; frontend strips any leftovers to prevent literal markers.
- Next focus: browser verification + styling polish once inline replacement is fully validated.

### System Stats (Verified Nov 10, 2025 - 3:30 PM)

**Run `python verify_system_stats.py` to get latest numbers!**

- **Books:** 922 EPUB, 1,778 PGN games
- **Chunks:** 313,057 total (311,266 EPUB + 1,791 PGN)
- **Diagrams:** 536,243 extracted from EPUBs
- **Collections:** chess_production, chess_pgn_repertoire, chess_pgn_test

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

---

## 🔄 Common Tasks

### Verify System State
```bash
python verify_system_stats.py
```

### Add New Books
- Run the canonical analyzer wrapper (processes **everything** in `/Volumes/T7 Shield/books/epub/1new/` and writes to `epub_analysis.db`):
  ```bash
  scripts/analyze_staged_books.sh
  ```
- Review `epub_analysis.db` (e.g. `sqlite3 epub_analysis.db "SELECT filename, score FROM epub_analysis ORDER BY score DESC;"`) and send the score report so the user can approve/reject each title.
- After approval, rename/move the approved files into `/Volumes/T7 Shield/books/epub/` (assistant automates this step)
- Continue with ingestion/diagram extraction per [DEVELOPMENT.md#adding-a-new-book](DEVELOPMENT.md#adding-a-new-book)
- After running `python verify_system_stats.py`, update the hardcoded stats in `templates/index.html` (subtitle + loading message) so the landing page reflects the new counts.

### Remove A Book (EPUB + Metadata)
Use the helper script whenever possible:
```bash
python scripts/remove_books.py <filename>.epub
```
- Deletes the EPUB from `/Volumes/T7 Shield/books/epub/`
- Removes the associated image folder under `/Volumes/T7 Shield/books/images/`
- Clears the row from `epub_analysis.db`
- Issues the Qdrant delete for that `book_name`

`--dry-run` prints the actions without deleting; `--qdrant-url` overrides the default endpoint.

Manual process (only if you can’t run the script):
1. Delete source files  
   `rm "/Volumes/T7 Shield/books/epub/<file>.epub"`  
   `rm -rf "/Volumes/T7 Shield/books/images/<book_id>"`
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
