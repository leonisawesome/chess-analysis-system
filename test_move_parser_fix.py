#!/usr/bin/env python3
"""
Test script for the fixed move parser
"""

import re
import chess
import chess.svg


def parse_moves_to_fen(moves_text: str, max_moves: int = 20) -> str:
    """
    Parse move notation and compute FEN after the moves.
    """
    try:
        print(f"  [parse_moves_to_fen] Input: {repr(moves_text[:100])}")

        # Clean up moves text
        moves_text = moves_text.strip()

        # Remove move numbers
        cleaned = re.sub(r'\d+\.+', '', moves_text)
        # Remove comments
        cleaned = re.sub(r'\{[^}]*\}', '', cleaned)
        cleaned = re.sub(r'\([^)]*\)', '', cleaned)

        # Split into tokens
        tokens = cleaned.split()
        print(f"  [parse_moves_to_fen] Tokens: {tokens}")

        board = chess.Board()
        move_count = 0
        failed_tokens = []

        for token in tokens:
            if move_count >= max_moves:
                break

            # Skip non-move tokens
            if token in ['1-0', '0-1', '1/2-1/2', '*', 'White', 'has', 'a', 'choice', 'between', 'After']:
                continue

            try:
                # Try to parse as SAN move
                move = board.parse_san(token)
                board.push(move)
                move_count += 1
                print(f"  [parse_moves_to_fen] ✓ Parsed move {move_count}: {token} -> {move}")
            except Exception as e:
                # If parsing fails, skip this token
                failed_tokens.append(f"{token}({str(e)[:20]})")
                continue

        print(f"  [parse_moves_to_fen] Parsed {move_count} moves, {len(failed_tokens)} failed")
        if failed_tokens:
            print(f"  [parse_moves_to_fen] Failed tokens: {failed_tokens[:5]}")

        if move_count > 0:
            fen = board.fen()
            print(f"  [parse_moves_to_fen] SUCCESS: {fen}")
            return fen
        else:
            print(f"  [parse_moves_to_fen] FAIL: move_count = 0")

    except Exception as e:
        print(f"  [parse_moves_to_fen] EXCEPTION: {str(e)}")

    return None


# Test case from user's screenshot
test_text = "After 3.e5 Nd5 4.Nf3 Nc6 White has a choice between 5."

print("=" * 80)
print("TESTING FIXED MOVE PARSER")
print("=" * 80)
print(f"\nTest input: {repr(test_text)}")
print("\n" + "-" * 80)

# Test with context window extraction (simulating the new approach)
move_number_pattern = r'\b(\d+)\.\s*[a-hNBRQKO]'
matches = list(re.finditer(move_number_pattern, test_text))

print(f"\nFound {len(matches)} move number matches:")
for i, match in enumerate(matches):
    print(f"  Match {i+1}: '{match.group(0)}' at position {match.start()}")

if matches:
    match = matches[0]  # Take first match
    start_pos = match.start()
    end_pos = min(len(test_text), start_pos + 200)
    search_start = max(0, start_pos - 100)
    context_window = test_text[search_start:end_pos]

    print(f"\nExtracted context window: {repr(context_window)}")
    print("\n" + "-" * 80)
    print("\nParsing moves...")
    print("-" * 80)

    fen = parse_moves_to_fen(context_window)

    print("\n" + "=" * 80)
    print("RESULT:")
    print("=" * 80)

    if fen:
        print(f"✅ SUCCESS!")
        print(f"Final FEN: {fen}")

        board = chess.Board(fen)
        print(f"\nFinal position:")
        print(board)

        # Count moves parsed
        move_count = board.fullmove_number
        halfmove_count = (move_count - 1) * 2 + (0 if board.turn else 1)
        print(f"\nMoves parsed: {halfmove_count} half-moves (up to move {move_count})")
        print(f"Expected: 4 moves parsed (3.e5, 3...Nd5, 4.Nf3, 4...Nc6)")

        # Check if we got all 4 moves
        if halfmove_count >= 4:
            print("✅ All 4 moves were parsed!")
        else:
            print(f"❌ Only {halfmove_count} moves parsed, expected 4")
    else:
        print(f"❌ FAILED - no FEN returned")

print("\n" + "=" * 80)
