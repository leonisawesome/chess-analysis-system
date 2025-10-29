#!/usr/bin/env python3
"""
APPROACH 4: Query Expansion + Combined Optimizations
Configuration: Query Expansion + Top 40 Candidates + Optimized Prompt
Expected gain: +2-4% (86% → 88-90%)
"""

import json
from qdrant_client import QdrantClient
from openai import OpenAI
import os

# Initialize
qdrant_client = QdrantClient(path="./qdrant_validation_db")
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

EMBEDDING_MODEL = "text-embedding-3-small"

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

def expand_query(query):
    """Use GPT-5 to expand vague queries with chess-specific terms"""

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

    expanded = response.choices[0].message.content.strip()
    return expanded

def get_semantic_candidates(query, limit=40):
    """Get semantic search results with expanded query"""
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

def create_optimized_prompt(query, candidates):
    """Chess-specific prompt with rubric (Approach 1)"""

    prompt = f"""You are a chess expert evaluating search results for a specific query.

QUERY: "{query}"

RUBRIC FOR SCORING (0-10):
- 10 = DIRECT MATCH: Content specifically addresses the query with actionable chess concepts
- 7-9 = STRONG: Relevant examples, games, or concrete illustrations of the concept
- 5-6 = TANGENTIAL: Related to chess but too general or not specific to query
- 0-4 = IRRELEVANT: Wrong intent, opposite concept, or bibliographies without content

CHESS-SPECIFIC RULES:
1. Attack ≠ Defend (opposite intents, score 0 if mismatched)
2. Openings ≠ Middlegame ≠ Endgame (different phases)
3. Book descriptions/bibliographies = 0-3 unless they contain actual instruction
4. Examples with variations/analysis = 7-9 (concrete instruction)
5. "How to" titles about the query topic = 8-10

NOW RATE THESE CHUNKS:
"""

    for i, candidate in enumerate(candidates, 1):
        text_preview = candidate.payload['text'][:250].replace('\n', ' ')
        prompt += f"\n{i}. {text_preview}...\n"

    prompt += "\nRespond with ONLY comma-separated scores"

    return prompt

def optimized_gpt5_rerank(query, candidates):
    """Rerank with optimized prompt"""
    prompt = create_optimized_prompt(query, candidates)

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    scores_text = response.choices[0].message.content.strip()
    scores = [int(s.strip()) for s in scores_text.split(',')]

    ranked = list(zip(candidates, scores))
    ranked.sort(key=lambda x: x[1], reverse=True)

    return ranked

def test_query_expansion():
    """Test all 3 approaches combined on all 10 queries"""

    print("="*80)
    print("APPROACH 4: QUERY EXPANSION + COMBINED OPTIMIZATIONS")
    print("="*80)
    print("Configuration:")
    print("  ✓ Query Expansion (Approach 4)")
    print("  ✓ Top 40 Candidates (Approach 2)")
    print("  ✓ Optimized Prompt (Approach 1)")
    print()
    print("Testing on all 10 validation queries")
    print("="*80)

    results = []

    for i, original_query in enumerate(VALIDATION_QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"QUERY {i}: {original_query}")
        print('='*80)

        # Step 1: Expand query
        expanded_query = expand_query(original_query)
        print(f"\nExpanded: {expanded_query}")

        # Step 2: Get 40 candidates using EXPANDED query
        candidates = get_semantic_candidates(expanded_query, limit=40)

        # Step 3: Rerank with optimized prompt using ORIGINAL query
        ranked = optimized_gpt5_rerank(original_query, candidates)

        # Show top 5
        top_5 = ranked[:5]

        print(f"\nTop 5 results:")
        for j, (candidate, score) in enumerate(top_5, 1):
            text_preview = candidate.payload['text'][:120].replace('\n', ' ')
            book = candidate.payload.get('book_name', 'unknown')
            chapter = candidate.payload.get('chapter_title', 'unknown')
            print(f"\n{j}. GPT-5 Score: {score}/10 | Semantic: {candidate.score:.4f}")
            print(f"   Book: {book}")
            print(f"   Chapter: {chapter}")
            print(f"   {text_preview}...")

        # Store for evaluation
        results.append({
            "query_id": i,
            "original_query": original_query,
            "expanded_query": expanded_query,
            "results": [
                {
                    "llm_score": score,
                    "semantic_score": candidate.score,
                    "book": candidate.payload.get('book_name', 'unknown'),
                    "chapter": candidate.payload.get('chapter_title', 'unknown'),
                    "text": candidate.payload['text'][:600]
                }
                for candidate, score in top_5
            ]
        })

    # Save results
    with open('approach4_query_expansion_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open('approach4_query_expansion_for_review.txt', 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("APPROACH 4: QUERY EXPANSION + COMBINED - MANUAL EVALUATION\n")
        f.write("="*80 + "\n\n")
        f.write("Configuration: Query Expansion + Top 40 Candidates + Optimized Prompt\n")
        f.write("Rate each result as: y (relevant), p (partial), n (not relevant)\n\n")

        for query_data in results:
            f.write("="*80 + "\n")
            f.write(f"QUERY {query_data['query_id']}: {query_data['original_query']}\n")
            f.write(f"Expanded: {query_data['expanded_query']}\n")
            f.write("="*80 + "\n\n")

            for i, result in enumerate(query_data['results'], 1):
                f.write(f"--- RESULT {i} ---\n")
                f.write(f"LLM Score: {result['llm_score']}/10\n")
                f.write(f"Semantic Score: {result['semantic_score']:.4f}\n")
                f.write(f"Book: {result['book']}\n")
                f.write(f"Chapter: {result['chapter']}\n\n")
                f.write("Text:\n")
                f.write(result['text'])
                if len(result['text']) >= 600:
                    f.write("\n[... truncated ...]")
                f.write("\n\nJUDGMENT: _____ (y/p/n)\n\n")

            f.write("\n")

    print(f"\n{'='*80}")
    print("APPROACH 4 TEST COMPLETE")
    print(f"Results saved to:")
    print(f"  - approach4_query_expansion_for_review.txt")
    print(f"\nNext: Manual evaluation to compare against 86-87% baseline")
    print(f"Target: 88-90% precision@5")
    print("="*80)

if __name__ == "__main__":
    test_query_expansion()
