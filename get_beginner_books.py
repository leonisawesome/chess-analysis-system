#!/usr/bin/env python3
import re

# Parse extraction_full.log to find beginner books with diagram counts
with open('extraction_full.log', 'r') as f:
    log_content = f.read()

# Find all beginner books with their diagram counts
pattern = r'Processing: (.*?beginner.*?\.epub).*?Extracted (\d+) diagrams'
matches = re.findall(pattern, log_content, re.IGNORECASE | re.DOTALL)

# Also check for books that had 0 diagrams (different pattern)
zero_pattern = r'Processing: (.*?beginner.*?\.epub).*?No diagrams found'
zero_matches = re.findall(zero_pattern, log_content, re.IGNORECASE | re.DOTALL)

results = []
for filename, count in matches:
    results.append((filename.strip(), int(count)))

for filename in zero_matches:
    results.append((filename.strip(), 0))

# Sort by diagram count (descending), then by filename
results.sort(key=lambda x: (-x[1], x[0].lower()))

print(f"{'BOOK FILENAME':<120} {'DIAGRAMS':>10}")
print("=" * 132)

total_diagrams = 0
for filename, count in results:
    print(f"{filename:<120} {count:>10,}")
    total_diagrams += count

print("=" * 132)
print(f"{'TOTAL:':<120} {len(results):>10} books")
print(f"{'TOTAL DIAGRAMS:':<120} {total_diagrams:>10,}")
