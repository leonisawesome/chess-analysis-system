#!/usr/bin/env python3
"""
Clean report of non-RAG-worthy books: category and title only.
"""
import re
from pathlib import Path
from collections import defaultdict

# Scan current EPUB files
epub_dir = Path("/Volumes/T7 Shield/books/epub")
current_files = sorted([f.name for f in epub_dir.glob("*.epub")])

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

    # Track if already categorized to avoid duplicates
    already_categorized = False

    # 1. BEGINNER BOOKS
    if 'beginner' in lower_name:
        categories['Beginner Books'].append(filename)
        already_categorized = True

    # 2. AUTOBIOGRAPHICAL BOOKS
    if not already_categorized:
        auto_keywords = ['my_life', 'my_games', 'autobiography', 'memoir', 'story_of',
                         'best_games', 'selected_games', 'lifes_work', 'career']
        for keyword in auto_keywords:
            if keyword in lower_name:
                categories['Autobiographical'].append(filename)
                already_categorized = True
                break

    # 3. HISTORICAL BOOKS
    if not already_categorized:
        hist_keywords = ['history_of', 'historical', 'world_championship', 'world_champions',
                         'great_masters', 'chess_legends', 'golden_age', 'classic_games',
                         'greatest_games', 'chess_in_the_', 'soviet_chess', 'chess_evolution']
        for keyword in hist_keywords:
            if keyword in lower_name:
                categories['Historical'].append(filename)
                already_categorized = True
                break

    # 4. PUZZLE/PROBLEM BOOKS
    if not already_categorized:
        puzzle_keywords = ['puzzle', 'problems', 'exercises', 'test_your', 'quiz',
                           'chess_cafe_puzzle', '1001_', 'workbook']
        for keyword in puzzle_keywords:
            if keyword in lower_name:
                categories['Puzzle Books'].append(filename)
                already_categorized = True
                break

    # 5. GENERAL INTEREST / NARRATIVE
    if not already_categorized:
        narrative_keywords = ['art_of', 'philosophy', 'psychology', 'thinking',
                              'secrets_of', 'wisdom', 'genius', 'master_class',
                              'immortal_games', 'chess_life', 'chess_bitch']
        for keyword in narrative_keywords:
            if keyword in lower_name:
                categories['General Interest'].append(filename)
                already_categorized = True
                break

    # 6. BIOGRAPHY
    if not already_categorized:
        bio_keywords = ['kasparov_on', 'tal_life', 'fischer_', 'karpov_', 'botvinnik_',
                        'capablanca_', 'alekhine_', 'lasker_', 'steinitz_', 'morphy_']
        for keyword in bio_keywords:
            if keyword in lower_name:
                categories['Biography'].append(filename)
                already_categorized = True
                break

    # 7. VERY LOW DIAGRAM COUNT (< 50 diagrams)
    if not already_categorized and diagrams > 0 and diagrams < 50:
        categories['Low Diagram Count (<50)'].append(filename)

# Output clean report
print("=" * 80)
print("NON-RAG-WORTHY BOOKS - CLEAN REPORT")
print("=" * 80)
print()

total_flagged = 0
for category in ['Beginner Books', 'Autobiographical', 'Biography', 'Historical',
                 'Puzzle Books', 'General Interest', 'Low Diagram Count (<50)']:
    if category in categories and categories[category]:
        books = categories[category]
        print(f"\n{category.upper()} ({len(books)} books)")
        print("-" * 80)
        for filename in sorted(books):
            print(f"  • {filename}")
        total_flagged += len(books)

print(f"\n{'=' * 80}")
print(f"TOTAL FLAGGED: {total_flagged} books out of {len(current_files)}")
print(f"{'=' * 80}")
