#!/usr/bin/env python3
import re
from collections import defaultdict

def normalize_title(filename):
    """Extract core title, removing year, publisher, edition markers."""
    title = filename.replace('.epub', '')
    
    # Remove common patterns
    patterns_to_remove = [
        r'_\d{4}_',  # Year patterns like _2019_
        r'_21st_century.*',
        r'_\d+th_ed.*',
        r'_\d+nd_ed.*',
        r'_\d+rd_ed.*',
        r'_\d+st_ed.*',
        r'_new_in_chess.*',
        r'_nic.*',
        r'_gambit.*',
        r'_everyman.*',
        r'_russell.*',
        r'_batsford.*',
        r'_quality_chess.*',
        r'_thinkers.*',
        r'_cardoza.*',
        r'_createspace.*',
        r'_ten_speed_press.*',
        r'_mundus.*',
        r'_dover.*',
        r'_no_dg.*',
        r'_uk_llp.*',
        r'_csi.*',
        r'_inc.*',
    ]
    
    for pattern in patterns_to_remove:
        title = re.sub(pattern, '_', title, flags=re.IGNORECASE)
    
    # Clean up multiple underscores
    title = re.sub(r'_+', '_', title).strip('_').lower()
    
    return title

# Parse extraction log
with open('extraction_full.log', 'r') as f:
    log_content = f.read()

# Extract all books with diagram counts
pattern = r'Processing: (.*?\.epub).*?Extracted (\d+) diagrams'
matches = re.findall(pattern, log_content, re.DOTALL)

# Group by normalized title
title_groups = defaultdict(list)
for filename, diagrams in matches:
    normalized = normalize_title(filename)
    title_groups[normalized].append((filename, int(diagrams)))

# Find duplicates (groups with more than 1 book)
duplicates = {k: v for k, v in title_groups.items() if len(v) > 1}

print(f"Found {len(duplicates)} groups with multiple editions")
print(f"Total duplicate books: {sum(len(v) for v in duplicates.values())}")
print()

# Sort and display
for normalized_title, books in sorted(duplicates.items()):
    books_sorted = sorted(books, key=lambda x: -x[1])  # Sort by diagram count descending
    print(f"\nGroup: {normalized_title}")
    print(f"  Editions: {len(books)}")
    for filename, diagrams in books_sorted:
        print(f"    {diagrams:5d} diagrams - {filename}")
