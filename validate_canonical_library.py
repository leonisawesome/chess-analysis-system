#!/usr/bin/env python3
"""
Validate all positions in canonical_positions.json using python-chess library.

Checks:
- All FEN strings are valid
- All positions are legal
- Counts positions by category
- Reports any invalid positions
"""

import json
import chess

def validate_canonical_library():
    """Load and validate all positions in the canonical library."""

    # Load library
    try:
        with open('canonical_positions.json', 'r') as f:
            library = json.load(f)
    except FileNotFoundError:
        print("❌ canonical_positions.json not found!")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return False

    print("=" * 80)
    print("CANONICAL POSITIONS LIBRARY VALIDATION")
    print("=" * 80)
    print()

    total_positions = 0
    invalid_positions = []
    category_counts = {}

    # Validate each category
    for category, positions in library.items():
        category_counts[category] = len(positions)
        total_positions += len(positions)

        print(f"📂 Category: {category} ({len(positions)} positions)")

        for key, position in positions.items():
            fen = position.get('fen')
            caption = position.get('caption', 'No caption')
            tactic = position.get('tactic', 'No tactic')

            # Validate FEN
            try:
                board = chess.Board(fen)

                # Check if position is legal
                if board.is_valid():
                    print(f"  ✅ {key}: Valid")
                else:
                    print(f"  ⚠️  {key}: FEN parses but position is not legal")
                    invalid_positions.append({
                        'category': category,
                        'key': key,
                        'fen': fen,
                        'reason': 'Position not legal'
                    })
            except ValueError as e:
                print(f"  ❌ {key}: Invalid FEN - {str(e)}")
                invalid_positions.append({
                    'category': category,
                    'key': key,
                    'fen': fen,
                    'reason': str(e)
                })

        print()

    # Summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"\n📊 Total positions: {total_positions}")
    print(f"✅ Valid positions: {total_positions - len(invalid_positions)}")
    print(f"❌ Invalid positions: {len(invalid_positions)}")
    print()

    print("📂 Breakdown by category:")
    for category, count in sorted(category_counts.items()):
        print(f"  - {category}: {count}")
    print()

    if invalid_positions:
        print("=" * 80)
        print("INVALID POSITIONS")
        print("=" * 80)
        for pos in invalid_positions:
            print(f"\n❌ {pos['category']}/{pos['key']}")
            print(f"   FEN: {pos['fen']}")
            print(f"   Reason: {pos['reason']}")
        print()
        return False
    else:
        print("=" * 80)
        print("✅ ALL POSITIONS VALID!")
        print("=" * 80)
        print()
        print(f"🎯 Library ready for use with {total_positions} verified positions")
        print("📈 Expanded from 15 to {total_positions} positions")
        print()
        return True

if __name__ == '__main__':
    success = validate_canonical_library()
    exit(0 if success else 1)
