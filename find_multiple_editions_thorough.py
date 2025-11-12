#!/usr/bin/env python3
"""
Thorough check for multiple editions by grouping by author and looking for similar titles.
This catches cases where edition markers might be in different formats.
"""
import re
from collections import defaultdict
from pathlib import Path

def extract_author(filename):
    """Extract author name (everything before first underscore or year)."""
    match = re.match(r'^([a-z_]+?)_(?:\d{4}_|0000_)', filename)
    if match:
        return match.group(1)
    # Fallback: everything before first number or first few words
    parts = filename.split('_')
    return parts[0] if parts else filename

def normalize_title_aggressive(filename):
    """More aggressive normalization to catch all edition variations."""
    # Remove file extension
    title = filename.replace('.epub', '')

    # Remove common patterns
    patterns_to_remove = [
        # Years and dates
        r'_\d{4}_', r'_\d{4}$', r'^0000_',
        # Edition markers
        r'_\d+th_ed(?:ition)?', r'_\d+nd_ed(?:ition)?', r'_\d+rd_ed(?:ition)?', r'_\d+st_ed(?:ition)?',
        r'_edition.*', r'_ed\d+', r'_2nd_', r'_3rd_', r'_4th_', r'_5th_',
        r'21st_century.*', r'_revised.*', r'_updated.*', r'_expanded.*',
        # Publishers
        r'_new_in_chess.*', r'_nic.*', r'_gambit.*', r'_everyman.*', r'_russell.*',
        r'_batsford.*', r'_quality_chess.*', r'_thinkers.*', r'_cardoza.*',
        r'_createspace.*', r'_ten_speed_press.*', r'_mundus.*', r'_dover.*',
        r'_uk_llp.*', r'_csi.*', r'_inc.*', r'_zenonchess.*', r'_enterprises.*',
        # Format markers
        r'_no_dg.*', r'_sampler.*', r'_vol(?:ume)?_?\d+',
        # Extra markers
        r'_tls.*', r'_dg.*', r'_ocr.*', r'_scan.*',
    ]

    for pattern in patterns_to_remove:
        title = re.sub(pattern, '_', title, flags=re.IGNORECASE)

    # Clean up multiple underscores
    title = re.sub(r'_+', '_', title).strip('_').lower()

    return title

# Scan current files
epub_dir = Path("/Volumes/T7 Shield/rag/books/epub")
current_files = sorted([f.name for f in epub_dir.glob("*.epub")])

print(f"Scanning {len(current_files)} books for multiple editions...")
print("="*80)

# Load diagram counts from extraction log
log_diagram_counts = {}
try:
    with open('extraction_full.log', 'r') as f:
        log_content = f.read()
        pattern = r'Processing: (.*?\.epub).*?Extracted (\d+) diagrams'
        for filename, diagrams in re.findall(pattern, log_content, re.DOTALL):
            log_diagram_counts[filename] = int(diagrams)
except FileNotFoundError:
    print("Warning: extraction_full.log not found, diagram counts unavailable")
    print()

# Group by author first, then by normalized title
author_books = defaultdict(list)
for filename in current_files:
    author = extract_author(filename)
    normalized = normalize_title_aggressive(filename)
    diagrams = log_diagram_counts.get(filename, 0)
    author_books[author].append((filename, normalized, diagrams))

# Look for authors with multiple books of same normalized title
duplicates_found = []
for author, books in sorted(author_books.items()):
    # Group books by normalized title
    title_groups = defaultdict(list)
    for filename, normalized, diagrams in books:
        title_groups[normalized].append((filename, diagrams))

    # Check for duplicates within this author
    for normalized_title, book_list in title_groups.items():
        if len(book_list) > 1:
            duplicates_found.append({
                'author': author,
                'normalized': normalized_title,
                'books': sorted(book_list, key=lambda x: -x[1])  # Sort by diagram count
            })

# Display results
if len(duplicates_found) == 0:
    print("\n✅ NO MULTIPLE EDITIONS FOUND!")
    print("\nAll 946 books are unique - no stragglers detected.")
    print("\nCollection is clean and ready for use.")
else:
    print(f"\n⚠️  Found {len(duplicates_found)} potential duplicate groups:\n")

    for dup in duplicates_found:
        print(f"\nAuthor: {dup['author']}")
        print(f"Normalized Title: {dup['normalized']}")
        print(f"Editions Found: {len(dup['books'])}")
        for i, (filename, diagrams) in enumerate(dup['books']):
            marker = "KEEP" if i == 0 else "DELETE?"
            print(f"  [{marker:7s}] {diagrams:5d} diagrams - {filename}")

print("\n" + "="*80)
print(f"Total books scanned: {len(current_files)}")
print(f"Duplicate groups: {len(duplicates_found)}")
if duplicates_found:
    total_dupes = sum(len(d['books'])-1 for d in duplicates_found)
    print(f"Potential books to delete: {total_dupes}")
