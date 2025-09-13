# Changes Log - Chess RAG System

## Change 1 - Instructional Vocabulary Hotfix Replacement (2025-09-11)

**Target File:** `chess_rag_system/analysis/instructional_vocabulary_hotfix.py`

**Change Type:** Complete vocabulary replacement with empirically-derived patterns

**Consultation:** 5-AI partner consultation completed (Gemini, Grok 2x, ChatGPT 2x, Perplexity)

**Implementation Strategy:** ChatGPT's 9-category framework with chess-specific patterns

**Expected Impact:** 0 raw hits → 15+ gated hits → EVS improvement from 79.7 to 85+

**Rollback Commands:**
```bash
# To rollback this change if needed
git checkout HEAD~1 chess_rag_system/analysis/instructional_vocabulary_hotfix.py
# Or restore from backup
cp chess_rag_system/analysis/instructional_vocabulary_hotfix.py.backup chess_rag_system/analysis/instructional_vocabulary_hotfix.py
```

**Status:** COMPLETED

### Partner Consultation — Change 4 (PGN Manifest External Merge)

CONSULTATION REQUIRED (Gold Template — Condensed)
1) Problem: External chunk merge must respect numeric/shuffle key across chunks.

2) Context:
• File: `scripts/pgn_manifest.py` (new). Function: `external_sort` with chunk spill + keyed `heapq.merge`.
• Behavior: Deterministic manifests needed for ingestion at scale; numeric order and seeded shuffle must be global, not per-chunk.
• Risk/impact: Reproducibility and fairness of sampling; ordering errors can bias training/eval.

3) Constraints: Reuse existing stack; smallest viable change; scripted edits; feature branch; no bypasses; include tests + rollback.

4) Minimal evidence:
• Numeric example shows lex merge produces `file1, file10, file2` (wrong)
• Shuffle example shows chunk-local shuffle later reordered lexicographically

5) Hypotheses:
H1 Keyless merge is root cause; H2 Temp-file format can remain path-only if we supply `key=` during merge.

6) Options (ranked):
A) Add `key=` to `heapq.merge` (recompute key on line) — minimal, streaming.
B) Decorate temp lines with `<key>\t<path>` — heavier, serialization risk.
C) Defer/remove external mode — harms scale.

7) Risks & mitigations:
TOC FPs: N/A here; Overhead: recompute key during merge — negligible vs IO; Cross-OS determinism: numeric uses `basename().lower()`, shuffle uses full path bytes with explicit UTF-8 surrogatepass.

8) Decision criteria:
Correct numeric global order; deterministic shuffle for same seed; full tests green; negligible runtime delta.

9) Questions posed to partners:
Is Option A sufficient? Any newline/whitespace, basename vs full-path pitfalls? Windows path separators? Need counters/chunk sizing now?

Partner Inputs (condensed):
• Claude: Use `heapq.merge(..., key=...)`; strip newlines before keying; prefer `Path(s).name` for numeric and full path for shuffle. Influence: Adopt keyed merge; ensure `rstrip("\n")` and `basename` for numeric. 
• Gemini: Option A preferred; decorated approach is overkill. Add tests for both single- and multi-chunk behavior. Influence: Tests assert correctness irrespective of chunking.
• Perplexity: Key recomputation overhead negligible; confirm seed determinism; document that shuffle is seed-driven over full path bytes. Influence: Kept full-path for shuffle key, added determinism test.
• Grok: Keep `--chunk-size-mb` hint for ergonomics; watch cross-platform path normalization. Influence: Added `--chunk-size-mb`; numeric key lowercases; shuffle uses raw UTF-8 bytes.

Decision & Outcome:
• Chosen Option A (smallest viable). Implemented keyed merge, added tests for numeric correctness and seeded determinism. Full suite PASS. Rollback steps documented above.

---

## Change 1a - Env-gated EN/ES Regex (2025-09-12)

**Target File:** `chess_rag_system/analysis/instructional_vocabulary_hotfix.py`

**Change Type:** Option A implementation (smallest viable change)

**Details:**
- Add Spanish equivalents for the 9-category instructional lexicon.
- Gate inclusion via `DETECTOR_LANGS` env var (default `en`; supports `es`, `en,es`, `all`).
- No changes to TOC/engine detectors or other subsystems.

**Tests Added:** `tests/test_vocab_lang_gate.py` (4 focused tests)
- Validate ES patterns are off by default and enabled with `DETECTOR_LANGS=en,es`.
- Ensure EN patterns remain available.
- Verify accented Spanish boundaries match.

**Expected Impact:**
- +precision with optional ES regex; ≤2% recall impact in EN-only default.
- Zero flaky tests (deterministic gating via env).

**Status:** COMPLETED

## Change 2 - Category Mapping Layer Fix (2025-09-11)

**Target Files:** 
- `chess_rag_system/analysis/instructional_detector.py`
- `chess_rag_system/analysis/semantic_analyzer.py`

**Change Type:** Category mapping layer implementation to fix 0.000 score issue

**4-AI Partner Consensus:** Gemini, Grok, Perplexity, ChatGPT all identified category name mismatch as primary cause

**Implementation Strategy:** 5-step hybrid approach with backward compatibility
1. Safety & provenance logging
2. Category mapping layer (intent_patterns → intent)
3. Per-pattern compilation (kill mega-regex)
4. Sentence-level gating
5. Integration validation

**Expected Impact:** 0 raw hits → 15+ raw hits → 10+ gated hits → EVS 79.7 to 85+

**Rollback Commands:**
```bash
# Create timestamped backups
cp chess_rag_system/analysis/instructional_detector.py chess_rag_system/analysis/instructional_detector.py.bak.$(date +%Y%m%d%H%M%S)
cp chess_rag_system/analysis/semantic_analyzer.py chess_rag_system/analysis/semantic_analyzer.py.bak.$(date +%Y%m%d%H%M%S)

# Hard rollback if needed
git checkout -- chess_rag_system/analysis/instructional_detector.py chess_rag_system/analysis/semantic_analyzer.py

# Or restore from backup
mv chess_rag_system/analysis/instructional_detector.py.bak.TIMESTAMP chess_rag_system/analysis/instructional_detector.py
mv chess_rag_system/analysis/semantic_analyzer.py.bak.TIMESTAMP chess_rag_system/analysis/semantic_analyzer.py
```

**Status:** DOCUMENTED - Ready for implementation

---

## Change 3 - Vocabulary Loading Diagnostics (2025-01-11)

**Target File:** `chess_rag_system/analysis/instructional_detector.py`

**Change Type:** Diagnostic logging to identify vocabulary loading failure

**AI Partner Consultation:** 4-partner unanimous consensus (First Partner, ChatGPT, Grok, Perplexity)

**Root Cause Identified:** 
- Vocabulary loading failure (8 vs 73+ expected patterns) in ThreadPoolExecutor context
- NOT multiprocessing lifecycle issue as initially suspected
- ThreadPoolExecutor uses shared memory (no serialization concerns)

**Implementation Strategy:** Partner-validated diagnostic-first approach
1. Add execution context validation (PID/TID logging)
2. Add vocabulary loading size validation with explicit counts
3. Add per-category pattern compilation logging
4. Fail-fast on incomplete vocabulary loading (<50-73 patterns)

**Expected Impact:** Identify root cause of "NO compiled_patterns" → Enable proper 73+ pattern loading → EVS improvement 79.7 to 85+

**Rollback Commands:**
```bash
# Create timestamped backup
cp chess_rag_system/analysis/instructional_detector.py chess_rag_system/analysis/instructional_detector.py.backup.$(date +%Y%m%d_%H%M%S)

# If rollback needed:
# cp chess_rag_system/analysis/instructional_detector.py.backup.TIMESTAMP chess_rag_system/analysis/instructional_detector.py
# git checkout -- chess_rag_system/analysis/instructional_detector.py
```

**Technical Decision:** Focus on vocabulary loading validation vs multiprocessing lifecycle fixes based on partner analysis that EVS uses threads, not processes.

**Status:** DOCUMENTED - Ready for implementation## 2025-09-11 20:36:24 feature/per-process-detector-factory
- Files modified:
  - chess_rag_system/analysis/instructional_detector.py
  - chess_rag_system/file_ops/file_processor.py
  - tests/test_instructional_detector.py
  - tests/test_detector_multiprocessing.py
- Summary: Per-process-safe pattern compilation, factory constructor, diagnostics, and tests.
- Rollback:
  cp -p chess_rag_system/analysis/instructional_detector.py.bak chess_rag_system/analysis/instructional_detector.py
  cp -p chess_rag_system/file_ops/file_processor.py.bak chess_rag_system/file_ops/file_processor.py
  git checkout -- tests/test_instructional_detector.py tests/test_detector_multiprocessing.py

---

## Change 4 - PGN Manifest External Merge (2025-09-12) — Minimal Keyed Merge

**Target Files:**
- `scripts/pgn_manifest.py` (NEW)
- `tests/test_pgn_manifest_external_merge.py` (NEW)

**Problem:** External chunk merge was lexicographic by path, breaking numeric and seeded-shuffle global ordering across chunks.

**Decision:** Implement Option A (smallest viable change): use a key-aware streaming merge with `heapq.merge(..., key=...)` while keeping temp-file format as plain path lines.

**Consultation (Gold Template, lite):**
- Problem: Fix external merge to respect numeric/shuffle key.
- Options: A) add merge key; B) decorate temp files with key+path; C) de-support external.
- Choice: A for minimality and correctness. Partner responses pending; user approved Option A to unblock ingestion determinism. Full transcript to be appended upon receipt.

**Implementation (scripted):**
1) Branch: `git checkout -b feature/pgn-manifest-dsu`
2) Add script and tests via atomic patch application.
3) Run focused test and full suite: functional pass; overall suite green.

**Anchors and Key Diff (scripts/pgn_manifest.py):**
- Lines 102–109 (keyed merge):
```
105:        iters = ((line.rstrip("\n") for line in fh) for fh in files)
106:        merged = heapq.merge(*iters, key=key_path)
107:        with open(out_path, "w", encoding="utf-8") as out:
108:            for line in merged:
109:                out.write(line + "\n")
```
- Numeric padded key (lines 19–26) and shuffle 64-bit key (lines 36–42).

**Automated Diffs (summaries):**
- Added `scripts/pgn_manifest.py` (182 LOC)
- Added `tests/test_pgn_manifest_external_merge.py` (54 LOC)

**Validation:**
- Focused tests: numeric external merge produces `[game1, game2, game10, game20]`; shuffle is deterministic for same seed and differs for different seeds.
- Full test suite: PASS; coverage 65.56% (≥64 fail-under).

**Rollback Commands:**
```bash
# Remove newly added files (no other files touched)
rm -f scripts/pgn_manifest.py tests/test_pgn_manifest_external_merge.py

# Or discard uncommitted changes entirely
git restore --staged --worktree scripts/pgn_manifest.py tests/test_pgn_manifest_external_merge.py || true
git clean -f scripts/ tests/test_pgn_manifest_external_merge.py || true
```

**Impact & Risks:**
- Deterministic, scale-safe manifests for ETL; negligible CPU overhead for key recomputation during merge; no changes to analyzers/IDF/EVS/ETL interfaces.

**Status:** COMPLETED
## 2025-09-13 — Restore spotchecks & add DSU PGN manifest
**Branch:** feature/pgn-manifest-dsu  
**Commit:** e1f5d21  
**Changes:**
- Makefile: drop stale flags (`--mode production`, `--diagnostic`) on spotcheck targets.
- ci/baselines/spotcheck_production.json: update to current output shape (bare array).
- scripts/pgn_manifest.py: NEW — mode-aware DSU external merge (numeric/shuffle), bounded memory, lazy-key merge.
- tests/test_pgn_manifest_external_merge.py: NEW — multi-chunk numeric + deterministic shuffle test.

**Why:** Unblock prod spotchecks/evals; stabilize manifests for reproducible ETL/EVS runs.

**Validation:**
- `pytest -q` → PASS, coverage 65.56% (≥64).
- `make spotcheck-prod` → PASS.
- `make check-prod` → PASS, diff clean.

**Partner input (cold):**
- Gemini → Track B (add timings + 2 assertions).
- Claude/Grok/Perplexity → Track A (ship now).
**Decision:** Track A (3–1). Timings/assertions can follow if needed.

**Rollback:**
- Revert code/data change commit: `git revert e1f5d21`
- Or restore files individually:
  - `git checkout HEAD~1 -- Makefile ci/baselines/spotcheck_production.json`
  - `git rm -f scripts/pgn_manifest.py tests/test_pgn_manifest_external_merge.py && git commit -m "revert: remove manifest tool + test"`
