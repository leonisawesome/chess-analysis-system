#!/usr/bin/env python3
"""
FULL VALIDATION TEST: Constrained Expansion (0.75 threshold) + All Optimizations
Combines: Constrained expansion, Top 40 candidates, Optimized GPT-5 prompt
"""

from openai import OpenAI
from qdrant_client import QdrantClient
import numpy as np
import os

# Initialize clients
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
qdrant_client = QdrantClient(path="./qdrant_validation_db")

EMBEDDING_MODEL = "text-embedding-3-small"

# 10 validation queries
QUERIES = [
    "How do I improve my calculation in the middlegame?",  # Query 1
    "What are the main ideas in the French Defense?",      # Query 2
    "When should I trade pieces in the endgame?",          # Query 3
    "How do I create weaknesses in my opponent's position?",  # Query 4
    "What is the best way to study chess openings?",       # Query 5 - CRITICAL
    "How do I defend against aggressive attacks?",         # Query 6
    "What endgame principles should beginners learn first?",  # Query 7
    "How do I improve my positional understanding?",       # Query 8
    "When is it correct to sacrifice material?",           # Query 9
    "How do I convert a winning position?",                # Query 10
]


def expand_query_constrained(query):
    """
    Expand query with strict constraints:
    - Max 3-5x original length
    - Preserve "HOW TO" meta-intent
    - Add synonyms, not technical details
    """

    prompt = f"""Expand this chess query CONSERVATIVELY for search.

Original query: "{query}"

STRICT RULES:
1. Maximum length: 3-5x original (absolute max 250 characters)
2. Preserve meta-intent:
   - "How to" / "best way" / "improve" queries → Add METHOD synonyms (learn, practice, train, develop, techniques)
   - Keep focus on the ACTION/PROCESS, not the CONTENT
3. Add 5-10 related synonyms ONLY
4. DO NOT add technical chess terms (openings names, tactics, structures)
5. DO NOT enumerate concepts or examples

GOOD EXAMPLES:
"How to study openings?" → "how to study learn practice chess openings repertoire preparation methods techniques"
(3x length, preserves "study methods" intent)

"Improve calculation middlegame" → "improve enhance develop calculation visualization tactical analysis middlegame"
(3x length, preserves "improvement methods" intent)

BAD EXAMPLES:
"study openings" → "Sicilian French tabiyas transpositions pawn structures gambits"
(Lost "study methods", became "opening content")

Now expand (max 250 chars):

"{query}"

Expanded query:"""

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    expanded = response.choices[0].message.content.strip()

    # Safety check: Reject if >6x original
    if len(expanded) > len(query) * 6:
        print(f"⚠️  Expansion rejected: Too long ({len(expanded)} chars vs {len(query)} original)")
        return query

    return expanded


def validate_expansion(original_query, expanded_query, threshold=0.85):
    """
    Validate that expanded query preserves intent using embedding similarity

    Args:
        original_query: Original user query
        expanded_query: Expanded version
        threshold: Minimum cosine similarity (default 0.75)

    Returns:
        (is_valid, cosine_score)
    """

    # Use OpenAI embeddings for consistency with our semantic search
    original_vec = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=original_query
    ).data[0].embedding

    expanded_vec = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=expanded_query
    ).data[0].embedding

    # Cosine similarity
    original_vec = np.array(original_vec)
    expanded_vec = np.array(expanded_vec)

    cosine = np.dot(original_vec, expanded_vec) / (
        np.linalg.norm(original_vec) * np.linalg.norm(expanded_vec)
    )

    is_valid = cosine >= threshold

    return is_valid, float(cosine)


def expand_with_validation(query, threshold=0.85):
    """
    Expand query with validation safeguard

    Returns original query if expansion fails validation
    """

    # Expand
    expanded = expand_query_constrained(query)

    # If expansion unchanged, return original
    if expanded == query:
        return query, None, "unchanged"

    # Validate
    is_valid, cosine = validate_expansion(query, expanded, threshold)

    if is_valid:
        return expanded, cosine, "validated"
    else:
        print(f"⚠️  Expansion rejected: Cosine {cosine:.3f} < {threshold}")
        return query, cosine, "rejected"


def get_semantic_candidates(query, limit=40):
    """Get top 40 semantic search candidates"""
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


def gpt5_rerank_optimized(query, candidates):
    """GPT-5 reranking with optimized chess-specific prompt"""

    prompt = f"""You are a chess expert evaluating search results for relevance.

Query: "{query}"

RUBRIC FOR SCORING (0-10):
- 10 = DIRECT MATCH: Content specifically addresses the query with concrete instruction
- 7-9 = STRONG: Relevant examples, games, or concrete illustrations
- 5-6 = TANGENTIAL: Related concepts but too general or off-topic
- 0-4 = IRRELEVANT: Wrong intent, opposite concept, or just metadata

CHESS-SPECIFIC RULES:
1. Attack ≠ Defend (opposite intents, score 0-3 if mismatched)
2. Openings ≠ Middlegame ≠ Endgame (different game phases)
3. Book descriptions/bibliographies = 0-3 unless they contain actual instruction
4. Examples with concrete moves/variations = 7-9 (high value)
5. Q&A sections directly answering the query = 9-10 (highest value)

FEW-SHOT EXAMPLES:

Query: "How to defend against attacks?"
- "I don't like defending" Q&A → 6 (mindset, not techniques)
- Defensive tactic with moves → 9 (concrete technique)
- "Attacking Chess" book → 2 (opposite intent)

Query: "What is the French Defense?"
- French Defense game with analysis → 9 (concrete example)
- "French Defense" in opening list → 3 (just metadata)
- Endgame after French → 6 (tangential)

Be strict. Only rate 8-10 if the chunk specifically addresses the query.

Chunks to rate:
"""

    for i, candidate in enumerate(candidates, 1):
        text_preview = candidate.payload['text'][:250].replace('\n', ' ')
        prompt += f"\n{i}. {text_preview}...\n"

    prompt += "\nRespond with ONLY comma-separated scores (e.g., 8,6,9,3,7,...)"

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    scores_text = response.choices[0].message.content.strip()
    scores = [int(s.strip()) for s in scores_text.split(',')]

    # Rank by score
    ranked = list(zip(candidates, scores))
    ranked.sort(key=lambda x: x[1], reverse=True)

    return ranked


def run_full_validation():
    """Run full validation test on all 10 queries"""

    print("="*80)
    print("FULL VALIDATION TEST: 0.85 THRESHOLD + ALL OPTIMIZATIONS")
    print("="*80)
    print("Configuration:")
    print("- Constrained query expansion (3-5x max) with 0.85 cosine validation")
    print("- Top 40 semantic candidates")
    print("- Optimized GPT-5 reranking prompt")
    print()
    print("Goal: Achieve ≥88% precision@5 with no regressions >5pp")
    print("="*80)

    all_results = []

    for i, query in enumerate(QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"QUERY {i}: {query}")
        print('='*80)

        # Step 1: Expand with validation
        expanded_query, cosine, status = expand_with_validation(query)

        if status == "validated":
            print(f"✓ Expansion validated (cosine={cosine:.3f})")
            print(f"  Expanded: {expanded_query}")
        elif status == "rejected":
            print(f"✗ Expansion rejected (cosine={cosine:.3f})")
            print(f"  Using original query")
        else:
            print(f"○ No expansion (unchanged)")

        # Step 2: Get top 40 semantic candidates
        candidates = get_semantic_candidates(expanded_query, limit=40)

        # Step 3: GPT-5 rerank with optimized prompt
        ranked = gpt5_rerank_optimized(query, candidates)

        # Step 4: Get top 5
        top5 = ranked[:5]

        print(f"\nTOP 5 RESULTS:")
        for j, (cand, score) in enumerate(top5, 1):
            book = cand.payload.get('book_name', 'unknown')
            chapter = cand.payload.get('chapter_title', 'unknown')
            text = cand.payload['text'][:200].replace('\n', ' ')
            print(f"\n{j}. [GPT-5 Score: {score}/10 | Semantic: {cand.score:.4f}]")
            print(f"   Book: {book}")
            print(f"   Chapter: {chapter}")
            print(f"   Text: {text}...")

        all_results.append({
            'query_num': i,
            'query': query,
            'expanded': expanded_query,
            'expansion_status': status,
            'cosine': cosine,
            'top5': top5
        })

    # Save results to file for manual evaluation
    print(f"\n{'='*80}")
    print("RESULTS SAVED - READY FOR MANUAL EVALUATION")
    print('='*80)

    # Save to JSON for later processing
    import json
    with open('validation_results_0.85.json', 'w') as f:
        # Convert results to JSON-serializable format
        json_results = []
        for r in all_results:
            json_results.append({
                'query_num': r['query_num'],
                'query': r['query'],
                'expanded': r['expanded'],
                'expansion_status': r['expansion_status'],
                'cosine': r['cosine'],
                'top5': [
                    {
                        'score': score,
                        'book': cand.payload.get('book_name', 'unknown'),
                        'chapter': cand.payload.get('chapter_title', 'unknown'),
                        'text': cand.payload['text'][:500]
                    }
                    for cand, score in r['top5']
                ]
            })
        json.dump(json_results, f, indent=2)

    print("\nResults saved to: validation_results_0.85.json")
    print("Ready for manual evaluation")

    return all_results


if __name__ == "__main__":
    run_full_validation()
