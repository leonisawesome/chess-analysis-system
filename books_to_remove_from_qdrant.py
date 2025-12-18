#!/usr/bin/env python3
"""
Identify books that should be removed from Qdrant because they're not RAG-worthy.
Focus on books that don't help with opening/tactical queries.
"""
import re
from pathlib import Path
from collections import defaultdict

# Scan current EPUB files
epub_dir = Path("/Volumes/T7 Shield/rag/books/epub")
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

# Books to REMOVE from Qdrant (not useful for opening/tactical RAG)
remove_categories = {
    'beginner': [],
    'autobiographical': [],
    'biography': [],
    'puzzle_books': [],
    'low_diagrams': [],
    'narrative': []
}

for filename in current_files:
    diagrams = log_diagram_counts.get(filename, 0)
    lower_name = filename.lower()

    # 1. BEGINNER BOOKS - Remove ALL (not useful for serious study)
    if 'beginner' in lower_name:
        remove_categories['beginner'].append(filename)
        continue

    # 2. AUTOBIOGRAPHICAL - Remove (game collections without deep analysis)
    auto_keywords = ['my_life', 'my_games', 'autobiography', 'memoir', 'story_of',
                     'best_games', 'selected_games', 'lifes_work', 'career']
    if any(kw in lower_name for kw in auto_keywords):
        remove_categories['autobiographical'].append(filename)
        continue

    # 3. BIOGRAPHY - Remove (narrative, not instructional)
    bio_keywords = ['kasparov_on', 'tal_life', 'fischer_', 'karpov_', 'botvinnik_',
                    'capablanca_', 'alekhine_', 'lasker_', 'steinitz_', 'morphy_']
    if any(kw in lower_name for kw in bio_keywords):
        remove_categories['biography'].append(filename)
        continue

    # 4. PUZZLE/EXERCISE BOOKS - Remove (no instructional text)
    puzzle_keywords = ['puzzle', 'problems', 'exercises', 'test_your', 'quiz',
                       'workbook', '1001_']
    if any(kw in lower_name for kw in puzzle_keywords):
        remove_categories['puzzle_books'].append(filename)
        continue

    # 5. VERY LOW DIAGRAM COUNT - Remove (likely narrative)
    if diagrams > 0 and diagrams < 50:
        remove_categories['low_diagrams'].append(filename)
        continue

    # 6. NARRATIVE/GENERAL INTEREST - Remove
    narrative_keywords = ['art_of', 'philosophy', 'psychology', 'thinking',
                          'secrets_of', 'wisdom', 'genius', 'immortal_games',
                          'chess_life', 'chess_bitch']
    if any(kw in lower_name for kw in narrative_keywords):
        remove_categories['narrative'].append(filename)

# Output
print("=" * 80)
print("BOOKS TO REMOVE FROM QDRANT")
print("=" * 80)
print("\nThese books are not useful for opening/tactical RAG queries.\n")

total_to_remove = 0
all_books_to_remove = []

for category, books in remove_categories.items():
    if books:
        category_name = category.replace('_', ' ').title()
        print(f"\n{category_name} ({len(books)} books)")
        print("-" * 80)
        for book in sorted(books):
            print(f"  {book}")
            all_books_to_remove.append(book)
        total_to_remove += len(books)

print(f"\n{'=' * 80}")
print(f"SUMMARY")
print(f"{'=' * 80}")
print(f"Total books to remove from Qdrant: {len(set(all_books_to_remove))}")
print(f"Books that will remain: {len(current_files) - len(set(all_books_to_remove))}")

# Save list for deletion script
output_file = "books_to_remove_from_qdrant.txt"
with open(output_file, 'w') as f:
    for book in sorted(set(all_books_to_remove)):
        f.write(f"{book}\n")

print(f"\nBook list saved to: {output_file}")
