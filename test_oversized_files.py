"""
Integration Tests - 4 Oversized PGN Files
==========================================

Test the splitter on the 4 known oversized files from the corpus.

Files:
1. Rapport's Stonewall Dutch - All in One.pgn - Game #1 (41,209 tokens)
2. The Correspondence Chess Today.pgn - Game #9 (12,119 tokens)
3. Queen's Gambit with h6 (MCM).pgn - Game #15 (9,540 tokens)
4. EN - Elite Najdorf Repertoire.pgn - Game #3 (8,406 tokens)

Success Criteria:
- All files split successfully
- All chunks ≤7,800 tokens
- Metadata properly linked
- Valid PGN output
"""

import pytest
from pathlib import Path
import chess.pgn

from split_oversized_game import split_oversized_game, count_tokens


# ============================================================================
# Configuration
# ============================================================================

ZLISTO_DIR = Path("/Users/leon/Downloads/ZListo")
MAX_TOKENS = 7800


# ============================================================================
# Helper Functions
# ============================================================================

def load_game_from_file(file_path: Path, game_number: int):
    """
    Load a specific game from a PGN file.

    Args:
        file_path: Path to PGN file
        game_number: Game number to load (1-indexed)

    Returns:
        chess.pgn.Game object or None
    """
    with open(file_path) as f:
        for i in range(game_number):
            game = chess.pgn.read_game(f)
            if not game:
                return None
        return game


def validate_chunk(chunk: dict, max_tokens: int = MAX_TOKENS) -> list:
    """
    Validate a single chunk.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check token count
    if chunk['token_count'] > max_tokens:
        errors.append(f"Chunk exceeds {max_tokens} tokens: {chunk['token_count']}")

    # Check metadata fields
    required_fields = ['parent_game_id', 'chunk_id', 'chunk_type', 'source_file', 'game_number']
    for field in required_fields:
        if field not in chunk['metadata']:
            errors.append(f"Missing metadata field: {field}")

    # Check content not empty
    if not chunk['content'] or len(chunk['content']) == 0:
        errors.append("Chunk content is empty")

    # Verify token count matches actual
    actual_tokens = count_tokens(chunk['content'])
    if abs(actual_tokens - chunk['token_count']) > 10:
        errors.append(f"Token count mismatch: stored={chunk['token_count']}, actual={actual_tokens}")

    return errors


# ============================================================================
# Test 1: Rapport's Stonewall Dutch (41,209 tokens - MONSTER FILE)
# ============================================================================

@pytest.mark.skipif(not ZLISTO_DIR.exists(), reason="ZListo directory not found")
def test_rapport_stonewall_dutch():
    """
    Test the 41K token aggregation file.
    This is the most challenging file with many embedded games.
    """
    file_path = ZLISTO_DIR / "Rapport's Stonewall Dutch - All in One pgn.pgn"

    if not file_path.exists():
        pytest.skip(f"File not found: {file_path}")

    print(f"\n{'='*60}")
    print(f"Testing: Rapport's Stonewall Dutch (Game #1)")
    print(f"{'='*60}")

    # Load game
    game = load_game_from_file(file_path, 1)
    assert game is not None, "Failed to load game"

    # Count original tokens
    original_text = str(game)
    original_tokens = count_tokens(original_text)
    print(f"Original tokens: {original_tokens:,}")

    # Split
    chunks = split_oversized_game(game, file_path.name, 1)

    print(f"Chunks created: {len(chunks)}")

    # Validate all chunks
    all_errors = []
    for i, chunk in enumerate(chunks, 1):
        errors = validate_chunk(chunk)
        if errors:
            all_errors.extend([f"Chunk {i}: {e}" for e in errors])

        print(f"  Chunk {i}: {chunk['metadata']['chunk_type']:15s} {chunk['token_count']:,} tokens")

    # Assertions
    assert len(chunks) > 1, "Should split into multiple chunks"
    assert len(chunks) < 100, f"Too many chunks created: {len(chunks)}"
    assert len(all_errors) == 0, f"Validation errors:\n" + "\n".join(all_errors)

    # Check all chunks under limit
    max_chunk_tokens = max(c['token_count'] for c in chunks)
    print(f"Max chunk size: {max_chunk_tokens:,} tokens")
    assert max_chunk_tokens <= MAX_TOKENS, f"Chunk exceeds limit: {max_chunk_tokens}"

    print(f"✅ SUCCESS - Rapport's Stonewall Dutch split successfully")


# ============================================================================
# Test 2: Correspondence Chess (12,119 tokens)
# ============================================================================

@pytest.mark.skipif(not ZLISTO_DIR.exists(), reason="ZListo directory not found")
def test_correspondence_chess():
    """Test deep correspondence analysis file."""
    file_path = ZLISTO_DIR / "The Correspondence Chess Today.pgn"

    if not file_path.exists():
        pytest.skip(f"File not found: {file_path}")

    print(f"\n{'='*60}")
    print(f"Testing: Correspondence Chess (Game #9)")
    print(f"{'='*60}")

    # Load game #9
    game = load_game_from_file(file_path, 9)
    assert game is not None, "Failed to load game #9"

    # Count original tokens
    original_tokens = count_tokens(str(game))
    print(f"Original tokens: {original_tokens:,}")

    # Split
    chunks = split_oversized_game(game, file_path.name, 9)

    print(f"Chunks created: {len(chunks)}")

    # Validate
    all_errors = []
    for i, chunk in enumerate(chunks, 1):
        errors = validate_chunk(chunk)
        if errors:
            all_errors.extend([f"Chunk {i}: {e}" for e in errors])

        print(f"  Chunk {i}: {chunk['metadata']['chunk_type']:15s} {chunk['token_count']:,} tokens")

    # Assertions
    assert len(chunks) in range(2, 6), f"Expected 2-5 chunks, got {len(chunks)}"
    assert len(all_errors) == 0, f"Validation errors:\n" + "\n".join(all_errors)

    # Check compression effectiveness
    total_chunk_tokens = sum(c['token_count'] for c in chunks)
    if total_chunk_tokens < original_tokens:
        compression_ratio = (original_tokens - total_chunk_tokens) / original_tokens
        print(f"Compression achieved: {compression_ratio:.1%}")

    print(f"✅ SUCCESS - Correspondence Chess split successfully")


# ============================================================================
# Test 3: Queen's Gambit with h6 (9,540 tokens)
# ============================================================================

@pytest.mark.skipif(not ZLISTO_DIR.exists(), reason="ZListo directory not found")
def test_queens_gambit_h6():
    """Test theory-heavy Modern Chess course file."""
    # Try both possible filenames
    file_names = [
        "Queen's Gambit with ...h7-h6*.pgn",
        "Queen's Gambit with h6 (MCM).pgn"
    ]

    file_path = None
    for name in file_names:
        matches = list(ZLISTO_DIR.glob(name))
        if matches:
            file_path = matches[0]
            break

    if not file_path:
        pytest.skip(f"Queen's Gambit file not found")

    print(f"\n{'='*60}")
    print(f"Testing: Queen's Gambit with h6 (Game #15)")
    print(f"{'='*60}")

    # Load game #15
    game = load_game_from_file(file_path, 15)
    assert game is not None, "Failed to load game #15"

    # Count original tokens
    original_tokens = count_tokens(str(game))
    print(f"Original tokens: {original_tokens:,}")

    # Split
    chunks = split_oversized_game(game, file_path.name, 15)

    print(f"Chunks created: {len(chunks)}")

    # Validate
    all_errors = []
    for i, chunk in enumerate(chunks, 1):
        errors = validate_chunk(chunk)
        if errors:
            all_errors.extend([f"Chunk {i}: {e}" for e in errors])

        print(f"  Chunk {i}: {chunk['metadata']['chunk_type']:15s} {chunk['token_count']:,} tokens")

    # Assertions
    assert len(chunks) >= 2, f"Should split into multiple chunks, got {len(chunks)}"
    assert len(chunks) <= 10, f"Too many chunks: {len(chunks)}"
    assert len(all_errors) == 0, f"Validation errors:\n" + "\n".join(all_errors)

    # Verify parent linkage
    parent_ids = {c['metadata']['parent_game_id'] for c in chunks}
    assert len(parent_ids) == 1, "All chunks should share same parent_game_id"

    print(f"✅ SUCCESS - Queen's Gambit h6 split successfully")


# ============================================================================
# Test 4: Elite Najdorf (8,406 tokens)
# ============================================================================

@pytest.mark.skipif(not ZLISTO_DIR.exists(), reason="ZListo directory not found")
def test_elite_najdorf():
    """Test just-over-limit detailed repertoire."""
    # Try glob pattern
    matches = list(ZLISTO_DIR.glob("*EN - Elite Najdorf*.pgn"))
    if not matches:
        matches = list(ZLISTO_DIR.glob("EN - Elite Najdorf Repertoire*.pgn"))

    if not matches:
        pytest.skip(f"Elite Najdorf file not found")

    file_path = matches[0]

    print(f"\n{'='*60}")
    print(f"Testing: Elite Najdorf (Game #3)")
    print(f"{'='*60}")

    # Load game #3
    game = load_game_from_file(file_path, 3)
    assert game is not None, "Failed to load game #3"

    # Count original tokens
    original_tokens = count_tokens(str(game))
    print(f"Original tokens: {original_tokens:,}")

    # Split
    chunks = split_oversized_game(game, file_path.name, 3)

    print(f"Chunks created: {len(chunks)}")

    # Validate
    all_errors = []
    for i, chunk in enumerate(chunks, 1):
        errors = validate_chunk(chunk)
        if errors:
            all_errors.extend([f"Chunk {i}: {e}" for e in errors])

        print(f"  Chunk {i}: {chunk['metadata']['chunk_type']:15s} {chunk['token_count']:,} tokens")

    # Assertions
    assert len(chunks) in range(1, 4), f"Expected 1-3 chunks, got {len(chunks)}"
    assert len(all_errors) == 0, f"Validation errors:\n" + "\n".join(all_errors)

    # Check chunk types
    if len(chunks) == 2:
        assert chunks[0]['metadata']['chunk_type'] in ['single', 'compressed', 'overview']
        assert chunks[1]['metadata']['chunk_type'] in ['variation_split', 'compressed']

    print(f"✅ SUCCESS - Elite Najdorf split successfully")


# ============================================================================
# Test 5: Summary Test (All 4 Files)
# ============================================================================

@pytest.mark.skipif(not ZLISTO_DIR.exists(), reason="ZListo directory not found")
def test_all_four_files_summary():
    """
    Run all 4 files and generate summary report.
    """
    print(f"\n{'='*60}")
    print(f"INTEGRATION TEST SUMMARY")
    print(f"{'='*60}\n")

    test_files = [
        ("Rapport's Stonewall Dutch - All in One pgn.pgn", 1, 41209),
        ("The Correspondence Chess Today.pgn", 9, 12119),
        # Will use glob for these two
    ]

    results = []

    # Test each file
    for i, test_func in enumerate([
        test_rapport_stonewall_dutch,
        test_correspondence_chess,
        test_queens_gambit_h6,
        test_elite_najdorf
    ], 1):
        try:
            test_func()
            results.append(f"Test {i}: PASSED ✅")
        except Exception as e:
            results.append(f"Test {i}: FAILED ❌ - {str(e)}")

    # Print summary
    print(f"\n{'='*60}")
    print("RESULTS:")
    for result in results:
        print(f"  {result}")

    passed = sum(1 for r in results if "PASSED" in r)
    print(f"\n  Total: {passed}/4 tests passed")
    print(f"{'='*60}\n")

    assert passed == 4, f"Only {passed}/4 tests passed"


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
