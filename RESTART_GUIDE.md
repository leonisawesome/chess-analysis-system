# Quick Restart Guide - After Reboot

## 1. START FLASK (REQUIRED)

```bash
cd /Users/leon/Downloads/python/chess-analysis-system
source .venv/bin/activate
export OPENAI_API_KEY="sk-proj-YOUR_API_KEY_HERE"
python app.py
```

**Wait for:**
```
✅ Loaded 526,463 diagrams from 920 books
   Filtered 8,003 small images (< 2,000 bytes)
Starting server at http://127.0.0.1:5001
```

---

## 2. VERIFY DIAGRAMS (30 seconds)

```bash
# Test diagram endpoint
curl -I http://localhost:5001/diagrams/book_00448974a7ea_0000

# Expected: HTTP/1.1 200 OK
```

---

## 3. TEST WEB UI (2 minutes)

```bash
open http://localhost:5001
```

**Test:**
1. Search "Najdorf Sicilian"
2. Check diagrams appear in results
3. Verify images load correctly

---

## WHAT WAS FIXED THIS SESSION

**Problem:** Diagrams returning 404 (not linked properly)

**Solution:** Changed size threshold in `app.py` line 106
- FROM: `min_size_bytes=12000` (filtered out 44,257 diagrams)
- TO: `min_size_bytes=2000` (filters only 8,003 icons)

**Result:** 526,463 diagrams now accessible (was 462,147)

---

## TROUBLESHOOTING

### Flask won't start - Port in use
```bash
lsof -ti:5001 | xargs kill -9
# Then restart Flask
```

### Diagrams return 404
```bash
# Check threshold
grep "min_size_bytes" app.py
# Should show: min_size_bytes=2000

# Check metadata exists
ls -lh diagram_metadata_full.json
# Should be ~385MB

# Check external drive mounted
ls /Volumes/T7\ Shield/books/images/ | head -5
# Should show book_ directories
```

### Query timeout
- Normal: 20-30 seconds
- OpenAI API can be slow
- Just wait or retry

---

## FILES CREATED FOR REFERENCE

1. **SESSION_NOTES.md** - Comprehensive session summary
2. **TECHNICAL_DETAILS.md** - Architecture and code details
3. **RESTART_GUIDE.md** - This file (quick start)

---

## NEXT PHASE

**Phase 6.1a:** Test static diagram display in web UI
- ✅ Extraction complete (534,466 diagrams)
- ✅ Endpoint working (HTTP 200)
- ✅ Flask configured (2KB threshold)
- ⏳ UI testing pending (user action needed)

**After UI Test:**
- Phase 6.1b: Dynamic diagram generation
- PGN expansion: 1,778 → 1M games
- Phase 5.2: RRF validation

---

## CRITICAL INFO

**Project:** `/Users/leon/Downloads/python/chess-analysis-system/`
**Server:** http://localhost:5001
**Diagrams:** `/Volumes/T7 Shield/rag/books/images/`
**Qdrant:** http://localhost:6333 (Docker, auto-starts)
**Modified:** `app.py` line 106 (min_size_bytes=2000)

**Status:** ✅ READY FOR TESTING
