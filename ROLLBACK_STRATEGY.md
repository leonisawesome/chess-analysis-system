# Rollback Strategy - PGN Variation Splitting
**Date:** November 8, 2025
**Feature:** PGN variation splitting for oversized chunks
**Branch:** `feature/pgn-variation-splitting`

---

## 🎯 Rollback Philosophy

**Principle:** Every change must be reversible without data loss.

**Safety Levels:**
1. **Code rollback:** Git branch strategy
2. **Data rollback:** Isolated collections, no production modification
3. **Quick recovery:** Documented procedures, tested restore paths

---

## 🔄 Rollback Mechanisms

### Level 1: Code Rollback (Git)

#### Current State (Before Changes)
```bash
Branch: feature/pgn-variation-splitting
Base: feature/add-new-epub-books
Status: Clean working directory (after initial commit)
```

#### Rollback Command
```bash
# Abort entire feature
git checkout main
git branch -D feature/pgn-variation-splitting

# Or rollback to specific commit
git log --oneline  # Find commit hash
git reset --hard <commit-hash>

# Or keep changes but uncommitted
git reset --soft <commit-hash>
```

#### Protected Files (Never Overwrite)
- ✅ `analyze_pgn_games.py` - Keep original intact, create new file
- ✅ `add_pgn_to_corpus.py` - Keep original, create v2
- ✅ `chess_positions.py` - Production code, don't touch
- ✅ `qdrant_docker_storage/` - Production data, isolated new collections

---

### Level 2: File Safety (New Files, Not Modifications)

**Strategy:** Create NEW files, don't modify existing ones.

#### New Files Created (Safe to Delete)
```
split_oversized_game.py          # New splitter logic
test_variation_splitter.py       # Unit tests
test_oversized_files.py          # Integration tests
test_validation.py               # Validation tests
test_full_corpus.py              # Corpus tests
test_production_validation.py    # Production tests
pgn_chunks_with_splits.json      # Test output (can delete)
split_processing_*.log           # Logs (can delete)
```

#### Files Modified (Git Tracked)
```
README.md                        # Documented changes (git diff shows what changed)
BACKLOG.txt                      # Documented changes (git diff)
session_notes_nov8_impl.md       # New file
```

**Rollback Process:**
```bash
# Discard all changes
git checkout -- README.md BACKLOG.txt

# Or restore specific file
git checkout HEAD~1 -- README.md
```

---

### Level 3: Data Safety (Isolated Collections)

#### Production Data (NEVER TOUCHED)
```
Collection: chess_production
Points: 358,529 (book chunks)
Status: ✅ UNTOUCHED - read-only during testing
```

#### Test Collection (Safe to Delete)
```
Collection: chess_pgn_split_test
Points: ~1,783 (test chunks)
Purpose: Isolated testing
Rollback: Delete entire collection
```

**Creation:**
```python
# Create isolated test collection
qdrant_client.recreate_collection(
    collection_name="chess_pgn_split_test",
    vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE)
)
```

**Rollback:**
```python
# Delete test collection entirely
qdrant_client.delete_collection("chess_pgn_split_test")
```

**Verification:**
```python
# Verify production untouched
info = qdrant_client.get_collection("chess_production")
assert info.points_count == 358529, "Production data modified!"
```

---

### Level 4: Incremental Commits (Checkpoint Strategy)

**Commit Strategy:** Small, atomic commits with clear messages.

#### Commit Plan

**Commit 1: Initial setup**
```bash
git add TESTING_STRATEGY.md ROLLBACK_STRATEGY.md
git commit -m "Add testing and rollback strategies for variation splitting"
```

**Commit 2: Splitter function**
```bash
git add split_oversized_game.py
git commit -m "Implement split_oversized_game() function (ChatGPT base + enhancements)"
```

**Commit 3: Unit tests**
```bash
git add test_variation_splitter.py
git commit -m "Add unit tests for variation splitter"
```

**Commit 4: Integration tests**
```bash
git add test_oversized_files.py
git commit -m "Add integration tests for 4 oversized files"
```

**Commit 5: Validation tests**
```bash
git add test_validation.py
git commit -m "Add validation tests (round-trip, legal moves, metadata)"
```

**Commit 6: Corpus test**
```bash
git add test_full_corpus.py
git commit -m "Add corpus test for all 1,779 games"
```

**Commit 7: Production validation**
```bash
git add test_production_validation.py
git commit -m "Add production validation tests (embedding, Qdrant, retrieval)"
```

**Commit 8: Documentation**
```bash
git add README.md BACKLOG.txt session_notes_nov8_impl.md
git commit -m "Update documentation (README, BACKLOG, session notes)"
```

**Each commit is a rollback point!**

---

## 📊 Rollback Scenarios

### Scenario 1: Unit Tests Fail

**Situation:** Splitter function has bugs, unit tests don't pass.

**Rollback:**
```bash
# Delete the broken function
rm split_oversized_game.py

# Or fix and re-commit
git add split_oversized_game.py
git commit --amend -m "Fix split_oversized_game() - corrected token counting"
```

**Impact:** Zero - no test data created yet

---

### Scenario 2: Integration Tests Fail (4 Files)

**Situation:** Splitter works in unit tests but fails on real oversized files.

**Rollback:**
```bash
# Revert to before integration tests
git log --oneline  # Find "Implement split_oversized_game()" commit
git revert <commit-hash>

# Or reset to that commit
git reset --hard <commit-hash>
```

**Cleanup:**
```bash
# Delete test output files
rm pgn_chunks_test_*.json
rm split_processing_*.log
```

**Impact:** Minimal - only test files created

---

### Scenario 3: Corpus Test Fails (1,779 Games)

**Situation:** Works on 4 files, fails on full corpus.

**Rollback:**
```bash
# Revert commits back to integration test success
git reset --hard <last-good-commit>
```

**Cleanup:**
```bash
# Delete corpus test outputs
rm pgn_chunks_corpus_*.json
rm corpus_test_*.log
```

**Impact:** Low - no Qdrant data created yet

---

### Scenario 4: Embedding/Upload Fails

**Situation:** Chunks created successfully, but embedding or Qdrant upload fails.

**Rollback:**
```bash
# Delete test collection
python -c "
from qdrant_client import QdrantClient
client = QdrantClient('localhost', port=6333)
client.delete_collection('chess_pgn_split_test')
"
```

**Code Rollback:**
```bash
# Revert to before production validation
git reset --hard <before-production-commit>
```

**Impact:** Medium - wasted embedding API costs (~$0.04), but no data corruption

---

### Scenario 5: Retrieval Quality Degraded

**Situation:** Everything works, but retrieval quality is worse than before.

**Rollback Decision Matrix:**

| Metric | Threshold | Action if Below |
|--------|-----------|-----------------|
| Retrieval precision | >90% | Rollback |
| Purity (PGN-only) | 100% | Rollback |
| Sibling attach rate | >50% | Investigate, maybe rollback |
| Synthesis quality | >8/10 | Investigate, maybe rollback |

**Rollback:**
```bash
# Delete test collection
qdrant_client.delete_collection("chess_pgn_split_test")

# Revert code
git reset --hard <commit-before-production-validation>
```

**Investigation:**
```bash
# Keep test collection for debugging
# Adjust sibling boosting parameters
# Re-test retrieval

# If still bad, full rollback
```

---

## 🚨 Emergency Rollback (Nuclear Option)

**Situation:** Complete failure, need to abort everything immediately.

### Procedure:

#### Step 1: Stop all running processes
```bash
# Kill any running Python processes
pkill -f "python.*pgn"

# Kill any embedding jobs
# (Check API dashboard, cancel if needed)
```

#### Step 2: Delete all test data
```bash
# Delete Qdrant test collection
python -c "
from qdrant_client import QdrantClient
client = QdrantClient('localhost', port=6333)
try:
    client.delete_collection('chess_pgn_split_test')
except:
    pass
"

# Delete all test output files
rm -f pgn_chunks_*.json
rm -f split_processing_*.log
rm -f test_report_*.html
```

#### Step 3: Revert all code changes
```bash
# Switch to main branch
git checkout main

# Delete feature branch
git branch -D feature/pgn-variation-splitting

# Verify clean state
git status
```

#### Step 4: Verify production integrity
```bash
# Check production collection untouched
python -c "
from qdrant_client import QdrantClient
client = QdrantClient('localhost', port=6333)
info = client.get_collection('chess_production')
print(f'Production points: {info.points_count}')
assert info.points_count == 358529, 'Production corrupted!'
print('✅ Production data intact')
"
```

**Time to Execute:** <5 minutes

**Data Loss:** Only test data (acceptable)

---

## ✅ Rollback Validation Checklist

After any rollback, verify:

- [ ] Code reverted to known good state
  ```bash
  git log --oneline -3  # Check commits
  git diff main  # No unexpected diffs
  ```

- [ ] Test files deleted
  ```bash
  ls pgn_chunks_*.json  # Should not exist
  ls split_processing_*.log  # Should not exist
  ```

- [ ] Test collection deleted
  ```bash
  qdrant_client.get_collection("chess_pgn_split_test")
  # Should raise exception (collection doesn't exist)
  ```

- [ ] Production data intact
  ```bash
  info = qdrant_client.get_collection("chess_production")
  assert info.points_count == 358529
  ```

- [ ] System functional
  ```bash
  # Run existing system test
  python test_pgn_retrieval.py
  # Should pass with original data
  ```

---

## 📋 Rollback Decision Tree

```
Did unit tests pass?
├─ NO → Rollback: Delete split_oversized_game.py, fix bugs
└─ YES → Continue

Did integration tests (4 files) pass?
├─ NO → Rollback: Revert commits, fix issues with oversized files
└─ YES → Continue

Did validation tests pass?
├─ NO → Rollback: Revert commits, fix PGN/metadata issues
└─ YES → Continue

Did corpus test (1,779 games) pass?
├─ NO → Rollback: Revert commits, investigate failures
└─ YES → Continue

Did embedding/upload succeed?
├─ NO → Rollback: Delete test collection, fix API/Qdrant issues
└─ YES → Continue

Is retrieval quality acceptable?
├─ NO → Investigate → Still bad? → Rollback
└─ YES → Continue to production
```

---

## 🎯 Success Criteria for "No Rollback Needed"

**All must be TRUE:**
- ✅ All tests passing (5 levels)
- ✅ 0 data corruption
- ✅ Retrieval quality maintained or improved
- ✅ Production data untouched
- ✅ Clear documentation of changes
- ✅ Git history clean and atomic

**If even ONE is false → Rollback and fix**

---

## 📊 Rollback Metrics

Track for each potential rollback scenario:

| Rollback Level | Time to Execute | Data Loss | Code Loss | Production Risk |
|----------------|-----------------|-----------|-----------|-----------------|
| Unit test fail | <1 min | None | 1 file | Zero |
| Integration fail | <2 min | Test outputs | 2-3 files | Zero |
| Corpus fail | <5 min | Test outputs | 3-4 commits | Zero |
| Embedding fail | <5 min | $0.04 API cost | 4-5 commits | Zero |
| Retrieval fail | <10 min | Test collection | All feature | Zero |
| **NUCLEAR** | <5 min | All test data | All feature | **Verify zero** |

**Key Insight:** Production risk is ZERO at every level due to isolated testing strategy.

---

## 📝 Post-Rollback Actions

After any rollback:

1. **Document failure**
   - Add to BACKLOG.txt as "ITEM-XXX: [FAILED] PGN Variation Splitting"
   - Note reason for rollback
   - Plan for fix

2. **Update session notes**
   - session_notes_nov8_impl.md
   - Section: "Rollback Event"
   - Timestamp, reason, resolution

3. **Communicate**
   - Update Leon on what happened
   - Explain what was learned
   - Propose fix strategy

4. **Fix and retry**
   - Address root cause
   - Re-run tests from Level 1
   - Don't skip any test level

---

**Created:** November 8, 2025
**Status:** Ready for implementation
**Confidence:** 99% (rollback risk near-zero due to isolation strategy)

**Next:** Begin implementation with full testing and rollback safety nets in place.
