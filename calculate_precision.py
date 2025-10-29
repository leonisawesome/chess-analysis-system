#!/usr/bin/env python3
"""
Calculate Precision@5 from Manual Judgments
Reads validation_results_for_review.txt with filled-in judgments.
"""

import re
import json


def parse_judgments(file_path='validation_results_for_review.txt'):
    """
    Parse judgment file and extract y/p/n ratings.
    Returns: list of dicts with query_id, result_num, and judgment
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all judgment lines
    judgment_pattern = r'JUDGMENT:\s*([ypn])'
    judgments = re.findall(judgment_pattern, content, re.IGNORECASE)

    # Find all query numbers
    query_pattern = r'QUERY (\d+):'
    queries = re.findall(query_pattern, content)

    if not judgments:
        print("❌ No judgments found!")
        print("Make sure you filled in 'JUDGMENT: y' or 'JUDGMENT: p' or 'JUDGMENT: n'")
        return None

    print(f"Found {len(judgments)} judgments for {len(queries)} queries")

    # Group judgments by query
    results = []
    judgment_idx = 0

    for query_id in queries:
        query_results = []
        for result_num in range(1, 6):  # 5 results per query
            if judgment_idx < len(judgments):
                judgment = judgments[judgment_idx].lower()
                query_results.append({
                    'query_id': int(query_id),
                    'result_num': result_num,
                    'judgment': judgment
                })
                judgment_idx += 1

        results.append({
            'query_id': int(query_id),
            'judgments': query_results
        })

    return results


def calculate_precision(results):
    """
    Calculate precision@5 for each query and overall.
    y = 1.0, p = 0.5, n = 0.0
    """
    if not results:
        return None

    query_scores = []
    total_relevant = 0.0

    print("\n" + "="*80)
    print("PRECISION@5 RESULTS")
    print("="*80)

    for query_result in results:
        query_id = query_result['query_id']
        judgments = query_result['judgments']

        relevant_count = 0.0
        judgment_str = []

        for j in judgments:
            if j['judgment'] == 'y':
                relevant_count += 1.0
                judgment_str.append('y')
            elif j['judgment'] == 'p':
                relevant_count += 0.5
                judgment_str.append('p')
            else:
                judgment_str.append('n')

        precision = relevant_count / 5.0
        query_scores.append({
            'query_id': query_id,
            'relevant_count': relevant_count,
            'precision': precision,
            'judgments': judgment_str
        })

        total_relevant += relevant_count

        print(f"\nQuery {query_id}:")
        print(f"  Judgments: {' '.join(judgment_str)}")
        print(f"  Relevant: {relevant_count}/5")
        print(f"  Precision@5: {precision:.1%}")

    overall_precision = total_relevant / (len(query_scores) * 5)

    print("\n" + "="*80)
    print("OVERALL RESULTS")
    print("="*80)
    print(f"\nTotal queries: {len(query_scores)}")
    print(f"Total results evaluated: {len(query_scores) * 5}")
    print(f"Total relevant: {total_relevant}")
    print(f"\n📊 OVERALL PRECISION@5: {overall_precision:.1%}")
    print(f"   Baseline (Week 1): 85.0%")

    improvement = overall_precision - 0.85
    print(f"   Improvement: {improvement*100:+.1f} percentage points")

    print("\n" + "="*80)
    print("SUCCESS CRITERIA")
    print("="*80)

    if overall_precision >= 0.90:
        print("✅ TARGET MET: Precision@5 ≥ 90%")
        print("   → Optimizations are working")
        print("   → PROCEED TO 100-BOOK SCALE TEST")
    elif overall_precision >= 0.86:
        print("⚠️  SMALL IMPROVEMENT: Precision@5 86-89%")
        print("   → Optimizations help slightly")
        print("   → Consider tuning parameters before scaling")
    else:
        print("❌ NO IMPROVEMENT: Precision@5 ≤ 85%")
        print("   → Optimizations not effective")
        print("   → Debug which optimization is failing")

    print("="*80)

    # Save results
    output = {
        'overall_precision_at_5': overall_precision,
        'baseline_precision': 0.85,
        'improvement': improvement,
        'target_met': overall_precision >= 0.90,
        'total_queries': len(query_scores),
        'total_relevant': total_relevant,
        'query_scores': query_scores
    }

    with open('precision_results.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Detailed results saved to: precision_results.json\n")

    return output


def main():
    print("="*80)
    print("CALCULATING PRECISION@5 FROM MANUAL JUDGMENTS")
    print("="*80)

    # Parse judgments
    results = parse_judgments()

    if not results:
        print("\n❌ Failed to parse judgments")
        print("\nMake sure validation_results_for_review.txt has judgments like:")
        print("  JUDGMENT: y")
        print("  JUDGMENT: p")
        print("  JUDGMENT: n")
        return

    # Calculate precision
    output = calculate_precision(results)

    if output and output['target_met']:
        print("\n✅ Ready to proceed to 100-book validation")
    else:
        print("\n⚠️  Review results before proceeding to scale test")


if __name__ == '__main__':
    main()
