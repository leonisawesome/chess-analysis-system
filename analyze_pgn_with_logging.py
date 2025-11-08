#!/usr/bin/env python3
"""
PGN Analysis with Comprehensive Logging
Re-analysis of /Users/leon/Downloads/ZListo to identify oversized chunks

Logs:
- pgn_analysis_YYYYMMDD_HHMMSS.log: Main analysis log
- oversized_chunks_YYYYMMDD_HHMMSS.log: Detailed oversized chunk tracking
- pgn_summary_YYYYMMDD_HHMMSS.json: Statistical summary
"""

import chess.pgn
import json
import sys
import io
import tiktoken
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

# Create timestamp for log files
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
MAIN_LOG = f"pgn_analysis_{TIMESTAMP}.log"
OVERSIZED_LOG = f"oversized_chunks_{TIMESTAMP}.log"
SUMMARY_JSON = f"pgn_summary_{TIMESTAMP}.json"

# Token limit for OpenAI embedding model
TOKEN_LIMIT = 8192

class LogWriter:
    """Writes to both console and log file"""
    def __init__(self, log_file):
        self.log_file = log_file
        self.log_handle = open(log_file, 'w', encoding='utf-8')

    def write(self, message):
        print(message)
        self.log_handle.write(message + '\n')
        self.log_handle.flush()

    def close(self):
        self.log_handle.close()

def count_tokens(text: str) -> int:
    """Count tokens using tiktoken (same as OpenAI API)"""
    encoding = tiktoken.encoding_for_model("text-embedding-3-small")
    return len(encoding.encode(text))

def parse_pgn_file(pgn_path: Path, log: LogWriter) -> Tuple[List[Dict], Dict]:
    """Parse a single PGN file and return chunks + stats"""
    chunks = []
    stats = {
        'file': str(pgn_path.name),
        'games_total': 0,
        'games_parsed': 0,
        'games_failed': 0,
        'chunks_created': 0,
        'chunks_oversized': 0,
        'oversized_details': [],
        'max_tokens': 0,
        'avg_tokens': 0,
        'total_tokens': 0
    }

    log.write(f"\n{'='*80}")
    log.write(f"Processing: {pgn_path.name}")
    log.write(f"{'='*80}")

    try:
        with open(pgn_path, 'r', encoding='utf-8', errors='ignore') as pgn_file:
            game_number = 0
            token_counts = []

            while True:
                try:
                    game = chess.pgn.read_game(pgn_file)
                    if game is None:
                        break

                    game_number += 1
                    stats['games_total'] += 1

                    # Extract metadata
                    headers = game.headers
                    event = headers.get('Event', '?')
                    white = headers.get('White', '?')
                    black = headers.get('Black', '?')

                    # Generate full PGN text
                    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
                    pgn_text = game.accept(exporter)

                    # Count tokens
                    token_count = count_tokens(pgn_text)
                    token_counts.append(token_count)
                    stats['total_tokens'] += token_count
                    stats['max_tokens'] = max(stats['max_tokens'], token_count)

                    # Create chunk
                    chunk = {
                        'source_file': pgn_path.name,
                        'game_number': game_number,
                        'event': event,
                        'white': white,
                        'black': black,
                        'content': pgn_text,
                        'token_count': token_count,
                        'oversized': token_count > TOKEN_LIMIT
                    }

                    chunks.append(chunk)
                    stats['chunks_created'] += 1
                    stats['games_parsed'] += 1

                    # Track oversized chunks
                    if token_count > TOKEN_LIMIT:
                        stats['chunks_oversized'] += 1
                        oversized_detail = {
                            'game_number': game_number,
                            'tokens': token_count,
                            'excess': token_count - TOKEN_LIMIT,
                            'event': event,
                            'white': white,
                            'black': black
                        }
                        stats['oversized_details'].append(oversized_detail)

                        log.write(f"  ⚠️  OVERSIZED: Game #{game_number} - {token_count:,} tokens ({token_count - TOKEN_LIMIT:,} over limit)")
                        log.write(f"      Event: {event}")
                        log.write(f"      Game: {white} vs {black}")

                    if game_number % 10 == 0:
                        log.write(f"  Processed {game_number} games...")

                except Exception as e:
                    stats['games_failed'] += 1
                    log.write(f"  ❌ Error parsing game #{game_number + 1}: {str(e)}")
                    continue

            # Calculate average
            if token_counts:
                stats['avg_tokens'] = sum(token_counts) / len(token_counts)

            log.write(f"\n✅ Completed: {pgn_path.name}")
            log.write(f"   Games: {stats['games_parsed']}/{stats['games_total']} parsed")
            log.write(f"   Chunks: {stats['chunks_created']} created")
            log.write(f"   Oversized: {stats['chunks_oversized']} chunks")
            log.write(f"   Tokens: {stats['total_tokens']:,} total, {stats['avg_tokens']:.0f} avg, {stats['max_tokens']:,} max")

    except Exception as e:
        log.write(f"❌ Failed to process file: {str(e)}")

    return chunks, stats

def main():
    source_dir = Path("/Users/leon/Downloads/ZListo")

    # Initialize logs
    main_log = LogWriter(MAIN_LOG)
    oversized_log = LogWriter(OVERSIZED_LOG)

    main_log.write(f"PGN Analysis with Comprehensive Logging")
    main_log.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    main_log.write(f"Source: {source_dir}")
    main_log.write(f"Token Limit: {TOKEN_LIMIT:,}")
    main_log.write(f"\nLog Files:")
    main_log.write(f"  - Main: {MAIN_LOG}")
    main_log.write(f"  - Oversized: {OVERSIZED_LOG}")
    main_log.write(f"  - Summary: {SUMMARY_JSON}")

    # Find PGN files
    pgn_files = sorted(source_dir.glob("*.pgn"))
    main_log.write(f"\nFound {len(pgn_files)} PGN files")

    # Process all files
    all_chunks = []
    all_stats = []
    oversized_by_file = defaultdict(list)

    for pgn_file in pgn_files:
        chunks, stats = parse_pgn_file(pgn_file, main_log)
        all_chunks.extend(chunks)
        all_stats.append(stats)

        # Track oversized chunks by file
        if stats['chunks_oversized'] > 0:
            oversized_by_file[stats['file']] = stats['oversized_details']

    # Generate summary
    total_games = sum(s['games_total'] for s in all_stats)
    total_chunks = sum(s['chunks_created'] for s in all_stats)
    total_oversized = sum(s['chunks_oversized'] for s in all_stats)
    total_tokens = sum(s['total_tokens'] for s in all_stats)

    summary = {
        'timestamp': TIMESTAMP,
        'source_directory': str(source_dir),
        'files_processed': len(pgn_files),
        'total_games': total_games,
        'total_chunks': total_chunks,
        'total_oversized': total_oversized,
        'oversized_percentage': (total_oversized / total_chunks * 100) if total_chunks > 0 else 0,
        'total_tokens': total_tokens,
        'avg_tokens_per_chunk': total_tokens / total_chunks if total_chunks > 0 else 0,
        'token_limit': TOKEN_LIMIT,
        'files_with_oversized': len(oversized_by_file),
        'per_file_stats': all_stats,
        'oversized_by_file': dict(oversized_by_file)
    }

    # Write summary
    with open(SUMMARY_JSON, 'w') as f:
        json.dump(summary, f, indent=2)

    # Write oversized details
    oversized_log.write(f"Oversized Chunks Report")
    oversized_log.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    oversized_log.write(f"\n{'='*80}")
    oversized_log.write(f"SUMMARY")
    oversized_log.write(f"{'='*80}")
    oversized_log.write(f"Total Chunks: {total_chunks:,}")
    oversized_log.write(f"Oversized Chunks: {total_oversized:,} ({summary['oversized_percentage']:.1f}%)")
    oversized_log.write(f"Files with Oversized: {len(oversized_by_file)}")

    oversized_log.write(f"\n{'='*80}")
    oversized_log.write(f"OVERSIZED CHUNKS BY FILE")
    oversized_log.write(f"{'='*80}")

    for filename, oversized_list in sorted(oversized_by_file.items()):
        oversized_log.write(f"\n{filename} - {len(oversized_list)} oversized chunks")
        oversized_log.write(f"{'-'*80}")
        for detail in oversized_list:
            oversized_log.write(f"  Game #{detail['game_number']}: {detail['tokens']:,} tokens ({detail['excess']:,} over)")
            oversized_log.write(f"    Event: {detail['event']}")
            oversized_log.write(f"    {detail['white']} vs {detail['black']}")

    # Final summary to console and main log
    main_log.write(f"\n{'='*80}")
    main_log.write(f"FINAL SUMMARY")
    main_log.write(f"{'='*80}")
    main_log.write(f"Files Processed: {len(pgn_files)}")
    main_log.write(f"Total Games: {total_games:,}")
    main_log.write(f"Total Chunks: {total_chunks:,}")
    main_log.write(f"Oversized Chunks: {total_oversized:,} ({summary['oversized_percentage']:.1f}%)")
    main_log.write(f"Files with Oversized: {len(oversized_by_file)}")
    main_log.write(f"Total Tokens: {total_tokens:,}")
    main_log.write(f"Avg Tokens/Chunk: {summary['avg_tokens_per_chunk']:.0f}")

    main_log.write(f"\n📄 Logs written:")
    main_log.write(f"   - {MAIN_LOG}")
    main_log.write(f"   - {OVERSIZED_LOG}")
    main_log.write(f"   - {SUMMARY_JSON}")

    # Close logs
    main_log.close()
    oversized_log.close()

    print(f"\n✅ Analysis complete!")
    print(f"   Review {OVERSIZED_LOG} for oversized chunk details")

if __name__ == "__main__":
    main()
