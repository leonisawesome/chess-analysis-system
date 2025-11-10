# ⚠️ START HERE - EVERY SESSION

**READ THIS ENTIRE FILE BEFORE DOING ANYTHING**

## Problem

Previous Claude sessions (3-4 times now) made the same critical mistakes:
1. **Trusted documentation instead of verifying actual state** → Stats were 40% inflated
2. **Deleted macOS `._*` metadata files** → User had to rebuild them
3. **Claimed work was "complete" without testing** → Bugs weren't actually fixed

## Your First Action

**RUN THIS COMMAND FIRST:**
```bash
cd /Users/leon/Downloads/python/chess-analysis-system
source .venv/bin/activate
python verify_system_stats.py
```

**USE THOSE NUMBERS.** Not the README. Not old docs. Those numbers.

## Critical Rules

### 1. macOS `._*` Files - NEVER DELETE THEM

```python
# ✅ CORRECT - Filter them out
files = [f for f in dir.glob("*.epub") if not f.name.startswith('._')]

# ❌ WRONG - Delete them
os.remove(file)  # DON'T DO THIS TO ._* FILES!
```

**Why:** macOS creates these on external drives for extended attributes. Mac needs them. User had to rebuild them after previous Claudes deleted them.

### 2. Before Any Commit

**Run these checks:**
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

## Current System State (Verified Nov 10, 2025 - 3:30 PM)

Run `verify_system_stats.py` to get latest, but as of now:
- **Books:** 922 EPUB
- **Production Chunks:** 313,057 (311,266 EPUB + 1,791 PGN)
- **Diagrams:** 536,243

## Common Tasks

**Adding new books:** See [Ingestion Process in README](README.md#book-ingestion-process)

**Fixing bugs:**
1. Read the issue
2. Locate the file
3. Make the fix
4. TEST IT
5. Update docs
6. Commit

**Updating stats:**
1. Run `python verify_system_stats.py`
2. Copy the output
3. Update README/SESSION_NOTES
4. Commit

## Files You'll Edit Most

- `README.md` - Line 3 (header stats), Current Status section
- `SESSION_NOTES.md` - Append updates to end
- `app.py` - Flask server
- `*.py` scripts - Various fixes

## If User Says "Fix This Again"

It means a previous Claude didn't actually fix it. Don't assume it's done. Verify:
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
