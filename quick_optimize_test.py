#!/usr/bin/env python3
"""
Quick Automated Optimization Test
Tests 3 queries automatically and shows improvement metrics.
"""

import json
from typing import List, Dict
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from rank_bm25 import BM25Okapi
import numpy as np
import sqlite3


# Configuration
EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "chess_quick_test"
QDRANT_PATH = "./qdrant_quick_test"
DB_PATH = "epub_analysis.db"

TIER_MULTIPLIERS = {'HIGH': 1.2, 'MEDIUM': 1.0, 'LOW': 0.8}
SEMANTIC_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3

QUERY_EXPANSIONS = {
    'calculation': ['calculation', 'calculating', 'calculate', 'analyze', 'variations', 'concrete'],
    'endgame': ['endgame', 'endgames', 'ending', 'endings'],
    'attack': ['attack', 'attacking', 'assault', 'initiative'],
}


def expand_query(query: str) -> str:
    query_lower = query.lower()
    expanded_terms = []
    for term, expansions in QUERY_EXPANSIONS.items():
        if term in query_lower:
            expanded_terms.extend(expansions)
    if expanded_terms:
        return f"{query} {' '.join(set(expanded_terms))}"
    return query


def load_quality_scores():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, tier, score FROM epub_analysis WHERE tier IS NOT NULL")
    quality_map = {}
    for filename, tier, score in cursor.fetchall():
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        quality_map[base_name] = {'tier': tier, 'score': score}
    conn.close()
    return quality_map


def setup_system(chunks):
    """Setup Qdrant, embed chunks, and create BM25 index"""
    openai_client = OpenAI()
    qdrant_client = QdrantClient(path=QDRANT_PATH)
    quality_map = load_quality_scores()

    # Create collection
    try:
        qdrant_client.delete_collection(COLLECTION_NAME)
    except:
        pass
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
    )

    # Embed and upload (batched)
    print(f"Embedding {len(chunks)} chunks...")
    BATCH_SIZE = 100
    all_points = []

    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(chunks))
        batch_chunks = chunks[batch_start:batch_end]
        texts = [c['text'] for c in batch_chunks]

        response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=texts)

        for i, chunk in enumerate(batch_chunks):
            book_name = chunk.get('book_name', 'unknown')
            quality_info = quality_map.get(book_name, {'tier': 'MEDIUM', 'score': 50})

            point = PointStruct(
                id=batch_start + i,
                vector=response.data[i].embedding,
                payload={
                    'text': chunk['text'],
                    'book_name': book_name,
                    'tier': quality_info['tier'],
                    'quality_score': quality_info['score'],
                    'multiplier': TIER_MULTIPLIERS.get(quality_info['tier'], 1.0)
                }
            )
            all_points.append(point)

    qdrant_client.upsert(collection_name=COLLECTION_NAME, points=all_points)
    print(f"✓ Embedded and uploaded {len(all_points)} chunks")

    # Setup BM25
    tokenized_corpus = [c['text'].lower().split() for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    print(f"✓ BM25 index ready")

    return openai_client, qdrant_client, bm25, chunks


def hybrid_search(query, openai_client, qdrant_client, bm25, chunks, top_k=5):
    """Hybrid search with optimizations"""
    expanded = expand_query(query)

    # Semantic search
    query_vector = openai_client.embeddings.create(
        model=EMBEDDING_MODEL, input=expanded
    ).data[0].embedding
    semantic_results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=20
    )

    # BM25 search
    tokenized_query = expanded.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)
    top_bm25_indices = np.argsort(bm25_scores)[-20:][::-1]

    # Combine scores
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
                qdrant_point = qdrant_client.retrieve(collection_name=COLLECTION_NAME, ids=[idx])[0]
                combined[idx] = {
                    'semantic_score': 0.0,
                    'bm25_score': bm25_score,
                    'multiplier': qdrant_point.payload['multiplier'],
                    'payload': qdrant_point.payload
                }
            except:
                pass

    # Calculate final scores with quality reranking
    final_scores = []
    for idx, scores in combined.items():
        hybrid_score = (SEMANTIC_WEIGHT * scores['semantic_score'] +
                       KEYWORD_WEIGHT * scores['bm25_score'])
        final_score = hybrid_score * scores['multiplier']

        final_scores.append({
            'id': idx,
            'final_score': final_score,
            'hybrid_score': hybrid_score,
            'semantic_score': scores['semantic_score'],
            'bm25_score': scores['bm25_score'],
            'multiplier': scores['multiplier'],
            'payload': scores['payload']
        })

    final_scores.sort(key=lambda x: x['final_score'], reverse=True)
    return final_scores[:top_k]


def main():
    print("="*80)
    print("QUICK OPTIMIZATION TEST")
    print("="*80)
    print("\nOptimizations:")
    print("  1. Quality-based reranking (HIGH: 1.2x)")
    print("  2. Hybrid search (70% semantic + 30% BM25)")
    print("  3. Query expansion")
    print()

    # Load data
    with open('validation_chunks.json', 'r') as f:
        chunks = json.load(f)
    print(f"Loaded {len(chunks)} chunks\n")

    # Setup system
    openai_client, qdrant_client, bm25, chunks = setup_system(chunks)

    # Test queries
    test_queries = [
        "How do I improve my calculation in the middlegame?",
        "When should I trade pieces in the endgame?",
        "How do I defend against aggressive attacks?"
    ]

    print("\n" + "="*80)
    print("RUNNING OPTIMIZED RETRIEVAL")
    print("="*80)

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"Query {i}: {query}")
        expanded = expand_query(query)
        if expanded != query:
            print(f"Expanded: ...{expanded[len(query):]}")
        print("="*80)

        results = hybrid_search(query, openai_client, qdrant_client, bm25, chunks, top_k=5)

        for j, result in enumerate(results, 1):
            print(f"\n{j}. Score: {result['final_score']:.4f} " +
                  f"(semantic: {result['semantic_score']:.3f}, bm25: {result['bm25_score']:.3f}, " +
                  f"{result['multiplier']:.1f}x {result['payload']['tier']})")
            print(f"   Book: {result['payload']['book_name']}")
            text_preview = result['payload']['text'][:200].replace('\n', ' ')
            print(f"   Text: {text_preview}...")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    print("\nKey observations:")
    print("  • Query expansion adds chess-specific synonyms")
    print("  • Hybrid search combines semantic + keyword matching")
    print("  • HIGH tier chunks get 1.2x boost in final ranking")
    print("\nReady for full 10-query validation if results look good.")
    print("="*80)


if __name__ == '__main__':
    main()
