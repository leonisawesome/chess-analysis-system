# Session 2025-11-10: Static Diagram Troubleshooting

## Problem Statement
All 3 diagram fixes failed simultaneously:
- ❌ GPT-5 still writing `[DIAGRAM: ...]` placeholders (6 found)
- ❌ Featured diagrams empty (0 returned)
- ❌ 0/10 relevance sources still appearing (10 found)

## Root Cause Analysis

### Partner Consult Results
Consulted with 3 AI systems (Gemini, Grok, ChatGPT) who unanimously agreed:

**PRIMARY CAUSE: Code caching cascade failure**
- Flask doesn't reliably reload imported modules (`synthesis_pipeline.py`)
- Our code edits were saved but never executed
- All 3 fixes failed because server was running stale code

### Secondary Issues Identified
1. **Featured diagrams:** `epub_diagrams` likely dropped during result formatting (not whitelisted in `formatted` dict)
2. **0/10 filter:** Wrong execution order - filter runs BEFORE GPT reranking adds scores
3. **GPT placeholders:** Prompt changes not strong enough or using wrong prompt path

## Actions Taken This Session

### Phase 1: Verify Code Loading ✅ **COMPLETED**

**Step 1.1:** Cleared Python cache
```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

**Step 1.2:** Added canary prints
- **app.py line 33:** `print("\n*** [CANARY] app.py VERSION: 6.1a-2025-11-10 LOADED ***\n")`
- **synthesis_pipeline.py line 15:** `print("\n*** [CANARY] synthesis_pipeline.py VERSION: 6.1a-2025-11-10 LOADED ***\n")`
- **Purpose:** Verify modules actually load at runtime

**Step 1.3:** Restarted Flask with clean environment
```bash
source .venv/bin/activate
export FLASK_ENV=development
export OPENAI_API_KEY="sk-proj-..."
python app.py > flask_canary_test.log 2>&1 &
```

**Step 1.4:** Verified canaries in logs ✅
```
*** [CANARY] synthesis_pipeline.py VERSION: 6.1a-2025-11-10 LOADED ***
*** [CANARY] app.py VERSION: 6.1a-2025-11-10 LOADED ***
Initializing clients...
```

**Result:** Code loading confirmed. Proceeded to Phase 2.

## Next Steps (Phases 2-5)

### Phase 2: Fix Featured Diagrams
**Problem:** `epub_diagrams` computed but dropped during result formatting

**Solution:**
1. Find where `formatted` dict is built (app.py ~line 460-480)
2. Add `"epub_diagrams": result.get("epub_diagrams", [])` to whitelist
3. Add debug logging in collection loop (lines 550-558)
4. Test with cURL

**Expected:** `featured_diagrams: N` where N > 0

### Phase 3: Fix 0/10 Relevance Filter
**Problem:** Filter at line 471 runs BEFORE GPT reranking

**Solution:**
1. Find GPT reranking code block (~line 400-450)
2. Move filter AFTER reranking: `reranked_results = [r for r in reranked_results if float(r.get('max_similarity', 0)) > 0]`
3. Add debug logging

**Expected:** No results with `max_similarity: 0`

### Phase 4: Fix GPT Placeholders
**Solution A (Strengthen Prompt):**
Replace line 187 in synthesis_pipeline.py with:
```python
- CRITICAL: You MUST NOT, under any circumstances, write the text string "[DIAGRAM:" anywhere in your response.
```

**Solution B (Post-Process Strip - Fallback):**
Add after line 333 in synthesis_pipeline.py:
```python
import re
final_answer = re.sub(r'\[DIAGRAM:[^\]]+\]', '', final_answer)
```

**Expected:** 0 `[DIAGRAM:` strings in answer

### Phase 5: Frontend Verification
1. Add console logging in index.html
2. Add debug endpoints (`/debug/featured-diagrams`, `/debug/prompt-check`)
3. Test in browser with DevTools

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| app.py | 31-33 | Added uuid import + canary print |
| synthesis_pipeline.py | 15 | Added canary print |
| app.py | 470-472 | PREVIOUS: Added 0/10 filter (wrong location) |
| app.py | 550-558 | PREVIOUS: Added featured diagrams collection |
| synthesis_pipeline.py | 180-188 | PREVIOUS: Removed diagram prompt rules |
| templates/index.html | 665-684 | PREVIOUS: Added featured diagrams display |

## Key Documents Created

1. **PARTNER_CONSULT.txt** - Full problem description sent to 3 AI systems
2. **AI_SYNTHESIS_ACTION_PLAN.md** - Consolidated 5-phase debugging strategy
3. **This file** - Session progress tracking

## Testing Protocol

### Quick Test Command
```bash
curl -s http://localhost:5001/query_merged \
  -H "Content-Type: application/json" \
  -d '{"query":"Caro-Kann Defense","top_k":5}' | \
python3 -c "
import sys, json, re
data = json.load(sys.stdin)
markers = re.findall(r'\[DIAGRAM:.*?\]', data.get('answer', ''))
featured = data.get('featured_diagrams', [])
zeros = [r for r in data.get('results', []) if float(r.get('max_similarity',1))==0]
print(f'Test 1 (Placeholders): {\"✅\" if len(markers)==0 else \"❌\"} ({len(markers)} found)')
print(f'Test 2 (Featured): {\"✅\" if len(featured)>0 else \"❌\"} ({len(featured)} diagrams)')
print(f'Test 3 (0/10 filter): {\"✅\" if len(zeros)==0 else \"❌\"} ({len(zeros)} found)')
print(f'OVERALL: {\"✅ PASSED\" if len(markers)==0 and len(featured)>0 and len(zeros)==0 else \"❌ FAILED\"}')
"
```

### Success Criteria
- ✅ No `[DIAGRAM:` strings in answer
- ✅ `featured_diagrams` array with N > 0 items
- ✅ No results with `max_similarity: 0`
- ✅ Browser shows images in featured section
- ✅ Network tab shows successful `/diagrams/` GETs

## Lessons Learned

1. **Code Caching:** Always clear `__pycache__` and use canary prints when debugging module imports
2. **Partner Consults:** Multiple AI perspectives caught issues single AI missed (especially execution order bugs)
3. **Data Flow:** Keys can be dropped between processing stages - must whitelist explicitly
4. **Testing:** Backend (cURL) and frontend (browser) must be tested separately to isolate issues

## Status: Phase 1 Complete, Phases 2-5 Pending

**Next Claude Session Should:**
1. Start by verifying canaries still appear in fresh Flask restart
2. Execute Phase 2 (fix featured diagrams formatting)
3. Execute Phase 3 (move 0/10 filter to correct location)
4. Execute Phase 4 (strengthen prompt + add regex strip)
5. Execute Phase 5 (verify in browser with DevTools)
6. Run full test protocol
7. Update SESSION_NOTES, README, and CHANGELOG (the "Big 3")
8. Commit all changes to git

