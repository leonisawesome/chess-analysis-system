"""
Diagram Processing Module

Handles:
- Extraction of [DIAGRAM: ...] markers from synthesized text
- Move sequence parsing from diagram descriptions
- FEN generation and SVG board creation
- Caption generation with context
- Diagram marker replacement with IDs
"""

import re
import chess
import chess.svg
from chess_positions import parse_moves_to_fen, create_lichess_url


def extract_moves_from_description(description: str) -> str:
    """
    Extract move sequence from a diagram description.

    Args:
        description: Text like "after 1.e4 c5 2.Nf3 Nc6"

    Returns:
        Move sequence like "1.e4 c5 2.Nf3 Nc6" or empty string
    """
    # Look for patterns like "after 1.e4 c5 2.Nf3"
    match = re.search(r'after\s+((?:\d+\.\s*)?[a-h0-9NBRQKOx+#=-]+(?:\s+(?:\d+\.\s*)?[a-h0-9NBRQKOx+#=-]+)*)', description, re.IGNORECASE)
    if match:
        moves = match.group(1).strip()
        print(f"  [extract_moves_from_description] Input description: {repr(description)}")
        print(f"  [extract_moves_from_description] Extracted moves: {repr(moves)}")
        print(f"  [extract_moves_from_description] Move length: {len(moves)} chars")
        return moves

    # Try direct pattern matching (move numbers with moves)
    match = re.search(r'(\d+\.\s*[a-hNBRQKO][^\]]*)', description)
    if match:
        moves = match.group(1).strip()
        print(f"  [extract_moves_from_description] Extracted (direct): {moves}")
        return moves

    print(f"  [extract_moves_from_description] No moves found in: {description[:50]}")
    return ""


def is_fen_string(text: str) -> bool:
    """
    Check if a string is a FEN position.

    Args:
        text: String to check

    Returns:
        True if text looks like a FEN string
    """
    # FEN has 6 space-separated fields
    parts = text.strip().split()
    if len(parts) < 4:
        return False

    # First part should contain piece placement (letters and numbers with slashes)
    piece_placement = parts[0]
    if '/' not in piece_placement:
        return False

    # Should have 8 ranks (7 slashes)
    if piece_placement.count('/') != 7:
        return False

    # Second part should be 'w' or 'b'
    if parts[1] not in ['w', 'b']:
        return False

    return True


def extract_diagram_markers(synthesized_text: str) -> list:
    """
    Find all [DIAGRAM: ...] markers in text and extract move sequences or FENs.

    Args:
        synthesized_text: Text containing [DIAGRAM: ...] markers

    Returns:
        List of dicts with marker, description, fen, svg, lichess_url
    """
    pattern = r'\[DIAGRAM:\s*([^\]]+)\]'
    matches = re.findall(pattern, synthesized_text)

    print(f"\n{'='*60}")
    print(f"EXTRACTING DIAGRAM MARKERS")
    print(f"{'='*60}")
    print(f"Found {len(matches)} diagram markers in synthesis output")

    diagrams = []
    for i, match in enumerate(matches):
        print(f"\n  Diagram {i+1}: {match[:60]}...")

        # Extract section context for caption
        marker_pos = synthesized_text.find(f'[DIAGRAM: {match}]')
        section_title = ''
        if marker_pos > 0:
            # Look backward for nearest ## or ### header
            text_before = synthesized_text[:marker_pos]
            # Prioritize ### (subsection) headers like "### Najdorf Variation"
            subsection_headers = re.findall(r'###\s+([^\n]+)', text_before)
            if subsection_headers:
                section_title = subsection_headers[-1].strip()
            else:
                # Fall back to ## headers if no ### found
                section_headers = re.findall(r'##\s+([^\n]+)', text_before)
                if section_headers:
                    section_title = section_headers[-1].strip()

        # If section title is generic, try to extract variation name from nearby text
        if section_title and section_title in ['Main Variations', 'Strategic Themes', 'Overview']:
            # Look for variation names in text around the diagram
            context_window = synthesized_text[max(0, marker_pos-500):min(len(synthesized_text), marker_pos+100)]

            # Common variation patterns
            variation_patterns = [
                r'(Open Sicilian)',
                r'(Alapin Variation)',
                r'(Closed Sicilian)',
                r'(Grand Prix Attack)',
                r'(Dragon Variation)',
                r'(Najdorf Variation)',
                r'(Sveshnikov Variation)',
                r'(Accelerated Dragon)',
            ]

            for pattern in variation_patterns:
                match_var = re.search(pattern, context_window, re.IGNORECASE)
                if match_var:
                    section_title = match_var.group(1)
                    break

        # Extract brief description following the diagram marker
        description = ''
        marker_end = marker_pos + len(f'[DIAGRAM: {match}]')
        context_after = synthesized_text[marker_end:marker_end + 300]
        # Get first sentence or two
        # Split on sentence boundaries, but not on abbreviations
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', context_after)
        if sentences and len(sentences) >= 2:
            # Take first 2-3 sentences
            description = ' '.join(sentences[:3])
            if not description.endswith(('.', '!', '?')):
                description += '.'
        elif sentences:
            description = sentences[0]
            if not description.endswith(('.', '!', '?')):
                description += '.'

        # Determine if marker contains FEN or move sequence
        fen = None
        if is_fen_string(match):
            # Direct FEN string (for middlegame concepts)
            print(f"  → Detected FEN string")
            fen = match.strip()
        else:
            # Move sequence (for openings)
            print(f"  → Extracting moves from description")
            moves = extract_moves_from_description(match)
            if moves:
                # Try to parse moves to FEN
                fen = parse_moves_to_fen(moves)
                if not fen:
                    print(f"  ❌ Failed to parse moves for diagram {i+1}")
            else:
                print(f"  ❌ No moves extracted from diagram {i+1}")

        # Create diagram if we have a valid FEN
        if fen:
            try:
                board = chess.Board(fen)
                svg = chess.svg.board(board, size=350)
                lichess_url = create_lichess_url(fen)

                # Format: Variation Name > Moves > Description
                caption_parts = []
                if section_title:
                    caption_parts.append(section_title)
                caption_parts.append(match)  # The moves or FEN
                if description:
                    caption_parts.append(description)
                caption = '\n'.join(caption_parts)

                diagrams.append({
                    'marker': f'[DIAGRAM: {match}]',
                    'description': match,
                    'fen': fen,
                    'svg': svg,
                    'lichess_url': lichess_url,
                    'caption': caption
                })
                print(f"  ✅ Successfully parsed diagram {i+1}")
            except Exception as e:
                print(f"  ❌ Failed to create board for diagram {i+1}: {e}")

    print(f"\n{'='*60}")
    print(f"Extracted {len(diagrams)} valid diagrams")
    print(f"{'='*60}\n")

    return diagrams


def replace_markers_with_ids(synthesized_text: str, diagrams: list) -> str:
    """
    Replace [DIAGRAM: ...] with [DIAGRAM_ID_0], [DIAGRAM_ID_1], etc.

    Args:
        synthesized_text: Text containing [DIAGRAM: ...] markers
        diagrams: List of diagram dicts from extract_diagram_markers()

    Returns:
        Text with markers replaced by IDs
    """
    modified_text = synthesized_text
    for i, diagram in enumerate(diagrams):
        marker = diagram['marker']
        placeholder = f'[DIAGRAM_ID_{i}]'
        modified_text = modified_text.replace(marker, placeholder, 1)
        print(f"  Replaced: {marker[:50]}... -> {placeholder}")

    return modified_text
