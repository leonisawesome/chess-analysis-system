# Testing Strategy - PGN Variation Splitting
**Date:** November 8, 2025
**Feature:** PGN variation splitting for oversized chunks
**Branch:** `feature/pgn-variation-splitting`

---

## 🎯 Testing Philosophy

**Principle:** Test at every level before promoting to production.

**Layers:**
1. Unit tests (individual functions)
2. Integration tests (4 oversized files)
3. Corpus tests (1,779 games)
4. Production validation (isolated Qdrant collection)

**Safety:** No production data touched until all tests pass.

---

## 📋 Test Levels

### Level 1: Unit Tests (Functions)

**File:** `test_variation_splitter.py`

**Test Cases:**

#### 1.1 Token Counting
```python
def test_count_tokens():
    """Verify tiktoken counting matches OpenAI API"""
    sample_text = "1. e4 c5 2. Nf3 d6 {Najdorf}"
    tokens = count_tokens(sample_text)
    assert isinstance(tokens, int)
    assert tokens > 0
    assert tokens < 100  # Reasonable for short text
```

#### 1.2 Context Header Generation
```python
def test_generate_context_header():
    """Verify header contains required fields"""
    context = {
        'course_name': 'Test Course',
        'chapter': 'Chapter 1',
        'section': 'Section A',
        'variation_name': '6.Bg5'
    }
    header = generate_context_header(context)
    assert 'Test Course' in header
    assert 'Chapter 1' in header
    assert '6.Bg5' in header
    assert count_tokens(header) < 500  # Header shouldn't be huge
```

#### 1.3 Variation Name Extraction
```python
def test_get_variation_name():
    """Test hybrid variation naming (move + comment)"""
    # With comment
    node_with_comment = create_test_node("6.Bg5", comment="Poisoned Pawn")
    name = get_variation_name(node_with_comment)
    assert name == "6.Bg5 (Poisoned Pawn)"

    # Without comment
    node_plain = create_test_node("6.Bg5", comment="")
    name = get_variation_name(node_plain)
    assert name == "6.Bg5"
```

#### 1.4 Eval Compression (Grok's enhancement)
```python
def test_eval_compression():
    """Test keeping evals only at key nodes"""
    pgn_with_many_evals = """
    1. e4 {+0.5} c5 {+0.5} 2. Nf3 {+0.5} d6 {+0.5}
    3. d4 {+0.5} cxd4 {+0.5} 4. Nxd4 {+0.8}
    """
    compressed = compress_evals_at_key_nodes(pgn_with_many_evals)

    # Should keep eval at move 4 (>0.3 shift)
    assert '{+0.8}' in compressed
    # Should remove redundant +0.5 evals
    assert compressed.count('{+0.5}') <= 2  # Only branch/end points
```

#### 1.5 Merge Small Chunks (Grok's logic)
```python
def test_merge_small_chunks():
    """Test merging chunks below 2,000 token threshold"""
    chunks = [
        {'content': 'chunk1', 'token_count': 1500},  # Too small
        {'content': 'chunk2', 'token_count': 1800},  # Too small
        {'content': 'chunk3', 'token_count': 5000},  # OK
    ]
    merged = merge_small_chunks(chunks, min_tokens=2000)
    assert len(merged) == 2  # First two merged
    assert merged[0]['token_count'] >= 2000
```

---

### Level 2: Integration Tests (4 Oversized Files)

**File:** `test_oversized_files.py`

**Purpose:** Validate splitter on known problematic files

#### 2.1 Rapport's Stonewall Dutch (41,209 tokens)
```python
def test_rapport_stonewall():
    """Test the monster 41K token aggregation file"""
    game = load_pgn("/Users/leon/Downloads/ZListo/Rapport's Stonewall Dutch - All in One pgn.pgn")
    chunks = split_oversized_game(game, 'Rapport.pgn', 1, count_tokens)

    # Assertions
    assert len(chunks) > 1, "Should split into multiple chunks"
    assert len(chunks) < 100, "Shouldn't explode into too many chunks"
    assert all(c['token_count'] <= 7800 for c in chunks), "All chunks under limit"

    # Check for embedded game detection
    embedded = [c for c in chunks if c['metadata']['chunk_type'] == 'embedded_game']
    assert len(embedded) > 0, "Should detect embedded games"
```

#### 2.2 Queen's Gambit with h6 (9,540 tokens)
```python
def test_queens_gambit_h6():
    """Test theory-heavy Modern Chess course"""
    game = load_pgn("/Users/leon/Downloads/ZListo/Queen's Gambit with ...h7-h6*.pgn")
    chunks = split_oversized_game(game, 'QG_h6.pgn', 15, count_tokens)

    assert len(chunks) in [2, 3, 4], "Should split into 2-4 chunks"
    assert all(c['token_count'] <= 7800 for c in chunks)

    # Verify parent linkage
    parent_ids = {c['metadata']['parent_game_id'] for c in chunks}
    assert len(parent_ids) == 1, "All chunks should share parent_game_id"
```

#### 2.3 Elite Najdorf (8,406 tokens)
```python
def test_elite_najdorf():
    """Test just-over-limit detailed repertoire"""
    game = load_pgn("/Users/leon/Downloads/ZListo/EN - Elite Najdorf Repertoire*.pgn")
    chunks = split_oversized_game(game, 'Najdorf.pgn', 3, count_tokens)

    assert len(chunks) == 2, "Should split into exactly 2 chunks (barely over)"
    assert chunks[0]['metadata']['chunk_type'] == 'overview'
    assert chunks[1]['metadata']['chunk_type'] == 'variation_split'
```

#### 2.4 Correspondence Chess (12,119 tokens)
```python
def test_correspondence_chess():
    """Test deep correspondence analysis"""
    game = load_pgn("/Users/leon/Downloads/ZListo/The Correspondence Chess Today.pgn")
    chunks = split_oversized_game(game, 'Corresp.pgn', 9, count_tokens)

    assert len(chunks) in [3, 4, 5], "Should split into 3-5 chunks"

    # Test eval compression worked
    original_game_text = export_game_to_text(game)
    chunk_text = ''.join(c['content'] for c in chunks)
    assert len(chunk_text) < len(original_game_text), "Compression should reduce size"
```

---

### Level 3: Validation Tests (Quality Assurance)

**File:** `test_validation.py`

#### 3.1 Round-Trip PGN Test
```python
def test_round_trip_pgn():
    """Verify split chunks can be re-parsed as valid PGN"""
    for chunk in all_test_chunks:
        pgn_text = chunk['content']

        # Try to parse
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        assert game is not None, f"Chunk {chunk['metadata']['chunk_id']} invalid PGN"

        # Re-export and compare
        exported = export_game_to_text(game)
        # Allow minor formatting differences, but structure should match
        assert_similar_pgn(pgn_text, exported)
```

#### 3.2 Legal Move Validation
```python
def test_all_moves_legal():
    """Verify every move in every chunk is legal chess"""
    for chunk in all_test_chunks:
        game = chess.pgn.read_game(io.StringIO(chunk['content']))
        board = game.board()

        for move in game.mainline_moves():
            assert board.is_legal(move), f"Illegal move: {move} in chunk {chunk['metadata']['chunk_id']}"
            board.push(move)
```

#### 3.3 Metadata Completeness
```python
def test_metadata_complete():
    """Verify all required metadata fields present"""
    required_fields = [
        'parent_game_id', 'chunk_id', 'chunk_type',
        'source_file', 'game_number',
        'course_name', 'chapter'
    ]

    for chunk in all_test_chunks:
        for field in required_fields:
            assert field in chunk['metadata'], f"Missing field: {field}"
            assert chunk['metadata'][field] is not None
```

#### 3.4 Token Limit Compliance
```python
def test_token_limits():
    """Hard assertion: no chunk exceeds 7,800 tokens"""
    for chunk in all_test_chunks:
        actual_tokens = count_tokens(chunk['content'])

        # Verify our counter matches stored value
        assert abs(actual_tokens - chunk['token_count']) < 5, "Token count mismatch"

        # Hard limit
        assert actual_tokens <= 7800, f"Chunk {chunk['metadata']['chunk_id']} exceeds limit: {actual_tokens} tokens"
```

#### 3.5 NAG Preservation
```python
def test_nag_preservation():
    """Verify annotations (!, !!, ?, etc.) are preserved"""
    original_game = load_test_game_with_nags()
    chunks = split_oversized_game(original_game, 'test.pgn', 1, count_tokens)

    # Count NAGs in original
    original_nags = count_nags(original_game)

    # Count NAGs in all chunks combined
    chunk_nags = sum(count_nags(parse_pgn(c['content'])) for c in chunks)

    assert chunk_nags == original_nags, "NAGs lost during splitting"
```

---

### Level 4: Corpus Test (1,779 Games)

**File:** `test_full_corpus.py`

#### 4.1 Process All Games
```python
def test_all_1779_games():
    """Process entire ZListo corpus"""
    results = {
        'total': 0,
        'normal': 0,  # Single chunk
        'split': 0,   # Multiple chunks
        'failed': 0,
        'total_chunks': 0,
        'failures': []
    }

    for pgn_file in Path("/Users/leon/Downloads/ZListo").glob("*.pgn"):
        with open(pgn_file) as f:
            game_num = 0
            while True:
                game = chess.pgn.read_game(f)
                if not game:
                    break

                game_num += 1
                results['total'] += 1

                try:
                    chunks = split_oversized_game(game, pgn_file.name, game_num, count_tokens)
                    results['total_chunks'] += len(chunks)

                    if len(chunks) == 1:
                        results['normal'] += 1
                    else:
                        results['split'] += 1

                    # Validate each chunk
                    for chunk in chunks:
                        assert chunk['token_count'] <= 7800

                except Exception as e:
                    results['failed'] += 1
                    results['failures'].append({
                        'file': pgn_file.name,
                        'game': game_num,
                        'error': str(e)
                    })

    # Assertions
    assert results['total'] == 1779, f"Expected 1779 games, got {results['total']}"
    assert results['failed'] == 0, f"{results['failed']} games failed: {results['failures']}"
    assert results['split'] <= 10, "More splits than expected"

    print(f"\n✅ Corpus Test Results:")
    print(f"   Total games: {results['total']}")
    print(f"   Normal (1 chunk): {results['normal']}")
    print(f"   Split (2+ chunks): {results['split']}")
    print(f"   Total chunks: {results['total_chunks']}")
    print(f"   Avg chunks/game: {results['total_chunks']/results['total']:.3f}")
```

---

### Level 5: Production Validation (Isolated Collection)

**File:** `test_production_validation.py`

#### 5.1 Embedding Generation
```python
def test_embedding_generation():
    """Generate embeddings for all chunks"""
    chunks = load_all_test_chunks()

    # Generate embeddings (use test API key limit)
    embeddings = generate_embeddings_batch(
        [c['content'] for c in chunks],
        model="text-embedding-3-small",
        batch_size=100
    )

    assert len(embeddings) == len(chunks), "Embedding count mismatch"
    assert all(len(e) == 1536 for e in embeddings), "Wrong embedding dimensions"
```

#### 5.2 Qdrant Upload (Test Collection)
```python
def test_qdrant_upload():
    """Upload to isolated test collection"""
    collection_name = "chess_pgn_split_test"

    # Create collection
    qdrant_client.recreate_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE)
    )

    # Upload chunks
    upload_chunks_to_qdrant(test_chunks, collection_name)

    # Verify count
    info = qdrant_client.get_collection(collection_name)
    assert info.points_count == len(test_chunks), "Upload count mismatch"
```

#### 5.3 Retrieval Quality
```python
def test_retrieval_quality():
    """Verify split chunks retrieve correctly"""
    test_queries = [
        "Najdorf 6.Bg5 Poisoned Pawn variation",
        "Stonewall Dutch structure",
        "Queen's Gambit h6 system",
        "Correspondence chess endgame technique"
    ]

    for query in test_queries:
        results = qdrant_client.search(
            collection_name="chess_pgn_split_test",
            query_vector=generate_embedding(query),
            limit=10
        )

        assert len(results) > 0, f"No results for: {query}"
        assert all(r.score > 0.4 for r in results), "Low relevance scores"
```

#### 5.4 Sibling Boosting
```python
def test_sibling_boosting():
    """Verify sibling chunks boost correctly"""
    query = "Najdorf 6.Bg5 analysis"

    # Stage 1: Initial search
    initial_results = qdrant_search(query, limit=20)

    # Stage 2: Check for variation chunks
    variation_chunks = [r for r in initial_results if r.payload['chunk_type'] == 'variation']

    if variation_chunks:
        parent_ids = {r.payload['parent_game_id'] for r in variation_chunks}

        # Stage 3: Fetch siblings
        siblings = fetch_siblings(parent_ids)

        # Verify overview chunks included
        overview_chunks = [s for s in siblings if s.payload['chunk_type'] == 'overview']
        assert len(overview_chunks) > 0, "Overview not retrieved with variation"
```

---

## 📊 Test Execution Plan

### Phase 1: Unit Tests (15 minutes)
```bash
pytest test_variation_splitter.py -v
```
**Pass criteria:** All unit tests green

### Phase 2: Integration Tests (30 minutes)
```bash
pytest test_oversized_files.py -v
```
**Pass criteria:** All 4 oversized files split successfully

### Phase 3: Validation Tests (20 minutes)
```bash
pytest test_validation.py -v
```
**Pass criteria:** PGN validity, legal moves, metadata complete

### Phase 4: Corpus Test (1 hour)
```bash
pytest test_full_corpus.py -v
```
**Pass criteria:** All 1,779 games process without errors

### Phase 5: Production Validation (30 minutes)
```bash
pytest test_production_validation.py -v
```
**Pass criteria:** Embeddings, upload, retrieval all working

---

## ✅ Test Success Criteria

**GATE 1 (Unit Tests):**
- [ ] All functions work in isolation
- [ ] Token counting accurate
- [ ] Metadata generation correct

**GATE 2 (Integration):**
- [ ] All 4 oversized files split successfully
- [ ] All chunks ≤7,800 tokens
- [ ] Metadata properly linked

**GATE 3 (Validation):**
- [ ] Round-trip PGN parsing works
- [ ] All moves are legal
- [ ] NAGs preserved

**GATE 4 (Corpus):**
- [ ] All 1,779 games processed
- [ ] 0 failures
- [ ] Split rate ~0.2-0.5%

**GATE 5 (Production):**
- [ ] Embeddings generated
- [ ] Qdrant upload successful
- [ ] Retrieval quality maintained
- [ ] Sibling boosting works

**PROCEED TO PRODUCTION ONLY IF ALL 5 GATES PASS**

---

## 📝 Test Reporting

After each test level, generate report:

```bash
pytest --html=test_report_level_X.html --self-contained-html
```

**Reports:**
- `test_report_unit.html`
- `test_report_integration.html`
- `test_report_validation.html`
- `test_report_corpus.html`
- `test_report_production.html`

---

## 🚨 Failure Handling

**If ANY test fails:**
1. Stop immediately (don't proceed to next level)
2. Log failure details
3. Debug and fix
4. Re-run all tests from the beginning
5. Update documentation

**No production deployment without 100% test pass rate.**

---

**Created:** November 8, 2025
**Status:** Ready for implementation
**Next:** Create rollback strategy, then begin coding
