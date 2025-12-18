# AI Partner Synthesis & Action Plan
**Date:** November 10, 2025
**Contributors:** Gemini, Grok, ChatGPT
**Problem:** All 3 fixes failing - GPT placeholders, featured diagrams, 0/10 filter

---

## 🎯 Consensus: Root Cause

**All 3 AIs agree:** This is a **code caching/loading cascade failure**, not three separate bugs.

### The Smoking Gun (Gemini)
`synthesis_pipeline.py` is an imported module. Flask's auto-reloader doesn't reliably reload imports. **Your server is running old code** despite file edits being saved.

### Why All 3 Failed (ChatGPT)
1. **GPT Placeholders:** Old prompt still has "MANDATORY DIAGRAM RULES"
2. **Featured Diagrams:** `epub_diagrams` dropped during result formatting (line not whitelisted)
3. **0/10 Filter:** Wrong execution order - filter runs BEFORE GPT reranking adds scores

---

## 📋 Action Plan (Execute in Order)

### Phase 1: Prove Code is Loading (15 minutes)

**Goal:** Verify Flask is running our edited code

#### Step 1.1: Clear Python Cache
```bash
# Delete all .pyc files
find /Users/leon/Downloads/python/chess-analysis-system -name "*.pyc" -delete
find /Users/leon/Downloads/python/chess-analysis-system -name "__pycache__" -type d -exec rm -r {} +
```

#### Step 1.2: Add Canary Prints (ChatGPT + Gemini)
**File: app.py** (top of file, after imports)
```python
import uuid, time

print("\n*** [CANARY] app.py VERSION: 6.1a-2025-11-10 LOADED ***\n")
```

**File: synthesis_pipeline.py** (top of file, after imports)
```python
print("\n*** [CANARY] synthesis_pipeline.py VERSION: 6.1a-2025-11-10 LOADED ***\n")
```

**File: synthesis_pipeline.py** (line 250, in stage2_expand_sections, before GPT call)
```python
print(f"[CANARY] Using system prompt: {system_prompt[:100]}...")
```

#### Step 1.3: Restart Flask with Reload Flag
```bash
# Kill old server
lsof -ti:5001 | xargs kill -9

	# Start with explicit reload
	export FLASK_ENV=development
	export OPENAI_API_KEY="sk-proj-YOUR_API_KEY_HERE"
	python app.py  # Or: flask run --reload -p 5001
	```

#### Step 1.4: Verify Canaries in Logs
**Must see:**
- `[CANARY] app.py VERSION: 6.1a-2025-11-10 LOADED`
- `[CANARY] synthesis_pipeline.py VERSION: 6.1a-2025-11-10 LOADED`
- On query: `[CANARY] Using system prompt: You are a chess expert...DO NOT include diagram markup`

**If canaries don't appear:** Wrong file path or process still cached. Reboot machine if needed.

---

### Phase 2: Fix Featured Diagrams (ChatGPT's Critical Insight)

**Problem:** `epub_diagrams` computed but dropped during result formatting

#### Step 2.1: Verify Keys Survive Formatting
**File: app.py** (wherever `formatted` is built, likely around line 460-480)

Find this pattern:
```python
formatted = {
    "id": result["id"],
    "collection": result.get("collection"),
    "title": result["payload"].get("title"),
    # ... other fields ...
}
```

**Add epub_diagrams to whitelist:**
```python
formatted = {
    "id": result["id"],
    "collection": result.get("collection"),
    "title": result["payload"].get("title"),
    "book_title": result["payload"].get("book_title"),
    "chunk_index": result["payload"].get("chunk_index"),
    "max_similarity": result.get("max_similarity", 0),
    "epub_diagrams": result.get("epub_diagrams", []),  # 👈 ADD THIS
    # ... other fields ...
}
```

#### Step 2.2: Add Debug Logging (Grok)
**File: app.py** (lines 550-558, in featured diagrams collection)
```python
# Collect featured diagrams from top 3 EPUB sources for prominent display
featured_diagrams = []
print(f"[DEBUG] Checking {len(final_results)} results for featured diagrams")
for i, result in enumerate(final_results[:3]):
    print(f"[DEBUG] Result {i}: keys={list(result.keys())}, has_epub_diagrams={('epub_diagrams' in result)}, count={len(result.get('epub_diagrams', []))}")
    if result.get('epub_diagrams'):
        print(f"[DEBUG] Found {len(result['epub_diagrams'])} diagrams, adding 2")
        featured_diagrams.extend(result['epub_diagrams'][:2])
    else:
        print(f"[DEBUG] No epub_diagrams for result {i}")

featured_diagrams = featured_diagrams[:6]
print(f"📷 Featured diagrams for display: {len(featured_diagrams)}")
```

#### Step 2.3: Test with cURL
```bash
curl -s http://localhost:5001/query_merged \
  -H "Content-Type: application/json" \
  -d '{"query":"Caro-Kann main plans","top_k":5}' | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'featured_diagrams: {len(d.get(\"featured_diagrams\",[]))}'); print(d.get('featured_diagrams',[])[0] if d.get('featured_diagrams') else 'EMPTY')"
```

**Expected:** `featured_diagrams: 4` (or similar), with URL like `/diagrams/book_xxx/image_1.png`

---

### Phase 3: Fix 0/10 Relevance Filter (Gemini's Insight)

**Problem:** Filter at line 471 runs BEFORE GPT-5 reranking adds max_similarity scores

#### Step 3.1: Find Where GPT Reranking Happens
**Search for:** `gpt_rerank` or `max_similarity` assignment in app.py

The flow should be:
1. Qdrant returns top 100
2. **GPT-5 reranks to top 30** ← max_similarity added here
3. **Your filter** ← needs to be AFTER step 2

#### Step 3.2: Move Filter to Correct Location
**Find the GPT reranking code block** (likely around line 400-450), which should look like:
```python
# GPT-5 reranking
reranked_results = rerank_with_gpt(results, query)
# Now reranked_results has max_similarity scores
```

**Add filter AFTER reranking:**
```python
# After GPT reranking adds max_similarity
reranked_results = [r for r in reranked_results if float(r.get('max_similarity', 0)) > 0]
print(f"[DEBUG] After 0/10 filter: {len(reranked_results)} results (removed {original_count - len(reranked_results)} irrelevant)")
```

---

### Phase 4: Fix GPT Placeholders (All 3 AIs)

#### Option A: Strengthen Prompt (Gemini)
**File: synthesis_pipeline.py** (line 187)

Replace:
```python
- DO NOT include diagram markup - diagrams will be provided separately from source materials
```

With:
```python
- CRITICAL: You MUST NOT, under any circumstances, write the text string "[DIAGRAM:" anywhere in your response. All chess diagrams will be provided separately via images. Writing [DIAGRAM: ...] will break the system.
```

#### Option B: Post-Process Strip (Grok + ChatGPT - Pragmatic Fallback)
**File: synthesis_pipeline.py** (line 333, in stage3_final_assembly, after GPT returns)

```python
response = openai_client.chat.completions.create(...)
final_answer = response.choices[0].message.content

# Strip any residual diagram markers (fallback safety)
import re
final_answer = re.sub(r'\[DIAGRAM:[^\]]+\]', '', final_answer)

return final_answer
```

**Use Both:** Strengthen prompt AND add strip as safety net.

---

### Phase 5: Frontend Verification (ChatGPT)

#### Step 5.1: Add Console Logging
**File: templates/index.html** (in displayResults function, around line 650)

```javascript
function displayResults(data) {
    console.log("=== RESPONSE DEBUG ===");
    console.log("Request ID:", data.request_id);
    console.log("Featured diagrams count:", data.featured_diagrams?.length);
    console.log("First 2 diagrams:", data.featured_diagrams?.slice(0,2));
    console.log("Results count:", data.results?.length);
    console.log("======================");

    // ... rest of function
}
```

#### Step 5.2: Debug Endpoints (ChatGPT)
**File: app.py** (add these temporary endpoints)

```python
@app.route('/debug/featured-diagrams')
def debug_featured():
    """Test endpoint to verify diagram serving works"""
    # Pick first book with 6+ diagrams
    for book_id, diagrams in diagram_service.by_book.items():
        if len(diagrams) >= 6:
            return jsonify({
                "book_id": book_id,
                "featured_diagrams": [
                    {
                        "id": d["diagram_id"],
                        "url": f"/diagrams/{d['book_id']}/{d['filename']}",
                        "caption": d.get("context_before", "")[:100]
                    }
                    for d in diagrams[:6]
                ]
            })
    return jsonify({"featured_diagrams": []})

@app.route('/debug/prompt-check')
def debug_prompt():
    """Verify which prompt is being used"""
    from synthesis_pipeline import stage2_expand_sections
    import inspect
    source = inspect.getsource(stage2_expand_sections)
    # Extract system_prompt variable
    has_diagram_rules = "MANDATORY DIAGRAM RULES" in source
    has_do_not = "DO NOT include diagram markup" in source
    return jsonify({
        "has_old_rules": has_diagram_rules,
        "has_new_instruction": has_do_not,
        "prompt_head": source[source.find("system_prompt"):source.find("system_prompt")+300]
    })
```

Test:
```bash
curl http://localhost:5001/debug/featured-diagrams | jq '.featured_diagrams | length'
curl http://localhost:5001/debug/prompt-check | jq '.has_new_instruction'
```

---

## 🧪 Testing Protocol (After Each Phase)

### Quick Test Script
```bash
# Test all 3 fixes at once
curl -s http://localhost:5001/query_merged \
  -H "Content-Type: application/json" \
  -d '{"query":"Tell me about the Caro-Kann Defense","top_k":5}' | \
python3 -c "
import sys, json, re

data = json.load(sys.stdin)
answer = data.get('answer', '')
featured = data.get('featured_diagrams', [])
results = data.get('results', [])

# Test 1: No placeholders
markers = re.findall(r'\[DIAGRAM:.*?\]', answer)
print(f'Test 1 (No placeholders): {\"✅ PASS\" if len(markers)==0 else \"❌ FAIL\"} ({len(markers)} found)')

# Test 2: Featured diagrams
print(f'Test 2 (Featured diagrams): {\"✅ PASS\" if len(featured)>0 else \"❌ FAIL\"} ({len(featured)} diagrams)')

# Test 3: No 0/10 sources
zeros = [r for r in results if float(r.get('max_similarity',1))==0]
print(f'Test 3 (No 0/10 sources): {\"✅ PASS\" if len(zeros)==0 else \"❌ FAIL\"} ({len(zeros)} found)')

print(f'\nOVERALL: {\"✅ ALL PASSED\" if len(markers)==0 and len(featured)>0 and len(zeros)==0 else \"❌ SOME FAILED\"}')
"
```

### Browser Test Checklist
1. Open http://localhost:5001 in browser
2. Open DevTools (F12) → Console tab
3. Search "Caro-Kann Defense"
4. Verify console shows:
   - `Featured diagrams count: 4` (or similar)
   - `First 2 diagrams: [{url: "/diagrams/...", ...}, ...]`
5. Check Network tab → Img filter:
   - Should see GETs to `/diagrams/book_xxx/image_N.png`
   - All return 200 OK with image/png MIME type
6. Verify images visible above "View Sources" section

---

## 🚨 If Still Failing

### Fallback: Incremental Rollback (Grok)
1. Revert ALL changes with git
2. Verify baseline behavior (placeholders present, no featured, irrelevants shown)
3. Apply ONE fix at a time
4. Test after each
5. Only proceed to next fix if current one passes

### Last Resort: Request ID Tracing (ChatGPT)
Add this at the START of `/query_merged` handler:

```python
req_id = str(uuid.uuid4())[:8]
t0 = time.time()
log = lambda msg: print(f"[{req_id} +{(time.time()-t0):.3f}s] {msg}")
log("Query started")
# ... use log() throughout instead of print()
```

Then grep server logs for one `req_id` to trace entire flow.

---

## 📊 Success Criteria

**Phase 1:** See all 3 canary prints in server logs
**Phase 2:** cURL shows `featured_diagrams: N` where N > 0
**Phase 3:** cURL shows 0 results with `max_similarity: 0`
**Phase 4:** cURL answer has 0 `[DIAGRAM:` strings
**Phase 5:** Browser console shows featured diagrams, Network tab shows image GETs, images visible on page

**Final:** All 3 tests pass in test script, browser shows diagrams prominently

---

## 💡 Key Takeaways

1. **Code Caching:** Flask doesn't reliably reload imports - always clear `__pycache__` and use canary prints
2. **Data Flow:** Keys get dropped during formatting - must whitelist `epub_diagrams` in `formatted` dict
3. **Execution Order:** Filters must run AFTER operations that create the data they filter
4. **End-to-End Testing:** Test backend (cURL) AND frontend (console/network) separately to isolate issues
5. **Defense in Depth:** Use both prompt engineering AND post-processing for critical requirements

---

**Next Steps:** Execute Phase 1 first. Only proceed to Phase 2 after seeing all canaries.
