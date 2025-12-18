# Development Guide

## Quick Start

```bash
cd /Users/leon/Downloads/python/chess-analysis-system
source .venv/bin/activate
python verify_system_stats.py  # Always run first!
```

## Mandatory Logging for New Scripts

Silent tooling keeps biting us. Every script, CLI, or long-running job you add **must** log:

- A startup banner (inputs, destination paths, key flags)
- Periodic heartbeat/progress messages (e.g., “Processed 1,000/10,000 PGNs”)
- A final summary with totals, dedupe counts, and output locations
- Clear error messages if something aborts

If you’re touching an existing quiet script, add this logging as part of the fix before merging. The only exception is truly trivial one-off utilities that finish in under a second—everything else needs human-readable output so we know what happened when a job stalls on Claude Code or a remote terminal.

## Environment & Dependencies

- **Python runtime:** All scripts target Python 3.9 (see `requirements.txt` comment and tested virtualenv). `setup.py` advertises `python_requires=">=3.8"`, but the production stack, embeddings, and spaCy model have only been validated under 3.9.x. Keep `pyenv` handy if you need to install/compile that version, but updating Homebrew’s `python@3.11`/`python@3.13` formulas will not affect this repo unless you explicitly switch the virtualenv interpreter.
- **Python packages:** `pip install -r requirements.txt` provides the minimal Flask/Qdrant/OpenAI stack (flask 3.0, qdrant-client 1.15.1, python-chess 1.999, spaCy 3.7, openai≥1.50, httpx≥0.27, requests 2.31). `setup.py` adds heavy NLP extras (`sentence-transformers`, `torch`, `transformers`, etc.) for the CLI package entry point. Make sure the virtualenv is active before upgrading brew-level tools so that `pip` continues targeting `.venv`.
- **Services:** `docker`/`docker-compose` are required because Qdrant runs via `docker compose up -d` (see `docker-compose.yml` and `assistant_notes.md`). Upgrading the Homebrew `docker` and `docker-completion` packages is safe and recommended so long as Docker Desktop keeps running.
- **Databases:** SQLite ships with Python and powers `epub_analysis.db`, `chessable_analysis.db`, etc. The Homebrew `sqlite` formula only provides command-line utilities; updating it won’t touch Python’s built-in module. `postgresql@16`, `tesseract`, `poppler`, and `libnghttp2` are installed globally but unused by this project.
- **System crypto/certs:** `ca-certificates`, `gettext`, `harfbuzz`, `icu4c@77`, and `nspr` are transitive dependencies of other tools (curl, git, GUI apps). Refreshing them is safe and does not impact the Python virtualenv.
- **Apps:** GUI casks like `claude-code` are unrelated to this repo.

In short, none of the currently outdated Homebrew packages block or interfere with `chess-analysis-system`. Upgrading them keeps the OS toolchain patched without changing the Python environment this project actually runs on.

---

## Common Tasks

### Adding a New Book

See [AGENT_START_HERE.md](AGENT_START_HERE.md#adding-books) for full process.

**Quick version:**
```bash
# 1. Analyze everything the user staged (writes scores + tiers into epub_analysis.db)
scripts/analyze_staged_books.sh
# → Share the SQLite report so the user can accept/reject each book

# 2. After approval, rename + move approved files into the main corpus (assistant automates this step)
- Run a fast drift check before moving anything:
  ```bash
  python - <<'PY'
  import sqlite3
  from pathlib import Path
  EPUB_DIR = Path('/Volumes/T7 Shield/rag/books/epub')
  cur = sqlite3.connect('epub_analysis.db').execute('SELECT filename FROM epub_analysis')
  db_names = {row[0] for row in cur}
  fs_names = {p.name for p in EPUB_DIR.glob('*.epub')}
  missing = sorted(db_names - fs_names)
  print(len(missing), "missing entries")
  if missing:
      print("\n".join(missing))
  PY
  ```
  Anything listed should be removed via `scripts/remove_books.py` (which now tolerates macOS `._*` files) before continuing so SQLite/Qdrant stay in sync.

# 3. Add to Qdrant
export OPENAI_API_KEY='sk-proj-...'
export QDRANT_MODE=docker
python add_books_to_corpus.py book.epub

# 4. Extract diagrams (append metadata for the new book; only rebuild the full file if you reprocessed the entire corpus)
python - <<'PY'
from pathlib import Path, defaultdict
from dataclasses import asdict
import json
from extract_epub_diagrams import DiagramExtractor
BOOKS = [
    "New Book 1.epub",
]
EPUB_DIR = Path("/Volumes/T7 Shield/rag/books/epub")
IMAGES_DIR = Path("/Volumes/T7 Shield/rag/books/images")
METADATA = Path("diagram_metadata_full.json")
metadata = json.loads(METADATA.read_text())
existing_ids = {entry["book_id"] for entry in metadata["stats"]["books"]}
for name in BOOKS:
    extractor = DiagramExtractor(EPUB_DIR / name, IMAGES_DIR)
    if extractor.book_id in existing_ids:
        continue
    metadata["diagrams"].extend(asdict(d) for d in extractor.extract())
    existing_ids.add(extractor.book_id)
stats = metadata["stats"]
stats["books"] = []
stats["total_diagrams"] = len(metadata["diagrams"])
METADATA.write_text(json.dumps(metadata, indent=2))
PY

The snippet above mirrors the incremental extraction flow we used this session: only the new EPUBs are processed, and `diagram_metadata_full.json` is rewritten afterward so the stats stay correct without running the 950‑book batch job.

# 5. Verify stats and update hardcoded homepage counts
python verify_system_stats.py

### Launching ingestion (Claude Code instructions)

Claude handles the long-running chunking/embedding jobs. Provide the approved filenames and have Claude run:
```bash
cd /Users/leon/Downloads/python/chess-analysis-system
source .venv/bin/activate
export OPENAI_API_KEY='sk-proj-REDACTED'
docker compose up -d  # make sure Qdrant is live
python add_books_to_corpus.py \
  "Book A.epub" \
  "Book B.epub"
```
Claude should record the token/chunk counts and update `SESSION_NOTES.md` once the ingest finishes. If the API key or Docker isn’t available in Claude’s shell, fall back to the user terminal instead.
```

### Troubleshooting Missing Diagrams

When a query returns prose without inline boards, capture evidence before tweaking the code:

1. Dump the ranked static diagrams for the problematic prompts:
   ```bash
   ./scripts/dump_diagram_candidates.py "Italian Game plans" "Italian Game tactics" \
     --output diagnostics/diagram_debug_italian.json \
     --markdown diagnostics/diagram_samples_italian.md
   ```
   The script loads `diagram_metadata_full.json`, re-runs the ranking heuristic, and records the exact files, captions, and dimensions per book.

2. Inspect `diagnostics/diagram_debug_*.json` (full metadata) or the Markdown table for a quick glance at sizes/context. If a diagram is missing, the `file_path` column will tell you whether the asset itself is gone or the filter removed it.

3. Spot-check a few image files via `sips -g pixelWidth -g pixelHeight <file>` (or Preview) to confirm whether we filtered out real boards or the extraction produced logos/photos.

Document any findings in `assistant_notes.md` (or the relevant ITEM doc) before making additional code changes so we keep a paper trail on what was discovered.

> **Note:** `diagram_service` now lazily reads image dimensions for diagrams missing width/height metadata (uses Pillow). If you see logs complaining about missing dimensions, install the dependency with `pip install pillow` inside the project virtualenv.

# Adding PGN Games

```bash
# 1. Score staged PGNs (writes per-file summaries into pgn_analysis.db)
python pgn_quality_analyzer.py "/Volumes/T7 Shield/rag/databases/pgn/1new" --db pgn_analysis.db --json pgn_scores.json

# 2. Share the EVS report for approval (only approved files move on)

# 3. Chunk + ingest the approved PGNs
python analyze_pgn_games.py "/Volumes/T7 Shield/rag/databases/pgn/approved" --output approved_pgn_chunks.json
python add_pgn_to_corpus.py approved_pgn_chunks.json --collection chess_pgn
```

Keep the EVS score in each chunk’s metadata so we can trace/remove noisy games later.

### Fixing a Bug

```bash
# 1. Locate the bug
grep -rn "bug_keyword" *.py

# 2. Read the code
cat -n filename.py | sed -n 'start,end p'

# 3. Make the fix
# Edit file with your preferred editor

# 4. TEST IT
python filename.py  # Run the script
python test_script.py  # If tests exist

# 5. Update docs
# Edit README.md, SESSION_NOTES.md

# 6. Commit
git add filename.py README.md SESSION_NOTES.md
git commit -m "Fix: description of what you fixed"
git push origin branch-name
```

### Updating Documentation Stats

```bash
# 1. Get actual stats
python verify_system_stats.py

# 2. Update README header (line 3)
# Change: "313,057 chunks from 922 books..."

# 3. Update SESSION_NOTES
# Append new section at end

# 4. Commit
git add README.md SESSION_NOTES.md
git commit -m "Docs: Update stats to current state"
```

###Adding a New Module

```python
# 1. Create module file
# new_module.py

def new_function():
    """Docstring explaining what it does."""
    pass

# 2. Import in app.py
from new_module import new_function

# 3. Use it
@app.route('/endpoint')
def endpoint():
    result = new_function()
    return jsonify(result)

# 4. Test it
curl http://localhost:5001/endpoint

# 5. Document it
# Add to ARCHITECTURE.md or relevant doc
```

---

## Development Workflow

### Before Starting Work

1. **Pull latest:**
   ```bash
   git pull origin branch-name
   ```

2. **Verify state:**
   ```bash
   python verify_system_stats.py
   docker ps | grep qdrant
   ```

3. **Create branch (if new feature):**
   ```bash
   git checkout -b feature/description
   ```

### During Work

1. **Make small commits:**
   ```bash
   git add file1.py file2.py
   git commit -m "Clear description of change"
   ```

2. **Test frequently:**
   ```bash
   python script.py
   python verify_system_stats.py
   ```

3. **Update docs as you go:**
   - README.md - If stats/status changed
   - SESSION_NOTES.md - What you did
   - Code comments - Why, not what

### After Completing Work

1. **Final verification:**
   ```bash
   python verify_system_stats.py
   git status
   git diff
   ```

2. **Update all docs:**
   - README.md - Current status
   - SESSION_NOTES.md - Session summary
   - CHANGELOG.md - If completing an ITEM

3. **Commit and push:**
   ```bash
   git add -A
   git commit -m "Detailed commit message"
   git push origin branch-name
   ```

---

## Code Style

### Python
- **PEP 8** style
- **Docstrings** for all functions
- **Type hints** where helpful
- **Comments** for WHY, not WHAT

### File Naming
- EPUBs: `lastname_year_title_publisher.epub`
- Scripts: `descriptive_snake_case.py`
- Modules: `single_purpose_name.py`

### Git Commits
```
Type: Short description (50 chars)

Longer explanation if needed:
- What changed
- Why it changed
- Any side effects

Co-Authored-By: Assistant <noreply@example.com>
```

**Types:** Fix, Feature, Docs, Refactor, Test, Chore

---

## Testing

```bash
# Run verification script
python verify_system_stats.py

# Test Flask endpoint
curl http://localhost:5001/query -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# Test imports
python3 -c "import module_name"

# Check for syntax errors
python3 -m py_compile script.py
```

---

## Useful Commands

### File Operations
```bash
# Count lines in file
wc -l filename.py

# Find text in files
grep -rn "search_term" *.py

# View specific lines
sed -n '100,200p' filename.py
cat -n filename.py | sed -n '100,200p'
```

### Git
```bash
# See recent commits
git log --oneline -10

# See what changed
git diff filename.py
git show commit_hash

# Undo changes
git restore filename.py
git reset --soft HEAD~1  # Undo last commit, keep changes
```

### Python
```bash
# Activate venv
source .venv/bin/activate

# Install package
pip install package_name

# List installed
pip list

# Check syntax
python3 -m py_compile file.py
```

---

**For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md)**
**For troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)**
# Removing a Book

```bash
# Recommended: automatic cleanup (filesystem + SQLite + Qdrant)
python scripts/remove_books.py <filename>.epub

# Preview the actions first
python scripts/remove_books.py --dry-run <filename>.epub
```

Manual fallback if the script can’t run:
1. Delete the EPUB (`/Volumes/T7 Shield/rag/books/epub/`) and its image folder (`/Volumes/T7 Shield/rag/books/images/<book_id>`).
2. Remove the row from `epub_analysis.db` (`DELETE FROM epub_analysis WHERE filename = ?`).
3. Delete Qdrant points for `book_name = <filename>.epub`.
4. Run `python verify_all_deletions.py` to ensure no chunks remain.
