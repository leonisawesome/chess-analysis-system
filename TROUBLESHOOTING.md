# Troubleshooting Guide

## Quick Diagnostics

**First, run these to verify system state:**
```bash
python verify_system_stats.py  # Check actual stats
docker ps | grep qdrant         # Check Qdrant is running
curl http://localhost:5001/health  # Check Flask (if exists)
```

---

## Common Issues

### OPENAI_API_KEY not set
```bash
export OPENAI_API_KEY='sk-proj-YOUR_KEY_HERE'
python app.py
```

### Docker Qdrant not running
```bash
open -a Docker  # Start Docker Desktop
docker-compose up -d  # Start Qdrant
```

### Git push fails
```bash
# Check authentication
git remote -v  # Should show git@github.com, not https
ssh -T git@github.com  # Should authenticate

# Fix if using HTTPS:
git remote set-url origin git@github.com:leonisawesome/chess-analysis-system.git
```

### Import errors after refactoring
```bash
# Verify all modules exist
ls -la *.py | grep -E "(rag_engine|synthesis_pipeline|reranker)"

# Test imports
python3 -c "import rag_engine; import synthesis_pipeline"
```

### "Module not found" errors
```bash
# Activate venv
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

## Known Bugs (November 10, 2025)

### 1. add_books_to_corpus.py - Hardcoded Wrong Path
- **Status:** ✅ FIXED (Nov 10, 2025)
- **Was:** Line 62 had `/Volumes/T7 Shield/epub` (missing `/books/`)
- **Fix:** Updated to `/Volumes/T7 Shield/books/epub`

### 2. batch_process_epubs.py - Summary Report Crash
- **Status:** ✅ FIXED (Nov 10, 2025)
- **Was:** TypeError when sorting keys with None values (line 273)
- **Fix:** Added `valid_formats = [k for k in keys() if k is not None]`

### 3. extract_epub_diagrams.py - No Specific File Support
- **Status:** ❌ NOT FIXED (design limitation)
- **Issue:** Only processes entire directory, can't specify individual files
- **Workaround:** Use inline extraction script for small batches

---

## Data Issues

### Stats don't match documentation
**Run verification:**
```bash
python verify_system_stats.py
```
Use those numbers, not README stats (README has been wrong multiple times).

### Missing diagrams
**Check diagram service loaded them:**
```bash
grep "Loaded.*diagrams" flask_final.log
ls "/Volumes/T7 Shield/books/images/book_*" | wc -l
```

### Qdrant collection missing points
**Verify collections:**
```bash
python3 << 'EOF'
from qdrant_client import QdrantClient
qdrant = QdrantClient(url="http://localhost:6333")
for coll in qdrant.get_collections().collections:
    info = qdrant.get_collection(coll.name)
    print(f"{coll.name}: {info.points_count:,} points")
EOF
```

---

## Performance Issues

### Query timeouts
- Check OpenAI API is responding
- Normal processing: Embedding (5-6s) + Search (1-2s) + Reranking (15-20s)
- Check logs: `tail -f flask_final.log`

### Diagram loading slow
- Diagrams are on external drive (`/Volumes/T7 Shield/`)
- Mount drive before starting Flask
- Check with: `ls /Volumes/T7\ Shield/books/images/ | head -5`

---

## Emergency Procedures

### Flask won't start
```bash
# Kill existing process
pkill -f "python.*app.py"

# Check port 5001
lsof -i :5001

# Restart
source .venv/bin/activate
export OPENAI_API_KEY="sk-proj-..."
python app.py
```

### Qdrant corrupted
```bash
# Stop Qdrant
docker-compose down

# Rebuild from backup (if you have one)
# Or re-ingest books (expensive!)
```

### Git disaster recovery
```bash
# See what changed
git status
git diff

# Undo uncommitted changes
git restore filename.py

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Nuclear option (lose all changes)
git reset --hard HEAD
```

---

**For development issues, see [DEVELOPMENT.md](DEVELOPMENT.md)**
