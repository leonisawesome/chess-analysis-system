#!/usr/bin/env python3
"""
Generate all 10 queries × 5 results for manual evaluation.
Outputs to validation_results_for_review.txt
"""

import json
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from rank_bm25 import BM25Okapi
import numpy as np
import sqlite3


EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "chess_full_validation"
QDRANT_PATH = "./qdrant_full_validation"
DB_PATH = "epub_analysis.db"

TIER_MULTIPLIERS = {'HIGH': 1.2, 'MEDIUM': 1.0, 'LOW': 0.8}
SEMANTIC_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3

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
    print("Setting up system...")
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
                    'chapter_title': chunk.get('chapter_title', 'Unknown'),
                    'tier': quality_info['tier'],
                    'quality_score': quality_info['score'],
                    'multiplier': TIER_MULTIPLIERS.get(quality_info['tier'], 1.0)
                }
            )
            all_points.append(point)

        print(f"  {batch_end}/{len(chunks)} chunks processed")

    qdrant_client.upsert(collection_name=COLLECTION_NAME, points=all_points)
    print(f"✓ System ready\n")

    # Setup BM25
    tokenized_corpus = [c['text'].lower().split() for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)

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
    print("GENERATING VALIDATION RESULTS FOR MANUAL REVIEW")
    print("="*80)
    print()

    # Load data
    with open('validation_chunks.json', 'r') as f:
        chunks = json.load(f)
    with open('validation_queries.json', 'r') as f:
        queries_data = json.load(f)
    queries = queries_data['conceptual_queries']

    print(f"Loaded {len(chunks)} chunks and {len(queries)} queries\n")

    # Setup system
    openai_client, qdrant_client, bm25, chunks = setup_system(chunks)

    # Generate results for all queries
    all_results = []
    output_lines = []

    output_lines.append("="*80)
    output_lines.append("OPTIMIZED SYSTEM A - VALIDATION RESULTS FOR MANUAL REVIEW")
    output_lines.append("="*80)
    output_lines.append("")
    output_lines.append("INSTRUCTIONS:")
    output_lines.append("Review each result and mark as:")
    output_lines.append("  y = relevant (directly answers the query)")
    output_lines.append("  p = partially relevant (related but not direct)")
    output_lines.append("  n = not relevant (off-topic)")
    output_lines.append("")
    output_lines.append("Add your judgment on the line after 'JUDGMENT: '")
    output_lines.append("="*80)
    output_lines.append("")

    for query in queries:
        query_id = query['id']
        query_text = query['query']

        print(f"Processing Query {query_id}: {query_text}")

        results = hybrid_search(query_text, openai_client, qdrant_client, bm25, chunks, top_k=5)

        output_lines.append("")
        output_lines.append("="*80)
        output_lines.append(f"QUERY {query_id}: {query_text}")
        output_lines.append("="*80)

        query_results = []
        for i, result in enumerate(results, 1):
            output_lines.append("")
            output_lines.append(f"--- RESULT {i} ---")
            output_lines.append(f"Score: {result['final_score']:.4f}")
            output_lines.append(f"  Semantic: {result['semantic_score']:.3f} | BM25: {result['bm25_score']:.3f}")
            output_lines.append(f"  Quality: {result['multiplier']:.1f}x ({result['payload']['tier']})")
            output_lines.append(f"  Book: {result['payload']['book_name']}")
            output_lines.append(f"  Chapter: {result['payload']['chapter_title']}")
            output_lines.append("")
            output_lines.append("Text:")

            # Show first 600 chars
            text = result['payload']['text']
            preview = text[:600] if len(text) > 600 else text
            output_lines.append(preview)
            if len(text) > 600:
                output_lines.append("[... truncated ...]")

            output_lines.append("")
            output_lines.append("JUDGMENT: _____  (enter y/p/n)")
            output_lines.append("")

            query_results.append({
                'result_num': i,
                'score': result['final_score'],
                'book': result['payload']['book_name'],
                'text_preview': preview[:200]
            })

        all_results.append({
            'query_id': query_id,
            'query': query_text,
            'results': query_results
        })

    # Save to file
    output_file = 'validation_results_for_review.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f"\n✅ Generated results for all {len(queries)} queries")
    print(f"📄 Saved to: {output_file}")
    print(f"\nTotal results to evaluate: {len(queries) * 5} (10 queries × 5 results)")
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("1. Open validation_results_for_review.txt")
    print("2. Fill in JUDGMENT for all 50 results (y/p/n)")
    print("3. Save the file")
    print("4. Run: python calculate_precision.py")
    print("="*80)

    # Also save structured results
    with open('validation_results_structured.json', 'w') as f:
        json.dump(all_results, f, indent=2)


if __name__ == '__main__':
    main()
