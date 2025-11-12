#!/usr/bin/env python3
"""
Scan all books and flag those that might not be RAG-worthy:
1. Beginner books
2. Autobiographical books (my life, my games, etc.)
3. Historical books
4. General interest/narrative books
"""
import re
from pathlib import Path
from collections import defaultdict

# Scan current EPUB files
epub_dir = Path("/Volumes/T7 Shield/rag/books/epub")
current_files = sorted([f.name for f in epub_dir.glob("*.epub")])

print(f"Scanning {len(current_files)} books for non-RAG-worthy content...")
print("="*80)

# Load diagram counts
log_diagram_counts = {}
try:
    with open('extraction_full.log', 'r') as f:
        log_content = f.read()
        pattern = r'Processing: (.*?\.epub).*?Extracted (\d+) diagrams'
        for filename, diagrams in re.findall(pattern, log_content, re.DOTALL):
            log_diagram_counts[filename] = int(diagrams)
except FileNotFoundError:
    pass

# Categorize books
categories = defaultdict(list)

for filename in current_files:
    diagrams = log_diagram_counts.get(filename, 0)
    lower_name = filename.lower()

    # 1. BEGINNER BOOKS
    if 'beginner' in lower_name:
        categories['Beginner Books'].append((filename, diagrams, "Contains 'beginner' in title"))

    # 2. AUTOBIOGRAPHICAL BOOKS
    auto_keywords = ['my_life', 'my_games', 'autobiography', 'memoir', 'story_of',
                     'best_games', 'selected_games', 'lifes_work', 'career']
    for keyword in auto_keywords:
        if keyword in lower_name:
            categories['Autobiographical'].append((filename, diagrams, f"Keyword: {keyword}"))
            break

    # 3. HISTORICAL BOOKS
    hist_keywords = ['history_of', 'historical', 'world_championship', 'world_champions',
                     'great_masters', 'chess_legends', 'golden_age', 'classic_games',
                     'greatest_games', 'chess_in_the_', 'soviet_chess', 'chess_evolution']
    for keyword in hist_keywords:
        if keyword in lower_name:
            categories['Historical'].append((filename, diagrams, f"Keyword: {keyword}"))
            break

    # 4. PUZZLE/PROBLEM BOOKS (often not instructional)
    puzzle_keywords = ['puzzle', 'problems', 'exercises', 'test_your', 'quiz',
                       'chess_cafe_puzzle', '1001_', 'workbook']
    for keyword in puzzle_keywords:
        if keyword in lower_name:
            categories['Puzzle Books'].append((filename, diagrams, f"Keyword: {keyword}"))
            break

    # 5. GENERAL INTEREST / NARRATIVE
    narrative_keywords = ['art_of', 'philosophy', 'psychology', 'thinking',
                          'secrets_of', 'wisdom', 'genius', 'master_class',
                          'immortal_games', 'chess_life', 'chess_bitch']
    for keyword in narrative_keywords:
        if keyword in lower_name:
            categories['General Interest'].append((filename, diagrams, f"Keyword: {keyword}"))
            break

    # 6. BIOGRAPHY (about specific players)
    bio_keywords = ['kasparov_on', 'tal_life', 'fischer_', 'karpov_', 'botvinnik_',
                    'capablanca_', 'alekhine_', 'lasker_', 'steinitz_', 'morphy_']
    for keyword in bio_keywords:
        if keyword in lower_name:
            categories['Biography'].append((filename, diagrams, f"Keyword: {keyword}"))
            break

    # 7. VERY LOW DIAGRAM COUNT (< 50 diagrams suggests non-instructional)
    if diagrams > 0 and diagrams < 50:
        categories['Low Diagram Count (<50)'].append((filename, diagrams, f"{diagrams} diagrams"))

# Output results
total_flagged = 0
for category, books in sorted(categories.items()):
    if books:
        print(f"\n{'='*80}")
        print(f"{category.upper()} ({len(books)} books)")
        print(f"{'='*80}")

        for filename, diagrams, reason in sorted(books, key=lambda x: -x[1]):
            print(f"{diagrams:5d} diagrams | {reason:30s} | {filename}")

        total_flagged += len(books)

# Summary
print(f"\n{'='*80}")
print(f"SUMMARY")
print(f"{'='*80}")
print(f"Total books scanned: {len(current_files)}")
print(f"Total flagged books: {total_flagged}")
print(f"\nNote: Some books may appear in multiple categories")
print(f"\nThese books might be less useful for opening/tactical RAG queries but")
print(f"could still be valuable for general chess knowledge, history, and culture.")
