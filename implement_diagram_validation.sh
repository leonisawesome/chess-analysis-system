#!/bin/bash
# ============================================================================
# DIAGRAM RELEVANCE FIX - Smart Hybrid Implementation (Option C)
# Phase 1: Validation + Phase 2: Canonical Fallback + Phase 3-lite: Optional TACTIC
# Partner Consult: Gemini, ChatGPT, Grok - Unanimous recommendation for validation
# ============================================================================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}DIAGRAM RELEVANCE FIX - EXECUTION LOG${NC}"
echo -e "${BLUE}Start Time: $(date)${NC}"
echo -e "${BLUE}============================================================================${NC}\n"

cd /Users/leon/Downloads/python/chess-analysis-system || exit 1
echo -e "${GREEN}✓ Changed to project directory${NC}\n"

# ============================================================================
# STEP 2: INSTALL PYTHON-CHESS
# ============================================================================
echo -e "${YELLOW}[STEP 2/8] Installing python-chess library...${NC}"

pip install --break-system-packages python-chess --quiet
echo -e "${GREEN}✓ Installed python-chess${NC}\n"

# ============================================================================
# STEP 3: CREATE DIAGRAM_VALIDATOR.PY (PHASE 1)
# ============================================================================
echo -e "${YELLOW}[STEP 3/8] Creating diagram_validator.py...${NC}"

cat > diagram_validator.py << 'PYTHON_EOF'
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

    # Determine pinned side
    pinned_color = chess.BLACK if 'black' in caption_lower else chess.WHITE

    # Check if any piece is pinned
    pinned_squares = []
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.color == pinned_color:
            if board.is_pinned(pinned_color, square):
                pinned_squares.append(square)

    if pinned_squares:
        logger.info(f"✓ Valid pin found: {len(pinned_squares)} piece(s) pinned")
        return (True, f"Pin validated: {len(pinned_squares)} piece(s) pinned")

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
PYTHON_EOF

echo -e "${GREEN}✓ Created diagram_validator.py with fork/pin validation${NC}\n"

# (Continuing in next message due to length...)
