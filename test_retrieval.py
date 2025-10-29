#!/usr/bin/env python3
"""
Test Retrieval and Calculate Precision@5
Validates semantic search performance on chess instructional content.
"""

import json
import os
from typing import List, Dict, Tuple

from openai import OpenAI
from qdrant_client import QdrantClient


# Configuration
EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "chess_validation"
TOP_K = 5


def load_queries(json_path: str = "validation_queries.json") -> List[Dict]:
    """Load test queries from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['conceptual_queries']


def embed_query(client: OpenAI, query: str) -> List[float]:
    """Embed a query using OpenAI API."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    )
    return response.data[0].embedding


def search_qdrant(qdrant_client: QdrantClient, query_vector: List[float], top_k: int = TOP_K) -> List[Dict]:
    """Search Qdrant for similar chunks."""
    results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k
    )
    return results


def display_results(query: str, query_id: int, results: List) -> None:
    """Display search results for a query."""
    print(f"\n{'='*80}")
    print(f"Query #{query_id}: {query}")
    print(f"{'='*80}\n")

    for i, result in enumerate(results, 1):
        payload = result.payload
        score = result.score

        print(f"{i}. Score: {score:.4f} | Book: {payload['book_name']} | Category: {payload['category']}")
        print(f"   Chapter: {payload['chapter_title']}")
        print(f"   Text preview: {payload['text'][:200]}...")
        print()


def manual_evaluation(query: str, query_id: int, results: List) -> Tuple[int, List[str]]:
    """
    Manually evaluate results for relevance.

    Returns:
        tuple: (relevant_count, list of judgments)
    """
    print(f"\n{'='*80}")
    print(f"EVALUATE Query #{query_id}: {query}")
    print(f"{'='*80}\n")

    judgments = []
    relevant_count = 0

    for i, result in enumerate(results, 1):
        payload = result.payload
        score = result.score

        print(f"\n{i}. Score: {score:.4f}")
        print(f"   Book: {payload['book_name']} ({payload['category']})")
        print(f"   Chapter: {payload['chapter_title']}")
        print(f"   Text: {payload['text'][:300]}...")
        print()

        # Manual judgment
        while True:
            judgment = input(f"   Relevant? (y/n/p for yes/no/partial): ").lower().strip()
            if judgment in ['y', 'n', 'p']:
                break
            print("   Invalid input. Use y/n/p")

        if judgment == 'y':
            judgments.append('relevant')
            relevant_count += 1
        elif judgment == 'p':
            judgments.append('partial')
            relevant_count += 0.5  # Partial credit
        else:
            judgments.append('not_relevant')

    precision = relevant_count / len(results)
    print(f"\nPrecision@{len(results)}: {precision:.2%} ({relevant_count}/{len(results)})")

    return relevant_count, judgments


def run_validation_test(auto_eval: bool = False):
    """
    Run validation test on all queries.

    Args:
        auto_eval: If True, automatically evaluate based on expected sources
    """
    print("=" * 80)
    print("CHESS RAG VALIDATION - RETRIEVAL TEST")
    print("=" * 80)

    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ OPENAI_API_KEY environment variable not set!")
        return

    # Initialize clients
    print("\n1. Initializing clients...")
    openai_client = OpenAI(api_key=api_key)
    qdrant_client = QdrantClient(path="./qdrant_validation_db")

    # Load queries
    print("2. Loading queries...")
    queries = load_queries()
    print(f"   Loaded {len(queries)} test queries")

    # Test each query
    all_results = []
    total_relevant = 0

    print("\n3. Testing retrieval...")
    for query_data in queries:
        query_id = query_data['id']
        query_text = query_data['query']

        print(f"\n   Query {query_id}/{len(queries)}: {query_text[:60]}...")

        # Embed query
        query_vector = embed_query(openai_client, query_text)

        # Search
        results = search_qdrant(qdrant_client, query_vector, top_k=TOP_K)

        # Store results
        all_results.append({
            'query_id': query_id,
            'query': query_text,
            'results': results,
            'expected_sources': query_data.get('expected_sources', []),
            'expected_topics': query_data.get('expected_topics', [])
        })

    # Display all results for manual evaluation
    print("\n" + "=" * 80)
    print("RETRIEVAL RESULTS - REVIEW")
    print("=" * 80)

    evaluation_results = []

    for result_data in all_results:
        query_id = result_data['query_id']
        query = result_data['query']
        results = result_data['results']

        # Display results
        display_results(query, query_id, results)

        if not auto_eval:
            # Manual evaluation
            relevant_count, judgments = manual_evaluation(query, query_id, results)

            evaluation_results.append({
                'query_id': query_id,
                'query': query,
                'relevant_count': relevant_count,
                'judgments': judgments,
                'precision': relevant_count / TOP_K
            })

            total_relevant += relevant_count

    # Calculate overall precision@5
    if not auto_eval:
        avg_precision = total_relevant / (len(queries) * TOP_K)

        print("\n" + "=" * 80)
        print("VALIDATION RESULTS")
        print("=" * 80)
        print(f"\nTotal queries tested: {len(queries)}")
        print(f"Total chunks evaluated: {len(queries) * TOP_K}")
        print(f"Total relevant chunks: {total_relevant}")
        print(f"\n📊 PRECISION@5: {avg_precision:.2%}")
        print()

        # Per-query breakdown
        print("Per-query precision:")
        for eval_result in evaluation_results:
            print(f"   Q{eval_result['query_id']:2d}: {eval_result['precision']:.2%} - {eval_result['query'][:60]}")

        # Success criteria
        print("\n" + "=" * 80)
        if avg_precision >= 0.70:
            print("✅ SUCCESS: Precision@5 >= 70%")
            print("   Recommendation: Proceed with System A (Semantic RAG)")
        else:
            print("⚠️  WARNING: Precision@5 < 70%")
            print("   Recommendation: Iterate on chunking or embedding strategy")
        print("=" * 80)

        # Save results
        output_path = 'validation_results.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'avg_precision_at_5': avg_precision,
                'total_queries': len(queries),
                'total_relevant': total_relevant,
                'per_query_results': evaluation_results
            }, f, indent=2)

        print(f"\n💾 Results saved to: {output_path}")

    else:
        # Auto-evaluation mode (for quick testing)
        print("\n📋 Auto-evaluation mode enabled")
        print("   Use manual mode for accurate precision@5")


def quick_test():
    """Quick test showing top 3 results for first 3 queries only."""
    print("=" * 80)
    print("QUICK RETRIEVAL TEST (First 3 Queries)")
    print("=" * 80)

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ OPENAI_API_KEY environment variable not set!")
        return

    openai_client = OpenAI(api_key=api_key)
    qdrant_client = QdrantClient(path="./qdrant_validation_db")

    queries = load_queries()[:3]  # First 3 only

    for query_data in queries:
        query_id = query_data['id']
        query_text = query_data['query']

        query_vector = embed_query(openai_client, query_text)
        results = search_qdrant(qdrant_client, query_vector, top_k=3)

        display_results(query_text, query_id, results)


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        quick_test()
    else:
        run_validation_test(auto_eval=False)
