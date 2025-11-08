"""
PGN Variation Splitter - Split oversized chess games by variation branches
===========================================================================

Based on consensus from Gemini, ChatGPT, and Grok AI partners (November 2025).

Core approach:
- Split oversized games (>7,800 tokens) by variation branches
- Context headers: course metadata + main line up to branch point (Gemini)
- Eval compression: Keep evals only at key nodes (Grok)
- Merge small chunks: Combine chunks <2,000 tokens (Grok)
- Transposition detection: Link chunks reaching same positions (per-game scope)
- Token counting: tiktoken for text-embedding-3-small

Target: ≤7,800 tokens per chunk (leaves 392 token buffer for 8,192 limit)
"""

import io
import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import chess
import chess.pgn
import tiktoken


# ============================================================================
# Token Counting
# ============================================================================

def count_tokens(text: str) -> int:
    """
    Count tokens using tiktoken for text-embedding-3-small model.

    Args:
        text: String to count tokens for

    Returns:
        Number of tokens
    """
    encoding = tiktoken.encoding_for_model("text-embedding-3-small")
    return len(encoding.encode(text))


# ============================================================================
# Eval Compression (Grok's Enhancement)
# ============================================================================

def compress_evals(game: chess.pgn.Game) -> None:
    """
    Compress evaluations by keeping only evals at key nodes.
    Removes redundant evaluations to save 20-30% tokens.

    Keep evals at:
    - Branch points (variations)
    - Significant eval shifts (>0.3)
    - End of lines
    - Every 5-10 moves as checkpoints

    Args:
        game: Game object to compress (modifies tree in-place)
    """
    # Start from first move node
    if not game.variations:
        return

    _compress_evals_recursive(game.variations[0], prev_eval=None, move_counter=0)


def _compress_evals_recursive(node: chess.pgn.GameNode, prev_eval: Optional[float], move_counter: int) -> None:
    """Helper function for recursive eval compression."""
    if not node:
        return

    move_counter += 1
    comment = node.comment

    # Extract eval from comment (format: {+0.5} or {-1.2})
    eval_match = re.search(r'\{([+\-]?\d+\.?\d*)\}', comment)

    if eval_match:
        current_eval = float(eval_match.group(1))

        # Determine if this is a key node
        is_branch_point = len(node.variations) > 1
        is_line_end = not node.variations
        is_checkpoint = move_counter % 7 == 0  # Every 7 moves
        is_significant_shift = (
            prev_eval is not None and
            abs(current_eval - prev_eval) > 0.3
        )

        # Remove eval if not a key node
        if not (is_branch_point or is_line_end or is_checkpoint or is_significant_shift):
            # Remove the eval annotation
            node.comment = re.sub(r'\{[+\-]?\d+\.?\d*\}', '', comment).strip()

        prev_eval = current_eval

    # Recursively compress all variations
    for variation in node.variations:
        _compress_evals_recursive(variation, prev_eval, move_counter)


# ============================================================================
# Context Header Generation (Gemini's Strategy)
# ============================================================================

def generate_context_header(
    game: chess.pgn.Game,
    branch_node: Optional[chess.pgn.GameNode],
    metadata: Dict[str, Any]
) -> str:
    """
    Generate context header for a variation chunk.
    Uses "main line up to branch point" strategy (Gemini's approach).

    Args:
        game: The full game
        branch_node: Node where variation branches (None for overview chunk)
        metadata: Metadata dict with course_name, chapter, section, etc.

    Returns:
        Formatted context header string
    """
    # Extract course hierarchy
    course_name = metadata.get('course_name', 'Unknown Course')
    chapter = metadata.get('chapter', '')
    section = metadata.get('section', '')

    # Build header
    header_parts = [f"Course: {course_name}"]

    if chapter:
        header_parts.append(f"Chapter: {chapter}")
    if section:
        header_parts.append(f"Section: {section}")

    # Add event/site from game headers if available
    event = game.headers.get("Event", "")
    if event:
        header_parts.append(f"Event: {event}")

    # Add main line up to branch point (Gemini's enhancement)
    if branch_node:
        spine_moves = get_spine_to_node(branch_node)
        if spine_moves:
            header_parts.append(f"Main line: {spine_moves}")

    return "\n".join(header_parts) + "\n\n"


def get_spine_to_node(target_node: chess.pgn.GameNode) -> str:
    """
    Get main line moves from root to target node.

    Args:
        target_node: The node to trace back from

    Returns:
        String of moves in SAN format (e.g., "1. e4 c5 2. Nf3 d6")
    """
    path = []
    node = target_node

    # Trace back to root
    while node.parent:
        if node.move:
            path.append(node.san())
        node = node.parent

    # Reverse to get root -> target order
    path.reverse()

    # Format with move numbers
    formatted_moves = []
    for i, move in enumerate(path):
        move_num = (i // 2) + 1
        if i % 2 == 0:  # White's move
            formatted_moves.append(f"{move_num}. {move}")
        else:  # Black's move
            formatted_moves.append(move)

    return " ".join(formatted_moves)


# ============================================================================
# Variation Name Extraction
# ============================================================================

def get_variation_name(node: chess.pgn.GameNode) -> str:
    """
    Get descriptive name for a variation.
    Hybrid approach: move + comment if available.

    Args:
        node: Starting node of variation

    Returns:
        Human-readable variation name
    """
    move = node.san() if node.move else "Start"

    # Check for comment annotation
    if node.comment:
        # Extract first line of comment (avoid full paragraphs)
        first_line = node.comment.split('\n')[0].strip()
        # Remove eval annotations
        clean_comment = re.sub(r'\{[+\-]?\d+\.?\d*\}', '', first_line).strip()
        if clean_comment and len(clean_comment) < 50:
            return f"{move} ({clean_comment})"

    return move


# ============================================================================
# Chunk Merging (Grok's Enhancement)
# ============================================================================

def merge_small_chunks(chunks: List[Dict[str, Any]], min_tokens: int = 2000) -> List[Dict[str, Any]]:
    """
    Merge sequential small chunks to avoid too many tiny chunks.

    Args:
        chunks: List of chunk dicts
        min_tokens: Minimum token count threshold (default 2,000)

    Returns:
        List of merged chunks
    """
    if not chunks:
        return chunks

    merged = []
    current_merge = None

    for chunk in chunks:
        token_count = chunk['token_count']

        if token_count < min_tokens:
            # Chunk is too small - merge it
            if current_merge is None:
                current_merge = chunk.copy()
                # Initialize transpositions if not present
                if 'transpositions' not in current_merge['metadata']:
                    current_merge['metadata']['transpositions'] = []
            else:
                # Merge with previous small chunk
                current_merge['content'] += "\n\n" + chunk['content']
                current_merge['token_count'] += chunk['token_count']

                # Update metadata (combine variation names if both have them)
                if 'variation_name' in chunk['metadata'] and 'variation_name' in current_merge['metadata']:
                    current_merge['metadata']['variation_name'] += f" + {chunk['metadata']['variation_name']}"
                elif 'variation_name' in chunk['metadata']:
                    # First chunk didn't have variation_name, add it now
                    current_merge['metadata']['variation_name'] = chunk['metadata']['variation_name']

                # Merge FENs from both chunks
                if 'fens' in chunk['metadata']:
                    if 'fens' not in current_merge['metadata']:
                        current_merge['metadata']['fens'] = []
                    current_merge['metadata']['fens'].extend(chunk['metadata']['fens'])

                # Update chunk type to indicate merged
                current_merge['metadata']['chunk_type'] = 'merged'
        else:
            # Chunk is large enough
            if current_merge:
                # Finish previous merge
                merged.append(current_merge)
                current_merge = None
            merged.append(chunk)

    # Don't forget last merge if exists
    if current_merge:
        merged.append(current_merge)

    return merged


# ============================================================================
# Main Splitting Logic
# ============================================================================

def split_by_variations(
    game: chess.pgn.Game,
    source_file: str,
    game_number: int,
    max_tokens: int = 7800,
    metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Split game by variation branches at depth 1.
    If still too large, recurse to depth 2+.

    Args:
        game: chess.pgn.Game object
        source_file: Name of source PGN file
        game_number: Game number within file
        max_tokens: Maximum tokens per chunk
        metadata: Additional metadata dict

    Returns:
        List of chunk dicts with content and metadata
    """
    metadata = metadata or {}
    chunks = []
    variation_counter = 0  # Counter to ensure unique chunk IDs

    # Generate parent game ID (stable, collision-resistant)
    parent_game_id = generate_game_id(source_file, game_number)

    # Extract course metadata from PGN headers
    course_metadata = extract_course_metadata(game)
    metadata.update(course_metadata)

    # 1. Create overview chunk (main line + metadata)
    overview_content = generate_overview_chunk(game, metadata)
    overview_tokens = count_tokens(overview_content)

    chunks.append({
        'content': overview_content,
        'token_count': overview_tokens,
        'metadata': {
            'parent_game_id': parent_game_id,
            'chunk_id': f"{parent_game_id}_overview",
            'chunk_type': 'overview',
            'source_file': source_file,
            'game_number': game_number,
            **metadata
        }
    })

    # 2. Split each depth-1 variation into separate chunks
    node = game
    while node and node.variations:
        main_variation = node.variations[0]

        # Process alternative variations (depth 1)
        for i, variation in enumerate(node.variations[1:], start=1):
            variation_counter += 1
            variation_chunks = extract_variation_chunk(
                game=game,
                variation_node=variation,
                parent_game_id=parent_game_id,
                source_file=source_file,
                game_number=game_number,
                metadata=metadata,
                max_tokens=max_tokens,
                depth=1,
                variation_index=variation_counter
            )
            chunks.extend(variation_chunks)
            # Increment counter by number of chunks created (for recursive splits)
            variation_counter += len(variation_chunks) - 1

        node = main_variation

    return chunks


def extract_variation_chunk(
    game: chess.pgn.Game,
    variation_node: chess.pgn.GameNode,
    parent_game_id: str,
    source_file: str,
    game_number: int,
    metadata: Dict[str, Any],
    max_tokens: int,
    depth: int,
    variation_index: int = 0,
    parent_chunk_id: str = None
) -> List[Dict[str, Any]]:
    """
    Extract a single variation as a chunk, with recursive splitting if needed.

    Args:
        game: Full game object
        variation_node: Starting node of variation
        parent_game_id: Parent game identifier
        source_file: Source PGN filename
        game_number: Game number in file
        metadata: Metadata dict
        max_tokens: Token limit
        depth: Current recursion depth
        variation_index: Unique index for this variation (prevents ID collisions)
        parent_chunk_id: Parent chunk ID for hierarchical IDs (used in recursion)

    Returns:
        List of chunk dicts (usually 1, but may be multiple if recursively split)
    """
    # Generate context header
    context_header = generate_context_header(game, variation_node, metadata)

    # Extract variation tree as PGN text
    variation_text = export_variation_to_pgn(variation_node)

    # Combine header + variation
    full_content = context_header + variation_text
    token_count = count_tokens(full_content)

    variation_name = get_variation_name(variation_node)

    # Generate chunk_id hierarchically to prevent collisions in recursive splits
    if parent_chunk_id:
        # Recursive: append to parent chunk ID (e.g., "var_001_002")
        chunk_id = f"{parent_chunk_id}_{variation_index:03d}"
    else:
        # Top-level: use game ID + variation index
        chunk_id = f"{parent_game_id}_var_{variation_index:03d}"

    # Collect FENs from this variation for transposition detection
    board = variation_node.parent.board() if variation_node.parent else chess.Board()
    fens = collect_fens_from_node(variation_node, board)

    # Check if still oversized
    if token_count <= max_tokens:
        # Fits! Return as single chunk
        return [{
            'content': full_content,
            'token_count': token_count,
            'metadata': {
                'parent_game_id': parent_game_id,
                'chunk_id': chunk_id,
                'chunk_type': 'variation_split',
                'variation_name': variation_name,
                'depth': depth,
                'source_file': source_file,
                'game_number': game_number,
                'fens': fens,  # For transposition detection
                **metadata
            }
        }]
    else:
        # Still too large - recurse to next depth
        sub_chunks = []
        node = variation_node
        sub_variation_counter = 0

        while node and node.variations:
            for i, sub_variation in enumerate(node.variations[1:], start=1):
                sub_variation_counter += 1
                recursive_chunks = extract_variation_chunk(
                    game=game,
                    variation_node=sub_variation,
                    parent_game_id=parent_game_id,
                    source_file=source_file,
                    game_number=game_number,
                    metadata=metadata,
                    max_tokens=max_tokens,
                    depth=depth + 1,
                    variation_index=sub_variation_counter,
                    parent_chunk_id=chunk_id  # Pass current chunk_id as parent
                )
                sub_chunks.extend(recursive_chunks)

            node = node.variations[0] if node.variations else None

        return sub_chunks


def generate_overview_chunk(game: chess.pgn.Game, metadata: Dict[str, Any]) -> str:
    """
    Generate overview chunk with game headers and main line.

    Args:
        game: chess.pgn.Game object
        metadata: Metadata dict

    Returns:
        Formatted PGN text for overview
    """
    # Start with course context
    course_name = metadata.get('course_name', 'Unknown Course')
    chapter = metadata.get('chapter', '')

    header = f"[Course] {course_name}\n"
    if chapter:
        header += f"[Chapter] {chapter}\n"

    # Add standard PGN headers
    for key, value in game.headers.items():
        header += f"[{key}] \"{value}\"\n"

    header += "\n"

    # Add main line (no variations)
    mainline = export_mainline(game)

    return header + mainline


def export_mainline(game: chess.pgn.Game) -> str:
    """
    Export only the main line (no variations).

    Args:
        game: chess.pgn.Game object

    Returns:
        Main line as PGN string
    """
    exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=True)
    return game.accept(exporter)


def export_variation_to_pgn(node: chess.pgn.GameNode) -> str:
    """
    Export a variation subtree as PGN text.

    Args:
        node: Starting node of variation

    Returns:
        PGN formatted string
    """
    # Create a temporary game starting from the parent's position
    temp_game = chess.pgn.Game()

    # Set up the board at the position BEFORE this variation
    if node.parent:
        temp_game.setup(node.parent.board())
    else:
        # No parent - start from initial position
        temp_game.setup(chess.Board())

    # Now copy the variation tree starting from this node
    _copy_variation_recursive(temp_game, node)

    # Export as string
    exporter = chess.pgn.StringExporter(headers=False, variations=True, comments=True)
    return temp_game.accept(exporter)


def _copy_variation_recursive(parent: chess.pgn.GameNode, source: chess.pgn.GameNode) -> chess.pgn.GameNode:
    """
    Recursively copy a variation subtree.

    Args:
        parent: Parent node to attach to
        source: Source node to copy from

    Returns:
        The newly created node
    """
    if not source.move:
        return parent

    # Add this move as a variation
    new_node = parent.add_variation(source.move)
    new_node.comment = source.comment
    new_node.nags = source.nags.copy()

    # Recursively copy all child variations
    for child in source.variations:
        _copy_variation_recursive(new_node, child)

    return new_node


def copy_variation_tree(parent: chess.pgn.GameNode, source: chess.pgn.GameNode) -> None:
    """
    Recursively copy variation tree (deprecated - use _copy_variation_recursive).

    Args:
        parent: Parent node to attach to
        source: Source node to copy from
    """
    _copy_variation_recursive(parent, source)


# ============================================================================
# Metadata Extraction
# ============================================================================

def extract_course_metadata(game: chess.pgn.Game) -> Dict[str, Any]:
    """
    Extract course hierarchy from PGN headers.

    Looks for patterns like:
    - [Event "Course Name - Chapter Name"]
    - [Site "Section Name"]
    - Custom tags if present

    Args:
        game: chess.pgn.Game object

    Returns:
        Dict with course_name, chapter, section
    """
    metadata = {}

    event = game.headers.get("Event", "")
    site = game.headers.get("Site", "")

    # Try to parse event as "Course - Chapter"
    if " - " in event:
        parts = event.split(" - ", 1)
        metadata['course_name'] = parts[0].strip()
        metadata['chapter'] = parts[1].strip()
    else:
        metadata['course_name'] = event
        metadata['chapter'] = ""

    # Site often contains section info
    if site:
        metadata['section'] = site

    return metadata


def generate_game_id(source_file: str, game_number: int) -> str:
    """
    Generate stable, collision-resistant game ID.
    Uses SHA-256 with namespace (ChatGPT's approach).

    Args:
        source_file: Source PGN filename
        game_number: Game number within file

    Returns:
        Hex string ID (16 chars)
    """
    namespace = "chess_pgn_game"
    content = f"{namespace}:{source_file}:{game_number}"
    hash_digest = hashlib.sha256(content.encode()).hexdigest()
    return hash_digest[:16]  # First 16 chars (64 bits)


# ============================================================================
# Transposition Detection
# ============================================================================

def collect_fens_from_node(
    node: chess.pgn.GameNode,
    board: chess.Board,
    collect_interval: int = 5
) -> List[Tuple[str, int]]:
    """
    Collect FENs (position fingerprints) from a variation tree.

    Collects FENs at key points:
    - Every N moves (collect_interval, default 5)
    - Branch points (where variations split)
    - End of line

    Args:
        node: Starting node of variation
        board: Chess board at starting position
        collect_interval: Collect FEN every N moves

    Returns:
        List of (FEN, move_number) tuples
    """
    fens = []
    move_counter = 0
    current_node = node
    current_board = board.copy()

    while current_node:
        # Make the move on the board
        if current_node.move:
            try:
                current_board.push(current_node.move)
                move_counter += 1
            except Exception:
                # Illegal move encountered - stop FEN collection
                # This can happen with corrupt PGN files or board state mismatches
                # Return FENs collected so far (may be empty)
                return fens

        # Determine if this is a key collection point
        is_branch_point = len(current_node.variations) > 1
        is_line_end = not current_node.variations
        is_checkpoint = move_counter % collect_interval == 0

        if is_branch_point or is_line_end or is_checkpoint:
            fen = current_board.fen()
            fens.append((fen, move_counter))

        # Move to next node (main line only)
        current_node = current_node.variations[0] if current_node.variations else None

    return fens


def build_transposition_map(chunks: List[Dict[str, Any]]) -> Dict[str, List[Tuple[str, int]]]:
    """
    Build map of FEN -> [(chunk_id, move_number), ...] from all chunks.

    Only includes FENs that appear in 2+ chunks (actual transpositions).

    Args:
        chunks: List of chunk dicts with metadata

    Returns:
        Dict mapping FEN strings to list of (chunk_id, move_number) tuples
    """
    fen_to_chunks: Dict[str, List[Tuple[str, int]]] = {}

    for chunk in chunks:
        chunk_id = chunk['metadata']['chunk_id']
        fens = chunk['metadata'].get('fens', [])

        for fen, move_num in fens:
            if fen not in fen_to_chunks:
                fen_to_chunks[fen] = []
            fen_to_chunks[fen].append((chunk_id, move_num))

    # Filter to only transpositions (positions appearing in 2+ chunks)
    transpositions = {
        fen: chunk_list
        for fen, chunk_list in fen_to_chunks.items()
        if len(chunk_list) >= 2
    }

    return transpositions


def add_transposition_links(
    chunks: List[Dict[str, Any]],
    transposition_map: Dict[str, List[Tuple[str, int]]],
    max_links_per_chunk: int = 10
) -> None:
    """
    Add transposition links to each chunk's metadata.

    For each chunk, finds positions that transpose to other chunks
    and adds the top N transposition links.

    Args:
        chunks: List of chunk dicts (modified in place)
        transposition_map: Map of FEN -> [(chunk_id, move_number), ...]
        max_links_per_chunk: Maximum transpositions to store per chunk
    """
    for chunk in chunks:
        chunk_id = chunk['metadata']['chunk_id']
        fens = chunk['metadata'].get('fens', [])

        transpositions = []

        for fen, move_num in fens:
            if fen in transposition_map:
                # Find chunks that share this position (excluding self)
                linked_chunks = [
                    (cid, mn)
                    for cid, mn in transposition_map[fen]
                    if cid != chunk_id
                ]

                if linked_chunks:
                    transpositions.append({
                        'fen': fen,
                        'move_number': move_num,
                        'linked_chunks': [cid for cid, _ in linked_chunks]
                    })

        # Sort by number of links (most connected first)
        transpositions.sort(key=lambda t: len(t['linked_chunks']), reverse=True)

        # Store top N transpositions
        chunk['metadata']['transpositions'] = transpositions[:max_links_per_chunk]


# ============================================================================
# Main Entry Point
# ============================================================================

def split_oversized_game(
    game: chess.pgn.Game,
    source_file: str,
    game_number: int,
    tokenizer_func=count_tokens,
    max_tokens: int = 7800,
    apply_eval_compression: bool = True,
    merge_small_chunks_enabled: bool = True,
    min_chunk_tokens: int = 2000
) -> List[Dict[str, Any]]:
    """
    Main entry point: Split oversized game into chunks.

    Pipeline:
    1. Try full game (if ≤7,800 tokens, return as-is)
    2. Apply eval compression (Grok) if enabled
    3. If still oversized, split by variations
    4. Merge small chunks (Grok) if enabled

    Args:
        game: chess.pgn.Game object
        source_file: Source PGN filename
        game_number: Game number within file
        tokenizer_func: Function to count tokens (default: count_tokens)
        max_tokens: Maximum tokens per chunk (default: 7,800)
        apply_eval_compression: Whether to compress evals (default: True)
        merge_small_chunks_enabled: Whether to merge small chunks (default: True)
        min_chunk_tokens: Minimum chunk size for merging (default: 2,000)

    Returns:
        List of chunk dicts with content and metadata
    """
    # Extract metadata
    metadata = extract_course_metadata(game)

    # Step 1: Try full game first
    full_game_text = str(game)
    full_game_tokens = tokenizer_func(full_game_text)

    if full_game_tokens <= max_tokens:
        # Fits as single chunk - no splitting needed
        parent_game_id = generate_game_id(source_file, game_number)

        # Collect FENs for transposition detection
        board = chess.Board()
        fens = collect_fens_from_node(game.variations[0], board) if game.variations else []

        return [{
            'content': full_game_text,
            'token_count': full_game_tokens,
            'metadata': {
                'parent_game_id': parent_game_id,
                'chunk_id': parent_game_id,
                'chunk_type': 'single',
                'source_file': source_file,
                'game_number': game_number,
                'fens': fens,
                'transpositions': [],  # No transpositions for single chunk
                **metadata
            }
        }]

    # Step 2: Apply eval compression (Grok's enhancement)
    if apply_eval_compression:
        compress_evals(game)
        compressed_text = str(game)
        compressed_tokens = tokenizer_func(compressed_text)

        # Check if compression was enough
        if compressed_tokens <= max_tokens:
            parent_game_id = generate_game_id(source_file, game_number)

            # Collect FENs for transposition detection
            board = chess.Board()
            fens = collect_fens_from_node(game.variations[0], board) if game.variations else []

            return [{
                'content': compressed_text,
                'token_count': compressed_tokens,
                'metadata': {
                    'parent_game_id': parent_game_id,
                    'chunk_id': parent_game_id,
                    'chunk_type': 'compressed',
                    'source_file': source_file,
                    'game_number': game_number,
                    'compression_applied': True,
                    'fens': fens,
                    'transpositions': [],  # No transpositions for single chunk
                    **metadata
                }
            }]

    # Step 3: Split by variations
    chunks = split_by_variations(
        game=game,
        source_file=source_file,
        game_number=game_number,
        max_tokens=max_tokens,
        metadata=metadata
    )

    # Step 4: Merge small chunks (Grok's enhancement)
    if merge_small_chunks_enabled:
        chunks = merge_small_chunks(chunks, min_tokens=min_chunk_tokens)

    # Step 5: Add transposition links (per-game scope)
    transposition_map = build_transposition_map(chunks)
    add_transposition_links(chunks, transposition_map)

    return chunks


# ============================================================================
# Testing / CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python split_oversized_game.py <pgn_file>")
        sys.exit(1)

    pgn_path = Path(sys.argv[1])

    if not pgn_path.exists():
        print(f"Error: File not found: {pgn_path}")
        sys.exit(1)

    print(f"Processing: {pgn_path.name}")
    print("=" * 60)

    with open(pgn_path) as f:
        game = chess.pgn.read_game(f)

        if not game:
            print("Error: Could not parse PGN game")
            sys.exit(1)

        # Count original tokens
        original_text = str(game)
        original_tokens = count_tokens(original_text)
        print(f"Original tokens: {original_tokens}")

        # Split
        chunks = split_oversized_game(game, pgn_path.name, 1)

        print(f"Chunks created: {len(chunks)}")
        print()

        for i, chunk in enumerate(chunks, 1):
            print(f"Chunk {i}:")
            print(f"  Type: {chunk['metadata']['chunk_type']}")
            print(f"  Tokens: {chunk['token_count']}")
            if 'variation_name' in chunk['metadata']:
                print(f"  Variation: {chunk['metadata']['variation_name']}")
            print()
