"""
Tests for Transposition Detection
==================================

Tests the FEN collection and transposition linking functionality.
"""

import pytest
import chess.pgn
import io
from split_oversized_game import (
    collect_fens_from_node,
    build_transposition_map,
    add_transposition_links,
    split_oversized_game
)


# ============================================================================
# Test 1: FEN Collection from Simple Line
# ============================================================================

def test_collect_fens_simple_line():
    """Test FEN collection from a simple line (no variations)."""
    pgn_text = """
[Event "Test"]
[White "Player1"]
[Black "Player2"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7
"""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    board = chess.Board()

    fens = collect_fens_from_node(game.variations[0], board)

    # Should collect FENs at move 5 (checkpoint) and end of line
    assert len(fens) >= 2
    assert all(isinstance(fen, str) and isinstance(move_num, int) for fen, move_num in fens)


# ============================================================================
# Test 2: FEN Collection at Branch Points
# ============================================================================

def test_collect_fens_with_variations():
    """Test that FENs are collected at variation branch points."""
    pgn_text = """
[Event "Test"]

1. e4 e5 (1... c5) 2. Nf3 Nc6 (2... d6) 3. Bb5
"""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    board = chess.Board()

    fens = collect_fens_from_node(game.variations[0], board)

    # Should collect at branch points (moves 1 and 2) plus checkpoints
    assert len(fens) >= 2

    # Check that FENs are valid
    for fen, move_num in fens:
        assert '/' in fen  # FEN contains slashes
        assert move_num > 0


# ============================================================================
# Test 3: Transposition Detection - Same Position via Different Moves
# ============================================================================

def test_transposition_detection_different_move_orders():
    """Test detection of transpositions (same position, different move order)."""

    # London System: two paths to same position
    pgn_text = """
[Event "London System Transposition"]

1. d4 Nf6 2. Bf4 d5 3. e3 e6
"""
    game = chess.pgn.read_game(io.StringIO(pgn_text))

    chunks = split_oversized_game(game, "test.pgn", 1)

    # Should have FENs collected
    assert len(chunks) == 1
    assert 'fens' in chunks[0]['metadata']
    assert len(chunks[0]['metadata']['fens']) > 0


# ============================================================================
# Test 4: Build Transposition Map
# ============================================================================

def test_build_transposition_map():
    """Test building transposition map from chunks with shared positions."""

    # Create mock chunks with overlapping FENs
    chunks = [
        {
            'metadata': {
                'chunk_id': 'chunk_1',
                'fens': [
                    ('rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1', 1),
                    ('rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2', 2)
                ]
            }
        },
        {
            'metadata': {
                'chunk_id': 'chunk_2',
                'fens': [
                    ('rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2', 2),
                    ('rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2', 3)
                ]
            }
        }
    ]

    transposition_map = build_transposition_map(chunks)

    # Should find the shared FEN (after 1. e4 e5)
    shared_fen = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2'
    assert shared_fen in transposition_map
    assert len(transposition_map[shared_fen]) == 2  # Both chunks

    # Check chunk IDs are correct
    chunk_ids = [cid for cid, _ in transposition_map[shared_fen]]
    assert 'chunk_1' in chunk_ids
    assert 'chunk_2' in chunk_ids


# ============================================================================
# Test 5: Add Transposition Links to Chunks
# ============================================================================

def test_add_transposition_links():
    """Test that transposition links are added to chunk metadata."""

    chunks = [
        {
            'metadata': {
                'chunk_id': 'chunk_1',
                'fens': [
                    ('rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2', 2)
                ]
            }
        },
        {
            'metadata': {
                'chunk_id': 'chunk_2',
                'fens': [
                    ('rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2', 2)
                ]
            }
        }
    ]

    transposition_map = build_transposition_map(chunks)
    add_transposition_links(chunks, transposition_map)

    # Both chunks should have transposition links
    assert 'transpositions' in chunks[0]['metadata']
    assert 'transpositions' in chunks[1]['metadata']

    # chunk_1 should link to chunk_2
    trans_1 = chunks[0]['metadata']['transpositions']
    assert len(trans_1) == 1
    assert 'chunk_2' in trans_1[0]['linked_chunks']

    # chunk_2 should link to chunk_1
    trans_2 = chunks[1]['metadata']['transpositions']
    assert len(trans_2) == 1
    assert 'chunk_1' in trans_2[0]['linked_chunks']


# ============================================================================
# Test 6: No Transpositions in Single Chunk
# ============================================================================

def test_no_transpositions_single_chunk():
    """Test that single chunk has empty transposition list."""

    chunks = [
        {
            'metadata': {
                'chunk_id': 'chunk_1',
                'fens': [
                    ('rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1', 1)
                ]
            }
        }
    ]

    transposition_map = build_transposition_map(chunks)
    add_transposition_links(chunks, transposition_map)

    # No transpositions (only 1 chunk)
    assert transposition_map == {}
    assert chunks[0]['metadata']['transpositions'] == []


# ============================================================================
# Test 7: Multiple Transpositions Sorted by Link Count
# ============================================================================

def test_multiple_transpositions_sorted():
    """Test that multiple transpositions are sorted by number of links."""

    chunks = [
        {
            'metadata': {
                'chunk_id': 'chunk_1',
                'fens': [
                    ('fen_a', 1),  # Shared with 2 chunks
                    ('fen_b', 2)   # Shared with 3 chunks
                ]
            }
        },
        {
            'metadata': {
                'chunk_id': 'chunk_2',
                'fens': [('fen_a', 1), ('fen_b', 2)]
            }
        },
        {
            'metadata': {
                'chunk_id': 'chunk_3',
                'fens': [('fen_a', 1), ('fen_b', 2)]
            }
        },
        {
            'metadata': {
                'chunk_id': 'chunk_4',
                'fens': [('fen_b', 2)]
            }
        }
    ]

    transposition_map = build_transposition_map(chunks)
    add_transposition_links(chunks, transposition_map)

    # chunk_1 should have transpositions sorted by link count
    trans = chunks[0]['metadata']['transpositions']
    assert len(trans) == 2

    # fen_b has 3 links (chunk_2, chunk_3, chunk_4)
    # fen_a has 2 links (chunk_2, chunk_3)
    # So fen_b should come first
    assert len(trans[0]['linked_chunks']) >= len(trans[1]['linked_chunks'])


# ============================================================================
# Test 8: Max Links Per Chunk Limit
# ============================================================================

def test_max_links_per_chunk():
    """Test that transposition links are limited to max_links_per_chunk."""

    # Create 15 chunks all sharing the same FEN
    chunks = [
        {
            'metadata': {
                'chunk_id': f'chunk_{i}',
                'fens': [('shared_fen', 1)]
            }
        }
        for i in range(15)
    ]

    transposition_map = build_transposition_map(chunks)
    add_transposition_links(chunks, transposition_map, max_links_per_chunk=10)

    # Each chunk should have at most 10 transpositions
    for chunk in chunks:
        trans = chunk['metadata']['transpositions']
        assert len(trans) <= 10
        if len(trans) > 0:
            # Should have 14 linked chunks (all others), but limited to 10
            assert len(trans[0]['linked_chunks']) <= 14


# ============================================================================
# Test 9: Integration - Full Game with Transpositions
# ============================================================================

def test_integration_full_game_with_transpositions():
    """Test end-to-end with a game that has actual transpositions."""

    # Sicilian Defense with transpose to same position
    pgn_text = """
[Event "Sicilian Transposition Test"]

1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6
"""
    game = chess.pgn.read_game(io.StringIO(pgn_text))

    chunks = split_oversized_game(game, "test.pgn", 1)

    # Should have 1 chunk (game is small)
    assert len(chunks) == 1

    # Should have FENs collected
    assert 'fens' in chunks[0]['metadata']
    fens = chunks[0]['metadata']['fens']
    assert len(fens) > 0

    # Should have transpositions metadata (even if empty for single chunk)
    assert 'transpositions' in chunks[0]['metadata']


# ============================================================================
# Test 10: Empty Game Handling
# ============================================================================

def test_empty_game():
    """Test that empty games don't crash FEN collection."""

    pgn_text = """
[Event "Empty Game"]

*
"""
    game = chess.pgn.read_game(io.StringIO(pgn_text))

    chunks = split_oversized_game(game, "test.pgn", 1)

    # Should return 1 chunk with empty/minimal FENs
    assert len(chunks) == 1
    assert 'fens' in chunks[0]['metadata']


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
