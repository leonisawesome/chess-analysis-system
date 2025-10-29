#!/usr/bin/env python3
"""
Split PGN File into Individual Games
Parses a multi-game PGN file and splits into individual files with metadata extraction.
"""

import chess.pgn
import json
from pathlib import Path


def split_pgn_file(pgn_path: str, output_dir: str = "individual_games"):
    """
    Split PGN file into individual game files and extract metadata.

    Args:
        pgn_path: Path to multi-game PGN file
        output_dir: Directory to save individual games

    Returns:
        List of metadata dicts for all games
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    print("="* 80)
    print("SPLITTING PGN FILE")
    print("="* 80)
    print(f"Input file: {pgn_path}")
    print(f"Output directory: {output_dir}\n")

    all_metadata = []
    game_count = 0

    with open(pgn_path, 'r', encoding='utf-8', errors='ignore') as pgn_file:
        while True:
            # Parse next game
            game = chess.pgn.read_game(pgn_file)

            if game is None:
                break  # End of file

            game_count += 1

            # Extract metadata
            headers = game.headers
            metadata = {
                'game_number': game_count,
                'filename': f'game_{game_count:03d}.pgn',
                'white': headers.get('White', 'Unknown'),
                'black': headers.get('Black', 'Unknown'),
                'event': headers.get('Event', 'Unknown'),
                'site': headers.get('Site', 'Unknown'),
                'date': headers.get('Date', 'Unknown'),
                'round': headers.get('Round', 'Unknown'),
                'result': headers.get('Result', '*'),
                'eco': headers.get('ECO', 'Unknown'),
                'opening': headers.get('Opening', 'Unknown'),
                'plycount': headers.get('PlyCount', 'Unknown'),
            }

            # Count moves
            move_count = 0
            node = game
            while node.variations:
                move_count += 1
                node = node.variations[0]
            metadata['move_count'] = move_count

            # Save individual game file
            game_file = output_path / metadata['filename']
            with open(game_file, 'w', encoding='utf-8') as f:
                exporter = chess.pgn.FileExporter(f)
                game.accept(exporter)

            all_metadata.append(metadata)

            if game_count % 25 == 0:
                print(f"Processed {game_count} games...")

    print(f"\n✅ Split complete: {game_count} games extracted\n")

    # Save metadata to JSON
    metadata_file = 'pgn_metadata.json'
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(all_metadata, f, indent=2, ensure_ascii=False)

    print(f"📄 Metadata saved to: {metadata_file}")

    # Print summary statistics
    print("\n" + "="* 80)
    print("SUMMARY STATISTICS")
    print("="* 80)

    # Count unique values
    from collections import Counter

    whites = Counter(m['white'] for m in all_metadata)
    blacks = Counter(m['black'] for m in all_metadata)
    ecos = Counter(m['eco'] for m in all_metadata if m['eco'] != 'Unknown')
    results = Counter(m['result'] for m in all_metadata)

    print(f"\nTotal games: {game_count}")
    print(f"\nTop 5 White players:")
    for player, count in whites.most_common(5):
        print(f"  {player}: {count} games")

    print(f"\nTop 5 Black players:")
    for player, count in blacks.most_common(5):
        print(f"  {player}: {count} games")

    print(f"\nECO codes: {len(ecos)} different openings")
    print(f"Top 5 ECO codes:")
    for eco, count in ecos.most_common(5):
        print(f"  {eco}: {count} games")

    print(f"\nResults:")
    for result, count in results.items():
        print(f"  {result}: {count} games")

    print("="* 80)

    return all_metadata


if __name__ == '__main__':
    pgn_file = "/Users/leon/Downloads/python/Space Advantage - From the Opening to the Middlegame.pgn"
    metadata = split_pgn_file(pgn_file)
