#!/usr/bin/env python3
"""
TEST PURE SEMANTIC BASELINE (Week 1 Configuration)
No optimizations - just pure semantic search to verify 85% baseline.
"""

import json
from openai import OpenAI
from qdrant_client import QdrantClient


EMBEDDING_MODEL = "text-embedding-3-small"
BASELINE_COLLECTION = "chess_validation"  # Week 1 collection
QDRANT_PATH = "./qdrant_validation_db"


def get_pure_semantic_results(query, openai_client, qdrant_client, top_k=5):
    """Pure semantic search - no optimizations"""

    # Embed query (no expansion)
    query_vector = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    ).data[0].embedding

    # Search (no hybrid, no reranking)
    results = qdrant_client.search(
        collection_name=BASELINE_COLLECTION,
        query_vector=query_vector,
        limit=top_k
    )

    return [
        {
            'score': r.score,
            'book': r.payload.get('book_name', 'unknown'),
            'chapter': r.payload.get('chapter_title', 'unknown'),
            'text': r.payload['text']
        }
        for r in results
    ]


def main():
    print("="*80)
    print("PURE SEMANTIC BASELINE TEST (Week 1 Configuration)")
    print("="*80)
    print("\nConfiguration:")
    print("  ✗ No reranking")
    print("  ✗ No hybrid search")
    print("  ✗ No query expansion")
    print("  ✓ Pure semantic search only")
    print()

    # Load queries
    with open('validation_queries.json', 'r') as f:
        queries_data = json.load(f)
    queries = queries_data['conceptual_queries']

    # Setup clients
    openai_client = OpenAI()
    qdrant_client = QdrantClient(path=QDRANT_PATH)

    # Generate results for all queries
    all_results = []

    for query in queries:
        query_id = query['id']
        query_text = query['query']

        print(f"\n{'='*80}")
        print(f"QUERY {query_id}: {query_text}")
        print("="*80)

        results = get_pure_semantic_results(query_text, openai_client, qdrant_client, top_k=5)

        for i, result in enumerate(results, 1):
            print(f"\n--- RESULT {i} ---")
            print(f"Score: {result['score']:.4f}")
            print(f"Book: {result['book']}")
            print(f"Chapter: {result['chapter']}")
            print(f"\nText preview:")
            text_preview = result['text'][:400]
            print(text_preview)
            if len(result['text']) > 400:
                print("[... truncated ...]")
            print(f"\nJUDGMENT: _____ (y/p/n)")

        all_results.append({
            'query_id': query_id,
            'query': query_text,
            'results': results
        })

    # Save to file for review
    output_file = 'baseline_test_results.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("PURE SEMANTIC BASELINE - MANUAL REVIEW\n")
        f.write("="*80 + "\n\n")
        f.write("Expected precision: 85% (Week 1 baseline)\n")
        f.write("Evaluate each result as y/p/n\n\n")

        for query_data in all_results:
            f.write("="*80 + "\n")
            f.write(f"QUERY {query_data['query_id']}: {query_data['query']}\n")
            f.write("="*80 + "\n\n")

            for i, result in enumerate(query_data['results'], 1):
                f.write(f"--- RESULT {i} ---\n")
                f.write(f"Score: {result['score']:.4f}\n")
                f.write(f"Book: {result['book']}\n")
                f.write(f"Chapter: {result['chapter']}\n\n")
                f.write("Text:\n")
                f.write(result['text'][:600])
                if len(result['text']) > 600:
                    f.write("\n[... truncated ...]")
                f.write("\n\nJUDGMENT: _____ (y/p/n)\n\n")

    print("\n" + "="*80)
    print(f"📄 Results saved to: {output_file}")
    print("\nNext: Manually evaluate all 50 results")
    print("Compare precision to 85% baseline")
    print("="*80)


if __name__ == '__main__':
    main()
