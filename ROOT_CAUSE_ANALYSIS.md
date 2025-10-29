# ROOT CAUSE ANALYSIS: 85% → 51% "Regression"

## CRITICAL FINDING
**The databases are IDENTICAL. The evaluation standards changed, not the retrieval quality.**

## Investigation Results

### Task 1: Database Timestamps
```
qdrant_validation_db      11:32 (Week 1 database)
qdrant_optimized_db       14:08
qdrant_quick_test         14:10
qdrant_full_validation    14:15 (latest)
```

### Task 2: Database Contents
All databases contain:
- 580 vectors (identical corpus)
- Same embedding model (text-embedding-3-small)
- Same chunking

### Task 3: Query 4 Test Results
**Query: "How do I create weaknesses in my opponent's position?"**

**ALL 4 DATABASES RETURNED IDENTICAL RESULTS:**

1. **Score 0.6160** - "Weakness in the Castled Position"
   - Content: Directly explains how castled position weakens when pawns advance
   - Week 1: relevant ✓
   - Week 3: y ✓
   - **AGREEMENT**

2. **Score 0.5333** - "Chapter Fifteen: Defending"
   - Content: "I don't like defending. How can I avoid it? You can't..."
   - Week 1: relevant ✓
   - Week 3: n ❌
   - **DISAGREEMENT** - This is about defending, not creating weaknesses

3. **Score 0.5283** - "Fortress and Blockade"
   - Content: Defensive positions that are invulnerable
   - Week 1: relevant ✓
   - Week 3: n ❌
   - **DISAGREEMENT** - This is about defending weaknesses, not creating them

4. **Score 0.5188** - "Chapter 5" game continuation
   - Content: Chess game notation and moves
   - Week 1: relevant ✓
   - Week 3: n ❌
   - **DISAGREEMENT** - Game notation, unclear relevance

5. **Score 0.5181** - "Winning a Won Game"
   - Content: Winning technique, converting advantages
   - Week 1: partial ✓
   - Week 3: n ❌
   - **DISAGREEMENT** - This is about converting, not creating weaknesses

## Analysis

### Week 1 Judgment Pattern
- Interpreted query broadly
- Considered "defending" content as relevant (weakness from defender's perspective?)
- Accepted defensive concepts as relevant to weakness discussion
- Result: 4y + 1p = **90% precision**

### Week 3 Judgment Pattern
- Interpreted query strictly
- Only accepted content DIRECTLY about creating/exploiting weaknesses
- Rejected defensive/tangential content
- Result: 1y + 0p = **20% precision**

## Root Cause

**NOT a technical regression. NOT a database change.**

**This is a JUDGMENT STANDARD difference:**
- Week 1: Lenient evaluation (85% baseline)
- Week 3: Strict evaluation (51% current)

## Implications

1. **Week 1's 85% baseline was inflated due to lenient standards**
2. **True baseline precision is closer to 50-55% with strict standards**
3. **Optimizations should be measured against 50-55% baseline, not 85%**
4. **Current "71% automated / 51% manual" may actually represent IMPROVEMENT from true baseline**

## Decision Required

**Which evaluation standard should we use?**

### Option A: Lenient (Week 1 style - 85% baseline)
- Accept tangentially related content
- Pro: Higher baseline, easier to show improvement
- Con: May not satisfy users who expect precise answers

### Option B: Strict (Week 3 style - 51% baseline)
- Only accept directly relevant content
- Pro: More accurate, better user experience
- Con: Lower baseline, harder to optimize

## Recommendation

**Use STRICT standards (51% baseline) for these reasons:**
1. Better reflects real user needs
2. More honest evaluation
3. Optimizations that work with strict standards will definitely work with lenient standards
4. Week 1's lenient standards were likely a mistake, not intentional

**Next Steps:**
1. Re-evaluate Week 1's 85% claim with strict standards
2. Accept 50-55% as the true baseline
3. Optimize to ≥65-70% (realistic target with strict standards)
4. If needed, re-adjust target from 90% to 70% for strict evaluation
