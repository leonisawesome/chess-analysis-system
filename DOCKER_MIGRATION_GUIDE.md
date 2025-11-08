# Docker Migration Guide for Chess RAG System

**Date:** November 7, 2025
**Purpose:** Migrate Qdrant from local file storage to Docker for better performance

---

## Why Migrate to Docker?

**Current Issues:**
- Flask startup: ~45 seconds (loading 358,529 chunks into memory)
- Local mode warning: "Not recommended for collections with >20,000 points"
- 5.5GB database loaded on every restart
- Concurrent access limitations

**Docker Benefits:**
- **Faster startup:** Flask restarts in 2-3 seconds (Qdrant stays running)
- **Better performance:** Optimized for large collections
- **Less memory usage:** More efficient indexing
- **Proper architecture:** Qdrant as a persistent service
- **Scalability:** Easy to move to cloud later

---

## Prerequisites

### 1. Install Docker Desktop

**Manual Installation (Required):**

1. **Download Docker Desktop for Mac:**
   - Visit: https://www.docker.com/products/docker-desktop
   - Click "Download for Mac" (Apple Silicon/M1/M2)
   - Or direct link: https://desktop.docker.com/mac/main/arm64/Docker.dmg

2. **Install:**
   - Open the downloaded `Docker.dmg`
   - Drag `Docker.app` to `/Applications`
   - Open `Docker.app` from Applications
   - Accept the service agreement
   - Docker Desktop will start (icon appears in menu bar)

3. **Verify Installation:**
   ```bash
   # Wait 30 seconds for Docker to fully start, then test:
   docker --version
   docker-compose --version
   docker ps
   ```

   Expected output:
   ```
   Docker version 24.0.x
   Docker Compose version v2.x.x
   CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
   ```

---

## Migration Steps

### Step 1: Start Qdrant in Docker

```bash
# Navigate to project directory
cd /Users/leon/Downloads/python/chess-analysis-system

# Start Qdrant container
docker-compose up -d

# Wait 15 seconds for Qdrant to start
sleep 15

# Verify Qdrant is running
curl http://localhost:6333/health

# Expected: {"title":"qdrant - vector search engine","version":"..."}
```

**Qdrant Dashboard:** http://localhost:6333/dashboard

### Step 2: Run Migration Script

```bash
# Activate virtual environment
source .venv/bin/activate

# Run migration
python migrate_to_docker_qdrant.py
```

**What the script does:**
1. Creates snapshot of local Qdrant (358,529 chunks)
2. Uploads snapshot to Docker Qdrant
3. Recovers collection in Docker
4. Verifies migration (counts must match)

**Expected output:**
```
================================================================================
QDRANT MIGRATION: LOCAL → DOCKER
================================================================================

1️⃣  Connecting to local Qdrant...
✅ Connected to local Qdrant
   Collection: chess_production
   Points: 358,529
   Size: 5.50 GB

2️⃣  Checking Docker Qdrant...
✅ Docker Qdrant is accessible

3️⃣  Creating snapshot...
✅ Snapshot created: chess_production-2025-11-07-07-54-23.snapshot
   Snapshot size: 4,200.5 MB

4️⃣  Migrating to Docker...
✅ Snapshot uploaded and collection recovered

5️⃣  Verifying migration...
📊 Comparison:
   Local Qdrant:  358,529 points
   Docker Qdrant: 358,529 points
✅ Migration successful! Counts match.

================================================================================
MIGRATION COMPLETE ✅
================================================================================
```

### Step 3: Update Flask Configuration

The Flask app already supports Docker Qdrant via environment variable:

```bash
# Option 1: Set environment variable (temporary)
export QDRANT_MODE=docker
export QDRANT_URL=http://localhost:6333

# Option 2: Update app.py directly (permanent)
# Already configured - just uncomment the Docker line in app.py
```

### Step 4: Restart Flask

```bash
# Stop current Flask
pkill -f "python.*app.py"

# Start with Docker Qdrant
export OPENAI_API_KEY='your-key-here'
export QDRANT_MODE=docker
source .venv/bin/activate
python app.py
```

**Expected startup:**
```
Initializing clients...
✓ Clients initialized (Qdrant: 358529 vectors)
...
================================================================================
SYSTEM A WEB UI
================================================================================
Corpus: 358,529 chunks from 1,055 books
Starting server at http://127.0.0.1:5001
================================================================================
```

**Startup time:** ~2-3 seconds (vs 45 seconds before!)

### Step 5: Test the System

```bash
# Test query
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"query":"How to improve endgame play?"}' \
  | python3 -m json.tool | head -50
```

---

## Docker Commands Reference

```bash
# Start Qdrant
docker-compose up -d

# Stop Qdrant
docker-compose down

# View logs
docker-compose logs -f qdrant

# Restart Qdrant
docker-compose restart qdrant

# Check status
docker ps
docker-compose ps

# Stop and remove (WARNING: deletes data unless backed up)
docker-compose down -v
```

---

## Troubleshooting

### Docker won't start
```bash
# Check Docker Desktop is running (menu bar icon)
# Restart Docker Desktop from the menu

# Verify Docker daemon
docker ps
```

### Qdrant container won't start
```bash
# Check logs
docker-compose logs qdrant

# Common issues:
# - Port 6333 already in use
# - Not enough disk space (needs ~6GB)
```

### Migration script fails
```bash
# Verify Qdrant is accessible
curl http://localhost:6333/health

# Check local Qdrant isn't locked
lsof +D ./qdrant_production_db

# Stop Flask if it's running
pkill -f "python.*app.py"
```

### Flask can't connect to Docker Qdrant
```bash
# Verify Qdrant is running
docker ps | grep qdrant

# Check port is exposed
curl http://localhost:6333/health

# Ensure QDRANT_URL is set
echo $QDRANT_URL
```

---

## Backup Strategy

### Before Migration
```bash
# Backup local Qdrant
tar -czf qdrant_local_backup_$(date +%Y%m%d).tar.gz qdrant_production_db/
```

### After Successful Migration
```bash
# Docker Qdrant data is in:
./qdrant_docker_storage/

# Regular backups
docker-compose exec qdrant tar -czf /tmp/backup.tar.gz /qdrant/storage
docker cp chess-rag-qdrant:/tmp/backup.tar.gz ./qdrant_backup_$(date +%Y%m%d).tar.gz
```

---

## Performance Comparison

| Metric | Before (Local) | After (Docker) |
|--------|----------------|----------------|
| Flask Startup | ~45 seconds | ~2-3 seconds |
| Qdrant Loading | Every restart | Once (persistent) |
| Memory Usage | High (loads all) | Optimized |
| Query Speed | Good | Better |
| Concurrent Access | Limited | Supported |
| Recommended For | <20K points | Any size |

---

## Rollback Procedure

If you need to revert to local Qdrant:

```bash
# 1. Stop Docker Qdrant
docker-compose down

# 2. Restore local Qdrant from backup (if needed)
tar -xzf qdrant_local_backup_YYYYMMDD.tar.gz

# 3. Update Flask to use local mode
export QDRANT_MODE=local
# Or comment out Docker settings in app.py

# 4. Restart Flask
python app.py
```

---

## Next Steps

After successful migration:

1. ✅ Verify all queries work correctly
2. ✅ Monitor performance improvements
3. ✅ Set up automated Docker Qdrant backups
4. ✅ Update deployment documentation
5. ⏸️ (Optional) Delete local Qdrant to free 5.5GB disk space

---

**Status:** Ready for migration
**Estimated Time:** 10-15 minutes
**Risk:** Low (local backup preserved)
