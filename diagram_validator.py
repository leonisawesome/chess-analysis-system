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

    # 1) Absolute pins (to king): use python-chess helper
    abs_pins = 0
    for color in [chess.WHITE, chess.BLACK]:
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color == color and board.is_pinned(color, square):
                abs_pins += 1

    if abs_pins > 0:
        logger.info(f"✓ Valid absolute pin(s) found: {abs_pins}")
        return (True, f"Absolute pin validated: {abs_pins} piece(s) pinned")

    # 2) Relative pins (to higher-value piece like queen/rook behind)
    # Heuristic: for each slider (B/R/Q), if along a ray we see: enemy piece then enemy queen/rook/king behind -> relative pin
    def ray_dirs(piece_type):
        if piece_type == chess.BISHOP:
            return [chess.DIAGONAL_NE, chess.DIAGONAL_NW, chess.DIAGONAL_SE, chess.DIAGONAL_SW]
        if piece_type == chess.ROOK:
            return [chess.UP, chess.DOWN, chess.LEFT, chess.RIGHT]
        # queen: both
        return [chess.DIAGONAL_NE, chess.DIAGONAL_NW, chess.DIAGONAL_SE, chess.DIAGONAL_SW, chess.UP, chess.DOWN, chess.LEFT, chess.RIGHT]

    def step(square, direction):
        # chess library doesn't have generic step; emulate by offsets
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        df, dr = 0, 0
        if direction == chess.UP:
            df, dr = 0, 1
        elif direction == chess.DOWN:
            df, dr = 0, -1
        elif direction == chess.LEFT:
            df, dr = -1, 0
        elif direction == chess.RIGHT:
            df, dr = 1, 0
        elif direction == chess.DIAGONAL_NE:
            df, dr = 1, 1
        elif direction == chess.DIAGONAL_NW:
            df, dr = -1, 1
        elif direction == chess.DIAGONAL_SE:
            df, dr = 1, -1
        elif direction == chess.DIAGONAL_SW:
            df, dr = -1, -1
        nf, nr = file + df, rank + dr
        if 0 <= nf <= 7 and 0 <= nr <= 7:
            return chess.square(nf, nr)
        return None

    def find_relative_pin():
        for sq in chess.SQUARES:
            a = board.piece_at(sq)
            if not a or a.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
                continue
            dirs = ray_dirs(a.piece_type)
            for d in dirs:
                s1 = sq
                # march to first blocker
                while True:
                    s1 = step(s1, d)
                    if s1 is None:
                        break
                    p1 = board.piece_at(s1)
                    if p1 is None:
                        continue
                    # must be enemy piece to be potentially pinned
                    if p1.color == a.color:
                        break
                    # march further to see what lies behind
                    s2 = s1
                    while True:
                        s2 = step(s2, d)
                        if s2 is None:
                            break
                        p2 = board.piece_at(s2)
                        if p2 is None:
                            continue
                        # if behind is same color as p1 and is king/queen/rook, count as relative pin
                        if p2.color == p1.color and p2.piece_type in (chess.KING, chess.QUEEN, chess.ROOK):
                            return True
                        # hit another piece; ray blocked
                        break
                    break
        return False

    if find_relative_pin():
        logger.info("✓ Valid relative pin found")
        return (True, "Relative pin validated")

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
