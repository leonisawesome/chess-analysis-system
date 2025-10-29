#!/usr/bin/env python3
"""
APPROACH 2: Larger Candidate Pool (20 → 40)
Expected gain: +1-3%
Effort: 0.5 day
Rationale: Positions 21-40 might contain edge-relevant content
"""

import json
from qdrant_client import QdrantClient
from openai import OpenAI
import os

# Initialize
qdrant_client = QdrantClient(path="./qdrant_validation_db")
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

EMBEDDING_MODEL = "text-embedding-3-small"

# Test on queries where baseline had issues
TEST_QUERIES = [
    (3, "When should I trade pieces in the endgame?"),             # 60% baseline
    (6, "How do I defend against aggressive attacks?"),            # 50% baseline (worst)
    (7, "What endgame principles should beginners learn first?"),  # 60% baseline
]

def get_semantic_candidates(query, limit=20):
    """Get semantic search results"""
    query_vector = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    ).data[0].embedding

    results = qdrant_client.search(
        collection_name="chess_validation",
        query_vector=query_vector,
        limit=limit
    )
    return results

def gpt5_rerank(query, candidates):
    """Simple GPT-5 reranking (baseline prompt)"""

    prompt = f"""You are a chess expert evaluating search results for relevance.

Query: "{query}"

Rate each chunk's relevance on a scale of 0-10:
- 10 = Directly answers the query with specific, relevant information
- 5 = Somewhat related but tangential or too general
- 0 = Completely irrelevant

Be strict. Only rate 8-10 if the chunk specifically addresses the query.

Chunks to rate:
"""

    for i, candidate in enumerate(candidates, 1):
        text_preview = candidate.payload['text'][:250].replace('\n', ' ')
        prompt += f"\n{i}. {text_preview}...\n"

    prompt += f"\nRespond with ONLY comma-separated scores (20 or 40 values depending on number of chunks)"

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    scores_text = response.choices[0].message.content.strip()
    scores = [int(s.strip()) for s in scores_text.split(',')]

    ranked = list(zip(candidates, scores))
    ranked.sort(key=lambda x: x[1], reverse=True)

    return ranked

def test_larger_pool():
    """Compare top-20 vs top-40 candidate pool"""

    print("="*80)
    print("APPROACH 2: LARGER CANDIDATE POOL TEST")
    print("="*80)
    print("Testing if expanding from 20 → 40 candidates improves top-5 quality")
    print()

    for query_id, query in TEST_QUERIES:
        print(f"\n{'='*80}")
        print(f"QUERY {query_id}: {query}")
        print('='*80)

        # Get 20 candidates (baseline)
        candidates_20 = get_semantic_candidates(query, limit=20)
        ranked_20 = gpt5_rerank(query, candidates_20)
        top5_from_20 = ranked_20[:5]

        # Get 40 candidates (larger pool)
        candidates_40 = get_semantic_candidates(query, limit=40)
        ranked_40 = gpt5_rerank(query, candidates_40)
        top5_from_40 = ranked_40[:5]

        print(f"\nTOP-5 FROM 20 CANDIDATES:")
        for i, (cand, score) in enumerate(top5_from_20, 1):
            book = cand.payload.get('book_name', 'unknown')
            chapter = cand.payload.get('chapter_title', 'unknown')
            text = cand.payload['text'][:100].replace('\n', ' ')
            print(f"{i}. [{score}/10 | Sem:{cand.score:.3f}] {book} / {chapter}")
            print(f"   {text}...")

        print(f"\nTOP-5 FROM 40 CANDIDATES:")
        for i, (cand, score) in enumerate(top5_from_40, 1):
            book = cand.payload.get('book_name', 'unknown')
            chapter = cand.payload.get('chapter_title', 'unknown')
            text = cand.payload['text'][:100].replace('\n', ' ')
            # Mark if this result came from positions 21-40
            position = next((idx for idx, c in enumerate(candidates_40, 1) if c.id == cand.id), None)
            source = " [FROM 21-40]" if position and position > 20 else ""
            print(f"{i}. [{score}/10 | Sem:{cand.score:.3f}]{source} {book} / {chapter}")
            print(f"   {text}...")

        # Check if any top-5 results came from positions 21-40
        positions = [next((idx for idx, c in enumerate(candidates_40, 1) if c.id == cand.id), 0)
                    for cand, _ in top5_from_40]
        from_21_40 = sum(1 for p in positions if p > 20)

        print(f"\n  → {from_21_40}/5 top results came from positions 21-40")

        if from_21_40 > 0:
            print(f"  ✓ Larger pool helped - found better content beyond top-20")
        else:
            print(f"  ✗ No benefit - all top-5 were already in top-20")

    print(f"\n{'='*80}")
    print("CONCLUSION:")
    print("="*80)
    print("If 0 results from 21-40: Larger pool adds no value (skip)")
    print("If 1-2 results from 21-40: Marginal benefit (+1-2%)")
    print("If 3+ results from 21-40: Strong benefit (+2-3%)")
    print("="*80)

if __name__ == "__main__":
    test_larger_pool()
