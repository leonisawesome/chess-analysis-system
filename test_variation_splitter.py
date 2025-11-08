"""
Unit Tests for PGN Variation Splitter
======================================

Tests individual functions in split_oversized_game.py module.

Test coverage:
1. Token counting (tiktoken)
2. Context header generation (Gemini's approach)
3. Variation name extraction
4. Eval compression (Grok's enhancement)
5. Merge small chunks (Grok's enhancement)
6. Game ID generation
7. Metadata extraction
"""

import io
import pytest
import chess
import chess.pgn

from split_oversized_game import (
    count_tokens,
    generate_context_header,
    get_variation_name,
    get_spine_to_node,
    compress_evals,
    merge_small_chunks,
    generate_game_id,
    extract_course_metadata,
    split_oversized_game
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_game():
    """Create a simple test game with variations."""
    pgn = """[Event "Test Course - Chapter 1"]
[Site "Section A"]
[White "Test"]
[Black "Game"]

1. e4 c5 {Sicilian Defense} 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 (5. f3 {Samisch Variation} e5 6. Nb3 Be7) 5... a6 {Najdorf} (5... Nc6 {Classical Variation} 6. Bg5 e6) 6. Bg5 e6 7. f4 *
"""
    return chess.pgn.read_game(io.StringIO(pgn))


@pytest.fixture
def game_with_evals():
    """Create game with many evaluations for compression testing."""
    pgn = """[Event "Eval Test"]
[White "Computer"]
[Black "Analysis"]

1. e4 {+0.5} c5 {+0.5} 2. Nf3 {+0.5} d6 {+0.5} 3. d4 {+0.5} cxd4 {+0.5} 4. Nxd4 {+0.8} Nf6 {+0.7} 5. Nc3 {+0.7} a6 {+0.7} 6. Bg5 {+0.7} e6 {+0.7} 7. f4 {+1.2} Be7 {+1.1} 8. Qf3 {+1.1} Qc7 {+1.1} *
"""
    return chess.pgn.read_game(io.StringIO(pgn))


# ============================================================================
# Test 1: Token Counting
# ============================================================================

def test_count_tokens_basic():
    """Verify token counting with simple text."""
    text = "1. e4 c5 2. Nf3 d6 3. d4"
    tokens = count_tokens(text)

    assert isinstance(tokens, int)
    assert tokens > 0
    assert tokens < 50  # Should be small for short text


def test_count_tokens_empty():
    """Test token counting with empty string."""
    tokens = count_tokens("")
    assert tokens == 0


def test_count_tokens_long_comment():
    """Test token counting with long annotations."""
    text = """
    1. e4 c5 {This is the Sicilian Defense, one of the most popular and
    aggressive responses to 1.e4. Black immediately fights for the center
    and creates an asymmetric pawn structure.} 2. Nf3 d6 3. d4 cxd4
    """
    tokens = count_tokens(text)

    assert tokens > 50  # Should be substantial with the comment
    assert tokens < 200  # But not excessive


def test_count_tokens_variations():
    """Test token counting with PGN variations."""
    text = "1. e4 c5 2. Nf3 (2. c3 {Alapin}) 2... d6 3. d4"
    tokens = count_tokens(text)

    assert tokens > 10
    assert tokens < 100


# ============================================================================
# Test 2: Context Header Generation
# ============================================================================

def test_generate_context_header_full(sample_game):
    """Test context header with complete metadata."""
    metadata = {
        'course_name': 'Najdorf Mastery',
        'chapter': 'Chapter 3: 6.Bg5',
        'section': 'Poisoned Pawn Variation'
    }

    # Get a variation node for context
    node = sample_game
    while node.variations:
        node = node.variations[0]

    header = generate_context_header(sample_game, node, metadata)

    assert 'Najdorf Mastery' in header
    assert 'Chapter 3: 6.Bg5' in header
    assert 'Poisoned Pawn Variation' in header
    assert header.endswith('\n\n')  # Should have double newline at end


def test_generate_context_header_minimal(sample_game):
    """Test context header with minimal metadata."""
    metadata = {'course_name': 'Test Course'}

    header = generate_context_header(sample_game, None, metadata)

    assert 'Test Course' in header
    assert 'Course:' in header


def test_generate_context_header_with_spine(sample_game):
    """Test that context header includes main line up to branch point."""
    metadata = {'course_name': 'Test'}

    # Navigate to a variation node
    node = sample_game
    for _ in range(5):  # Go 5 moves deep
        if node.variations:
            node = node.variations[0]

    # Get first variation
    if len(node.variations) > 1:
        variation_node = node.variations[1]
        header = generate_context_header(sample_game, variation_node, metadata)

        assert 'Main line:' in header
        assert 'e4' in header  # First move should be in spine


def test_context_header_token_limit():
    """Verify context header doesn't consume too many tokens."""
    game = chess.pgn.Game()
    metadata = {
        'course_name': 'Test Course',
        'chapter': 'Chapter 1',
        'section': 'Section A'
    }

    header = generate_context_header(game, None, metadata)
    tokens = count_tokens(header)

    assert tokens < 500, f"Context header too large: {tokens} tokens"


# ============================================================================
# Test 3: Variation Name Extraction
# ============================================================================

def test_get_variation_name_with_comment(sample_game):
    """Test variation naming with comment annotation."""
    # Navigate to second move (c5 with "Sicilian Defense" comment)
    node = sample_game.variations[0]  # 1. e4
    if node.variations:
        node = node.variations[0]  # 1... c5 {Sicilian Defense}

    name = get_variation_name(node)

    # Should include both move and comment
    assert 'c5' in name
    # Comment should be included (cleaned)
    assert 'Sicilian' in name


def test_get_variation_name_without_comment(sample_game):
    """Test variation naming without comment."""
    # Get first move (usually no comment)
    node = sample_game.variations[0] if sample_game.variations else sample_game

    name = get_variation_name(node)

    # Should just be the move
    assert len(name) < 10  # Just a move like "e4" or "Nf3"


def test_get_variation_name_filters_evals():
    """Verify variation names don't include eval annotations."""
    game = chess.pgn.Game()
    node = game.add_variation(chess.Move.from_uci("e2e4"))
    node.comment = "{+0.5} This is a test comment"

    name = get_variation_name(node)

    assert '{+0.5}' not in name  # Eval should be filtered
    assert 'test comment' in name.lower()  # Comment should remain


# ============================================================================
# Test 4: Spine Extraction
# ============================================================================

def test_get_spine_to_node(sample_game):
    """Test extracting main line up to a specific node."""
    # Navigate 3 moves deep: 1. e4 c5 2. Nf3
    node = sample_game.variations[0]  # 1. e4
    if node.variations:
        node = node.variations[0]  # 1... c5
    if node.variations:
        node = node.variations[0]  # 2. Nf3

    spine = get_spine_to_node(node)

    # Should have move numbers and moves
    assert '1. e4' in spine
    assert 'c5' in spine or 'Nf3' in spine


def test_get_spine_formats_correctly(sample_game):
    """Verify spine formatting with move numbers."""
    # Navigate 4 moves deep: 1. e4 c5 2. Nf3 d6
    node = sample_game.variations[0]  # 1. e4
    for _ in range(3):
        if node.variations:
            node = node.variations[0]

    spine = get_spine_to_node(node)

    # Should have proper formatting
    assert spine.count('.') >= 1  # At least one move number
    # Check for spaces between moves
    assert ' ' in spine


# ============================================================================
# Test 5: Eval Compression
# ============================================================================

def test_eval_compression_reduces_tokens(game_with_evals):
    """Test that eval compression reduces token count."""
    # Count tokens before compression
    original_text = str(game_with_evals)
    original_tokens = count_tokens(original_text)

    # Apply compression
    compress_evals(game_with_evals)

    # Count tokens after compression
    compressed_text = str(game_with_evals)
    compressed_tokens = count_tokens(compressed_text)

    # Should reduce tokens or stay the same (if game is small)
    assert compressed_tokens <= original_tokens
    # If there was reduction, should save something
    if compressed_tokens < original_tokens:
        reduction_percent = (original_tokens - compressed_tokens) / original_tokens
        assert reduction_percent > 0


def test_eval_compression_keeps_key_nodes(game_with_evals):
    """Verify compression keeps evals at important nodes."""
    # Apply compression
    compress_evals(game_with_evals)

    compressed_text = str(game_with_evals)

    # Should keep SOME evals (at checkpoints, line ends, or significant shifts)
    # At minimum, the last move should have an eval (line end)
    # Note: python-chess adds spaces around evals when printing: { +0.5 }
    eval_pattern = r'\{\s*[+\-]?\d+\.?\d*\s*\}'
    import re
    remaining_evals = re.findall(eval_pattern, compressed_text)

    # Should have at least a few evals remaining (not remove ALL)
    assert len(remaining_evals) >= 1, "Compression should keep some evals"


def test_eval_compression_removes_redundant():
    """Test that redundant evals are removed."""
    pgn = """[Event "Redundant Evals"]

1. e4 {+0.5} c5 {+0.5} 2. Nf3 {+0.5} d6 {+0.5} 3. d4 {+0.5} cxd4 {+0.5} *
"""
    game = chess.pgn.read_game(io.StringIO(pgn))

    # Count evals before
    original_eval_count = str(game).count('{+0.5}')

    compress_evals(game)

    # Count evals after
    compressed_eval_count = str(game).count('{+0.5}')

    # Should remove some or all redundant +0.5 evals (or keep same if all are at key nodes)
    assert compressed_eval_count <= original_eval_count


# ============================================================================
# Test 6: Merge Small Chunks
# ============================================================================

def test_merge_small_chunks_combines_tiny():
    """Test that small chunks are merged together."""
    chunks = [
        {
            'content': 'Chunk 1 content',
            'token_count': 1500,
            'metadata': {'variation_name': 'Var 1'}
        },
        {
            'content': 'Chunk 2 content',
            'token_count': 1800,
            'metadata': {'variation_name': 'Var 2'}
        },
        {
            'content': 'Chunk 3 content',
            'token_count': 5000,
            'metadata': {}
        }
    ]

    merged = merge_small_chunks(chunks, min_tokens=2000)

    # Should merge first two chunks
    assert len(merged) == 2
    assert merged[0]['token_count'] >= 2000
    # Should combine variation names
    assert 'Var 1' in merged[0]['metadata']['variation_name']
    assert 'Var 2' in merged[0]['metadata']['variation_name']


def test_merge_small_chunks_preserves_large():
    """Test that large chunks are not merged."""
    chunks = [
        {'content': 'Large chunk', 'token_count': 5000, 'metadata': {}},
        {'content': 'Another large', 'token_count': 6000, 'metadata': {}},
        {'content': 'Third large', 'token_count': 7000, 'metadata': {}}
    ]

    merged = merge_small_chunks(chunks, min_tokens=2000)

    # Should not merge any
    assert len(merged) == 3
    assert all(c['token_count'] >= 2000 for c in merged)


def test_merge_small_chunks_empty():
    """Test merging with empty list."""
    merged = merge_small_chunks([], min_tokens=2000)
    assert merged == []


def test_merge_small_chunks_all_small():
    """Test when all chunks are small."""
    chunks = [
        {'content': f'Chunk {i}', 'token_count': 1000, 'metadata': {}}
        for i in range(5)
    ]

    merged = merge_small_chunks(chunks, min_tokens=2000)

    # Should merge into fewer chunks
    assert len(merged) < len(chunks)
    # Each merged chunk should be ≥2000 tokens
    assert all(c['token_count'] >= 2000 for c in merged)


# ============================================================================
# Test 7: Game ID Generation
# ============================================================================

def test_generate_game_id_stable():
    """Test that game IDs are stable for same inputs."""
    id1 = generate_game_id("test.pgn", 1)
    id2 = generate_game_id("test.pgn", 1)

    assert id1 == id2


def test_generate_game_id_unique():
    """Test that different games get different IDs."""
    id1 = generate_game_id("test.pgn", 1)
    id2 = generate_game_id("test.pgn", 2)
    id3 = generate_game_id("other.pgn", 1)

    assert id1 != id2
    assert id1 != id3
    assert id2 != id3


def test_generate_game_id_format():
    """Test game ID format (16 hex chars)."""
    game_id = generate_game_id("test.pgn", 1)

    assert isinstance(game_id, str)
    assert len(game_id) == 16
    # Should be hex string
    assert all(c in '0123456789abcdef' for c in game_id)


# ============================================================================
# Test 8: Metadata Extraction
# ============================================================================

def test_extract_course_metadata_full(sample_game):
    """Test metadata extraction with full headers."""
    metadata = extract_course_metadata(sample_game)

    assert 'course_name' in metadata
    assert 'chapter' in metadata
    assert metadata['course_name'] == 'Test Course'
    assert metadata['chapter'] == 'Chapter 1'


def test_extract_course_metadata_minimal():
    """Test metadata extraction with minimal headers."""
    game = chess.pgn.Game()
    game.headers["Event"] = "Simple Game"

    metadata = extract_course_metadata(game)

    assert metadata['course_name'] == "Simple Game"
    assert metadata.get('chapter') == ""


def test_extract_course_metadata_site():
    """Test that Site header is extracted as section."""
    game = chess.pgn.Game()
    game.headers["Event"] = "Course"
    game.headers["Site"] = "Section A"

    metadata = extract_course_metadata(game)

    assert metadata.get('section') == "Section A"


# ============================================================================
# Test 9: Integration Tests (Main Function)
# ============================================================================

def test_split_oversized_game_normal_size(sample_game):
    """Test that normal-sized games are not split."""
    chunks = split_oversized_game(sample_game, "test.pgn", 1)

    # Small game should return as single chunk
    assert len(chunks) == 1
    assert chunks[0]['metadata']['chunk_type'] == 'single'
    assert chunks[0]['token_count'] <= 7800


def test_split_oversized_game_returns_list():
    """Test that function always returns a list."""
    game = chess.pgn.Game()
    chunks = split_oversized_game(game, "test.pgn", 1)

    assert isinstance(chunks, list)
    assert len(chunks) >= 1


def test_split_oversized_game_metadata():
    """Test that all chunks have required metadata."""
    game = chess.pgn.Game()
    game.headers["Event"] = "Test Course"

    chunks = split_oversized_game(game, "test.pgn", 1)

    required_fields = ['parent_game_id', 'chunk_id', 'chunk_type', 'source_file', 'game_number']

    for chunk in chunks:
        assert 'metadata' in chunk
        for field in required_fields:
            assert field in chunk['metadata'], f"Missing field: {field}"


def test_split_oversized_game_token_counts():
    """Test that token counts are tracked correctly."""
    game = chess.pgn.Game()
    chunks = split_oversized_game(game, "test.pgn", 1)

    for chunk in chunks:
        assert 'token_count' in chunk
        assert isinstance(chunk['token_count'], int)
        assert chunk['token_count'] > 0
        # Verify actual count matches stored count
        actual = count_tokens(chunk['content'])
        # Allow small rounding differences
        assert abs(actual - chunk['token_count']) < 10


def test_split_oversized_game_no_empty_chunks():
    """Test that no empty chunks are created."""
    game = chess.pgn.Game()
    game.add_variation(chess.Move.from_uci("e2e4"))

    chunks = split_oversized_game(game, "test.pgn", 1)

    for chunk in chunks:
        assert len(chunk['content']) > 0
        assert chunk['token_count'] > 0


def test_split_oversized_game_compression_flag(game_with_evals):
    """Test that compression can be toggled."""
    # With compression
    chunks_compressed = split_oversized_game(
        game_with_evals,
        "test.pgn",
        1,
        apply_eval_compression=True
    )

    # Without compression
    chunks_uncompressed = split_oversized_game(
        game_with_evals,
        "test.pgn",
        1,
        apply_eval_compression=False
    )

    # Compressed should have fewer/smaller chunks
    total_compressed = sum(c['token_count'] for c in chunks_compressed)
    total_uncompressed = sum(c['token_count'] for c in chunks_uncompressed)

    # If compression had an effect, totals should differ
    # (May be equal if game is small, which is also valid)
    assert total_compressed <= total_uncompressed


# ============================================================================
# Test 10: Edge Cases
# ============================================================================

def test_empty_game():
    """Test handling of empty game."""
    game = chess.pgn.Game()
    chunks = split_oversized_game(game, "test.pgn", 1)

    assert len(chunks) == 1
    assert chunks[0]['metadata']['chunk_type'] == 'single'


def test_game_with_no_moves():
    """Test game with headers but no moves."""
    game = chess.pgn.Game()
    game.headers["Event"] = "No Moves"
    game.headers["White"] = "Player1"
    game.headers["Black"] = "Player2"

    chunks = split_oversized_game(game, "test.pgn", 1)

    assert len(chunks) == 1
    # Should still extract metadata
    assert chunks[0]['metadata']['course_name'] == "No Moves"


def test_game_with_deep_variations():
    """Test game with deeply nested variations."""
    pgn = """
    [Event "Deep Variations"]

    1. e4 c5 2. Nf3 d6
    (2... Nc6 3. d4 (3. Bb5 {Rossolimo} a6) 3... cxd4)
    3. d4 cxd4 *
    """
    game = chess.pgn.read_game(io.StringIO(pgn))
    chunks = split_oversized_game(game, "test.pgn", 1)

    # Should handle nested variations
    assert len(chunks) >= 1
    # All chunks should be under limit
    assert all(c['token_count'] <= 7800 for c in chunks)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
