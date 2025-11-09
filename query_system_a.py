#!/usr/bin/env python3
"""
System A Query Interface
Interactive chess knowledge retrieval from 1,052-book corpus
"""

import os
import sys
from typing import List, Dict
from openai import OpenAI
from qdrant_client import QdrantClient


# ============================================================================
# CONFIGURATION
# ============================================================================

EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "chess_production"
QDRANT_PATH = "./qdrant_production_db"
TOP_K = 40  # Candidates for reranking
TOP_N = 5   # Final results to return


# ============================================================================
# QUERY PIPELINE
# ============================================================================

def embed_query(openai_client: OpenAI, query: str) -> List[float]:
    """Generate embedding for query."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    )
    return response.data[0].embedding


def semantic_search(qdrant_client: QdrantClient, query_vector: List[float], top_k: int = 40, collection_name: str = None) -> List[Dict]:
    """Perform semantic search in Qdrant.

    Args:
        qdrant_client: Qdrant client instance
        query_vector: Embedding vector for the query
        top_k: Number of results to return
        collection_name: Optional collection name (defaults to COLLECTION_NAME)

    Returns:
        List of search results from Qdrant
    """
    # Use provided collection_name or fall back to default
    target_collection = collection_name if collection_name is not None else COLLECTION_NAME

    results = qdrant_client.search(
        collection_name=target_collection,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True
    )
    return results


def gpt5_rerank(openai_client: OpenAI, query: str, candidates: List, top_k: int = 5) -> List[tuple]:
    """
    Rerank candidates using GPT-5.

    Returns:
        List of (candidate, score) tuples, sorted by score descending
    """
    # Build prompt - optimized version from validation
    prompt = f"""You are a chess knowledge expert evaluating search results.

Query: "{query}"

Rate each chunk's relevance on a scale of 0-10:
- 10: Perfect answer, directly addresses the question
- 8-9: Highly relevant, addresses most of the question
- 6-7: Somewhat relevant, provides useful context
- 4-5: Tangentially related
- 0-3: Not relevant

Chunks:
"""

    for i, candidate in enumerate(candidates, 1):
        # Handle both EPUB chunks ('text' field) and PGN chunks ('content' field)
        chunk_text = candidate.payload.get('text') or candidate.payload.get('content', '')
        # Truncate long chunks for faster processing
        if len(chunk_text) > 500:
            chunk_text = chunk_text[:500] + "..."

        prompt += f"\n{i}. {chunk_text}\n"

    prompt += "\nProvide scores as a JSON array of numbers, e.g., [9.5, 8.0, 7.5, ...]"

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a precise evaluator. Return only a JSON array of scores."},
                {"role": "user", "content": prompt}
            ]
        )

        scores_text = response.choices[0].message.content.strip()

        # Parse JSON array
        import json
        scores = json.loads(scores_text)

        # Pair candidates with scores and sort
        ranked = list(zip(candidates, scores))
        ranked.sort(key=lambda x: -x[1])  # Sort by score descending

        return ranked[:top_k]

    except Exception as e:
        print(f"Warning: Reranking failed ({e}), falling back to semantic order")
        # Fallback: return top candidates with semantic scores
        return [(c, c.score * 10) for c in candidates[:top_k]]


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def format_results(query: str, ranked_results: List[tuple]) -> str:
    """Format results for display."""
    output = []
    output.append("=" * 80)
    output.append(f"Query: {query}")
    output.append("=" * 80)
    output.append("")
    output.append("Top 5 Results:")
    output.append("")

    for i, (candidate, score) in enumerate(ranked_results, 1):
        payload = candidate.payload

        # Extract metadata
        book_name = payload.get('book_name', 'Unknown')
        # Clean up book name (remove file extension)
        if book_name.endswith('.epub') or book_name.endswith('.mobi'):
            book_name = book_name[:-5]

        text = payload.get('text', '')
        chapter = payload.get('chapter_title', '')

        # Format output
        output.append(f"{i}. [{score:.1f}/10] {chapter[:60]}")
        output.append(f"   Book: {book_name[:70]}")
        output.append(f"   ")

        # Show first 300 characters of text
        display_text = text[:300]
        if len(text) > 300:
            display_text += "..."

        # Indent text
        lines = display_text.split('\n')
        for line in lines[:5]:  # Max 5 lines
            output.append(f"   {line}")

        output.append("")

    output.append("=" * 80)

    return '\n'.join(output)


# ============================================================================
# MAIN QUERY FUNCTION
# ============================================================================

def query_system_a(query: str, openai_client: OpenAI, qdrant_client: QdrantClient, verbose: bool = True) -> List[tuple]:
    """
    Query System A and return ranked results.

    Args:
        query: User question
        openai_client: OpenAI client
        qdrant_client: Qdrant client
        verbose: Print progress

    Returns:
        List of (candidate, score) tuples
    """
    if verbose:
        print(f"\n🔍 Processing query: {query}")
        print(f"   Step 1/3: Embedding query...")

    # 1. Embed query
    query_vector = embed_query(openai_client, query)

    if verbose:
        print(f"   Step 2/3: Searching {COLLECTION_NAME} collection...")

    # 2. Semantic search
    candidates = semantic_search(qdrant_client, query_vector, top_k=TOP_K)

    if verbose:
        print(f"   Step 3/3: Reranking top {TOP_K} candidates with GPT-5...")

    # 3. Rerank with GPT-5
    ranked_results = gpt5_rerank(openai_client, query, candidates, top_k=TOP_N)

    if verbose:
        print(f"   ✅ Query complete\n")

    return ranked_results


# ============================================================================
# CLI INTERFACE
# ============================================================================

def interactive_mode(openai_client: OpenAI, qdrant_client: QdrantClient):
    """Run in interactive mode."""
    print("=" * 80)
    print("SYSTEM A: CHESS KNOWLEDGE QUERY INTERFACE")
    print("=" * 80)
    print(f"Corpus: 357,957 chunks from 1,052 books")
    print(f"Collection: {COLLECTION_NAME}")
    print()
    print("Enter your chess questions below. Type 'quit' or 'exit' to stop.")
    print("=" * 80)
    print()

    while True:
        try:
            query = input("❓ Question: ").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            # Process query
            ranked_results = query_system_a(query, openai_client, qdrant_client, verbose=True)

            # Display results
            print(format_results(query, ranked_results))
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def main():
    """Main entry point."""
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set!")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    # Initialize clients
    openai_client = OpenAI(api_key=api_key)
    qdrant_client = QdrantClient(path=QDRANT_PATH)

    # Check collection exists
    collections = qdrant_client.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        print(f"❌ Error: Collection '{COLLECTION_NAME}' not found!")
        print(f"   Database path: {QDRANT_PATH}")
        sys.exit(1)

    # Check if query provided as command-line argument
    if len(sys.argv) > 1:
        # Single query mode
        query = ' '.join(sys.argv[1:])

        print("=" * 80)
        print("SYSTEM A: CHESS KNOWLEDGE QUERY INTERFACE")
        print("=" * 80)
        print(f"Corpus: 357,957 chunks from 1,052 books")
        print()

        ranked_results = query_system_a(query, openai_client, qdrant_client, verbose=True)
        print(format_results(query, ranked_results))
    else:
        # Interactive mode
        interactive_mode(openai_client, qdrant_client)


if __name__ == '__main__':
    main()
