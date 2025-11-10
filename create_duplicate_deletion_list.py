#!/usr/bin/env python3
import re
from collections import defaultdict

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
        r'_enterprises.*',
    ]
    for pattern in patterns_to_remove:
        title = re.sub(pattern, '_', title, flags=re.IGNORECASE)
    return re.sub(r'_+', '_', title).strip('_').lower()

# Parse extraction log
with open('extraction_full.log', 'r') as f:
    log_content = f.read()

pattern = r'Processing: (.*?\.epub).*?Extracted (\d+) diagrams'
matches = re.findall(pattern, log_content, re.DOTALL)

# Group by normalized title
title_groups = defaultdict(list)
for filename, diagrams in matches:
    normalized = normalize_title(filename)
    title_groups[normalized].append((filename, int(diagrams)))

# Find duplicates
duplicates = {k: v for k, v in title_groups.items() if len(v) > 1}

# Create deletion list
deletion_list = []
for normalized_title, books in sorted(duplicates.items()):
    books_sorted = sorted(books, key=lambda x: -x[1])
    # Keep the first (highest diagram count), delete the rest
    for filename, diagrams in books_sorted[1:]:
        deletion_list.append((filename, diagrams))

# Write to file
with open('duplicate_books_to_delete_v2.txt', 'w') as f:
    f.write(f"# Duplicate books to delete (keeping highest diagram count per group)\n")
    f.write(f"# Total: {len(deletion_list)} books to delete\n")
    f.write(f"# Format: filename|diagram_count\n\n")
    for filename, diagrams in deletion_list:
        f.write(f"{filename}|{diagrams}\n")

print(f"Created duplicate_books_to_delete_v2.txt with {len(deletion_list)} books")
print(f"\nBreakdown:")
print(f"  - {len(duplicates)} duplicate groups")
print(f"  - {sum(len(v) for v in duplicates.values())} total books in duplicate groups")
print(f"  - {len(deletion_list)} books to DELETE (keeping {len(duplicates)} best editions)")
