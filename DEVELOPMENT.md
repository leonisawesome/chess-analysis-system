# Development Guide

## Quick Start

```bash
cd /Users/leon/Downloads/python/chess-analysis-system
source .venv/bin/activate
python verify_system_stats.py  # Always run first!
```

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

# 3. Add to Qdrant
export OPENAI_API_KEY='sk-proj-...'
export QDRANT_MODE=docker
python add_books_to_corpus.py book.epub

# 4. Extract diagrams (append metadata for the new book; only rebuild the full file if you reprocessed the entire corpus)
python extract_epub_diagrams.py --book-id book_<hash> --append

# 5. Verify stats and update hardcoded homepage counts
python verify_system_stats.py
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
python pgn_quality_analyzer.py "/Volumes/T7 Shield/rag/pgn/1new" --db pgn_analysis.db --json pgn_scores.json

# 2. Share the EVS report for approval (only approved files move on)

# 3. Chunk + ingest the approved PGNs
python analyze_pgn_games.py "/Volumes/T7 Shield/rag/pgn/approved" --output approved_pgn_chunks.json
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
