#!/usr/bin/env python3
"""
Find duplicate books by scanning CURRENT files on disk, not extraction log.
This will only show books that ACTUALLY EXIST right now.
"""
import re
from collections import defaultdict
from pathlib import Path

def normalize_title(filename):
    """Extract core title, removing year, publisher, edition markers."""
    title = filename.replace('.epub', '')
    patterns_to_remove = [
        r'_\d{4}_', r'_21st_century.*', r'_\d+th_ed.*', r'_\d+nd_ed.*', 
        r'_\d+rd_ed.*', r'_\d+st_ed.*', r'_new_in_chess.*', r'_nic.*',
        r'_gambit.*', r'_everyman.*', r'_russell.*', r'_batsford.*',
        r'_quality_chess.*', r'_thinkers.*', r'_cardoza.*', r'_createspace.*',
        r'_ten_speed_press.*', r'_mundus.*', r'_dover.*', r'_no_dg.*',
        r'_uk_llp.*', r'_csi.*', r'_inc.*', r'_zenonchess.*',
        r'_enterprises.*', r'_sampler.*', r'_edition.*',
    ]
    for pattern in patterns_to_remove:
        title = re.sub(pattern, '_', title, flags=re.IGNORECASE)
    return re.sub(r'_+', '_', title).strip('_').lower()

# Scan CURRENT epub files on disk
epub_dir = Path("/Volumes/T7 Shield/books/epub")
current_files = sorted([f.name for f in epub_dir.glob("*.epub")])

print(f"Scanning {len(current_files)} CURRENT EPUB files on disk...")
print()

# Load extraction log to get diagram counts
log_diagram_counts = {}
with open('extraction_full.log', 'r') as f:
    log_content = f.read()
    pattern = r'Processing: (.*?\.epub).*?Extracted (\d+) diagrams'
    for filename, diagrams in re.findall(pattern, log_content, re.DOTALL):
        log_diagram_counts[filename] = int(diagrams)

# Group by normalized title
title_groups = defaultdict(list)
for filename in current_files:
    normalized = normalize_title(filename)
    diagrams = log_diagram_counts.get(filename, 0)
    title_groups[normalized].append((filename, diagrams))

# Find duplicates
duplicates = {k: v for k, v in title_groups.items() if len(v) > 1}

if len(duplicates) == 0:
    print("✓ NO DUPLICATES FOUND!")
    print("All books on disk are unique editions.")
else:
    print(f"Found {len(duplicates)} groups with multiple editions")
    print(f"Total duplicate books: {sum(len(v) for v in duplicates.values())}")
    print()
    
    # Display each group
    for normalized_title, books in sorted(duplicates.items()):
        books_sorted = sorted(books, key=lambda x: -x[1])
        print(f"\nGroup: {normalized_title}")
        print(f"  Editions: {len(books)}")
        for i, (filename, diagrams) in enumerate(books_sorted):
            marker = "KEEP" if i == 0 else "DELETE"
            print(f"    [{marker:6s}] {diagrams:5d} diagrams - {filename}")

print()
print("="*80)
print(f"Total EPUB files on disk: {len(current_files)}")
print(f"Duplicate groups: {len(duplicates)}")
if duplicates:
    print(f"Books to delete: {sum(len(v)-1 for v in duplicates.values())}")
