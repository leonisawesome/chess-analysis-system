#!/usr/bin/env python3
"""
Phase 3: Full Validation Test
Test two-stage reranking on all 10 validation queries
"""

from phase2_two_stage_reranking import two_stage_rerank
import json

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


def run_full_validation():
    """Run full validation on all 10 queries"""

    print("="*80)
    print("PHASE 3: FULL VALIDATION TEST")
    print("="*80)
    print("Configuration:")
    print("- Two-stage reranking")
    print("- Intent-aware boosting")
    print("- Chain-of-thought justifications")
    print()
    print("Goal: Achieve ≥88% precision@5")
    print("="*80)

    all_results = []

    for i, query in enumerate(QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"QUERY {i}: {query}")
        print('='*80)

        # Run two-stage reranking
        top5 = two_stage_rerank(query, verbose=False)

        print(f"\nTOP 5 RESULTS:")
        for j, result in enumerate(top5, 1):
            book = result.get('book_name', 'unknown')
            chapter = result.get('chapter_title', 'unknown')
            score = result.get('stage2_score', 0)
            intent = result.get('intent', 'unknown')
            label = result.get('final_label', 'unknown')
            justification = result.get('justification', 'N/A')
            text = result['text'][:200].replace('\n', ' ')

            print(f"\n{j}. [Score: {score}/10 | Intent: {intent} | Label: {label}]")
            print(f"   Book: {book}")
            print(f"   Chapter: {chapter}")
            print(f"   Justification: {justification}")
            print(f"   Text: {text}...")

        all_results.append({
            'query_num': i,
            'query': query,
            'top5': top5
        })

    # Save results
    print(f"\n{'='*80}")
    print("RESULTS SAVED - READY FOR MANUAL EVALUATION")
    print('='*80)

    with open('two_stage_validation_results.json', 'w') as f:
        # Convert results to JSON-serializable format
        json_results = []
        for r in all_results:
            json_results.append({
                'query_num': r['query_num'],
                'query': r['query'],
                'top5': [
                    {
                        'chunk_id': str(result.get('chunk_id', '')),
                        'score': result.get('stage2_score', 0),
                        'intent': result.get('intent', 'unknown'),
                        'label': result.get('final_label', 'unknown'),
                        'justification': result.get('justification', ''),
                        'book': result.get('book_name', 'unknown'),
                        'chapter': result.get('chapter_title', 'unknown'),
                        'text': result.get('text', '')[:500]
                    }
                    for result in r['top5']
                ]
            })
        json.dump(json_results, f, indent=2)

    print("\nResults saved to: two_stage_validation_results.json")
    print("Ready for manual evaluation")

    return all_results


if __name__ == "__main__":
    run_full_validation()
