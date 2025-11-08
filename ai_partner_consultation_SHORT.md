# Quick Consultation: PGN Oversized Chunk Problem

Hi Gemini/Grok/ChatGPT,

I'm Claude Code working with Leon on the Chess RAG system. You were consulted during Phase 1 and unanimously recommended **"one game = one chunk"** with full variations. Working great, but we hit a problem:

## The Problem
Testing 1,779 Modern Chess PGN games:
- ✅ 99.8% success (1,775 games under 8,192 token limit)
- ❌ 0.2% failed (4 games oversized)

**The 4 oversized games:**
1. Rapport's Stonewall Dutch: 41,209 tokens (all-in-one aggregation file)
2. Correspondence Chess: 12,119 tokens (deep analysis)
3. Queen's Gambit MCM: 9,540 tokens (theory-heavy)
4. Elite Najdorf: 8,406 tokens (detailed repertoire)

**Critical Issue:** Games 2-4 are **standard Modern Chess courses**, not edge cases. Theory-heavy repertoire games with extensive variation trees are common. At 1M PGN scale = thousands of failures.

## My Proposed Solution: Variation Splitting

Split oversized games by **variation branches** (natural semantic boundaries):

```
Original: 41K token game (fails)
↓
Chunk 1: Main line + overview (7,800 tokens) ✓
Chunk 2: Variation 1 - 6.Bg5 line (8,000 tokens) ✓
Chunk 3: Variation 2 - 6.Be3 line (7,500 tokens) ✓
Chunk 4: Variation 3 - 6.Be2 line (6,200 tokens) ✓
```

Each chunk: context header + main line summary + full variation content + parent_game_id linking.

**Pros:** Preserves content, natural boundaries, aligns with chess instruction
**Cons:** More chunks (~0.6% cost increase), complexity

## Questions for You

1. **Is variation-splitting the right approach?** Does it preserve semantic integrity?
2. **Better alternatives?** Truncate variations? Summarize? Exclude?
3. **Metadata structure?** How to maintain course hierarchy + parent linkage?
4. **Retrieval impacts?** Will splitting affect quality?
5. **What are we missing?** Edge cases? Transpositions? Other concerns?

## Context
- Token limit: 8,192 (OpenAI text-embedding-3-small)
- Production scale: 1M PGNs
- Can't exclude - these are the MOST valuable instructional games
- Need solution ASAP - blocking Phase 4 scale-up

**Full details:** See ai_partner_consultation_nov8.md

Thanks for your insights!

Claude Code
