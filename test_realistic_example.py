#!/usr/bin/env python3
"""
Test with realistic chess book text that includes full game context
"""

import re
import chess
import chess.svg


def parse_moves_to_fen(moves_text: str, max_moves: int = 20) -> str:
    """Parse move notation and compute FEN after the moves."""
    try:
        print(f"  [parse_moves_to_fen] Input: {repr(moves_text[:150])}...")

        moves_text = moves_text.strip()
        cleaned = re.sub(r'\d+\.+', '', moves_text)
        cleaned = re.sub(r'\{[^}]*\}', '', cleaned)
        cleaned = re.sub(r'\([^)]*\)', '', cleaned)

        tokens = cleaned.split()
        print(f"  [parse_moves_to_fen] Tokens: {tokens[:15]}...")

        board = chess.Board()
        move_count = 0
        failed_tokens = []

        for token in tokens:
            if move_count >= max_moves:
                break

            if token in ['1-0', '0-1', '1/2-1/2', '*', 'White', 'has', 'a', 'choice', 'between', 'After']:
                continue

            try:
                move = board.parse_san(token)
                board.push(move)
                move_count += 1
                print(f"  ✓ Move {move_count}: {token}")
            except Exception as e:
                failed_tokens.append(f"{token}")
                continue

        print(f"  [parse_moves_to_fen] Parsed {move_count} moves, {len(failed_tokens)} failed")

        if move_count > 0:
            fen = board.fen()
            print(f"  [parse_moves_to_fen] SUCCESS")
            return fen

    except Exception as e:
        print(f"  [parse_moves_to_fen] EXCEPTION: {str(e)}")

    return None


# Realistic text from a chess book - includes full game from move 1
realistic_text = """
The Sicilian Defense is one of Black's most popular responses to 1.e4.
Let's examine a typical line:

1.e4 c5 2.Nf3 Nc6 3.Bb5

This is the Rossolimo Variation. White develops quickly and puts pressure on the c6 knight.
After 3.e5 Nd5 4.Nf3 Nc6 White has a choice between 5.d4 or 5.Bc4.

The move 5.Bc4 is more positional, aiming to control the center.
"""

print("=" * 80)
print("TESTING WITH REALISTIC CHESS BOOK TEXT")
print("=" * 80)
print(f"\nTest text preview:")
print(realistic_text[:200] + "...")

# Simulate the extraction logic from app.py
move_number_pattern = r'\b(\d+)\.\s*[a-hNBRQKO]'
matches = list(re.finditer(move_number_pattern, realistic_text))

print(f"\nFound {len(matches)} move number matches")

# Test extraction for "3.e5" (which appears mid-text)
for i, match in enumerate(matches):
    move_num = match.group(1)
    if move_num == "3":  # Focus on move 3
        print(f"\n{'='*80}")
        print(f"Testing extraction for move {move_num} at position {match.start()}")
        print(f"{'='*80}")

        start_pos = match.start()
        end_pos = min(len(realistic_text), start_pos + 300)
        search_start = max(0, start_pos - 500)

        context_window = realistic_text[search_start:end_pos]

        print(f"\nExtracted context window (500 chars back, 300 forward):")
        print(f"{repr(context_window[:200])}...")

        print("\n" + "-" * 80)
        print("Parsing moves from this window...")
        print("-" * 80)

        fen = parse_moves_to_fen(context_window, max_moves=10)

        if fen:
            board = chess.Board(fen)
            print(f"\n{'='*80}")
            print("✅ SUCCESS - Final position:")
            print("=" * 80)
            print(board)

            halfmove_count = (board.fullmove_number - 1) * 2 + (0 if board.turn else 1)
            print(f"\nParsed {halfmove_count} half-moves (up to move {board.fullmove_number})")
            print(f"It's {'White' if board.turn else 'Black'}'s turn")
        else:
            print("\n❌ FAILED - no FEN returned")

        break  # Just test the first move 3

print("\n" + "=" * 80)
