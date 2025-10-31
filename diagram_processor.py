"""
Diagram Processing Module
Extracts and processes chess diagram markers from synthesized text
WITH VALIDATION - validates positions match captions and provides canonical fallbacks
"""

import re
import uuid
import chess
import chess.svg
from chess_positions import parse_moves_to_fen
import json
from diagram_validator import validate_diagram
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load canonical positions library
try:
    with open('canonical_positions.json', 'r') as f:
        CANONICAL_LIBRARY = json.load(f)
    logger.info(f"✓ Loaded canonical library with {sum(len(v) for v in CANONICAL_LIBRARY.values())} positions")
except FileNotFoundError:
    CANONICAL_LIBRARY = {}
    logger.warning("⚠ canonical_positions.json not found, validation will skip fallback")

def extract_fen_from_marker(marker_content):
    """Extract FEN string from diagram marker content."""
    # FEN pattern: 8 ranks separated by /, followed by color, castling, etc.
    fen_pattern = r'([rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}\s+[wb]\s+[-KQkq]+\s+[-a-h0-8]+\s+\d+\s+\d+)'
    match = re.search(fen_pattern, marker_content)
    if match:
        return match.group(1).strip()
    return None

def extract_moves_from_description(description):
    """
    Extract move sequence from diagram description.
    Handles:
    - Multiple sequences with 'OR' (takes first sequence)
    - Move annotations like '!', '?', '!!', '!?', '?!'
    """
    # Handle 'OR' - split and take first valid move sequence
    if ' OR ' in description.upper():
        parts = re.split(r'\s+OR\s+', description, flags=re.IGNORECASE)
        for part in parts:
            # Try each part until we find valid moves
            result = _extract_single_sequence(part)
            if result:
                return result
        return None

    return _extract_single_sequence(description)

def _extract_single_sequence(text):
    """Extract a single move sequence, stripping annotations."""
    # Remove move annotations: !, ?, !!, !?, ?!
    cleaned = re.sub(r'[!?]+', '', text)

    # Extract move sequence
    moves_match = re.search(r'[1-9]\.[a-zA-Z0-9\s\.\-\+#=]+', cleaned)
    if moves_match:
        return moves_match.group(0).strip()
    return None

def generate_svg_from_fen(fen):
    """Generate SVG diagram from FEN string."""
    try:
        board = chess.Board(fen)
        svg = chess.svg.board(board, size=390)
        return svg
    except Exception as e:
        print(f"Warning: Could not generate SVG for FEN '{fen}': {e}")
        return None

def find_canonical_fallback(search_term):
    """Find a canonical position matching the search term."""
    if not CANONICAL_LIBRARY:
        return None

    search_lower = search_term.lower()

    # Search through all categories
    for category, positions in CANONICAL_LIBRARY.items():
        for key, position in positions.items():
            # Match by tactic field or caption
            if (position.get('tactic', '').lower() in search_lower or
                search_lower in position.get('caption', '').lower() or
                category in search_lower):
                logger.info(f"Found canonical match: {category}/{key}")
                return position

    return None

def extract_diagram_markers(text):
    """
    Extract all diagram markers from text and generate SVG.
    Handles both FEN strings and move sequences.
    NEW: Supports caption format [DIAGRAM: <position> | Caption: <description> | TACTIC: <type>]
    WITH VALIDATION: Validates positions and provides fallbacks
    Returns list of diagram objects with id, fen, svg, and caption.
    """
    pattern = r'\[DIAGRAM:\s*([^\]]+)\]'
    matches = re.findall(pattern, text)

    diagram_positions = []
    for match in matches:
        fen = None
        caption = None
        tactic = None
        position_part = match  # Default to full match

        # Check for caption separator (|)
        if '|' in match:
            parts = match.split('|')
            position_part = parts[0].strip()

            # Extract caption from second part
            if len(parts) > 1:
                caption_part = parts[1].strip()
                if caption_part.lower().startswith('caption:'):
                    caption = caption_part[8:].strip()
                else:
                    caption = caption_part
                logger.info(f"[extract_diagram_markers] Found caption: {caption[:50]}...")

            # Extract TACTIC from third part (if present)
            if len(parts) > 2:
                tactic_part = parts[2].strip()
                if tactic_part.lower().startswith('tactic:'):
                    tactic = tactic_part[7:].strip()
                else:
                    tactic = tactic_part
                logger.info(f"[extract_diagram_markers] Found tactic: {tactic}")

        # Strategy 1: Try to extract FEN string directly from position part
        fen = extract_fen_from_marker(position_part)

        if fen:
            # FEN found - use extracted caption, or fallback to moves
            if not caption:
                moves = extract_moves_from_description(position_part)
                caption = moves if moves else f"Position: {fen[:20]}..."
        else:
            # Strategy 2: No FEN, try to extract and parse move sequence
            moves = extract_moves_from_description(position_part)

            if moves:
                # Try to convert moves to FEN
                logger.info(f"[extract_diagram_markers] Parsing moves: {moves}")
                fen = parse_moves_to_fen(moves)

                if fen:
                    # Use extracted caption, or fallback to moves
                    if not caption:
                        caption = moves
                    logger.info(f"[extract_diagram_markers] Successfully parsed moves to FEN")
                else:
                    logger.warning(f"[extract_diagram_markers] Failed to parse moves: {moves}")

        # If we got a FEN (from either strategy), validate and potentially generate SVG
        if fen:
            svg = generate_svg_from_fen(fen)
            diagram_id = str(uuid.uuid4())

            # PHASE 1: Validate diagram
            is_valid, validation_reason = validate_diagram(fen, caption or position_part, tactic)

            if is_valid:
                logger.info(f"✓ Diagram validated: {validation_reason}")
                diagram_positions.append({
                    'id': diagram_id,
                    'fen': fen,
                    'svg': svg,
                    'caption': caption or f"Position: {fen[:20]}...",
                    'tactic': tactic,
                    'validated': True,
                    'validation_reason': validation_reason,
                    'original_marker': f'[DIAGRAM: {match}]'
                })
            else:
                logger.warning(f"✗ Diagram validation failed: {validation_reason}")

                # PHASE 2: Try canonical fallback
                fallback = find_canonical_fallback(tactic or caption or position_part)
                if fallback:
                    logger.info(f"✓ Using canonical fallback position")
                    fallback_svg = generate_svg_from_fen(fallback['fen'])
                    diagram_positions.append({
                        'id': diagram_id,
                        'fen': fallback['fen'],
                        'svg': fallback_svg,
                        'caption': fallback['caption'],
                        'tactic': fallback.get('tactic'),
                        'validated': True,
                        'replaced': True,
                        'original_fen': fen,
                        'validation_reason': f"Replaced: {validation_reason}",
                        'original_marker': f'[DIAGRAM: {match}]'
                    })
                else:
                    logger.warning(f"✗ No canonical fallback found, skipping diagram")
                    # Don't add invalid diagram - better to skip than show wrong position
        else:
            logger.warning(f"[extract_diagram_markers] No FEN or moves found in marker: {match[:50]}")

    return diagram_positions

def replace_markers_with_ids(text, diagram_positions):
    """
    Replace diagram markers with UUID placeholders.
    NON-DESTRUCTIVE: Uses re.sub with specific patterns.
    """
    result = text

    for diagram in diagram_positions:
        # Replace specific marker, not greedy
        original_marker = re.escape(diagram['original_marker'])
        result = re.sub(
            original_marker,
            f'[DIAGRAM_ID:{diagram["id"]}]',
            result,
            count=1
        )

    return result

def wrap_bare_fens(text):
    """
    POST-PROCESSING: Wrap any bare FEN strings that slipped through.
    Catches FENs that aren't already in [DIAGRAM: ...] brackets.
    """
    # FEN pattern: 8 ranks separated by /, followed by color, castling, etc.
    # Simple pattern without problematic variable-width lookbehind
    fen_pattern = r'([rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}\s+[wb]\s+[-KQkq]+\s+[-a-h0-8]+\s+\d+\s+\d+)'

    def wrap_match(match):
        fen = match.group(1)
        # Check if already wrapped by looking at preceding text
        start_pos = match.start()
        # Get preceding 20 characters
        preceding = text[max(0, start_pos - 20):start_pos]
        # If we find [DIAGRAM: in the preceding text, don't wrap again
        if '[DIAGRAM:' in preceding:
            return fen  # Return unchanged
        else:
            return f'[DIAGRAM: {fen}]'  # Wrap it

    return re.sub(fen_pattern, wrap_match, text)
