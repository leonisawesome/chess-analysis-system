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

# Feature flag: disable forced tactical canonical replacement by default.
# We still validate and only fallback to canonical when a diagram is invalid.
ENFORCE_TACTICAL_CANONICAL = False

# Honor @canonical/category/id references in [DIAGRAM: ...] markers?
# For dynamic, content-driven diagrams, disable by default.
ALLOW_CANONICAL_REFERENCES = False

# When validation fails but a FEN/SVG exists, keep the original diagram instead of
# replacing it with a canonical fallback. This preserves dynamic variety.
USE_FALLBACK_ON_FAILED_VALIDATION = False

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

def parse_canonical_reference(reference):
    """
    Parse @canonical/category/id references.

    Format: @canonical/category/id
    Example: @canonical/forks/knight_fork_queen_rook

    Returns:
        tuple: (category, id) or (None, None) if not a valid reference
    """
    if not reference.startswith('@canonical/'):
        return None, None

    # Remove @canonical/ prefix
    path = reference[11:]  # len('@canonical/') = 11

    # Split into category/id
    parts = path.split('/', 1)
    if len(parts) != 2:
        logger.warning(f"Invalid canonical reference format: {reference}")
        return None, None

    category, position_id = parts
    return category, position_id

def lookup_canonical_position(category, position_id):
    """
    Look up a position in the canonical library by category and ID.

    Args:
        category: The category name (e.g., 'forks', 'pins')
        position_id: The position ID within the category

    Returns:
        dict: Position data or None if not found
    """
    if not CANONICAL_LIBRARY:
        logger.warning("Canonical library not loaded")
        return None

    if category not in CANONICAL_LIBRARY:
        logger.warning(f"Category '{category}' not found in canonical library")
        logger.info(f"Available categories: {list(CANONICAL_LIBRARY.keys())}")
        return None

    positions = CANONICAL_LIBRARY[category]
    if position_id not in positions:
        logger.warning(f"Position '{position_id}' not found in category '{category}'")
        logger.info(f"Available positions: {list(positions.keys())}")
        return None

    logger.info(f"✓ Found canonical position: {category}/{position_id}")
    return positions[position_id]

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


# ============================================================================
# POST-SYNTHESIS ENFORCEMENT - Tactical Diagram Validation
# ============================================================================

TACTICAL_KEYWORDS = {
    'pin', 'fork', 'skewer', 'discovered', 'deflection', 'decoy',
    'clearance', 'interference', 'removal', 'zwischenzug', 'zugzwang'
}

def infer_category(caption_or_tactic):
    """
    Infer tactical category from caption or tactic field.

    Args:
        caption_or_tactic: Caption text or tactic keyword

    Returns:
        str: Category name or None
    """
    text_lower = caption_or_tactic.lower()

    # Direct category matches
    if 'pin' in text_lower:
        return 'pins'
    elif 'fork' in text_lower:
        return 'forks'
    elif 'skewer' in text_lower:
        return 'skewers'
    elif 'discovered' in text_lower:
        return 'discovered_attacks'
    elif 'deflection' in text_lower or 'deflect' in text_lower:
        return 'deflection'
    elif 'decoy' in text_lower:
        return 'decoy'
    elif 'clearance' in text_lower:
        return 'clearance'
    elif 'interference' in text_lower:
        return 'interference'
    elif 'removal' in text_lower or 'remove' in text_lower:
        return 'removal_of_defender'

    return None

def is_tactical_diagram(caption, tactic=None):
    """
    Check if a diagram represents a tactical concept.

    Args:
        caption: Diagram caption text
        tactic: Optional tactic field from marker

    Returns:
        bool: True if tactical concept detected
    """
    # Check tactic field first
    if tactic and any(keyword in tactic.lower() for keyword in TACTICAL_KEYWORDS):
        return True

    # Check caption
    if caption:
        caption_lower = caption.lower()
        return any(keyword in caption_lower for keyword in TACTICAL_KEYWORDS)

    return False

def enforce_canonical_for_tactics(diagram_positions):
    """
    Post-synthesis enforcement: Replace non-canonical tactical diagrams.

    This function ensures 100% accuracy for tactical concepts by:
    1. Detecting tactical keywords in captions
    2. Checking if diagram uses canonical reference
    3. Auto-replacing with canonical position if not

    Args:
        diagram_positions: List of diagram objects from extract_diagram_markers()

    Returns:
        List of diagram objects with tactical diagrams enforced as canonical
    """
    enforced_positions = []

    for diagram in diagram_positions:
        caption = diagram.get('caption', '')
        tactic = diagram.get('tactic')
        # Check if this diagram came from a canonical reference
        # We can infer this from the presence of 'validated' field set by canonical lookup
        is_from_canonical_reference = diagram.get('replaced', False) or \
                                     ('validation_reason' in diagram and 'canonical' in diagram.get('validation_reason', '').lower())

        # Check if this is a tactical diagram
        if is_tactical_diagram(caption, tactic) and not is_from_canonical_reference:
            logger.warning(f"⚠️ Non-canonical tactical diagram detected: {caption[:50]}...")

            # Infer category from caption or tactic
            category = infer_category(tactic or caption)

            if category:
                # Find canonical fallback
                fallback = find_canonical_fallback(category)

                if fallback:
                    # Replace with canonical position
                    original_fen = diagram.get('fen')
                    diagram['fen'] = fallback['fen']
                    diagram['svg'] = generate_svg_from_fen(fallback['fen'])
                    diagram['caption'] = fallback['caption']
                    diagram['tactic'] = fallback.get('tactic')
                    diagram['enforced'] = True
                    diagram['original_fen'] = original_fen
                    diagram['enforcement_reason'] = f"Non-canonical tactical diagram replaced with {category}"

                    logger.info(f"✓ Enforced canonical: {category}")
                else:
                    logger.warning(f"⚠️ No canonical fallback found for category: {category}")
            else:
                logger.warning(f"⚠️ Could not infer category from: {caption[:50]}")

        enforced_positions.append(diagram)

    return enforced_positions


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
        # Strategy 0: Check for @canonical/ reference first
        if ALLOW_CANONICAL_REFERENCES:
            category, position_id = parse_canonical_reference(position_part.strip())
            if category and position_id:
                # This is a canonical reference - look it up
                canonical_pos = lookup_canonical_position(category, position_id)
            if canonical_pos:
                fen = canonical_pos['fen']
                # Use provided caption if available, otherwise use canonical caption
                if not caption:
                    caption = canonical_pos['caption']
                # Use canonical tactic if not provided
                if not tactic:
                    tactic = canonical_pos.get('tactic')
                logger.info(f"✓ Loaded canonical position: {category}/{position_id}")
            else:
                logger.warning(f"✗ Canonical position not found: {category}/{position_id}")
                # Try fallback by category
                fallback = find_canonical_fallback(category)
                if fallback:
                    fen = fallback['fen']
                    caption = fallback['caption']
                    tactic = fallback.get('tactic')
                    logger.info(f"✓ Using category fallback from {category}")
        else:
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

                if USE_FALLBACK_ON_FAILED_VALIDATION:
                    # PHASE 2 (optional): Try canonical fallback
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
                        logger.warning(f"✗ No canonical fallback found, keeping original diagram (unvalidated)")
                        diagram_positions.append({
                            'id': diagram_id,
                            'fen': fen,
                            'svg': svg,
                            'caption': caption or f"Position: {fen[:20]}...",
                            'tactic': tactic,
                            'validated': False,
                            'validation_reason': validation_reason,
                            'original_marker': f'[DIAGRAM: {match}]'
                        })
                else:
                    # Keep original diagram to preserve dynamic variety
                    diagram_positions.append({
                        'id': diagram_id,
                        'fen': fen,
                        'svg': svg,
                        'caption': caption or f"Position: {fen[:20]}...",
                        'tactic': tactic,
                        'validated': False,
                        'validation_reason': validation_reason,
                        'original_marker': f'[DIAGRAM: {match}]'
                    })
        else:
            logger.warning(f"[extract_diagram_markers] No FEN or moves found in marker: {match[:50]}")

    # POST-SYNTHESIS ENFORCEMENT: Ensure tactical diagrams use canonical positions
    if ENFORCE_TACTICAL_CANONICAL:
        diagram_positions = enforce_canonical_for_tactics(diagram_positions)

    # Deduplicate diagrams (prefer unique FENs) to avoid repeated static boards
    seen_fens = set()
    uniq = []
    for d in diagram_positions:
        fen = d.get('fen')
        if fen and fen in seen_fens:
            continue
        if fen:
            seen_fens.add(fen)
        uniq.append(d)

    return uniq

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
