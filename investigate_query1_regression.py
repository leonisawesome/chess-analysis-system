#!/usr/bin/env python3
"""
INVESTIGATION: Query 1 Regression (75% → 70%)
Compare baseline vs expanded query results
"""

import json
from qdrant_client import QdrantClient
from openai import OpenAI
import os

# Initialize
qdrant_client = QdrantClient(path="./qdrant_validation_db")
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

EMBEDDING_MODEL = "text-embedding-3-small"

QUERY_1 = "How do I improve my calculation in the middlegame?"

def expand_query(query):
    """Use GPT-5 to expand query"""
    prompt = f"""Expand this chess query to improve semantic search retrieval.

Original query: "{query}"

Rules for expansion:
1. Add specific chess terms, concepts, and synonyms
2. Include relevant game phases (opening/middlegame/endgame) if applicable
3. Add related tactical/strategic concepts
4. Keep it focused - don't over-expand or add unrelated topics
5. Maintain the original intent

Examples:
- "positional understanding" → "positional understanding strategic principles pawn structure piece activity space advantage"
- "French Defense ideas" → "French Defense main ideas key plans pawn structures typical middlegame themes"
- "sacrifice material" → "sacrifice material exchange sacrifice positional compensation initiative attacking chances"

Respond with ONLY the expanded query (one line, no explanation).
"""

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()

def get_semantic_candidates(query, limit=40):
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

def gpt5_rerank_baseline(query, candidates):
    """Baseline prompt"""
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

    prompt += "\nRespond with ONLY comma-separated scores"

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    scores_text = response.choices[0].message.content.strip()
    scores = [int(s.strip()) for s in scores_text.split(',')]

    ranked = list(zip(candidates, scores))
    ranked.sort(key=lambda x: x[1], reverse=True)

    return ranked

def investigate_query1():
    """Compare baseline vs expanded for Query 1"""

    print("="*80)
    print("QUERY 1 REGRESSION INVESTIGATION")
    print("="*80)
    print(f"\nOriginal Query: {QUERY_1}")
    print()

    # Test 1: Baseline
    print("="*80)
    print("BASELINE: No expansion, Top 20 candidates")
    print("="*80)

    candidates_baseline = get_semantic_candidates(QUERY_1, limit=20)
    ranked_baseline = gpt5_rerank_baseline(QUERY_1, candidates_baseline)
    top5_baseline = ranked_baseline[:5]

    print("\nTop 5 results (BASELINE - achieved 75% precision):")
    for i, (cand, score) in enumerate(top5_baseline, 1):
        book = cand.payload.get('book_name', 'unknown')
        chapter = cand.payload.get('chapter_title', 'unknown')
        text = cand.payload['text'][:150].replace('\n', ' ')
        print(f"\n{i}. [Score: {score}/10 | Semantic: {cand.score:.4f}]")
        print(f"   Book: {book}")
        print(f"   Chapter: {chapter}")
        print(f"   Text: {text}...")

    # Test 2: Expanded
    print("\n" + "="*80)
    print("EXPANDED QUERY TEST")
    print("="*80)

    expanded = expand_query(QUERY_1)
    print(f"\nExpanded Query Text:")
    print(f"'{expanded}'")
    print()

    candidates_expanded = get_semantic_candidates(expanded, limit=40)
    ranked_expanded = gpt5_rerank_baseline(QUERY_1, candidates_expanded)
    top5_expanded = ranked_expanded[:5]

    print("\nTop 5 results (EXPANDED - achieved 70% precision):")
    for i, (cand, score) in enumerate(top5_expanded, 1):
        book = cand.payload.get('book_name', 'unknown')
        chapter = cand.payload.get('chapter_title', 'unknown')
        text = cand.payload['text'][:150].replace('\n', ' ')

        in_baseline = any(c.id == cand.id for c, _ in top5_baseline)
        baseline_marker = " [WAS IN BASELINE TOP-5]" if in_baseline else " [NEW - NOT IN BASELINE]"

        print(f"\n{i}. [Score: {score}/10 | Semantic: {cand.score:.4f}]{baseline_marker}")
        print(f"   Book: {book}")
        print(f"   Chapter: {chapter}")
        print(f"   Text: {text}...")

    # Analysis
    print("\n" + "="*80)
    print("ROOT CAUSE ANALYSIS")
    print("="*80)

    baseline_ids = {c.id for c, _ in top5_baseline}
    expanded_ids = {c.id for c, _ in top5_expanded}
    lost_results = baseline_ids - expanded_ids
    new_results = expanded_ids - baseline_ids

    print(f"\nResults lost from baseline: {len(lost_results)}/5")
    print(f"New results (not in baseline): {len(new_results)}/5")

    if lost_results:
        print("\nLOST RESULTS:")
        for cand, score in top5_baseline:
            if cand.id in lost_results:
                book = cand.payload.get('book_name', 'unknown')
                chapter = cand.payload.get('chapter_title', 'unknown')
                text = cand.payload['text'][:100].replace('\n', ' ')
                print(f"  - [{score}/10] {book} / {chapter}")
                print(f"    {text}...")

    print(f"\nExpansion length analysis:")
    print(f"  Original query length: {len(QUERY_1)} chars")
    print(f"  Expanded query length: {len(expanded)} chars")
    print(f"  Expansion ratio: {len(expanded)/len(QUERY_1):.1f}x")

    if len(expanded) / len(QUERY_1) > 10:
        print("  ⚠️ PROBLEM: Expansion is >10x original length - likely over-specified")
    elif len(expanded) / len(QUERY_1) > 5:
        print("  ⚠️ WARNING: Expansion is >5x original length - may be too broad")

    print("\n" + "="*80)

if __name__ == "__main__":
    investigate_query1()
