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
