#!/usr/bin/env python3
"""
Constrained query expansion with cosine similarity validation
Combines Grok's constrained approach with ChatGPT's validation
"""

from openai import OpenAI
import numpy as np
import os

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

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

    response = client.chat.completions.create(
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
        threshold: Minimum cosine similarity (default 0.85)

    Returns:
        (is_valid, cosine_score)
    """

    # Use OpenAI embeddings for consistency with our semantic search
    original_vec = client.embeddings.create(
        model="text-embedding-3-small",
        input=original_query
    ).data[0].embedding

    expanded_vec = client.embeddings.create(
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


def test_constrained_validated():
    """Test on all 10 validation queries"""

    queries = [
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

    results = []

    print("="*80)
    print("CONSTRAINED + VALIDATED EXPANSION TEST")
    print("="*80)
    print("Goal: Preserve intent, limit to 3-5x length, cosine ≥0.85")
    print()

    for i, query in enumerate(queries, 1):
        print(f"\n{'='*80}")
        print(f"Query {i}: {query}")
        print(f"Original length: {len(query)} chars")
        print('='*80)

        expanded, cosine, status = expand_with_validation(query)

        print(f"\nExpanded: {expanded}")
        print(f"Expanded length: {len(expanded)} chars ({len(expanded)/len(query):.1f}x)")
        if cosine:
            print(f"Cosine similarity: {cosine:.3f}")
        print(f"Status: {status}")

        # Check for success criteria
        ratio = len(expanded) / len(query)
        if status == "validated":
            if ratio <= 5 and cosine >= 0.85:
                print("✓ PASS: Good expansion")
            elif ratio > 5:
                print(f"⚠️  WARNING: Ratio {ratio:.1f}x exceeds 5x target")
            elif cosine < 0.85:
                print(f"⚠️  WARNING: Cosine {cosine:.3f} below 0.85")
        elif status == "rejected":
            print("❌ REJECTED: Using original query")

        results.append({
            "query_num": i,
            "original": query,
            "expanded": expanded,
            "ratio": len(expanded) / len(query),
            "cosine": cosine,
            "status": status
        })

    print(f"\n{'='*80}")
    print("EXPANSION SUMMARY")
    print('='*80)

    validated_count = sum(1 for r in results if r['status'] == 'validated')
    rejected_count = sum(1 for r in results if r['status'] == 'rejected')

    print(f"\nValidated: {validated_count}/10")
    print(f"Rejected: {rejected_count}/10")
    print()

    for r in results:
        status_symbol = "✓" if r['status'] == 'validated' else "✗"
        cosine_str = f"{r['cosine']:.3f}" if r['cosine'] else "N/A"
        print(f"{status_symbol} Q{r['query_num']}: {r['ratio']:.1f}x, cosine={cosine_str}, {r['status']}")

    # Check critical queries
    print(f"\n{'='*80}")
    print("CRITICAL QUERY CHECK")
    print('='*80)

    q1 = results[0]  # Query 1
    q5 = results[4]  # Query 5

    print(f"\nQuery 1 (Calculation): {q1['ratio']:.1f}x, cosine={q1['cosine']:.3f if q1['cosine'] else 'N/A'}")
    if q1['ratio'] <= 5 and (q1['cosine'] is None or q1['cosine'] >= 0.85):
        print("  ✓ GOOD: Should avoid regression")
    else:
        print(f"  ⚠️  WARNING: May still cause issues")

    print(f"\nQuery 5 (Study openings): {q5['ratio']:.1f}x, cosine={q5['cosine']:.3f if q5['cosine'] else 'N/A'}")
    if q5['ratio'] <= 5 and (q5['cosine'] is None or q5['cosine'] >= 0.85):
        print("  ✓ GOOD: Should avoid 90%→60% regression")
    else:
        print(f"  ⚠️  WARNING: May still regress")

    print(f"\n{'='*80}")
    print("NEXT STEP")
    print('='*80)

    if validated_count >= 8 and all(r['ratio'] <= 5.5 for r in results if r['status'] == 'validated'):
        print("\n✓ Expansions look good!")
        print("→ Proceed to full validation test on all 10 queries")
    else:
        print("\n⚠️  Expansions may still have issues")
        print("→ Review manually before proceeding to full validation")

    return results

if __name__ == "__main__":
    test_constrained_validated()
