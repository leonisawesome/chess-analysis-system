#!/usr/bin/env python3
"""
Optimize System A: Semantic RAG with Reranking, Hybrid Search, and Query Expansion
Week 3 Validation: Test optimizations on 5-book corpus before scaling to 100 books.
"""

import json
import sqlite3
from typing import List, Dict, Tuple
from pathlib import Path
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from rank_bm25 import BM25Okapi
import numpy as np


# Configuration
EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "chess_validation_optimized"
QDRANT_PATH = "./qdrant_optimized_db"  # Local file-based Qdrant
DB_PATH = "epub_analysis.db"

# Quality score multipliers
TIER_MULTIPLIERS = {
    'HIGH': 1.2,
    'MEDIUM': 1.0,
    'LOW': 0.8
}

# Hybrid search weights
SEMANTIC_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3

# Chess-specific query expansion dictionary
QUERY_EXPANSIONS = {
    'knight': ['knight', 'N', '♘', 'Knights'],
    'bishop': ['bishop', 'B', '♗', 'Bishops'],
    'rook': ['rook', 'R', '♖', 'Rooks'],
    'queen': ['queen', 'Q', '♕'],
    'king': ['king', 'K', '♔'],
    'pawn': ['pawn', 'P', '♙', 'pawns'],
    'calculation': ['calculation', 'calculating', 'calculate', 'analyze', 'variations', 'concrete'],
    'endgame': ['endgame', 'endgames', 'ending', 'endings'],
    'opening': ['opening', 'openings', 'debut', 'repertoire'],
    'tactics': ['tactics', 'tactical', 'combination', 'combinations'],
    'strategy': ['strategy', 'strategic', 'positional', 'plan', 'planning'],
    'attack': ['attack', 'attacking', 'assault', 'initiative'],
    'defense': ['defense', 'defending', 'defend', 'counterplay'],
    'sacrifice': ['sacrifice', 'sacrifices', 'compensation', 'sac'],
    'checkmate': ['checkmate', 'mate', 'mating', 'checkmating'],
    'convert': ['convert', 'converting', 'technique', 'winning', 'realization']
}


def expand_query(query: str) -> str:
    """
    Expand chess-specific terms in query.
    Example: "knight" → "knight N ♘"
    """
    query_lower = query.lower()
    expanded_terms = []

    for term, expansions in QUERY_EXPANSIONS.items():
        if term in query_lower:
            # Add all expansions
            expanded_terms.extend(expansions)

    # Combine original query with expanded terms
    if expanded_terms:
        expanded_query = f"{query} {' '.join(set(expanded_terms))}"
        return expanded_query

    return query


def load_book_quality_scores(db_path: str) -> Dict[str, Dict]:
    """
    Load quality scores and tiers for books from database.
    Returns: {book_filename: {'tier': 'HIGH', 'score': 85}}
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT filename, tier, score
        FROM epub_analysis
        WHERE tier IS NOT NULL
    """)

    quality_map = {}
    for filename, tier, score in cursor.fetchall():
        # Extract base name without path and extension
        base_name = Path(filename).stem
        quality_map[base_name] = {
            'tier': tier,
            'score': score
        }

    conn.close()
    return quality_map


def setup_qdrant_collection(client: QdrantClient, dimension: int = 1536):
    """Create or recreate Qdrant collection."""
    # Delete if exists
    try:
        client.delete_collection(collection_name=COLLECTION_NAME)
        print(f"✓ Deleted existing collection: {COLLECTION_NAME}")
    except:
        pass

    # Create new collection
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
    )
    print(f"✓ Created collection: {COLLECTION_NAME}")


def embed_and_store_chunks(
    openai_client: OpenAI,
    qdrant_client: QdrantClient,
    chunks: List[Dict],
    quality_map: Dict[str, Dict]
):
    """
    Embed chunks and store in Qdrant with quality metadata.
    Batches to avoid OpenAI's 300K token per request limit.
    """
    print(f"\nEmbedding {len(chunks)} chunks...")

    BATCH_SIZE = 100  # Process 100 chunks at a time
    all_points = []

    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(chunks))
        batch_chunks = chunks[batch_start:batch_end]

        # Embed batch
        texts = [chunk['text'] for chunk in batch_chunks]
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts
        )

        # Prepare points for this batch
        for i, chunk in enumerate(batch_chunks):
            # Get quality info for this book
            book_name = chunk.get('book_name', 'unknown')
            quality_info = quality_map.get(book_name, {'tier': 'MEDIUM', 'score': 50})

            point = PointStruct(
                id=batch_start + i,
                vector=response.data[i].embedding,
                payload={
                    'text': chunk['text'],
                    'book_name': book_name,
                    'chapter_title': chunk.get('chapter_title', 'Unknown'),
                    'chunk_index': chunk.get('chunk_index', 0),
                    'tier': quality_info['tier'],
                    'quality_score': quality_info['score'],
                    'multiplier': TIER_MULTIPLIERS.get(quality_info['tier'], 1.0)
                }
            )
            all_points.append(point)

        print(f"   Embedded {batch_end}/{len(chunks)} chunks ({batch_end/len(chunks)*100:.1f}%)")

    # Upload all points to Qdrant
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=all_points
    )

    print(f"✓ Uploaded {len(all_points)} chunks to Qdrant")

    # Calculate embedding cost
    total_tokens = sum(chunk.get('token_count', len(chunk['text'].split()) * 1.3) for chunk in chunks)
    cost = (total_tokens / 1_000_000) * 0.02
    print(f"✓ Embedding cost: ${cost:.4f}")


def setup_bm25(chunks: List[Dict]) -> BM25Okapi:
    """
    Setup BM25 keyword search index.
    """
    # Tokenize all chunk texts
    tokenized_corpus = [chunk['text'].lower().split() for chunk in chunks]
    bm25 = BM25Okapi(tokenized_corpus)

    print(f"✓ BM25 index created with {len(chunks)} documents")
    return bm25


def hybrid_search(
    query: str,
    openai_client: OpenAI,
    qdrant_client: QdrantClient,
    bm25: BM25Okapi,
    chunks: List[Dict],
    top_k: int = 5
) -> List[Dict]:
    """
    Perform hybrid search combining semantic (Qdrant) and keyword (BM25) search.

    Steps:
    1. Expand query with chess terms
    2. Get top 20 results from semantic search
    3. Get top 20 results from BM25 keyword search
    4. Combine scores with weights (70% semantic, 30% keyword)
    5. Rerank by quality multiplier
    6. Return top K
    """
    # Step 1: Expand query
    expanded_query = expand_query(query)
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"Expanded: {expanded_query}")
    print(f"{'='*80}")

    # Step 2: Semantic search (top 20)
    query_vector = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=expanded_query
    ).data[0].embedding

    semantic_results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=20
    )

    # Step 3: BM25 keyword search (top 20)
    tokenized_query = expanded_query.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)

    # Get top 20 BM25 results
    top_bm25_indices = np.argsort(bm25_scores)[-20:][::-1]

    # Step 4: Combine scores
    combined_scores = {}

    # Add semantic scores (normalized to 0-1)
    for result in semantic_results:
        idx = result.id
        semantic_score = result.score
        multiplier = result.payload['multiplier']

        combined_scores[idx] = {
            'semantic_score': semantic_score,
            'bm25_score': 0.0,
            'multiplier': multiplier,
            'payload': result.payload
        }

    # Add BM25 scores (normalized to 0-1)
    max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
    for idx in top_bm25_indices:
        bm25_score = bm25_scores[idx] / max_bm25

        if idx in combined_scores:
            combined_scores[idx]['bm25_score'] = bm25_score
        else:
            # Get chunk info
            chunk = chunks[idx]
            # Get quality info from Qdrant (if available) or default
            try:
                qdrant_point = qdrant_client.retrieve(
                    collection_name=COLLECTION_NAME,
                    ids=[idx]
                )[0]
                multiplier = qdrant_point.payload['multiplier']
                payload = qdrant_point.payload
            except:
                multiplier = 1.0
                payload = chunk

            combined_scores[idx] = {
                'semantic_score': 0.0,
                'bm25_score': bm25_score,
                'multiplier': multiplier,
                'payload': payload
            }

    # Step 5: Calculate weighted scores and apply quality multiplier
    final_scores = []
    for idx, scores in combined_scores.items():
        # Hybrid score: 70% semantic + 30% keyword
        hybrid_score = (
            SEMANTIC_WEIGHT * scores['semantic_score'] +
            KEYWORD_WEIGHT * scores['bm25_score']
        )

        # Apply quality multiplier (reranking)
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

    # Step 6: Sort by final score and return top K
    final_scores.sort(key=lambda x: x['final_score'], reverse=True)

    return final_scores[:top_k]


def manual_evaluation(query_id: int, query: str, results: List[Dict]) -> Tuple[float, List[str]]:
    """
    Manually evaluate results for relevance.
    Returns: (relevant_count, judgments)
    """
    print(f"\n{'='*80}")
    print(f"MANUAL EVALUATION - Query {query_id}")
    print(f"Query: {query}")
    print(f"{'='*80}")

    judgments = []
    relevant_count = 0.0

    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"Final Score: {result['final_score']:.4f} (hybrid: {result['hybrid_score']:.4f})")
        print(f"  Semantic: {result['semantic_score']:.4f} | BM25: {result['bm25_score']:.4f}")
        print(f"  Quality Multiplier: {result['multiplier']:.2f}x ({result['payload'].get('tier', 'MEDIUM')})")
        print(f"  Book: {result['payload'].get('book_name', 'Unknown')}")
        print(f"  Chapter: {result['payload'].get('chapter_title', 'Unknown')}")

        # Show text preview
        text = result['payload']['text']
        preview = text[:400] + "..." if len(text) > 400 else text
        print(f"\nText preview:")
        print(preview)

        # Manual judgment
        while True:
            judgment = input(f"\nRelevant? (y=yes, n=no, p=partial): ").strip().lower()
            if judgment in ['y', 'n', 'p']:
                break
            print("Invalid input. Please enter y, n, or p.")

        if judgment == 'y':
            judgments.append('relevant')
            relevant_count += 1.0
        elif judgment == 'p':
            judgments.append('partial')
            relevant_count += 0.5
        else:
            judgments.append('not_relevant')

    precision = relevant_count / len(results)
    print(f"\n{'='*80}")
    print(f"Query {query_id} Precision@5: {precision:.2%} ({relevant_count}/5)")
    print(f"{'='*80}")

    return relevant_count, judgments


def run_optimized_validation(
    chunks_file: str = "validation_chunks.json",
    queries_file: str = "validation_queries.json",
    db_path: str = DB_PATH
):
    """
    Run optimized validation on 5-book corpus.
    """
    print("="*80)
    print("WEEK 3 OPTIMIZATION VALIDATION - SYSTEM A")
    print("="*80)
    print("\nOptimizations:")
    print("  1. Reranking by quality score (HIGH: 1.2x, MEDIUM: 1.0x)")
    print("  2. Hybrid search (70% semantic + 30% BM25 keyword)")
    print("  3. Query expansion (chess-specific terms)")
    print()

    # Load chunks
    print("Loading validation chunks...")
    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    print(f"✓ Loaded {len(chunks)} chunks")

    # Load queries
    print("Loading validation queries...")
    with open(queries_file, 'r', encoding='utf-8') as f:
        queries_data = json.load(f)
    queries = queries_data['conceptual_queries']
    print(f"✓ Loaded {len(queries)} queries")

    # Load quality scores
    print("Loading quality scores from database...")
    quality_map = load_book_quality_scores(db_path)
    print(f"✓ Loaded quality data for {len(quality_map)} books")

    # Setup OpenAI
    openai_client = OpenAI()

    # Setup Qdrant (local file-based)
    print("\nSetting up Qdrant...")
    qdrant_client = QdrantClient(path=QDRANT_PATH)
    setup_qdrant_collection(qdrant_client)

    # Embed and store chunks
    embed_and_store_chunks(openai_client, qdrant_client, chunks, quality_map)

    # Setup BM25
    print("\nSetting up BM25 keyword search...")
    bm25 = setup_bm25(chunks)

    # Run queries
    print("\n" + "="*80)
    print("RUNNING OPTIMIZED RETRIEVAL TESTS")
    print("="*80)

    all_results = []
    total_relevant = 0.0

    for query in queries:
        query_id = query['id']
        query_text = query['query']

        # Perform hybrid search
        results = hybrid_search(
            query_text,
            openai_client,
            qdrant_client,
            bm25,
            chunks,
            top_k=5
        )

        # Manual evaluation
        relevant_count, judgments = manual_evaluation(query_id, query_text, results)

        total_relevant += relevant_count

        all_results.append({
            'query_id': query_id,
            'query': query_text,
            'relevant_count': relevant_count,
            'judgments': judgments,
            'precision_at_5': relevant_count / 5.0,
            'results': [
                {
                    'final_score': r['final_score'],
                    'semantic_score': r['semantic_score'],
                    'bm25_score': r['bm25_score'],
                    'multiplier': r['multiplier'],
                    'tier': r['payload'].get('tier', 'MEDIUM'),
                    'book_name': r['payload'].get('book_name', 'Unknown'),
                    'judgment': judgments[i]
                }
                for i, r in enumerate(results)
            ]
        })

    # Calculate overall precision
    overall_precision = total_relevant / (len(queries) * 5)

    # Summary
    print("\n" + "="*80)
    print("OPTIMIZATION VALIDATION SUMMARY")
    print("="*80)
    print(f"\nTotal queries: {len(queries)}")
    print(f"Total chunks evaluated: {len(queries) * 5}")
    print(f"Total relevant: {total_relevant}")
    print(f"\n📊 OVERALL PRECISION@5: {overall_precision:.1%}")
    print(f"\n🎯 TARGET: ≥90%")

    if overall_precision >= 0.90:
        print(f"✅ SUCCESS: Optimization target met!")
        print(f"   Improvement: {(overall_precision - 0.85) * 100:.1f} percentage points over baseline (85%)")
        print(f"\n➡️  READY TO PROCEED: 100-book scale test")
    elif overall_precision > 0.85:
        print(f"⚠️  IMPROVEMENT: +{(overall_precision - 0.85) * 100:.1f} percentage points")
        print(f"   But below 90% target. Consider additional optimizations.")
    else:
        print(f"❌ REGRESSION: Performance decreased from baseline")
        print(f"   Review optimization parameters.")

    print("="*80)

    # Save results
    output_file = "optimized_validation_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'overall_precision_at_5': overall_precision,
            'total_queries': len(queries),
            'total_relevant': total_relevant,
            'baseline_precision': 0.85,
            'improvement': overall_precision - 0.85,
            'target_met': overall_precision >= 0.90,
            'query_results': all_results,
            'optimizations_applied': {
                'reranking': True,
                'hybrid_search': True,
                'query_expansion': True,
                'semantic_weight': SEMANTIC_WEIGHT,
                'keyword_weight': KEYWORD_WEIGHT,
                'tier_multipliers': TIER_MULTIPLIERS
            }
        }, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")

    return overall_precision, all_results


if __name__ == '__main__':
    precision, results = run_optimized_validation()
