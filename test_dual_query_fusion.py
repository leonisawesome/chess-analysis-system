#!/usr/bin/env python3
"""
Full validation test: Dual-Query Fusion + Domain Filter
Expected precision: 89-90%
"""

from dual_query_fusion import dual_query_fusion_rerank
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
    """Run full validation test on all 10 queries"""

    print("="*80)
    print("DUAL-QUERY FUSION VALIDATION TEST")
    print("="*80)
    print("Configuration:")
    print("- Domain-preserving expansion for HOW-TO queries")
    print("- Dual retrieval (original + domain-focused)")
    print("- Domain scoring + filtering")
    print("- GPT-5 reranking with method/theory classification")
    print()
    print("Goal: Achieve ≥89% precision@5")
    print("="*80)

    all_results = []

    for i, query in enumerate(QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"QUERY {i}: {query}")
        print('='*80)

        # Run dual-query fusion
        top5 = dual_query_fusion_rerank(query, verbose=False)

        print(f"\nTOP 5 RESULTS:")
        for j, result in enumerate(top5, 1):
            book = result['meta'].get('book_name', 'unknown')
            chapter = result['meta'].get('chapter', 'unknown')
            score = result.get('score', 0)
            label = result.get('label', 'unknown')
            domain_score = result.get('domain_score', 0)
            text = result['text'][:200].replace('\n', ' ')

            print(f"\n{j}. [Score: {score}/10 | Label: {label} | Domain: {domain_score:.2f}]")
            print(f"   Book: {book}")
            print(f"   Chapter: {chapter}")
            print(f"   Justification: {result.get('justification', 'N/A')}")
            print(f"   Text: {text}...")

        all_results.append({
            'query_num': i,
            'query': query,
            'top5': top5
        })

    # Save results to file
    print(f"\n{'='*80}")
    print("RESULTS SAVED - READY FOR MANUAL EVALUATION")
    print('='*80)

    with open('dual_fusion_validation_results.json', 'w') as f:
        # Convert results to JSON-serializable format
        json_results = []
        for r in all_results:
            json_results.append({
                'query_num': r['query_num'],
                'query': r['query'],
                'top5': [
                    {
                        'chunk_id': str(result.get('chunk_id', '')),
                        'score': result.get('score', 0),
                        'label': result.get('label', 'unknown'),
                        'domain_score': result.get('domain_score', 0),
                        'justification': result.get('justification', ''),
                        'book': result['meta'].get('book_name', 'unknown'),
                        'chapter': result['meta'].get('chapter', 'unknown'),
                        'text': result.get('text', '')[:500]
                    }
                    for result in r['top5']
                ]
            })
        json.dump(json_results, f, indent=2)

    print("\nResults saved to: dual_fusion_validation_results.json")
    print("Ready for manual evaluation")

    return all_results


if __name__ == "__main__":
    run_full_validation()
