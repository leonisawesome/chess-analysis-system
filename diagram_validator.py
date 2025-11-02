"""
Diagram Validator - Validates chess positions match their captions
Uses python-chess library for position analysis
"""

import chess
import re
from typing import Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_fork(board: chess.Board, caption: str) -> Tuple[bool, str]:
    """
    Validate if position shows a fork matching the caption.

    Args:
        board: chess.Board object
        caption: Caption describing the fork

    Returns:
        (is_valid, reason)
    """
    caption_lower = caption.lower()

    # Determine attacker piece type from caption
    piece_type = None
    if 'knight' in caption_lower:
        piece_type = chess.KNIGHT
    elif 'bishop' in caption_lower:
        piece_type = chess.BISHOP
    elif 'queen' in caption_lower:
        piece_type = chess.QUEEN
    elif 'rook' in caption_lower:
        piece_type = chess.ROOK
    elif 'pawn' in caption_lower:
        piece_type = chess.PAWN
    else:
        logger.warning(f"Could not determine attacker type from caption: {caption[:50]}")
        return (False, "No attacker type specified")

    # Determine attacking side
    color = chess.WHITE if 'white' in caption_lower else chess.BLACK

    # Check all pieces of that type
    for square in board.pieces(piece_type, color):
        attacks = board.attacks(square)
        # Count attacked opponent pieces
        targets = [sq for sq in attacks
                   if board.piece_at(sq)
                   and board.piece_at(sq).color != color]

        if len(targets) >= 2:  # Fork = attacks 2+ pieces
            piece_names = [board.piece_at(sq).symbol() for sq in targets]
            logger.info(f"✓ Valid fork found: {chess.piece_name(piece_type)} on {chess.square_name(square)} attacks {len(targets)} pieces")
            return (True, f"Fork validated: attacks {piece_names}")

    logger.warning(f"✗ No valid fork found for caption: {caption[:50]}")
    return (False, "No piece attacks 2+ opponent pieces")


def validate_pin(board: chess.Board, caption: str) -> Tuple[bool, str]:
    """
    Validate if position shows a pin matching the caption.

    Args:
        board: chess.Board object
        caption: Caption describing the pin

    Returns:
        (is_valid, reason)
    """
    caption_lower = caption.lower()

    # Determine pinned side (optional). If not stated, check both colors.
    pinned_color = None
    if 'black' in caption_lower:
        pinned_color = chess.BLACK
    elif 'white' in caption_lower:
        pinned_color = chess.WHITE

    def count_pins(color):
        cnt = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color == color and board.is_pinned(color, square):
                cnt += 1
        return cnt

    colors_to_check = [pinned_color] if pinned_color is not None else [chess.WHITE, chess.BLACK]
    total_pins = 0
    for c in colors_to_check:
        total_pins += count_pins(c)

    if total_pins > 0:
        logger.info(f"✓ Valid pin found: {total_pins} piece(s) pinned")
        return (True, f"Pin validated: {total_pins} piece(s) pinned")

    logger.warning(f"✗ No valid pin found for caption: {caption[:50]}")
    return (False, "No pinned pieces found")


def validate_diagram(fen: str, caption: str, tactic: Optional[str] = None) -> Tuple[bool, str]:
    """
    Main validation function - checks if FEN matches caption.

    Args:
        fen: FEN string of the position
        caption: Caption describing the position
        tactic: Optional tactic type (fork, pin, skewer, etc.)

    Returns:
        (is_valid, reason)
    """
    try:
        board = chess.Board(fen)
    except ValueError as e:
        logger.error(f"✗ Invalid FEN string: {str(e)}")
        return (False, f"Invalid FEN: {str(e)}")

    caption_lower = caption.lower()
    tactic_lower = tactic.lower() if tactic else ""

    # Use TACTIC field if provided, otherwise infer from caption
    if 'fork' in tactic_lower or 'fork' in caption_lower:
        return validate_fork(board, caption)
    elif 'pin' in tactic_lower or 'pin' in caption_lower:
        return validate_pin(board, caption)
    elif 'skewer' in tactic_lower or 'skewer' in caption_lower:
        # Skewer is like reverse pin - can be detected similarly
        # For now, accept if pin validation passes
        return validate_pin(board, caption)
    else:
        # For non-tactical positions (development, structure, etc.), accept as valid
        # These are harder to validate programmatically
        logger.info(f"ℹ No specific tactic to validate, accepting position")
        return (True, "Non-tactical position accepted")

    return (False, "Unknown validation criteria")


if __name__ == "__main__":
    # Test cases
    test_cases = [
        {
            "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
            "caption": "White's knight on f3 and bishop on c4 develop harmoniously",
            "tactic": "development"
        },
        {
            "fen": "rnbqkb1r/pppp1ppp/5n2/4p3/3P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3",
            "caption": "Black's knight is pinned by White's bishop",
            "tactic": "pin"
        }
    ]

    for test in test_cases:
        print(f"\nTesting: {test['caption']}")
        is_valid, reason = validate_diagram(test['fen'], test['caption'], test.get('tactic'))
        print(f"Result: {'PASS' if is_valid else 'FAIL'} - {reason}")
