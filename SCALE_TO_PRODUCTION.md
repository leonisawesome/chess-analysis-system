# System A: Scale to Production (1,052 Books)

**Status:** Week 3 optimization complete at 86-87% precision@5 ✓
**Next:** Scale from 5 books → 1,052 books (HIGH + MEDIUM tiers)

---

## Current State

### Books Analyzed
- **Total books:** 1,111 successfully analyzed (stored in SQLite)
- **Tier distribution:**
  - HIGH: 191 books
  - MEDIUM: 861 books
  - LOW: 59 books
- **Target corpus:** 1,052 books (HIGH + MEDIUM)
- **Total words:** 84M words

### Validation Configuration (5 books)
- **Model:** OpenAI text-embedding-3-small (1536 dims)
- **Reranking:** GPT-5 with optimized prompt
- **Top-K:** 40 candidates
- **Precision@5:** 86-87% ✓
- **No query expansion** (causes intent drift)

---

## Execution Plan

### Phase 1: Build Production Corpus

**Script:** `build_production_corpus.py`

**What it does:**
1. Queries SQLite for HIGH + MEDIUM tier books (1,052 books)
2. Extracts chunks from each book (512 tokens, 64 overlap)
3. Generates embeddings using OpenAI text-embedding-3-small
4. Uploads to Qdrant production database

**Estimated:**
- Chunks: ~350,000 (based on 84M words)
- Tokens: ~110M tokens
- Cost: ~$2.20 (at $0.02/1M tokens)
- Time: ~60-90 minutes (embedding + upload)

**Run:**
```bash
source .venv/bin/activate
export OPENAI_API_KEY='your-key-here'
python build_production_corpus.py
```

**Output:**
- `production_chunks.json` - all chunks with metadata
- `qdrant_production_db/` - Qdrant database
- Collection: `chess_production`

---

### Phase 2: Validate at Scale

**Script:** `validate_production_corpus.py`

**What it does:**
1. Runs same 10 validation queries on full 1,052-book corpus
2. Tests if precision@5 maintains 86-87%
3. Saves results for manual evaluation

**Expected:**
- Precision@5: 86-87% (same as 5-book validation)
- If lower: investigate corpus quality issues
- If higher: bonus! More books = better coverage

**Run:**
```bash
python validate_production_corpus.py
```

**Output:**
- `production_validation_results.json` - top 5 for each query
- Manual evaluation needed (y/p/n scoring)

---

### Phase 3: Performance Testing

**Script:** `test_production_performance.py`

**What it does:**
1. Tests query latency (cold start, warm, batch)
2. Measures memory usage
3. Tests Qdrant search performance (100 searches)
4. System stability check

**Success Criteria:**
- ✅ Latency: <5s per query (avg warm)
- ✅ Memory: Reasonable for production
- ✅ No crashes or errors

**Run:**
```bash
python test_production_performance.py
```

**Output:**
- `production_performance_results.json` - latency, memory, search stats

---

## Success Criteria

### Phase 1: Corpus Building
- [ ] All 1,052 books processed and chunked
- [ ] Embeddings generated for all chunks
- [ ] Qdrant collection created with all chunks
- [ ] No major errors or failures

### Phase 2: Validation
- [ ] Precision@5 maintains 86-87% on validation set
- [ ] No significant regressions on any query
- [ ] Results quality comparable to 5-book validation

### Phase 3: Performance
- [ ] Average latency <5s per query
- [ ] System stable under load (100 queries)
- [ ] Memory usage acceptable for production
- [ ] Qdrant search fast (<100ms avg)

---

## Timeline Estimate

| Phase | Task | Estimated Time |
|-------|------|----------------|
| 1 | Extract chunks from 1,052 books | 30-45 min |
| 1 | Generate embeddings (110M tokens) | 30-45 min |
| 1 | Upload to Qdrant | 5-10 min |
| 2 | Run validation queries (10 queries) | 5-10 min |
| 2 | Manual evaluation | 10-15 min |
| 3 | Performance testing | 10-15 min |
| **Total** | **All phases** | **~2-2.5 hours** |

---

## Cost Estimate

### OpenAI API Costs
- **Embedding:** ~110M tokens × $0.02/1M = ~$2.20
- **Validation queries:** 10 queries × $0.01 = ~$0.10
- **Reranking:** 10 queries × 40 candidates × $0.10 = ~$0.50
- **Performance testing:** ~$0.20
- **Total:** ~$3.00

---

## Troubleshooting

### If precision@5 drops below 86%:

**Possible causes:**
1. Book quality issues (some LOW tier books sneaked in)
2. Chunking differences (validation used different chunk boundaries)
3. More books = more noise (harder to find best results)

**Solutions:**
- Filter to only HIGH tier books (191 books)
- Adjust chunking parameters
- Increase top-K from 40 to 60
- Use more aggressive reranking

### If latency exceeds 5s:

**Possible causes:**
1. Qdrant search slow at scale (350K vectors)
2. Reranking 40 candidates takes too long
3. Network latency to OpenAI API

**Solutions:**
- Reduce top-K from 40 to 30
- Use faster reranking (smaller prompt)
- Consider caching common queries
- Optimize Qdrant parameters (HNSW)

### If memory usage too high:

**Possible causes:**
1. All embeddings loaded in memory
2. Qdrant cache too large
3. Memory leak

**Solutions:**
- Use disk-based Qdrant (not in-memory)
- Reduce Qdrant cache size
- Restart process periodically

---

## After Completion

### If all phases successful:

**System A is PRODUCTION READY** ✓

Next steps:
1. Deploy to production environment
2. Create user-facing API/interface
3. Monitor real-world performance
4. **Start System B (PGN database)**

### If any phase fails:

**Debug and iterate:**
1. Analyze failure mode
2. Adjust parameters
3. Re-test specific phase
4. Do NOT proceed until fixed

---

## Files Created

### Pipeline Scripts
- `build_production_corpus.py` - Build 1,052-book corpus
- `validate_production_corpus.py` - Validate precision@5
- `test_production_performance.py` - Performance testing

### Existing Infrastructure
- `epub_analysis.db` - SQLite with 1,111 analyzed books
- `fast_epub_analyzer.py` - EPUB extraction and chunking
- `batch_process_epubs.py` - Batch book processing

### Validation Reference
- `TWO_STAGE_FINAL_RESULTS.txt` - Week 3 optimization results
- `validation_chunks.json` - 5-book validation corpus

---

## Ready to Execute?

**Checklist:**
- [ ] OpenAI API key set: `export OPENAI_API_KEY='...'`
- [ ] Virtual environment activated: `source .venv/bin/activate`
- [ ] Sufficient disk space (~5GB for Qdrant DB)
- [ ] Stable internet connection (for API calls)
- [ ] ~2.5 hours available for full pipeline
- [ ] ~$3 budget for API costs

**Start with:**
```bash
python build_production_corpus.py
```

Good luck! 🚀
