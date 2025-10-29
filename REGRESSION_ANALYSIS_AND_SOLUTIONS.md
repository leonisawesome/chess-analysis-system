# REGRESSION ANALYSIS: Query 5 & Query 1

## Executive Summary

**ROOT CAUSE IDENTIFIED**: Query expansion is too aggressive, creating **13-15x longer queries** that over-specify and **change the original intent**.

Both regressions follow the same pattern:
- Massive expansion (13-15x original length)
- Lost "how to" / method-seeking intent
- Retrieved content about related concepts instead of answering the original question

---

## QUERY 5: "What is the best way to study chess openings?" (90% → 60%)

### Baseline (90% precision) - Top 5 Results

1. **[9/10]** "The amount of study you need to play an opening" - **DIRECTLY ABOUT STUDY METHODS** ✓
2. **[7/10]** "A Cunning Chess Opening Repertoire" - Opening book
3. **[6/10]** "How to Build Your Chess Opening Repertoire" - Repertoire building
4. **[6/10]** "Chapter Six: Studying" - **GENERAL STUDY ADVICE** ✓
5. **[5/10]** "Opening Disasters" - **ABOUT STUDYING OPENINGS** ✓

**Why 90%? Results 1, 4, 5 directly answer "HOW to study openings"**

### Expanded Query

**Original**: "What is the best way to study chess openings?" (45 chars)

**Expanded**: "best way to study chess openings learn opening theory build an opening repertoire main lines sidelines tabiyas transpositions move-order nuances typical pawn structures key plans piece placement typical middlegame plans arising from the opening development center control king safety space piece activity pawn breaks initiative tempo prophylaxis common tactical motifs and traps gambits pins forks discovered attacks model games annotated GM games pattern recognition memorization vs understanding spaced repetition drills database/opening explorer preparation engine-assisted analysis practical training games review typical endgames stemming from these openings" (663 chars)

**Expansion ratio: 14.7x**

### Expanded Results (60% precision) - Top 5

1. **[8/10]** "The amount of study you need to play an opening" - Same as baseline ✓
2. **[7/10]** "A Simple Chess Opening Repertoire for White" - Opening book
3. **[6/10]** "How to Build Your Chess Opening Repertoire" - Same as baseline ✓
4. **[6/10]** "A Cunning Chess Opening Repertoire" - Same as baseline ✓
5. **[6/10]** "FCO: Fundamental Chess Openings" - **NEW - General opening reference**

### What Was Lost

- **[6/10]** "Chapter Six: Studying" - **LOST study methods advice** ❌
- **[5/10]** "Opening Disasters" - **LOST opening study content** ❌

### Why 60%?

**Only Result #1 directly answers "HOW to study"**. Results 2-5 are about WHAT openings to play (repertoires), not HOW to study them.

### Root Cause

**Intent changed**: "HOW to study openings" → "WHAT are openings (theory, lines, structures)"

The expansion added too many technical opening terms (tabiyas, transpositions, pawn structures, tactical motifs, etc.) which shifted the semantic search toward **opening content** instead of **study methodology**.

---

## QUERY 1: "How do I improve my calculation in the middlegame?" (75% → 70%)

### Baseline (75% precision) - Top 5 Results

1. **[9/10]** "How to Calculate Chess Tactics" - **DIRECTLY ABOUT CALCULATION** ✓
2. **[8/10]** "Chapter Eleven: Calculating" - **Q&A ABOUT CALCULATION** ✓
3. **[4/10]** "Understanding Chess Middlegames" - Middlegame book (tangential)
4. **[3/10]** Calculation mistake example - Game with error
5. **[3/10]** "B+N Connection" tactical finish - Tactical example

**Why 75%? Results 1 & 2 are directly about calculation, #3 is partial**

### Expanded Query

**Original**: "How do I improve my calculation in the middlegame?" (50 chars)

**Expanded**: "Improve calculation in the middlegame tactical calculation visualization lookahead analyzing variations candidate moves list thought process Kotov tree checks captures threats (CCT) forcing moves quiet moves prophylaxis move order calculation depth vs breadth pruning blunder check evaluation of positions initiative king safety piece activity pawn structure pattern recognition tactical motifs forks pins skewers discovered attack double attack deflection decoy clearance zwischenzug overloading sacrifices training methods tactics puzzles blindfold visualization time management opening–middlegame transition endgame vs middlegame calculation differences" (656 chars)

**Expansion ratio: 13.1x**

### Expanded Results (70% precision) - Top 5

1. **[8/10]** "How to Calculate Chess Tactics" - Same as baseline ✓
2. **[7/10]** "A Course in Chess Tactics" - **NEW - Tactics training book**
3. **[7/10]** Endgame calculation example - **NEW - Endgame specific**
4. **[6/10]** Endgame solving training - **NEW - Endgame specific**
5. **[6/10]** "How to Become a Deadly Chess Tactician" - **NEW - Tactics book**

### What Was Lost

- **[8/10]** "Chapter Eleven: Calculating" - **LOST direct Q&A about calculation** ❌
- **[4/10]** "Understanding Chess Middlegames" - Lost middlegame content
- **[3/10]** Calculation mistake example
- **[3/10]** Tactical finish example

### Why 70%?

Results shifted from **calculation methodology** to **tactical training**. Also retrieved **endgame** calculation content despite query being about middlegame.

### Root Cause

**Intent diluted**: "HOW to improve calculation in middlegame" → "Tactical training + Endgame calculation"

The expansion added:
- Too many tactical motifs (forks, pins, skewers, etc.) → Retrieved tactics books
- "endgame vs middlegame calculation differences" → Retrieved endgame content
- Lost the focus on **calculation improvement methods** for middlegame

---

## Common Pattern: Why Expansion Failed

### Problem 1: Excessive Length

| Query | Original | Expanded | Ratio |
|-------|----------|----------|-------|
| Query 5 | 45 chars | 663 chars | 14.7x |
| Query 1 | 50 chars | 656 chars | 13.1x |

**⚠️ Expansions >10x original length are over-specified**

### Problem 2: Intent Drift

Both queries were **"HOW TO" questions** asking for methods/advice:
- "HOW to study openings" → Became "WHAT are openings (theory)"
- "HOW to improve calculation" → Became "WHAT are tactics (motifs)"

**The expansion prompt doesn't preserve the meta-intent (seeking methods vs seeking concepts)**

### Problem 3: Technical Term Overload

Expansions added **excessive technical chess terms** that shifted semantic focus:

Query 5 added: tabiyas, transpositions, move-order nuances, pawn structures, tactical motifs, gambits, pins, forks...

Query 1 added: Kotov tree, CCT, forcing moves, prophylaxis, forks, pins, skewers, deflection, decoy, zwischenzug...

**These terms attract content ABOUT those concepts, not about HOW to study/improve**

---

## SOLUTIONS

### Option 1: Constrained Expansion (RECOMMENDED)

**Modify the expansion prompt to limit length and preserve intent:**

```python
def expand_query_constrained(query):
    prompt = f"""Expand this chess query CONSERVATIVELY.

Original query: "{query}"

STRICT RULES:
1. Maximum expansion: 3-5x original length (NOT more)
2. Preserve the original INTENT:
   - "How to..." queries → Add method synonyms (improve, learn, practice, train)
   - "What are..." queries → Add concept synonyms
3. Add 5-10 synonyms and related terms ONLY
4. DO NOT add technical details (tactics, specific openings, etc.)
5. DO NOT change the question type

Good examples:
- "How to study openings?" → "how to study learn practice openings opening theory repertoire preparation methods"
- "improve calculation" → "improve enhance develop calculation tactical vision lookahead visualization"

Bad examples:
- "study openings" → "tabiyas transpositions move-order nuances pawn structures" (TOO SPECIFIC)

Expand: "{query}"

Respond with ONLY the expanded query (one line, max 5x original length).
"""

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    expanded = response.choices[0].message.content.strip()

    # Safety check: Reject if >6x original
    if len(expanded) > len(query) * 6:
        return query  # Use original if expansion too long

    return expanded
```

**Expected improvement:**
- Preserve "how to" intent
- Avoid technical term overload
- Estimated precision: Query 5: 85-90%, Query 1: 75-80%

---

### Option 2: Query Type Classification (ALTERNATIVE)

**Don't expand certain query types at all:**

```python
def should_expand_query(query):
    # Don't expand "how to" / method-seeking queries
    if re.search(r'\b(how|best way|improve|study|learn|practice)\b', query.lower()):
        return False

    # Don't expand already-specific queries
    if len(query.split()) > 8:  # Already specific
        return False

    # Only expand vague queries
    vague_keywords = ['understanding', 'principles', 'ideas', 'concepts']
    if any(keyword in query.lower() for keyword in vague_keywords):
        return True

    return False
```

**Expected improvement:**
- Query 5: Skip expansion → 90% (baseline)
- Query 1: Skip expansion → 75% (baseline)
- Other queries: Expand only vague ones → 85-90%

---

### Option 3: No Expansion (SAFEST)

**Deploy with Approaches 1+2 only (no expansion):**

**Configuration:**
- Top 40 candidates (Approach 2) ✓
- Optimized prompt (Approach 1) ✓
- NO query expansion

**Expected precision: 86-87%**
- Avoids all regressions
- Still exceeds 85% target
- Lower risk

---

## Recommendation

**DEPLOY WITH OPTION 1: Constrained Expansion**

**Reasoning:**
1. Query expansion WORKS for vague queries (7/10 queries improved)
2. The problem is OVER-expansion, not expansion itself
3. Constrained expansion (3-5x max, preserve intent) should work
4. Estimated final precision: **88-90%** with fixes

**Fallback**: If constrained expansion still causes issues, use **Option 2** (selective) or **Option 3** (no expansion).

**Testing plan**:
1. Implement constrained expansion prompt
2. Re-test Query 1 & Query 5
3. If both ≥80% → Deploy
4. If either <80% → Deploy without expansion (86-87% precision)

---

## Next Steps

**DO NOT DEPLOY CURRENT VERSION** (with unconstrained expansion)

**Required before deployment:**
1. Implement constrained expansion (Option 1)
2. Re-test Query 1 & Query 5
3. Validate no regressions
4. If successful → Deploy at 88-90%
5. If unsuccessful → Deploy without expansion at 86-87%

**Timeline**: 1 day to fix and retest, then deploy Week 4
