# ⚠️ START HERE - EVERY SESSION

**READ THIS ENTIRE FILE BEFORE DOING ANYTHING**

## Problem

Previous assistant sessions (3-4 times now) made the same critical mistakes:
1. **Trusted documentation instead of verifying actual state** → Stats were 40% inflated
2. **Deleted macOS `._*` metadata files** → User had to rebuild them
3. **Claimed work was "complete" without testing** → Bugs weren't actually fixed

## Your First Action

**When you need fresh counts (e.g., before editing stats in docs or after touching data), run:**
```bash
cd /Users/leon/Downloads/python/chess-analysis-system
source .venv/bin/activate
python verify_system_stats.py
```

Use those numbers for documentation and ingestion validation. For code-only work you can skip the command, but do not update stats in README/SESSION_NOTES without rerunning it.

## Critical Rules

### 1. macOS `._*` Files - NEVER DELETE THEM

```python
# ✅ CORRECT - Filter them out
files = [f for f in dir.glob("*.epub") if not f.name.startswith('._')]

# ❌ WRONG - Delete them
os.remove(file)  # DON'T DO THIS TO ._* FILES!
```

**Why:** macOS creates these on external drives for extended attributes. Mac needs them. User had to rebuild them after previous assistants deleted them.

### 2. Before Any Commit

**Run these checks (skip the stats script only if nothing touched data/stats):**
```bash
# 1. Verify actual state
python verify_system_stats.py

# 2. Test that claimed fixes actually work
python your_fixed_script.py

# 3. Check git status
git status

# 4. Update docs with VERIFIED numbers
# Edit README.md, SESSION_NOTES.md, BACKLOG.md
```

### 3. Documentation Priority

Update in this order (always):
1. **README.md** - Current stats in header
2. **SESSION_NOTES.md** - What you did today
3. **BACKLOG.md** - Item status if relevant

### 4. Documentation Location

All working docs, scratch notes, and deliverables belong inside `/Users/leon/Downloads/python/chess-analysis-system`. If you need a new note, create it inside the repo (for example under `docs/` or the project root). Do **not** leave Markdown/text files directly under `/Users/leon/`.

### 5. Logging & Output Are Mandatory

Every script or long-running command you add **must** emit human-readable progress logs (start banner, periodic status, completion/summary, and clear error messages). Silent scripts cost us hours of guesswork the last few times. If a job might run longer than a minute, add at least:

- A startup banner including the source/target paths and important flags  
- Heartbeat/progress messages (every N files/items)  
- A final summary with totals, unique counts, and the output path

Never merge a new script or major change without this logging in place. If you’re enhancing an existing quiet script, add the logging as part of the fix.

## Current System State (Verified Nov 10, 2025 - 3:30 PM)

Run `verify_system_stats.py` to get latest. Last verified (Nov 13, 2025):
- **Books:** 937 EPUB
- **Production Chunks:** 592,306 (359,095 EPUB + 233,211 PGN)
- **Diagrams:** 550,068
- **PGN Status:** `chess_pgn_repertoire` is live; current focus is validating diagram tooling against a cleaned PGN export

## Common Tasks

**Adding new books:** Run `scripts/analyze_staged_books.sh` against whatever the user staged (processes `/Volumes/T7 Shield/rag/books/epub/1new/` and updates `epub_analysis.db`), share the SQLite score report for approval, then follow the [full ingestion process in README](README.md#book-ingestion-process) (assistant handles renaming/moving approved titles)

**Adding new PGNs:** Run `python pgn_quality_analyzer.py "/Volumes/T7 Shield/rag/databases/pgn/1new" --db pgn_analysis.db` to score every staged PGN, share the EVS summary for approval, then chunk + ingest only the approved files (`analyze_pgn_games.py` → `add_pgn_to_corpus.py`).

**Fixing bugs:**
1. Read the issue
2. Locate the file
3. Make the fix
4. TEST IT
5. Update docs
6. Commit

**Updating stats (only when numbers change):**
1. Run `python verify_system_stats.py`
2. Copy the output
3. Update README/SESSION_NOTES
4. Commit

## Current Focus

- EPUB inline diagrams are fixed (markers now sync with available assets).
- Build/testing tooling for PGN-derived diagrams is in progress. The existing prototype struggles with extremely large PGN files, so wait for the cleaned/split corpus and rerun the tool once it lands. Capture findings in SESSION_NOTES along with any adjustments needed for the pipeline.

## Files You'll Edit Most

- `README.md` - Line 3 (header stats), Current Status section
- `SESSION_NOTES.md` - Append updates to end
- `app.py` - Flask server
- `*.py` scripts - Various fixes

## If User Says "Fix This Again"

It means a previous assistant didn't actually fix it. Don't assume it's done. Verify:
```bash
# Check the actual code
cat -n filename.py | grep "line_number"

# Run the script to test
python filename.py

# Check git history
git log --oneline | grep "relevant keyword"
```

---

**Bottom line:** Verify everything. Trust nothing. Test before claiming success.
