"""
Chess Position Detection & Parsing Module

Handles:
- FEN string detection in text
- Move notation parsing to FEN
- Chess position extraction from chunks
- Opening-specific position filtering
- Lichess URL generation
"""

import re
import chess
import chess.svg
import urllib.parse


def detect_fen(text: str) -> list:
    """
    Detect FEN strings in text.

    Returns list of (FEN, position_in_text) tuples
    """
    # FEN pattern: 8 ranks separated by slashes, then optional metadata
    # e.g. "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    fen_pattern = r'\b([rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}\s+[wb]\s+(?:K?Q?k?q?|-)\s+(?:[a-h][36]|-)\s+\d+\s+\d+)\b'

    matches = []
    for match in re.finditer(fen_pattern, text):
        fen = match.group(1)
        try:
            # Validate FEN
            chess.Board(fen)
            matches.append((fen, match.start()))
        except:
            continue

    return matches


def parse_moves_to_fen(moves_text: str, max_moves: int = 20) -> str:
    """
    Parse move notation and compute FEN after the moves.

    IMPORTANT: Only parses complete games starting from move 1.
    Skips mid-game fragments to avoid incorrect positions.

    Args:
        moves_text: Text containing chess moves like "1.e4 e5 2.Nf3 Nc6"
        max_moves: Maximum number of moves to parse

    Returns:
        FEN string after the moves, or None if parsing fails
    """
    try:
        # DEBUG: Log input
        print(f"  [parse_moves_to_fen] Input: {repr(moves_text[:100])}")

        # Clean up moves text
        moves_text = moves_text.strip()

        # Find the start of the game (move 1)
        move_1_match = re.search(r'\b1\.\s*[a-hNBRQKO]', moves_text)
        if not move_1_match:
            print(f"  [parse_moves_to_fen] SKIP: No '1.' found, mid-game fragment")
            return None

        # Extract from move 1 onwards
        game_start = move_1_match.start()
        game_text = moves_text[game_start:]
        print(f"  [parse_moves_to_fen] Found '1.' at position {game_start}")

        # Try parsing as PGN moves
        # Remove move numbers
        cleaned = re.sub(r'\d+\.+', '', game_text)
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

        # Require at least 2 successful moves to avoid garbage
        if move_count >= 2:
            fen = board.fen()
            print(f"  [parse_moves_to_fen] SUCCESS: {fen[:50]}")
            return fen
        else:
            print(f"  [parse_moves_to_fen] FAIL: only {move_count} moves parsed (need ≥2)")

    except Exception as e:
        print(f"  [parse_moves_to_fen] EXCEPTION: {str(e)}")
        pass

    return None


def filter_relevant_positions(positions: list, query: str) -> list:
    """
    Filter positions by relevance to query.

    For opening queries (e.g., "Sicilian Defense"), only return positions
    that match the opening characteristics.
    """
    query_lower = query.lower()

    # Sicilian Defense: Look for black c5 pawn
    if "sicilian" in query_lower:
        relevant = []
        for pos in positions:
            try:
                board = chess.Board(pos['fen'])
                # Check if c5 has black pawn (Sicilian indicator)
                piece = board.piece_at(chess.C5)
                if piece and piece.piece_type == chess.PAWN and piece.color == chess.BLACK:
                    relevant.append(pos)
            except:
                continue
        if relevant:
            return relevant

    # French Defense: Look for black e6 pawn and white e4 pawn
    elif "french" in query_lower:
        relevant = []
        for pos in positions:
            try:
                board = chess.Board(pos['fen'])
                e6_piece = board.piece_at(chess.E6)
                e4_piece = board.piece_at(chess.E4)
                if (e6_piece and e6_piece.piece_type == chess.PAWN and e6_piece.color == chess.BLACK and
                    e4_piece and e4_piece.piece_type == chess.PAWN and e4_piece.color == chess.WHITE):
                    relevant.append(pos)
            except:
                continue
        if relevant:
            return relevant

    # For other queries, return all positions
    return positions


def create_lichess_url(fen: str) -> str:
    """
    Create Lichess analysis URL from FEN.

    Returns:
        Lichess analysis URL
    """
    # URL encode the FEN
    fen_encoded = urllib.parse.quote(fen)
    return f"https://lichess.org/analysis/{fen_encoded}"


def extract_chess_positions(text: str, query: str = "") -> list:
    """
    Extract chess positions from text (FEN strings or move sequences).

    Args:
        text: Text to extract positions from
        query: User's query (for relevance filtering)

    Returns:
        List of dict with 'fen', 'svg', 'caption', 'type', 'lichess_url'
    """
    positions = []
    starting_fen = chess.Board().fen()

    # 1. Detect explicit FEN strings
    fens = detect_fen(text)
    for fen, pos in fens:
        try:
            # Skip starting position (not interesting)
            if fen == starting_fen:
                continue

            board = chess.Board(fen)
            svg = chess.svg.board(board, size=350)

            # Extract FULL context for caption (500 chars)
            caption_start = max(0, pos - 250)
            caption_end = min(len(text), pos + 250)
            caption = text[caption_start:caption_end].strip()

            # Create Lichess URL
            lichess_url = create_lichess_url(fen)

            positions.append({
                'fen': fen,
                'svg': svg,
                'caption': caption,
                'type': 'fen',
                'lichess_url': lichess_url
            })
        except Exception as e:
            print(f"  [extract_chess_positions] Failed to generate SVG for FEN: {e}")
            continue

    # 2. Detect move sequences
    move_number_pattern = r'\b(\d+)\.\s*[a-hNBRQKO]'
    seen_positions = set()  # Track FENs we've already added

    for match in re.finditer(move_number_pattern, text):
        start_pos = match.start()

        # Extract context window (300 chars ahead from move number)
        end_pos = min(len(text), start_pos + 300)
        search_start = max(0, start_pos - 500)
        context_window = text[search_start:end_pos]

        # Try to parse this window
        fen = parse_moves_to_fen(context_window)
        if fen:
            try:
                # Skip duplicates
                if fen in seen_positions:
                    continue

                # Skip starting position (not interesting)
                if fen == starting_fen:
                    continue

                board = chess.Board(fen)

                # Count moves parsed
                moves_parsed = board.fullmove_number - 1
                if board.turn == chess.BLACK:
                    moves_parsed += 1

                # Require at least 1 full move (2 half-moves)
                if moves_parsed < 1:
                    continue

                seen_positions.add(fen)
                svg = chess.svg.board(board, size=350)

                # Extract FULL context for caption (500 chars around match)
                caption_start = max(0, start_pos - 250)
                caption_end = min(len(text), start_pos + 250)
                caption = text[caption_start:caption_end].strip()

                # Create Lichess URL
                lichess_url = create_lichess_url(fen)

                positions.append({
                    'fen': fen,
                    'svg': svg,
                    'caption': caption,
                    'type': 'moves',
                    'moves_parsed': moves_parsed,
                    'lichess_url': lichess_url
                })

                # Limit to 5 positions max (will filter down further)
                if len(positions) >= 5:
                    break

            except Exception as e:
                print(f"  [extract_chess_positions] Failed to generate SVG for moves: {e}")
                continue

    # 3. Filter by relevance to query
    if query and positions:
        filtered_positions = filter_relevant_positions(positions, query)
        if filtered_positions:
            positions = filtered_positions

    # Limit to top 3 most relevant positions
    return positions[:3]
