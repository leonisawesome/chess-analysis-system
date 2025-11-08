"""
Test Transposition Detection on Real Split Games
=================================================

Tests transposition detection on the 4 actual games that require splitting.
"""

import pytest
import chess.pgn
from pathlib import Path
from split_oversized_game import split_oversized_game


ZLISTO_DIR = Path("/Users/leon/Downloads/ZListo")

# The 4 games that require splitting (after removing Rapport's file)
TEST_FILES = [
    {
        'file': 'EN - Elite Najdorf Repertoire for Black - Part 1.pgn',
        'game_number': 3,
        'expected_chunks': 3
    },
    {
        'file': "Queen's Gambit with ...h7-h6 - Universal Rep. vs. 1.d4, 1.Nf3, 1.Nf3 & 1.c4 - Ioannis Papaioannou (MCM).pgn",
        'game_number': 15,
        'expected_chunks': 5
    },
    {
        'file': "Queen's Gambit with ...h7-h6 - Universal Rep. vs. 1.d4, 1.Nf3, 1.Nf3 & 1.c4 - Ioannis Papaioannou (MCM).pgn",
        'game_number': 24,
        'expected_chunks': 5
    },
    {
        'file': 'The Correspondence Chess Today.pgn',
        'game_number': 9,
        'expected_chunks': 4
    }
]


@pytest.mark.skipif(not ZLISTO_DIR.exists(), reason="ZListo directory not found")
@pytest.mark.parametrize("test_case", TEST_FILES, ids=[
    "Elite Najdorf Game 3",
    "Queen's Gambit Game 15",
    "Queen's Gambit Game 24",
    "Correspondence Chess Game 9"
])
def test_transpositions_in_split_games(test_case):
    """
    Test that transposition detection works on real split games.
    """
    pgn_path = ZLISTO_DIR / test_case['file']

    if not pgn_path.exists():
        pytest.skip(f"File not found: {pgn_path}")

    # Read the specific game
    with open(pgn_path) as f:
        game = None
        for i in range(test_case['game_number']):
            game = chess.pgn.read_game(f)
            if not game:
                pytest.fail(f"Could not read game {test_case['game_number']}")

    # Split the game
    chunks = split_oversized_game(game, test_case['file'], test_case['game_number'])

    # Verify chunk count
    assert len(chunks) == test_case['expected_chunks'], \
        f"Expected {test_case['expected_chunks']} chunks, got {len(chunks)}"

    # Verify all chunks have FENs and transpositions metadata
    for i, chunk in enumerate(chunks):
        assert 'fens' in chunk['metadata'], f"Chunk {i} missing 'fens'"
        assert 'transpositions' in chunk['metadata'], f"Chunk {i} missing 'transpositions'"

        # FENs should not be empty (unless it's an empty variation)
        fens = chunk['metadata']['fens']
        print(f"\nChunk {i} ({chunk['metadata']['chunk_id']}):")
        print(f"  FENs collected: {len(fens)}")
        print(f"  Transpositions: {len(chunk['metadata']['transpositions'])}")

        # Print transposition details
        for trans in chunk['metadata']['transpositions']:
            print(f"    - Move {trans['move_number']}: links to {len(trans['linked_chunks'])} chunks")
            print(f"      Linked: {trans['linked_chunks'][:3]}{'...' if len(trans['linked_chunks']) > 3 else ''}")


@pytest.mark.skipif(not ZLISTO_DIR.exists(), reason="ZListo directory not found")
def test_transposition_summary_all_split_games():
    """
    Generate summary of transpositions found in all 4 split games.
    """
    results = {
        'total_chunks': 0,
        'chunks_with_transpositions': 0,
        'total_transposition_links': 0,
        'max_transpositions_per_chunk': 0,
        'games': []
    }

    for test_case in TEST_FILES:
        pgn_path = ZLISTO_DIR / test_case['file']

        if not pgn_path.exists():
            continue

        # Read the specific game
        with open(pgn_path) as f:
            game = None
            for i in range(test_case['game_number']):
                game = chess.pgn.read_game(f)
                if not game:
                    break

        if not game:
            continue

        # Split the game
        chunks = split_oversized_game(game, test_case['file'], test_case['game_number'])

        game_results = {
            'file': test_case['file'],
            'game_number': test_case['game_number'],
            'chunks': len(chunks),
            'chunks_with_transpositions': 0,
            'total_transposition_links': 0
        }

        for chunk in chunks:
            results['total_chunks'] += 1

            trans = chunk['metadata']['transpositions']
            if len(trans) > 0:
                results['chunks_with_transpositions'] += 1
                game_results['chunks_with_transpositions'] += 1

            total_links = sum(len(t['linked_chunks']) for t in trans)
            results['total_transposition_links'] += total_links
            game_results['total_transposition_links'] += total_links

            results['max_transpositions_per_chunk'] = max(
                results['max_transpositions_per_chunk'],
                len(trans)
            )

        results['games'].append(game_results)

    # Print summary
    print("\n" + "=" * 80)
    print("TRANSPOSITION DETECTION SUMMARY - 4 Split Games")
    print("=" * 80)
    print(f"Total chunks: {results['total_chunks']}")
    print(f"Chunks with transpositions: {results['chunks_with_transpositions']}")
    print(f"Total transposition links: {results['total_transposition_links']}")
    print(f"Max transpositions per chunk: {results['max_transpositions_per_chunk']}")
    print("\nPer-game breakdown:")
    for game in results['games']:
        print(f"\n{game['file']} (game {game['game_number']}):")
        print(f"  Chunks: {game['chunks']}")
        print(f"  Chunks with transpositions: {game['chunks_with_transpositions']}")
        print(f"  Total links: {game['total_transposition_links']}")
    print("=" * 80)

    # Assertions
    assert results['total_chunks'] == 17, f"Expected 17 total chunks (3+5+5+4)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
