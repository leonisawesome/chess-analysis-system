"""
RAG Engine Module

Handles:
- Query execution pipeline (embed → search → rerank)
- Result formatting for web display
- Position extraction from retrieved chunks
- Context preparation for synthesis
"""

import time
from typing import List, Tuple, Dict, Any
from openai import OpenAI
from qdrant_client import QdrantClient

# Import from existing modules
from chess_positions import extract_chess_positions


def execute_rag_query(
    openai_client: OpenAI,
    qdrant_client: QdrantClient,
    query_text: str,
    collection_name: str,
    top_k: int = 100,
    top_n: int = 10,
    embed_func=None,
    search_func=None,
    rerank_func=None
) -> Tuple[List[Tuple[Any, float]], Dict[str, float]]:
    """
    Execute the complete RAG query pipeline.
    
    Args:
        openai_client: OpenAI client instance
        qdrant_client: Qdrant client instance
        query_text: User's query
        collection_name: Qdrant collection name
        top_k: Number of initial candidates to retrieve
        top_n: Number of results after reranking
        embed_func: Embedding generation function
        search_func: Semantic search function
        rerank_func: GPT-5 reranking function
    
    Returns:
        Tuple of (ranked_results, timing_dict)
    """
    timing = {}
    
    # Step 1: Generate embedding
    start = time.time()
    query_vector = embed_func(openai_client, query_text)
    timing['embedding'] = round(time.time() - start, 2)
    print(f"⏱  Embedding: {timing['embedding']}s")
    
    # Step 2: Search Qdrant
    start = time.time()
    candidates = search_func(qdrant_client, query_vector, top_k=top_k)
    timing['search'] = round(time.time() - start, 2)
    print(f"⏱  Qdrant search: {timing['search']}s")
    
    # Step 3: Rerank with GPT-5
    start = time.time()
    ranked_results = rerank_func(openai_client, query_text, candidates, top_k=top_n)
    timing['reranking'] = round(time.time() - start, 2)
    print(f"⏱  GPT-5 reranking: {timing['reranking']}s")
    
    return ranked_results, timing


def format_rag_results(
    ranked_results: List[Tuple[Any, float]],
    query_text: str,
    extract_positions: bool = True
) -> List[Dict[str, Any]]:
    """
    Format RAG search results for web display.
    
    Args:
        ranked_results: List of (candidate, score) tuples from reranking
        query_text: Original query for position relevance filtering
        extract_positions: Whether to extract chess positions from text
    
    Returns:
        List of formatted result dictionaries
    """
    formatted_results = []
    
    for candidate, score in ranked_results:
        payload = candidate.payload
        
        # Extract metadata
        book_name = payload.get('book_name', 'Unknown')
        if book_name.endswith('.epub') or book_name.endswith('.mobi'):
            book_name = book_name[:-5]
        
        text = payload.get('text', '')
        chapter = payload.get('chapter_title', '')
        
        # Extract chess positions if requested
        positions = []
        if extract_positions:
            positions = extract_chess_positions(text, query=query_text)
        
        # Format result
        result = {
            'score': round(score, 1),
            'book_name': book_name,
            'book': book_name,  # Backwards compatibility
            'chapter_title': chapter,
            'chapter': chapter,  # Backwards compatibility
            'text': text,
            'positions': positions,
            'has_positions': len(positions) > 0
        }
        formatted_results.append(result)
    
    return formatted_results


def prepare_synthesis_context(
    formatted_results: List[Dict[str, Any]],
    canonical_fen: str = None,
    top_n: int = 8
) -> List[str]:
    """
    Prepare context chunks for synthesis pipeline with structured source attribution.

    NEW (Phase 5): Adds source type labels for mixed-media RAG (EPUB + PGN).

    Args:
        formatted_results: Formatted RAG results
        canonical_fen: Optional canonical FEN to inject at start
        top_n: Number of top results to include

    Returns:
        List of context strings with source attribution
    """
    context_chunks = []

    for i, result in enumerate(formatted_results[:top_n], start=1):
        # Detect source type based on available metadata
        # EPUB results have 'book_name', PGN results will have 'source_file'
        if 'source_file' in result:
            # PGN source
            source_type = "PGN"
            title = result.get('source_file', 'Unknown Game')
            if 'opening' in result:
                title = f"{result['opening']} ({result['source_file']})"
        else:
            # EPUB source (default)
            source_type = "Book"
            title = result.get('book_name', 'Unknown Book')

        content = result.get('text', '')

        # Format with structured source label
        formatted_chunk = f"[Source {i}: {source_type} - \"{title}\"]\n{content}"
        context_chunks.append(formatted_chunk)

    # Inject canonical FEN if provided
    if canonical_fen:
        context_chunks.insert(0, f"[CANONICAL POSITION: {canonical_fen}]")
        print(f"📋 Injected canonical FEN into synthesis context")

    return context_chunks


def collect_answer_positions(
    formatted_results: List[Dict[str, Any]],
    max_positions: int = 2
) -> List[Dict[str, Any]]:
    """
    Collect chess positions from top sources for answer display.
    
    Args:
        formatted_results: Formatted RAG results
        max_positions: Maximum number of positions to collect
    
    Returns:
        List of position dictionaries
    """
    collected_positions = []
    
    for result in formatted_results[:5]:  # Check top 5 sources
        if result.get('has_positions') and result.get('positions'):
            for pos in result['positions']:
                # Avoid duplicates (same FEN)
                if not any(p['fen'] == pos['fen'] for p in collected_positions):
                    collected_positions.append(pos)
                    if len(collected_positions) >= max_positions:
                        break
        if len(collected_positions) >= max_positions:
            break
    
    return collected_positions


def debug_position_extraction(formatted_results: List[Dict[str, Any]], num_sources: int = 5):
    """
    Debug helper: Print position extraction information.
    
    Args:
        formatted_results: Formatted RAG results
        num_sources: Number of sources to debug
    """
    print("\n=== POSITION EXTRACTION DEBUG ===")
    
    for i, result in enumerate(formatted_results[:num_sources]):
        chunk_text = result.get('text', '')
        print(f"\nSource {i+1}:")
        print(f"  Book: {result.get('book_name', 'unknown')}")
        print(f"  Text preview: {chunk_text[:100]}...")
        
        if 'positions' in result:
            print(f"  ✅ Positions array length: {len(result['positions'])}")
            if len(result['positions']) > 0:
                print(f"     First position: {result['positions'][0]}")
        else:
            print(f"  ❌ No 'positions' key")
        
        if 'has_positions' in result:
            print(f"  has_positions flag: {result['has_positions']}")
        else:
            print(f"  ❌ No 'has_positions' key")
        
        # Try to detect patterns in text
        import re
        fen_pattern = r'[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}'
        moves_pattern = r'1\.\s*e4\s+c5'
        
        if re.search(fen_pattern, chunk_text):
            print(f"  📋 FEN detected in text")
        if re.search(moves_pattern, chunk_text, re.IGNORECASE):
            print(f"  ♟ Moves '1.e4 c5' detected in text")
    
    print("=== END POSITION DEBUG ===\n")
