#!/usr/bin/env python3
"""
Validate Production Corpus - System A
Test same 10 validation queries on full 1,052-book corpus

Expected: 86-87% precision@5 (same as 5-book validation)
"""

import os
import json
from typing import List, Dict
import numpy as np

from openai import OpenAI
from qdrant_client import QdrantClient


# ============================================================================
# CONFIGURATION
# ============================================================================

EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "chess_production"
QDRANT_PATH = "./qdrant_production_db"

# Same 10 validation queries from Week 3
VALIDATION_QUERIES = [
    "How do I improve my calculation in the middlegame?",
    "What are the main ideas in the French Defense?",
    "When should I trade pieces in the endgame?",
    "How do I create weaknesses in my opponent's position?",
    "What is the best way to study chess openings?",
    "How do I defend against aggressive attacks?",
    "What endgame principles should beginners learn first?",
    "How do I improve my positional understanding?",
    "When is it correct to sacrifice material?",
    "How do I convert a winning position?"
]


# ============================================================================
# EMBEDDING & SEARCH
# ============================================================================

def embed_query(openai_client: OpenAI, query: str) -> List[float]:
    """Generate embedding for query."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    )
    return response.data[0].embedding


def semantic_search(qdrant_client: QdrantClient, query_vector: List[float], top_k: int = 40) -> List[Dict]:
    """Perform semantic search on production corpus."""
    results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True
    )

    candidates = []
    for result in results:
        candidates.append({
            'chunk_id': result.id,
            'score': result.score,
            'text': result.payload.get('text', ''),
            'book_name': result.payload.get('book_name', ''),
            'book_tier': result.payload.get('book_tier', ''),
            'book_score': result.payload.get('book_score', 0),
            'chapter_title': result.payload.get('chapter_title', ''),
            'chapter_index': result.payload.get('chapter_index', 0),
            'chunk_index': result.payload.get('chunk_index', 0)
        })

    return candidates


# ============================================================================
# GPT-5 RERANKING
# ============================================================================

def gpt5_rerank(openai_client: OpenAI, query: str, candidates: List[Dict], top_k: int = 5) -> List[Dict]:
    """
    Rerank candidates using GPT-5 (Approach 1 - optimized prompt).

    Returns: Top K reranked results
    """
    # Build prompt
    prompt = f"""You are a chess expert evaluating search results.

Query: "{query}"

Rate each chunk's relevance from 0-10 and provide a one-sentence justification.

Scoring criteria:
- 10: Directly answers the query with actionable content
- 7-9: Highly relevant with specific information
- 4-6: Related but tangential or too general
- 0-3: Irrelevant or wrong intent

Chunks to evaluate:
"""

    for i, cand in enumerate(candidates[:40], 1):  # Evaluate top 40
        text_preview = cand['text'][:300].replace('\n', ' ')
        book = cand['book_name'][:50]
        chapter = cand['chapter_title'][:50]
        prompt += f"\n{i}. Book: {book} | Chapter: {chapter}\n   {text_preview}...\n"

    prompt += """
Output format (JSON list):
[
  {"chunk_num": 1, "score": 8.5, "justification": "Provides step-by-step methods for improving calculation."},
  ...
]

Output only valid JSON:"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.choices[0].message.content.strip()

        # Parse JSON
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]

        rankings = json.loads(result_text)

        # Map back to candidates
        reranked = []
        for ranking in rankings:
            chunk_num = ranking['chunk_num'] - 1
            if chunk_num < len(candidates):
                result = candidates[chunk_num].copy()
                result['rerank_score'] = ranking['score']
                result['justification'] = ranking['justification']
                reranked.append(result)

        # Sort by rerank score and return top K
        reranked.sort(key=lambda x: -x['rerank_score'])
        return reranked[:top_k]

    except Exception as e:
        print(f"   ⚠️  Reranking failed: {e}")
        # Fallback: return top K from semantic search
        return candidates[:top_k]


# ============================================================================
# VALIDATION
# ============================================================================

def validate_query(openai_client: OpenAI, qdrant_client: QdrantClient, query: str) -> Dict:
    """
    Run validation on a single query.

    Returns: dict with query, top 5 results, metadata
    """
    # Embed query
    query_vector = embed_query(openai_client, query)

    # Semantic search (top 40)
    candidates = semantic_search(qdrant_client, query_vector, top_k=40)

    # GPT-5 reranking (40 → 5)
    top5 = gpt5_rerank(openai_client, query, candidates, top_k=5)

    return {
        'query': query,
        'top5': top5,
        'num_candidates': len(candidates)
    }


def run_validation(openai_client: OpenAI, qdrant_client: QdrantClient) -> List[Dict]:
    """
    Run validation on all 10 queries.

    Returns: List of validation results
    """
    print("\n" + "=" * 80)
    print("VALIDATION: Testing on Production Corpus")
    print("=" * 80)

    results = []

    for i, query in enumerate(VALIDATION_QUERIES, 1):
        print(f"\n[{i}/10] {query}")

        result = validate_query(openai_client, qdrant_client, query)
        results.append(result)

        # Show top 5
        print(f"\nTop 5 Results:")
        for j, item in enumerate(result['top5'], 1):
            score = item.get('rerank_score', 0)
            book = item['book_name'][:40]
            chapter = item['chapter_title'][:40]
            print(f"  {j}. [{score:.1f}/10] {book} | {chapter}")

    return results


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main validation pipeline."""
    print("=" * 80)
    print("PRODUCTION CORPUS VALIDATION")
    print("=" * 80)
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Queries: {len(VALIDATION_QUERIES)}")
    print(f"Target: 86-87% precision@5")
    print()

    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not set!")
        return

    # Initialize clients
    print("Initializing clients...")
    openai_client = OpenAI(api_key=api_key)
    qdrant_client = QdrantClient(path=QDRANT_PATH)

    # Check collection exists
    collections = qdrant_client.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        print(f"❌ Collection '{COLLECTION_NAME}' not found!")
        print("   Run build_production_corpus.py first")
        return

    # Get collection info
    collection_info = qdrant_client.get_collection(COLLECTION_NAME)
    print(f"✅ Collection found: {collection_info.points_count:,} chunks")

    # Run validation
    results = run_validation(openai_client, qdrant_client)

    # Save results
    output_file = 'production_validation_results.json'
    print(f"\n\n📝 Saving results to {output_file}...")

    # Convert to JSON-serializable format
    json_results = []
    for result in results:
        json_results.append({
            'query': result['query'],
            'top5': [
                {
                    'chunk_id': int(r['chunk_id']),
                    'rerank_score': r.get('rerank_score', 0),
                    'semantic_score': r.get('score', 0),
                    'justification': r.get('justification', ''),
                    'book_name': r['book_name'],
                    'book_tier': r['book_tier'],
                    'chapter_title': r['chapter_title'],
                    'text': r['text'][:500]
                }
                for r in result['top5']
            ]
        })

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)

    print(f"✅ Results saved")

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print(f"✅ Tested {len(results)} queries")
    print(f"✅ Results saved to {output_file}")
    print()
    print("Next steps:")
    print("1. Manually evaluate results (y/p/n)")
    print("2. Calculate precision@5")
    print("3. Compare to 86-87% baseline")
    print("=" * 80)


if __name__ == '__main__':
    main()
