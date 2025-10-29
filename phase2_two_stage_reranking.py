#!/usr/bin/env python3
"""
Phase 2: Two-Stage Reranking with Intent Boosting
Stage 1: Fast 0-10 scoring (40 → 10-15)
Stage 2: Chain-of-thought reasoning (10-15 → 5)
"""

from openai import OpenAI
from qdrant_client import QdrantClient
import numpy as np
import re
import os

# Initialize clients
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
qdrant_client = QdrantClient(path="./qdrant_validation_db")

EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "chess_validation"


def detect_query_type(query):
    """
    Detect query type for intent-aware boosting

    Returns: "how_to", "what_are", or "other"
    """

    query_lower = query.lower()

    # HOW-TO queries: seeking methods, improvement, training
    if re.search(r'\b(how|improve|practice|train|best way|steps to|learn to)\b', query_lower):
        return "how_to"

    # WHAT-ARE queries: seeking concepts, ideas, principles
    if re.search(r'\b(what are|what is|main ideas|principles|concepts)\b', query_lower):
        return "what_are"

    return "other"


def compute_intent_boost(chunk_intent, query_type):
    """
    Compute intent-aware boost score

    Rules:
    - HOW-TO queries: boost 'method' chunks, penalize 'theory'
    - WHAT-ARE queries: boost 'theory' chunks
    - Other queries: no boosting
    """

    if query_type == "how_to":
        boost_map = {
            'method': 0.2,     # Strong boost for method
            'example': 0.1,    # Small boost for examples
            'theory': -0.1,    # Small penalty for theory
            'pgn': -0.05       # Small penalty for PGN
        }
    elif query_type == "what_are":
        boost_map = {
            'theory': 0.2,     # Strong boost for theory
            'example': 0.1,    # Small boost for examples
            'method': 0.0,     # Neutral for method
            'pgn': -0.1        # Penalty for PGN
        }
    else:
        # No boosting for other query types
        boost_map = {'method': 0, 'theory': 0, 'example': 0, 'pgn': 0}

    return boost_map.get(chunk_intent, 0)


def embed(text):
    """Generate embedding for text"""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return np.array(response.data[0].embedding)


def semantic_search(query, top_k=40):
    """Perform semantic search and return candidates with intent labels"""

    query_vector = embed(query)

    results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector.tolist(),
        limit=top_k,
        with_payload=True
    )

    candidates = []
    for result in results:
        candidates.append({
            'chunk_id': result.id,
            'text': result.payload.get('text', ''),
            'book_name': result.payload.get('book_name', ''),
            'chapter_title': result.payload.get('chapter_title', ''),
            'intent': result.payload.get('intent', 'theory'),  # Default to theory if not labeled
            'intent_confidence': result.payload.get('intent_confidence', 'low'),
            'semantic_score': result.score
        })

    return candidates


def stage1_fast_scoring(query, candidates, query_type):
    """
    Stage 1: Fast 0-10 relevance scoring
    Returns top 10-15 candidates
    """

    prompt = f"""You are a chess expert providing quick relevance scores.

Query: "{query}"
Query Type: {query_type.replace('_', ' ').title()}

Rate each chunk's relevance from 0-10:
- 10 = Directly answers the query
- 7-9 = Highly relevant
- 4-6 = Somewhat relevant
- 0-3 = Irrelevant

Be fast and decisive. Respond with ONLY comma-separated scores.

Chunks:
"""

    for i, cand in enumerate(candidates, 1):
        text_preview = cand['text'][:200].replace('\n', ' ')
        prompt += f"{i}. {text_preview}...\n"

    prompt += "\nScores (comma-separated):"

    try:
        response = openai_client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}]
        )

        scores_text = response.choices[0].message.content.strip()
        scores = [float(s.strip()) for s in scores_text.split(',')]

        # Add scores to candidates
        for i, score in enumerate(scores[:len(candidates)]):
            candidates[i]['stage1_score'] = score

    except Exception as e:
        print(f"Warning: Stage 1 scoring failed: {e}")
        # Fallback: use semantic scores
        for cand in candidates:
            cand['stage1_score'] = cand['semantic_score'] * 10

    # Apply intent boosting
    for cand in candidates:
        intent_boost = compute_intent_boost(cand['intent'], query_type)
        # Boosted score = stage1_score + (intent_boost * 10)
        cand['boosted_score'] = cand['stage1_score'] + (intent_boost * 10)

    # Sort by boosted score and take top 10-15
    candidates.sort(key=lambda x: -x['boosted_score'])
    top_candidates = candidates[:15]

    return top_candidates


def stage2_cot_reranking(query, candidates, query_type):
    """
    Stage 2: Chain-of-thought reasoning with justifications
    Returns top 5 with detailed justifications
    """

    prompt = f"""You are a chess expert providing detailed relevance analysis.

Query: "{query}"
Query Type: {query_type.replace('_', ' ').title()}

For each chunk, provide:
1. Relevance score (0-10)
2. One-sentence justification
3. Label: method/theory/example/pgn

**Scoring criteria:**
- 10: Directly answers the query with actionable content
- 7-9: Highly relevant with specific information
- 4-6: Related but tangential or too general
- 0-3: Irrelevant or wrong intent

**Query type guidance:**
- HOW-TO queries: Prefer method chunks with practical steps
- WHAT-ARE queries: Prefer theory chunks with clear explanations

Chunks to analyze:
"""

    for i, cand in enumerate(candidates, 1):
        text_preview = cand['text'][:300].replace('\n', ' ')
        meta = f"Book: {cand['book_name']}, Chapter: {cand['chapter_title']}"
        intent_label = f"Intent: {cand['intent']} ({cand['intent_confidence']})"
        prompt += f"\n{i}. {meta} | {intent_label}\n   {text_preview}...\n"

    prompt += """\n**Output format (JSON list):**
[
  {"chunk_num": 1, "score": 8.5, "justification": "Provides step-by-step calculation methods.", "label": "method"},
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

        import json
        rankings = json.loads(result_text)

        # Map back to candidates
        final_results = []
        for ranking in rankings:
            chunk_num = ranking['chunk_num'] - 1
            if chunk_num < len(candidates):
                result = candidates[chunk_num].copy()
                result['stage2_score'] = ranking['score']
                result['justification'] = ranking['justification']
                result['final_label'] = ranking['label']
                final_results.append(result)

        # Sort by stage2_score and take top 5
        final_results.sort(key=lambda x: -x['stage2_score'])
        return final_results[:5]

    except Exception as e:
        print(f"Warning: Stage 2 reranking failed: {e}")
        # Fallback: return top 5 from stage 1
        return candidates[:5]


def two_stage_rerank(query, verbose=False):
    """
    Main two-stage reranking pipeline

    Returns: Top 5 results with justifications
    """

    # Detect query type
    query_type = detect_query_type(query)
    if verbose:
        print(f"Query type: {query_type}")

    # Retrieve top 40 candidates
    if verbose:
        print("Retrieving top 40 candidates...")
    candidates = semantic_search(query, top_k=40)

    if verbose:
        intent_dist = {}
        for c in candidates:
            intent = c['intent']
            intent_dist[intent] = intent_dist.get(intent, 0) + 1
        print(f"Intent distribution in top 40: {intent_dist}")

    # Stage 1: Fast scoring
    if verbose:
        print("Stage 1: Fast scoring (40 → 15)...")
    stage1_results = stage1_fast_scoring(query, candidates, query_type)

    if verbose:
        print(f"Stage 1 complete: {len(stage1_results)} candidates")
        print("Top 3 after Stage 1:")
        for i, r in enumerate(stage1_results[:3], 1):
            print(f"  {i}. [{r['stage1_score']:.1f} → {r['boosted_score']:.1f}] "
                  f"{r['intent']} - {r['chapter_title'][:50]}")

    # Stage 2: CoT reranking
    if verbose:
        print("\nStage 2: Chain-of-thought reranking (15 → 5)...")
    final_results = stage2_cot_reranking(query, stage1_results, query_type)

    if verbose:
        print(f"Stage 2 complete: {len(final_results)} final results")

    return final_results


if __name__ == "__main__":
    # Test on Query 5 (the critical regression case)
    test_query = "What is the best way to study chess openings?"

    print("="*80)
    print("TWO-STAGE RERANKING TEST")
    print("="*80)
    print(f"Query: {test_query}")
    print()

    results = two_stage_rerank(test_query, verbose=True)

    print("\n" + "="*80)
    print("FINAL TOP 5 RESULTS")
    print("="*80)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. [Score: {result.get('stage2_score', 0)}/10]")
        print(f"   Intent: {result['intent']} ({result['intent_confidence']})")
        print(f"   Label: {result.get('final_label', 'N/A')}")
        print(f"   Book: {result['book_name']}")
        print(f"   Chapter: {result['chapter_title']}")
        print(f"   Justification: {result.get('justification', 'N/A')}")
        print(f"   Text: {result['text'][:200]}...")
