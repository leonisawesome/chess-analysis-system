#!/usr/bin/env python3
"""
APPROACH 1: Prompt Engineering with Chess-Specific Rubric
Expected gain: +3-5% (80% → 83-85%)
Effort: 1 day
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

def get_semantic_candidates(query, limit=20):
    """Get top 20 semantic search results"""
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
    """
    Create chess-specific prompt with:
    - Clear rubric for 0/5/10 scoring
    - Intent disambiguation (attack vs defend, opening vs endgame)
    - Few-shot examples for chess context
    """

    prompt = f"""You are a chess expert evaluating search results for a specific query.

QUERY: "{query}"

RUBRIC FOR SCORING (0-10):
- 10 = DIRECT MATCH: Content specifically addresses the query with actionable chess concepts
  * For "create weaknesses": Pawn breaks, forcing moves, exploiting square control
  * For "defend attacks": Defensive techniques, counterplay, prophylaxis
  * For "French Defense": Specific variations, key ideas, pawn structures

- 5 = TANGENTIAL: Related to chess but too general or not specific to query
  * General strategy without query-specific details
  * Correct topic area but lacks actionable information
  * Book descriptions without content snippets

- 0 = IRRELEVANT: Wrong intent, opposite concept, or unrelated
  * Defending content for attacking query (or vice versa)
  * Wrong opening (Sicilian for French Defense query)
  * Wrong game phase (opening for endgame query)
  * Bibliography/references without instructional content

CHESS-SPECIFIC RULES:
1. Attack ≠ Defend (opposite intents, score 0 if mismatched)
2. Openings ≠ Middlegame ≠ Endgame (different phases)
3. Book descriptions/bibliographies = 0 unless they contain actual chess instruction
4. Examples/games = 5-7 (illustrative but not direct instruction)
5. "How to" titles about the query topic = 8-10

FEW-SHOT EXAMPLES:

Query: "When is it correct to sacrifice material?"
- Chunk: "Why does a sacrifice make sense? It means you have less material to attack with..." → 10 (directly explains sacrifice logic)
- Chunk: "The Exchange Sacrifice: The 'exchange' is the difference between rook and minor piece..." → 10 (specific sacrifice type)
- Chunk: "Conserve your pieces in the endgame to maintain material advantage" → 0 (opposite concept)
- Chunk: "Chess Explained: Sacrifices by John Doe" → 3 (book title only, no content)

Query: "How do I defend against aggressive attacks?"
- Chunk: "Secrets of Chess Defence: Good defensive abilities earn many points..." → 10 (directly about defense)
- Chunk: "Chapter Fifteen: Defending - I don't like defending. How can I avoid it? You can't..." → 7 (Q&A about defense mindset)
- Chunk: "Secrets of Attacking Chess: The premise for a successful attack..." → 0 (opposite intent - attacking, not defending)

Query: "What are the main ideas in the French Defense?"
- Chunk: "The Winawer French: 1.e4 e6 2.d4 d5 3.Nc3 Bb4 - Black's counterplay on the queenside..." → 10 (specific variation with ideas)
- Chunk: "Introduction: What makes a French player? The French is vast in scale..." → 7 (overview but vague)
- Chunk: "Bibliography: A Ferocious Opening Repertoire, Beating the French..." → 0 (just book list)
- Chunk: "In the Sicilian Defense, Black plays c5 to counter White's center..." → 0 (wrong opening)

NOW RATE THESE CHUNKS FOR THE QUERY:
"""

    for i, candidate in enumerate(candidates, 1):
        text_preview = candidate.payload['text'][:300].replace('\n', ' ')
        book = candidate.payload.get('book_name', 'unknown')
        chapter = candidate.payload.get('chapter_title', 'unknown')
        prompt += f"\n{i}. [Book: {book} | Chapter: {chapter}]\n   {text_preview}...\n"

    prompt += """
RESPOND WITH ONLY comma-separated scores (e.g., 7,3,9,2,6,8,1,4,10,5,4,3,8,9,1,6,7,2,5,4)
Use the rubric strictly. Be harsh on mismatched intents and bibliographies.
"""

    return prompt

def optimized_gpt5_rerank(query, candidates):
    """Rerank with optimized prompt"""

    prompt = create_optimized_prompt(query, candidates)

    # Get scores from GPT-5
    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse scores
    scores_text = response.choices[0].message.content.strip()
    scores = [int(s.strip()) for s in scores_text.split(',')]

    # Combine candidates with scores and sort
    ranked = list(zip(candidates, scores))
    ranked.sort(key=lambda x: x[1], reverse=True)

    return ranked

def test_prompt_engineering():
    """Test optimized prompt vs baseline on vague queries"""

    print("="*80)
    print("APPROACH 1: PROMPT ENGINEERING TEST")
    print("="*80)
    print("Testing on queries where GPT-5 baseline had room for improvement")
    print()

    # Focus on queries with <80% or potential for improvement
    test_queries = [
        (1, "How do I improve my calculation in the middlegame?"),      # 75% baseline
        (2, "What are the main ideas in the French Defense?"),          # 80% baseline
        (3, "When should I trade pieces in the endgame?"),              # 60% baseline (low)
        (4, "How do I create weaknesses in my opponent's position?"),   # 80% baseline
        (6, "How do I defend against aggressive attacks?"),             # 50% baseline (worst)
        (7, "What endgame principles should beginners learn first?"),   # 60% baseline (low)
    ]

    results = []

    for query_id, query in test_queries:
        print(f"\n{'='*80}")
        print(f"QUERY {query_id}: {query}")
        print('='*80)

        # Get semantic candidates
        candidates = get_semantic_candidates(query, limit=20)

        # Optimized rerank
        ranked = optimized_gpt5_rerank(query, candidates)

        # Show top 5
        top_5 = ranked[:5]

        print(f"\nTop 5 with OPTIMIZED prompt:")
        for i, (candidate, score) in enumerate(top_5, 1):
            text_preview = candidate.payload['text'][:150].replace('\n', ' ')
            book = candidate.payload.get('book_name', 'unknown')
            chapter = candidate.payload.get('chapter_title', 'unknown')
            print(f"\n{i}. GPT-5 Score: {score}/10 | Semantic: {candidate.score:.4f}")
            print(f"   Book: {book} | Chapter: {chapter}")
            print(f"   {text_preview}...")

        # Store for evaluation
        results.append({
            "query_id": query_id,
            "query": query,
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
    with open('approach1_prompt_engineering_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open('approach1_prompt_engineering_for_review.txt', 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("APPROACH 1: PROMPT ENGINEERING - MANUAL EVALUATION\n")
        f.write("="*80 + "\n\n")
        f.write("Compare to GPT-5 baseline results\n")
        f.write("Rate each result as: y (relevant), p (partial), n (not relevant)\n\n")

        for query_data in results:
            f.write("="*80 + "\n")
            f.write(f"QUERY {query_data['query_id']}: {query_data['query']}\n")
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
    print("APPROACH 1 TEST COMPLETE")
    print(f"Results saved to:")
    print(f"  - approach1_prompt_engineering_for_review.txt")
    print(f"\nNext: Manual evaluation to measure improvement over 80% baseline")
    print("="*80)

if __name__ == "__main__":
    test_prompt_engineering()
