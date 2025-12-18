#!/usr/bin/env python3
"""
Extract diagrams from EPUB files converted from .mobi format.
"""

import sys
from pathlib import Path
import json
from extract_epub_diagrams import extract_diagrams_from_epub

EPUB_DIR = Path("/Volumes/T7 Shield/rag/books/epub")
OUTPUT_DIR = Path("/Volumes/T7 Shield/rag/books/images")
CONVERTED_LIST = Path("mobi_converted_epubs.txt")

def main():
    print("=" * 80)
    print("EXTRACTING DIAGRAMS FROM CONVERTED .MOBI EPUB FILES")
    print("=" * 80)
    print()

    # Read list of converted EPUBs
    if not CONVERTED_LIST.exists():
        print(f"❌ File not found: {CONVERTED_LIST}")
        print("   Run: grep '✅ Success:' mobi_conversion.log | awk -F': ' '{print $2}' > mobi_converted_epubs.txt")
        sys.exit(1)

    with open(CONVERTED_LIST, 'r') as f:
        epub_filenames = [line.strip() for line in f if line.strip()]

    print(f"📚 Found {len(epub_filenames)} converted EPUB files")
    print()

    results = []
    success_count = 0
    fail_count = 0

    for i, filename in enumerate(epub_filenames, 1):
        epub_path = EPUB_DIR / filename

        if not epub_path.exists():
            print(f"⚠️  [{i}/{len(epub_filenames)}] File not found: {filename}")
            fail_count += 1
            continue

        print(f"📖 [{i}/{len(epub_filenames)}] Processing: {filename}")

        try:
            result = extract_diagrams_from_epub(str(epub_path), str(OUTPUT_DIR))

            if result['success']:
                print(f"   ✅ Extracted {result['diagram_count']} diagrams")
                print(f"      Book ID: {result['book_id']}")
                print(f"      Images dir: {Path(result['output_path']).name}/")
                success_count += 1
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
                fail_count += 1

            results.append(result)

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            fail_count += 1
            results.append({
                'success': False,
                'epub_path': str(epub_path),
                'error': str(e)
            })

        print()

    # Summary
    print("=" * 80)
    print("EXTRACTION SUMMARY")
    print("=" * 80)
    print(f"Total files: {len(epub_filenames)}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print()

    # Save results
    results_file = Path("mobi_diagram_extraction_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"💾 Results saved to: {results_file}")
    print()

    # Show diagram count distribution
    successful_results = [r for r in results if r.get('success')]
    if successful_results:
        diagram_counts = [(r['epub_path'].split('/')[-1], r['diagram_count']) for r in successful_results]
        diagram_counts.sort(key=lambda x: x[1])

        print("=" * 80)
        print("DIAGRAM COUNT DISTRIBUTION (LOWEST TO HIGHEST)")
        print("=" * 80)
        print()

        for filename, count in diagram_counts[:20]:  # Show bottom 20
            print(f"   {count:4d} diagrams - {filename}")

        if len(diagram_counts) > 20:
            print(f"   ... ({len(diagram_counts) - 20} more books)")

    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
