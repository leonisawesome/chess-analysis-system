#!/usr/bin/env python3
"""
Automated Relevance Evaluation
Uses keyword matching and semantic heuristics to judge relevance.
Less accurate than human evaluation, but allows rapid validation.
"""

import json
import re


# Query-specific relevance keywords
RELEVANCE_KEYWORDS = {
    1: {  # How do I improve my calculation in the middlegame?
        'high': ['calculation', 'calculating', 'calculate', 'how far ahead', 'see ahead', 'visualization', 'candidate moves', 'variations'],
        'medium': ['tactics', 'analyze', 'thinking', 'moves ahead', 'evaluation'],
        'book_bonus': ['500_questions', 'fundamental_tactics']
    },
    2: {  # What are the main ideas in the French Defense?
        'high': ['french', 'pawn chain', 'central pawn', 'e5', 'd5', 'space advantage', 'typical plans'],
        'medium': ['opening', 'defense', 'ideas', 'strategy'],
        'book_bonus': ['french_defense']
    },
    3: {  # When should I trade pieces in the endgame?
        'high': ['trade', 'trading', 'exchange', 'simplify', 'endgame', 'technique', 'piece activity'],
        'medium': ['endgame', 'ending', 'conversion'],
        'book_bonus': ['endgames', '500_questions']
    },
    4: {  # How do I create weaknesses in my opponent's position?
        'high': ['weakness', 'weaknesses', 'weak square', 'pawn structure', 'target', 'positional'],
        'medium': ['attack', 'strategy', 'plan'],
        'book_bonus': ['fundamentals', '500_questions']
    },
    5: {  # What is the best way to study chess openings?
        'high': ['study', 'learning', 'opening repertoire', 'preparation', 'memorize', 'understanding'],
        'medium': ['opening', 'openings', 'theory', 'lines'],
        'book_bonus': ['500_questions', 'french_defense']
    },
    6: {  # How do I defend against aggressive attacks?
        'high': ['defend', 'defending', 'defense', 'counterplay', 'attack', 'aggressive'],
        'medium': ['tactics', 'calculation', 'pressure'],
        'book_bonus': ['500_questions', 'fundamental_tactics']
    },
    7: {  # What endgame principles should beginners learn first?
        'high': ['endgame principle', 'king activity', 'pawn endgame', 'basic technique', 'beginner', 'fundamental'],
        'medium': ['endgame', 'ending', 'technique'],
        'book_bonus': ['endgames', 'fundamentals', '500_questions']
    },
    8: {  # How do I improve my positional understanding?
        'high': ['positional', 'position', 'understanding', 'strategic', 'plan', 'piece coordination'],
        'medium': ['strategy', 'improve', 'evaluation'],
        'book_bonus': ['fundamentals', '500_questions']
    },
    9: {  # When is it correct to sacrifice material?
        'high': ['sacrifice', 'sacrifices', 'compensation', 'initiative', 'attack', 'material'],
        'medium': ['tactics', 'combinations', 'aggressive'],
        'book_bonus': ['fundamental_tactics', '500_questions']
    },
    10: {  # How do I convert a winning position?
        'high': ['convert', 'winning', 'technique', 'simplify', 'endgame', 'realization'],
        'medium': ['win', 'advantage', 'technique'],
        'book_bonus': ['endgames', '500_questions', 'fundamentals']
    }
}


def score_relevance(query_id, text, book_name, chapter_title):
    """
    Score relevance of a result to a query.
    Returns: 'y', 'p', or 'n'
    """
    text_lower = text.lower()
    book_lower = book_name.lower()
    chapter_lower = chapter_title.lower()

    keywords = RELEVANCE_KEYWORDS.get(query_id, {})
    high_keywords = keywords.get('high', [])
    medium_keywords = keywords.get('medium', [])
    bonus_books = keywords.get('book_bonus', [])

    score = 0

    # Check high-relevance keywords (2 points each)
    for keyword in high_keywords:
        if keyword.lower() in text_lower or keyword.lower() in chapter_lower:
            score += 2

    # Check medium-relevance keywords (1 point each)
    for keyword in medium_keywords:
        if keyword.lower() in text_lower or keyword.lower() in chapter_lower:
            score += 1

    # Book bonus (1 point if from expected book)
    for bonus_book in bonus_books:
        if bonus_book.lower() in book_lower:
            score += 1

    # Decision thresholds
    if score >= 5:
        return 'y'  # Highly relevant
    elif score >= 2:
        return 'p'  # Partially relevant
    else:
        return 'n'  # Not relevant


def auto_evaluate():
    """Generate automatic judgments for all results"""

    # Load structured results
    with open('validation_results_structured.json', 'r') as f:
        all_results = json.load(f)

    # Load full results file for text
    with open('validation_results_for_review.txt', 'r', encoding='utf-8') as f:
        full_content = f.read()

    # Parse out text sections
    query_sections = re.split(r'={80}\nQUERY (\d+):', full_content)

    evaluations = []
    total_y = 0
    total_p = 0
    total_n = 0

    print("="*80)
    print("AUTOMATED RELEVANCE EVALUATION")
    print("="*80)
    print("\nUsing keyword matching and semantic heuristics")
    print("Note: Less accurate than human evaluation\n")

    for query_data in all_results:
        query_id = query_data['query_id']
        query_text = query_data['query']

        print(f"\nQuery {query_id}: {query_text}")

        query_judgments = []

        # Find the section for this query
        result_num = 1
        for i in range(1, len(query_sections)):
            if query_sections[i] == str(query_id):
                section_text = query_sections[i+1] if i+1 < len(query_sections) else ""

                # Extract each result's text
                result_texts = re.split(r'--- RESULT \d+ ---', section_text)

                for result_idx, result_text in enumerate(result_texts[1:6], 1):  # Results 1-5
                    # Extract book name and text
                    book_match = re.search(r'Book: (.+)', result_text)
                    chapter_match = re.search(r'Chapter: (.+)', result_text)
                    text_match = re.search(r'Text:\n(.+?)(?:\[... truncated ...\]|\n\nJUDGMENT:)', result_text, re.DOTALL)

                    if book_match and text_match:
                        book_name = book_match.group(1).strip()
                        chapter_title = chapter_match.group(1).strip() if chapter_match else ''
                        result_content = text_match.group(1).strip()

                        # Score relevance
                        judgment = score_relevance(query_id, result_content, book_name, chapter_title)
                        query_judgments.append(judgment)

                        if judgment == 'y':
                            total_y += 1
                            symbol = '✓'
                        elif judgment == 'p':
                            total_p += 1
                            symbol = '~'
                        else:
                            total_n += 1
                            symbol = '✗'

                        print(f"  Result {result_idx}: {judgment} {symbol} ({book_name})")

                break

        evaluations.append({
            'query_id': query_id,
            'judgments': query_judgments
        })

    # Calculate precision
    total_relevant = total_y + (total_p * 0.5)
    precision = total_relevant / 50.0

    print("\n" + "="*80)
    print("AUTOMATED EVALUATION RESULTS")
    print("="*80)
    print(f"\nJudgments:")
    print(f"  Relevant (y): {total_y}")
    print(f"  Partial (p): {total_p}")
    print(f"  Not relevant (n): {total_n}")
    print(f"\nTotal relevant: {total_relevant} / 50")
    print(f"\n📊 ESTIMATED PRECISION@5: {precision:.1%}")
    print(f"   Baseline (Week 1): 85.0%")
    print(f"   Improvement: {(precision - 0.85)*100:+.1f} percentage points")

    print("\n" + "="*80)
    if precision >= 0.90:
        print("✅ ESTIMATED TARGET MET")
        print("   Automated evaluation suggests optimizations are working")
    elif precision >= 0.86:
        print("⚠️  SMALL IMPROVEMENT DETECTED")
    else:
        print("❌ NO IMPROVEMENT DETECTED")
    print("\n⚠️  Note: Automated evaluation is approximate")
    print("   For final decision, consider manual review of borderline cases")
    print("="*80)

    # Save automated judgments
    output = {
        'method': 'automated_keyword_matching',
        'precision_at_5': precision,
        'baseline': 0.85,
        'improvement': precision - 0.85,
        'evaluations': evaluations,
        'counts': {'y': total_y, 'p': total_p, 'n': total_n}
    }

    with open('automated_evaluation_results.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Saved to: automated_evaluation_results.json\n")

    return precision, evaluations


if __name__ == '__main__':
    precision, evals = auto_evaluate()
