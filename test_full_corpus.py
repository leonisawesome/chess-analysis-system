"""
Full Corpus Test - All 1,778 PGN Games
=======================================

Process entire ZListo corpus through the variation splitter and validate results.

Success Criteria:
- All 1,778 games processed
- 100% success rate (0 failures)
- All chunks ≤7,800 tokens
- Comprehensive logging
- Token distribution analysis
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import chess.pgn

from split_oversized_game import split_oversized_game, count_tokens


# ============================================================================
# Configuration
# ============================================================================

ZLISTO_DIR = Path("/Users/leon/Downloads/ZListo")
MAX_TOKENS = 7800
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Log file paths
LOG_DIR = Path(".")
PROCESSING_LOG = LOG_DIR / f"split_processing_{TIMESTAMP}.log"
VALIDATION_LOG = LOG_DIR / f"split_validation_{TIMESTAMP}.log"
SUMMARY_JSON = LOG_DIR / f"split_summary_{TIMESTAMP}.json"


# ============================================================================
# Logging Utilities
# ============================================================================

def log_processing(message: str):
    """Write to processing log."""
    with open(PROCESSING_LOG, 'a') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")
    print(message)


def log_validation(message: str):
    """Write to validation log."""
    with open(VALIDATION_LOG, 'a') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")


def save_summary(data: Dict[str, Any]):
    """Save summary JSON."""
    with open(SUMMARY_JSON, 'w') as f:
        json.dump(data, f, indent=2)


# ============================================================================
# Test: Full Corpus Processing
# ============================================================================

@pytest.mark.skipif(not ZLISTO_DIR.exists(), reason="ZListo directory not found")
def test_full_corpus():
    """
    Process all 1,778 games from ZListo corpus.

    Validates:
    - All games process successfully
    - All chunks ≤7,800 tokens
    - Token distribution
    - Split rate statistics
    """

    log_processing("=" * 80)
    log_processing("FULL CORPUS TEST - Starting")
    log_processing(f"Source Directory: {ZLISTO_DIR}")
    log_processing(f"Max Tokens: {MAX_TOKENS}")
    log_processing("=" * 80)

    # Initialize results tracking
    results = {
        'total_games': 0,
        'total_chunks': 0,
        'single_chunk_games': 0,
        'split_games': 0,
        'failed_games': 0,
        'failures': [],
        'token_stats': {
            'min': float('inf'),
            'max': 0,
            'total': 0,
            'avg': 0
        },
        'chunk_size_distribution': {
            '0-1000': 0,
            '1000-2000': 0,
            '2000-3000': 0,
            '3000-4000': 0,
            '4000-5000': 0,
            '5000-6000': 0,
            '6000-7000': 0,
            '7000-7800': 0,
            'over_7800': 0
        },
        'files_processed': [],
        'split_games_details': []
    }

    # Process all PGN files
    pgn_files = sorted(ZLISTO_DIR.glob("*.pgn"))
    total_files = len(pgn_files)

    log_processing(f"\nFound {total_files} PGN files to process")
    log_processing("")

    for file_idx, pgn_file in enumerate(pgn_files, 1):
        log_processing(f"[{file_idx}/{total_files}] Processing: {pgn_file.name}")

        file_results = {
            'filename': pgn_file.name,
            'games': 0,
            'chunks': 0,
            'split_games': 0
        }

        # Try different encodings (some files use latin-1)
        file_content = None
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'windows-1252']:
            try:
                with open(pgn_file, encoding=encoding) as f:
                    file_content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if file_content is None:
            log_validation(f"ERROR: Could not decode file {pgn_file.name} with any encoding")
            continue

        try:
            import io
            with io.StringIO(file_content) as f:
                game_num = 0

                while True:
                    game = chess.pgn.read_game(f)
                    if not game:
                        break

                    game_num += 1
                    results['total_games'] += 1
                    file_results['games'] += 1

                    try:
                        # Split the game
                        chunks = split_oversized_game(game, pgn_file.name, game_num)

                        num_chunks = len(chunks)
                        results['total_chunks'] += num_chunks
                        file_results['chunks'] += num_chunks

                        # Track single vs split
                        if num_chunks == 1:
                            results['single_chunk_games'] += 1
                        else:
                            results['split_games'] += 1
                            file_results['split_games'] += 1

                            # Log split game details
                            results['split_games_details'].append({
                                'file': pgn_file.name,
                                'game_number': game_num,
                                'num_chunks': num_chunks,
                                'chunk_sizes': [c['token_count'] for c in chunks]
                            })

                            log_processing(f"  Game {game_num}: SPLIT into {num_chunks} chunks")

                        # Validate and track token statistics
                        for chunk in chunks:
                            tokens = chunk['token_count']

                            # Update stats
                            results['token_stats']['min'] = min(results['token_stats']['min'], tokens)
                            results['token_stats']['max'] = max(results['token_stats']['max'], tokens)
                            results['token_stats']['total'] += tokens

                            # Distribution
                            if tokens > MAX_TOKENS:
                                results['chunk_size_distribution']['over_7800'] += 1
                                log_validation(f"ERROR: Chunk exceeds limit: {pgn_file.name} game {game_num} - {tokens} tokens")
                            elif tokens >= 7000:
                                results['chunk_size_distribution']['7000-7800'] += 1
                            elif tokens >= 6000:
                                results['chunk_size_distribution']['6000-7000'] += 1
                            elif tokens >= 5000:
                                results['chunk_size_distribution']['5000-6000'] += 1
                            elif tokens >= 4000:
                                results['chunk_size_distribution']['4000-5000'] += 1
                            elif tokens >= 3000:
                                results['chunk_size_distribution']['3000-4000'] += 1
                            elif tokens >= 2000:
                                results['chunk_size_distribution']['2000-3000'] += 1
                            elif tokens >= 1000:
                                results['chunk_size_distribution']['1000-2000'] += 1
                            else:
                                results['chunk_size_distribution']['0-1000'] += 1

                    except Exception as e:
                        results['failed_games'] += 1
                        error_detail = {
                            'file': pgn_file.name,
                            'game': game_num,
                            'error': str(e)
                        }
                        results['failures'].append(error_detail)
                        log_validation(f"FAILED: {pgn_file.name} game {game_num} - {str(e)}")

        except Exception as e:
            log_validation(f"ERROR reading file {pgn_file.name}: {str(e)}")
            continue

        results['files_processed'].append(file_results)
        log_processing(f"  File complete: {file_results['games']} games, {file_results['chunks']} chunks")

    # Calculate final statistics
    if results['total_chunks'] > 0:
        results['token_stats']['avg'] = results['token_stats']['total'] / results['total_chunks']

    results['split_rate'] = (results['split_games'] / results['total_games'] * 100) if results['total_games'] > 0 else 0

    # Save summary
    save_summary(results)

    # Print final report
    log_processing("")
    log_processing("=" * 80)
    log_processing("CORPUS TEST COMPLETE")
    log_processing("=" * 80)
    log_processing(f"Total Games:        {results['total_games']}")
    log_processing(f"Total Chunks:       {results['total_chunks']}")
    log_processing(f"Single Chunk Games: {results['single_chunk_games']}")
    log_processing(f"Split Games:        {results['split_games']} ({results['split_rate']:.2f}%)")
    log_processing(f"Failed Games:       {results['failed_games']}")
    log_processing("")
    log_processing("Token Statistics:")
    log_processing(f"  Min:     {results['token_stats']['min']}")
    log_processing(f"  Max:     {results['token_stats']['max']}")
    log_processing(f"  Average: {results['token_stats']['avg']:.1f}")
    log_processing("")
    log_processing("Chunk Size Distribution:")
    for range_name, count in results['chunk_size_distribution'].items():
        percentage = (count / results['total_chunks'] * 100) if results['total_chunks'] > 0 else 0
        log_processing(f"  {range_name:15s}: {count:5d} ({percentage:5.2f}%)")
    log_processing("")
    log_processing(f"Logs saved to:")
    log_processing(f"  - {PROCESSING_LOG}")
    log_processing(f"  - {VALIDATION_LOG}")
    log_processing(f"  - {SUMMARY_JSON}")
    log_processing("=" * 80)

    # Assertions
    assert results['total_games'] == 1778, f"Expected 1778 games, got {results['total_games']}"
    assert results['failed_games'] == 0, f"{results['failed_games']} games failed: {results['failures']}"
    assert results['chunk_size_distribution']['over_7800'] == 0, f"Found {results['chunk_size_distribution']['over_7800']} chunks over limit!"

    # Print split games for review
    if results['split_games'] > 0:
        log_processing("\nSplit Games Details:")
        for detail in results['split_games_details']:
            log_processing(f"  {detail['file']} game {detail['game_number']}: {detail['num_chunks']} chunks, sizes: {detail['chunk_sizes']}")


# ============================================================================
# Run Test
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
