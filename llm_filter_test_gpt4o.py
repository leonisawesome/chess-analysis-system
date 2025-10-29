#!/usr/bin/env python3
"""
Test with GPT-4o (best available model) to establish ceiling for filtering
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

def llm_rerank(query, candidates, model="gpt-4o"):
    """Use best available model to rerank candidates by relevance"""

    # Build prompt
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

    prompt += "\nRespond with ONLY comma-separated scores like: 7,3,9,2,6,8,1,4,10,5,4,3,8,9,1,6,7,2,5,4"

    # Get scores from best model
    response = openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=100
    )

    # Parse scores
    scores_text = response.choices[0].message.content.strip()
    scores = [int(s.strip()) for s in scores_text.split(',')]

    # Combine candidates with scores and sort
    ranked = list(zip(candidates, scores))
    ranked.sort(key=lambda x: x[1], reverse=True)

    return ranked

def test_llm_filtering():
    """Run LLM filtering test with GPT-4o (best model)"""

    # Try GPT-4o, fall back to GPT-4-turbo if not available
    models_to_try = ["gpt-4o", "gpt-4-turbo", "gpt-4"]

    model_used = None
    for model in models_to_try:
        try:
            # Test if model works
            test_response = openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            model_used = model
            print(f"✓ Using model: {model}")
            break
        except Exception as e:
            print(f"✗ Model {model} not available: {e}")
            continue

    if not model_used:
        print("ERROR: No suitable model available")
        return

    results = []
    total_cost = 0

    for i, query in enumerate(VALIDATION_QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"Query {i}: {query}")
        print('='*80)

        # Get semantic candidates
        candidates = get_semantic_candidates(query, limit=20)

        # LLM rerank with best model
        ranked = llm_rerank(query, candidates, model=model_used)

        # Show top 5
        top_5 = ranked[:5]

        print(f"\nTop 5 after {model_used} reranking:")
        for j, (candidate, score) in enumerate(top_5, 1):
            text_preview = candidate.payload['text'][:200].replace('\n', ' ')
            book = candidate.payload.get('book_name', 'unknown')
            chapter = candidate.payload.get('chapter_title', 'unknown')
            print(f"\n{j}. LLM Score: {score}/10 | Semantic: {candidate.score:.4f}")
            print(f"   Book: {book}")
            print(f"   Chapter: {chapter}")
            print(f"   {text_preview}...")

        # Store for evaluation
        results.append({
            "query_id": i,
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

        # Estimate cost
        if model_used == "gpt-4o":
            total_cost += 0.10  # GPT-4o is cheaper than GPT-4
        elif model_used == "gpt-4-turbo":
            total_cost += 0.15
        else:
            total_cost += 0.20

    # Save results
    with open('llm_filtering_gpt4o_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Save human-readable version for manual evaluation
    with open('llm_filtering_gpt4o_for_review.txt', 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write(f"{model_used.upper()} FILTERING TEST - MANUAL EVALUATION\n")
        f.write("="*80 + "\n\n")
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
    print(f"{model_used.upper()} filtering test complete")
    print(f"Estimated cost: ${total_cost:.2f}")
    print(f"Results saved to:")
    print(f"  - llm_filtering_gpt4o_results.json (machine-readable)")
    print(f"  - llm_filtering_gpt4o_for_review.txt (human evaluation)")
    print(f"\n{'='*80}")
    print("Next: Manual evaluation to establish CEILING for filtering")
    print("="*80)

if __name__ == "__main__":
    test_llm_filtering()
