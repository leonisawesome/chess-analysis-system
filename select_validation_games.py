#!/usr/bin/env python3
"""
Select 100 Diverse Games for Validation
Chooses games with maximum opening diversity and clear metadata.
"""

import json
import shutil
from pathlib import Path
from collections import defaultdict, Counter


def select_diverse_games(metadata_file: str = "pgn_metadata.json",
                         source_dir: str = "individual_games",
                         output_dir: str = "validation_games",
                         target_count: int = 100):
    """
    Select diverse games prioritizing:
    1. Unique ECO codes (maximum opening diversity)
    2. Games with results (complete games)
    3. Games with real player names
    """
    # Load metadata
    with open(metadata_file, 'r', encoding='utf-8') as f:
        all_metadata = json.load(f)

    print("="* 80)
    print("SELECTING VALIDATION GAMES")
    print("="* 80)
    print(f"Total games available: {len(all_metadata)}")
    print(f"Target: {target_count} games\n")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Group games by ECO code
    games_by_eco = defaultdict(list)
    for game in all_metadata:
        eco = game.get('eco', 'Unknown')
        if eco != 'Unknown':
            games_by_eco[eco].append(game)

    print(f"Found {len(games_by_eco)} different ECO codes\n")

    # Selection strategy:
    # 1. Take at least one game from each ECO code (up to 45 games)
    # 2. For popular ECO codes, take 2-3 games
    # 3. Prioritize games with results

    selected_games = []
    eco_counts = Counter()

    # First pass: one game per ECO code
    for eco in sorted(games_by_eco.keys()):
        games = games_by_eco[eco]

        # Prioritize games with results
        games_with_result = [g for g in games if g['result'] in ['1-0', '0-1', '1/2-1/2']]

        if games_with_result:
            selected = games_with_result[0]
        else:
            selected = games[0]

        selected_games.append(selected)
        eco_counts[eco] += 1

    print(f"After first pass: {len(selected_games)} games (1 per ECO)")

    # Second pass: add more games from diverse ECOs until we reach 100
    while len(selected_games) < target_count:
        # Find ECOs with fewer representatives
        sorted_ecos = sorted(eco_counts.items(), key=lambda x: x[1])

        added = False
        for eco, count in sorted_ecos:
            if len(selected_games) >= target_count:
                break

            # Get games from this ECO not yet selected
            remaining_games = [g for g in games_by_eco[eco]
                              if g not in selected_games]

            if remaining_games:
                # Prioritize games with results
                games_with_result = [g for g in remaining_games
                                    if g['result'] in ['1-0', '0-1', '1/2-1/2']]

                if games_with_result:
                    selected = games_with_result[0]
                else:
                    selected = remaining_games[0]

                selected_games.append(selected)
                eco_counts[eco] += 1
                added = True

        if not added:
            # No more games to add, break
            break

    print(f"After second pass: {len(selected_games)} games\n")

    # Copy selected games to validation directory
    print(f"Copying {len(selected_games)} games to {output_dir}/...")
    for game in selected_games:
        source_file = Path(source_dir) / game['filename']
        dest_file = output_path / game['filename']
        shutil.copy2(source_file, dest_file)

    # Save selected game metadata
    output_metadata_file = 'validation_games_metadata.json'
    with open(output_metadata_file, 'w', encoding='utf-8') as f:
        json.dump(selected_games, f, indent=2, ensure_ascii=False)

    print(f"✅ Games copied successfully")
    print(f"📄 Metadata saved to: {output_metadata_file}\n")

    # Print statistics
    print("="* 80)
    print("SELECTION SUMMARY")
    print("="* 80)

    print(f"\nTotal selected: {len(selected_games)} games")

    print(f"\nECO distribution:")
    for eco, count in sorted(eco_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {eco}: {count} games")

    if len(eco_counts) > 10:
        print(f"  ... and {len(eco_counts) - 10} more ECO codes")

    # Result distribution
    results = Counter(g['result'] for g in selected_games)
    print(f"\nResults:")
    for result, count in results.items():
        print(f"  {result}: {count} games")

    # Player names (where available)
    named_games = [g for g in selected_games
                   if g['white'] != 'Unknown' and g['black'] not in ['?', 'Unknown']]
    print(f"\nGames with complete player metadata: {len(named_games)}")

    print("="* 80)

    return selected_games


if __name__ == '__main__':
    selected = select_diverse_games(target_count=100)
