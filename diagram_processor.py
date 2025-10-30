"""
Diagram Processing Module
Extracts and processes chess diagram markers from synthesized text
"""

import re
import uuid

def extract_moves_from_description(description):
    """Extract move sequence from diagram description."""
    moves_match = re.search(r'[1-9]\.[a-zA-Z0-9\s\.\-\+#=]+', description)
    if moves_match:
        return moves_match.group(0).strip()
    return None

def extract_diagram_markers(text):
    """
    Extract all diagram markers from text.
    NON-DESTRUCTIVE: Uses re.findall, doesn't modify original text.
    """
    pattern = r'\[DIAGRAM:\s*([^\]]+)\]'
    matches = re.findall(pattern, text)
    
    diagram_positions = []
    for match in matches:
        moves = extract_moves_from_description(match)
        if moves:
            diagram_positions.append({
                'moves': moves,
                'original_marker': f'[DIAGRAM: {match}]'
            })
    
    return diagram_positions

def replace_markers_with_ids(text, diagram_positions):
    """
    Replace diagram markers with UUID placeholders.
    NON-DESTRUCTIVE: Uses re.sub with specific patterns.
    """
    result = text
    
    for diagram in diagram_positions:
        diagram_id = str(uuid.uuid4())
        diagram['id'] = diagram_id
        
        # Replace specific marker, not greedy
        original_marker = re.escape(diagram['original_marker'])
        result = re.sub(
            original_marker,
            f'[DIAGRAM_ID:{diagram_id}]',
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

