#!/usr/bin/env python3
"""
Test script for parse_moves_to_fen function
"""

import re
import chess
import chess.pgn


def parse_moves_to_fen(moves_text: str, max_moves: int = 20) -> str:
    """
    Parse move notation and compute FEN after the moves.

    Args:
        moves_text: Text containing chess moves like "1.e4 e5 2.Nf3 Nc6"
        max_moves: Maximum number of moves to parse

    Returns:
        FEN string after the moves, or None if parsing fails
    """
    try:
        # DEBUG: Log input
        print(f"  [parse_moves_to_fen] Input: {repr(moves_text[:100])}")

        # Create a new game
        game = chess.pgn.Game()
        node = game

        # Clean up moves text
        moves_text = moves_text.strip()

        # Try parsing as PGN moves
        # Remove move numbers
        cleaned = re.sub(r'\d+\.+', '', moves_text)
        # Remove comments
        cleaned = re.sub(r'\{[^}]*\}', '', cleaned)
        cleaned = re.sub(r'\([^)]*\)', '', cleaned)

        # Split into tokens
        tokens = cleaned.split()
        print(f"  [parse_moves_to_fen] Tokens: {tokens[:10]}")

        board = chess.Board()
        move_count = 0
        failed_tokens = []

        for token in tokens:
            if move_count >= max_moves:
                break

            # Skip non-move tokens
            if token in ['1-0', '0-1', '1/2-1/2', '*']:
                break

            try:
                # Try to parse as SAN move
                move = board.parse_san(token)
                board.push(move)
                move_count += 1
            except Exception as e:
                # If parsing fails, skip this token
                failed_tokens.append(f"{token}({str(e)[:20]})")
                continue

        print(f"  [parse_moves_to_fen] Parsed {move_count} moves, {len(failed_tokens)} failed")
        if failed_tokens:
            print(f"  [parse_moves_to_fen] Failed tokens: {failed_tokens[:5]}")

        if move_count > 0:
            fen = board.fen()
            print(f"  [parse_moves_to_fen] SUCCESS: {fen[:50]}")
            return fen
        else:
            print(f"  [parse_moves_to_fen] FAIL: move_count = 0")

    except Exception as e:
        print(f"  [parse_moves_to_fen] EXCEPTION: {str(e)}")
        pass

    return None


# Test cases from actual source data
test_cases = [
    "5.Nge2\n1.e4 c5 2.Nc3 Nc6 3.g3 g6 4.Bg2 Bg7 5.Nge2",
    " e5 advance, after which he can attack the e5-pawn.\nAfter\n3.e5 Nd5 4.Nf3 Nc6",
    "1.e4 c5 2.Nf3 Nc6",
    "1.e4 c5",
]

print("=" * 80)
print("TESTING parse_moves_to_fen()")
print("=" * 80)

for i, test in enumerate(test_cases, 1):
    print(f"\nTest Case {i}:")
    print(f"Input text: {repr(test[:60])}...")
    result = parse_moves_to_fen(test)
    print(f"Result: {result}\n")
    print("-" * 80)
