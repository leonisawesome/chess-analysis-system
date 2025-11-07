# PGN Game Collection Chunking Strategy - Expert Consultation

## Context
I'm building a chess RAG (Retrieval-Augmented Generation) system with 358K chunks from 1,134 chess books (EPUB/MOBI). Now adding 1M+ PGN games from Chessable, ChessBase, Modern Chess, and other publishers.

**Current System:**
- Vector DB: Qdrant (Docker, 358K chunks)
- Embedding: OpenAI text-embedding-3-small (1536 dims)
- Corpus: Instructional chess books with high educational value
- Use case: Answer chess questions with synthesized responses + diagrams

## The Challenge
How should I chunk 1M+ PGN games for optimal RAG retrieval?

## Question 1: Chunking Strategy

**Which approach would work best for RAG retrieval?**

**Option A: One Game = One Chunk**
```
Chunk contains: Full PGN game (headers + all moves + annotations)
Size: ~500-2000 tokens per chunk
Example chunk:
  [Event "World Championship"]
  [White "Carlsen"]
  [Black "Nakamura"]
  [ECO "B90"]
  [Opening "Najdorf Sicilian"]
  1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6...
  {Full game with all moves and annotations}
```

**Option B: Game + Rich Metadata Chunk**
```
Chunk contains: Metadata summary + key moments + full game
Size: ~800-2500 tokens per chunk
Example chunk:
  Game: Magnus Carlsen (2863) vs Hikaru Nakamura (2789)
  Opening: Najdorf Sicilian, Poisoned Pawn (B97)
  Event: World Championship 2023, Round 5
  Result: 1-0 (White wins)
  Critical Moment: Move 23. Bxh7+ - Spectacular bishop sacrifice
  Endgame Type: Rook + 3 pawns vs Rook + 2 pawns

  {Full PGN with annotations}
```

**Option C: Split by Phase**
```
Chunk 1 (Opening): Moves 1-15 + opening annotations
Chunk 2 (Middlegame): Moves 16-35 + tactical commentary
Chunk 3 (Endgame): Moves 36-end + endgame technique notes
Each chunk: ~400-800 tokens
Links: All chunks reference same game_id
```

**Option D: Critical Positions Only**
```
Extract key moments: Opening novelty, tactical blow, endgame technique
Chunk contains: Position FEN + context + annotation
Size: ~200-500 tokens per position
Example chunk:
  Game: Carlsen vs Nakamura (2023)
  Position: After 23. Bxh7+ (Critical sacrifice)
  FEN: r1bq1rk1/ppp2Npp/3p1n2/4p3/2BnP3/2N5/PPP2PPP/R1BQK2R
  Annotation: "Spectacular positional sacrifice. White trades the
  bishop pair for a lasting initiative and weak dark squares..."
  Continuation: 23...Kxh7 24. Ng5+ Kg8 25. Qh5...
```

**Which option would:**
- Give best retrieval for queries like "Carlsen Najdorf games"?
- Give best retrieval for "Rook endgame technique"?
- Give best retrieval for "Typical Sicilian middlegame plans"?
- Scale well to 1M+ games (cost vs quality tradeoff)?

---

## Question 2: Quality Filtering

**With 1M games from various sources, what filtering strategy?**

Should I:
1. **Include all games** (democratic approach, full coverage)
2. **Master games only** (2200+ rating, higher quality)
3. **Annotated games priority** (instructional value)
4. **Blitz/bullet exclusion** (quality games only)
5. **Deduplication strategy** (same game from multiple sources)

**Considerations:**
- Annotated games: ~10% of collection, highest educational value
- Master games: ~40% of collection, quality play
- Amateur games: May show common mistakes (pedagogical value?)
- Duplicates: Same game from ChessBase + Chessable + Modern Chess

---

## Question 3: Metadata Design

**What metadata should be embedded in the chunk text for better retrieval?**

Should each chunk include:
- [ ] Player names + ratings (searchable by player)
- [ ] ECO code + opening name (searchable by opening)
- [ ] Event, date, location (historical context)
- [ ] Result (1-0, 0-1, ½-½)
- [ ] Time control (classical, rapid, blitz)
- [ ] Game phase tags (opening, middlegame, endgame)
- [ ] Tactical themes (sacrifice, pin, fork, zugzwang)
- [ ] Strategic themes (space advantage, weak squares, pawn structure)
- [ ] Source (Chessable/ChessBase/Modern Chess)

**Tradeoff:** More metadata = better filtering but uses token budget

---

## Question 4: Variations Handling

**How to handle game variations (alternative lines in annotations)?**

```
Example PGN with variations:
23. Bxh7+ Kxh7 24. Ng5+ Kg8
  (24...Kg6?? 25. Qd3+ f5 26. exf6+ Kxf6 27. Qh3 wins)
25. Qh5 Re8 26. Qxf7+ Kh8 27. Qh5+ Kg8 ½-½
```

**Options:**
- Include all variations in the same chunk (preserves context)
- Extract main line only (simpler, cleaner)
- Create separate chunks for deep variations (more granular)

---

## Question 5: Use Case Priority

**Rank these use cases by importance (1-5):**

- [ ] Find games by specific players ("Magnus Carlsen Najdorf games")
- [ ] Learn opening theory ("How to play the Poisoned Pawn Najdorf")
- [ ] Study endgame technique ("Rook + 3 pawns vs Rook + 2 pawns")
- [ ] Understand middlegame plans ("Typical King's Indian attacks")
- [ ] See tactical patterns ("Knight sacrifice on f7")

**Question:** Should chunking strategy optimize for all equally, or prioritize certain queries?

---

## Question 6: Cost vs Quality

**Scale considerations:**

- Current corpus: 358K chunks (books)
- Adding 1M games with different strategies:
  - Option A (1 game = 1 chunk): +1M chunks (~$5 embedding cost)
  - Option B (game + metadata): +1M chunks (~$6 embedding cost)
  - Option C (3 chunks per game): +3M chunks (~$15 embedding cost)
  - Option D (5 positions per game): +5M chunks (~$25 embedding cost)

Storage:
- Current Qdrant: 358K chunks (5.5GB)
- +1M chunks: ~15GB additional
- +3M chunks: ~45GB additional

**Question:** What's the sweet spot for cost vs retrieval quality?

---

## Your Recommendation

Please provide:
1. **Preferred chunking strategy** (A, B, C, D, or hybrid)
2. **Reasoning** (why this approach for chess RAG)
3. **Quality filtering recommendation**
4. **Metadata priority** (what to include/exclude)
5. **Variations handling approach**
6. **Any concerns or edge cases** I should consider

Thank you for your expertise!
