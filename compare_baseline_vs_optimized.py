#!/usr/bin/env python3
"""
Compare Baseline (Week 1) vs Optimized results for specific queries
"""

from openai import OpenAI
from qdrant_client import QdrantClient


EMBEDDING_MODEL = "text-embedding-3-small"

# Query 4: "How do I create weaknesses in my opponent's position?"
# Baseline: 90% precision (4y, 1p)
# Optimized: 20% precision (2p, 3n) - MAJOR REGRESSION

TEST_QUERY = "How do I create weaknesses in my opponent's position?"


def get_baseline_results(query):
    """Get top 5 from baseline system (pure semantic)"""
    client = OpenAI()
    qdrant = QdrantClient(path="./qdrant_validation_db")

    query_vector = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    ).data[0].embedding

    results = qdrant.search(
        collection_name="chess_validation",
        query_vector=query_vector,
        limit=5
    )

    return [
        {
            'score': r.score,
            'book': r.payload.get('book_name', 'unknown'),
            'text_preview': r.payload['text'][:200]
        }
        for r in results
    ]


def get_optimized_results(query):
    """Get top 5 from optimized system (hybrid + reranking)"""
    from rank_bm25 import BM25Okapi
    import numpy as np
    import json
    import sqlite3

    client = OpenAI()
    qdrant = QdrantClient(path="./qdrant_full_validation")

    # Load chunks for BM25
    with open('validation_chunks.json', 'r') as f:
        chunks = json.load(f)

    # Load quality scores
    conn = sqlite3.connect('epub_analysis.db')
    cursor = conn.cursor()
    cursor.execute("SELECT filename, tier, score FROM epub_analysis WHERE tier IS NOT NULL")
    quality_map = {}
    for filename, tier, score in cursor.fetchall():
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        quality_map[base_name] = {'tier': tier, 'score': score}
    conn.close()

    TIER_MULTIPLIERS = {'HIGH': 1.2, 'MEDIUM': 1.0, 'LOW': 0.8}

    # Query expansion
    expanded = f"{query} weakness weaknesses weak square pawn structure target positional"

    # Semantic search
    query_vector = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=expanded
    ).data[0].embedding

    semantic_results = qdrant.search(
        collection_name="chess_full_validation",
        query_vector=query_vector,
        limit=20
    )

    # BM25 search
    tokenized_corpus = [c['text'].lower().split() for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = expanded.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)
    top_bm25_indices = np.argsort(bm25_scores)[-20:][::-1]

    # Combine
    combined = {}
    for result in semantic_results:
        combined[result.id] = {
            'semantic_score': result.score,
            'bm25_score': 0.0,
            'multiplier': result.payload['multiplier'],
            'payload': result.payload
        }

    max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
    for idx in top_bm25_indices:
        bm25_score = bm25_scores[idx] / max_bm25
        if idx in combined:
            combined[idx]['bm25_score'] = bm25_score
        else:
            try:
                qdrant_point = qdrant.retrieve(collection_name="chess_full_validation", ids=[idx])[0]
                combined[idx] = {
                    'semantic_score': 0.0,
                    'bm25_score': bm25_score,
                    'multiplier': qdrant_point.payload['multiplier'],
                    'payload': qdrant_point.payload
                }
            except:
                pass

    # Calculate final scores
    final_scores = []
    for idx, scores in combined.items():
        hybrid_score = 0.7 * scores['semantic_score'] + 0.3 * scores['bm25_score']
        final_score = hybrid_score * scores['multiplier']

        final_scores.append({
            'final_score': final_score,
            'hybrid_score': hybrid_score,
            'semantic_score': scores['semantic_score'],
            'bm25_score': scores['bm25_score'],
            'multiplier': scores['multiplier'],
            'book': scores['payload'].get('book_name', 'unknown'),
            'text_preview': scores['payload']['text'][:200]
        })

    final_scores.sort(key=lambda x: x['final_score'], reverse=True)
    return final_scores[:5]


def main():
    print("="*80)
    print(f"COMPARING BASELINE VS OPTIMIZED")
    print("="*80)
    print(f"\nQuery: {TEST_QUERY}")
    print("\n" + "="*80)

    # Baseline
    print("BASELINE RESULTS (Pure Semantic Search)")
    print("="*80)
    baseline = get_baseline_results(TEST_QUERY)
    for i, r in enumerate(baseline, 1):
        print(f"\n{i}. Score: {r['score']:.4f}")
        print(f"   Book: {r['book']}")
        print(f"   Text: {r['text_preview']}...")

    # Optimized
    print("\n" + "="*80)
    print("OPTIMIZED RESULTS (Hybrid + Reranking + Query Expansion)")
    print("="*80)
    optimized = get_optimized_results(TEST_QUERY)
    for i, r in enumerate(optimized, 1):
        print(f"\n{i}. Final Score: {r['final_score']:.4f}")
        print(f"   Semantic: {r['semantic_score']:.3f} | BM25: {r['bm25_score']:.3f} | Multiplier: {r['multiplier']:.1f}x")
        print(f"   Book: {r['book']}")
        print(f"   Text: {r['text_preview']}...")

    # Analysis
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)

    baseline_books = [r['book'] for r in baseline]
    optimized_books = [r['book'] for r in optimized]

    print(f"\nBaseline books: {baseline_books}")
    print(f"Optimized books: {optimized_books}")

    overlap = set(baseline_books) & set(optimized_books)
    print(f"\nOverlap: {len(overlap)}/5 books in common")

    if len(overlap) < 3:
        print("⚠️  Major ranking change - optimizations retrieved different results")
    else:
        print("✓ Similar results - likely evaluation method difference")

    print("\n" + "="*80)


if __name__ == '__main__':
    main()
