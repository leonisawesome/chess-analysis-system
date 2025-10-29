#!/usr/bin/env python3
"""
Compare Week 1 vs Week 3 retrieval results
Check if RESULTS changed or just JUDGMENTS changed
"""

import json

# Week 1 judgments
week1_judgments = {
    2: ["relevant", "partial", "relevant", "relevant", "partial"],  # French Defense: 80%
    4: ["relevant", "relevant", "relevant", "relevant", "partial"],  # Weaknesses: 90%
    6: ["relevant", "relevant", "relevant", "relevant", "relevant"],  # Defend: 100%
}

# Week 3 judgments (my current evaluation of baseline)
week3_judgments = {
    2: ["n", "p", "y", "p", "n"],  # French Defense: 40%
    4: ["y", "n", "n", "n", "n"],  # Weaknesses: 20%
    6: ["y", "y", "n", "n", "n"],  # Defend: 40%
}

# Load baseline results to see what was actually retrieved
with open('baseline_test_results.txt', 'r') as f:
    content = f.read()

print("="*80)
print("WEEK 1 VS WEEK 3 JUDGMENT COMPARISON")
print("="*80)
print("\nFor queries that degraded significantly:")
print()

for query_id in [2, 4, 6]:
    week1 = week1_judgments[query_id]
    week3 = week3_judgments[query_id]

    # Convert to scores
    def score(judgment):
        if judgment in ['relevant', 'y']: return 1.0
        if judgment in ['partial', 'p']: return 0.5
        return 0.0

    week1_score = sum(score(j) for j in week1) / 5.0
    week3_score = sum(score(j) for j in week3) / 5.0

    print(f"\nQuery {query_id}:")
    print(f"  Week 1 judgments: {week1} = {week1_score:.0%}")
    print(f"  Week 3 judgments: {week3} = {week3_score:.0%}")
    print(f"  Change: {(week3_score - week1_score)*100:+.0f} percentage points")

    # Check if ANY judgments match
    matches = sum(1 for i in range(5) if (week1[i] in ['relevant', 'partial']) == (week3[i] in ['y', 'p']))
    print(f"  Agreement: {matches}/5 results judged similarly")

    if matches < 3:
        print(f"  ⚠️  Major disagreement - likely DIFFERENT RESULTS retrieved")
    else:
        print(f"  ✓ Similar - likely same results, different judgment standards")

print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)

print("""
If agreement < 3/5 for most queries:
  → Results CHANGED (different embeddings/database)
  → Need to investigate why retrieval differs

If agreement ≥ 3/5 for most queries:
  → Results SAME, but I judged more harshly
  → Week 1 evaluation may have been too lenient
  → True baseline is ~50%, not 85%
""")
