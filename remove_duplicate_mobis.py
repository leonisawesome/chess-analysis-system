#!/usr/bin/env python3
"""
Remove duplicate .mobi files that have corresponding .epub versions.
Also removes newly converted duplicate .epub files from the partial conversion.
"""

from pathlib import Path
import json

EPUB_DIR = Path("/Volumes/T7 Shield/rag/books/epub")
METADATA_FILE = Path("diagram_metadata_full.json")

def load_extracted_books():
    """Load list of books we already extracted diagrams from."""
    if not METADATA_FILE.exists():
        return set()

    with open(METADATA_FILE, 'r') as f:
        metadata = json.load(f)

    # Get unique book IDs that we've already extracted
    extracted_books = set()
    for book_id, data in metadata.items():
        if book_id.startswith('book_'):
            extracted_books.add(book_id)

    return extracted_books

def main():
    print("=" * 80)
    print("REMOVING DUPLICATE .MOBI FILES")
    print("=" * 80)
    print()

    # Load books we already extracted diagrams from
    extracted_books = load_extracted_books()
    print(f"📊 Books with extracted diagrams: {len(extracted_books)}")
    print()

    # Find all .mobi files
    mobi_files = sorted(EPUB_DIR.glob("*.mobi"))
    print(f"📚 Found {len(mobi_files)} .mobi files")
    print()

    # Check for duplicates
    duplicates = []
    unique_mobis = []

    for mobi_file in mobi_files:
        epub_file = mobi_file.with_suffix('.epub')

        if epub_file.exists():
            duplicates.append(mobi_file)
        else:
            unique_mobis.append(mobi_file)

    print(f"🔄 Duplicate .mobi files (have .epub): {len(duplicates)}")
    print(f"✅ Unique .mobi files (no .epub): {len(unique_mobis)}")
    print()

    if duplicates:
        print("🗑️  REMOVING DUPLICATE .MOBI FILES:")
        print("-" * 80)

        for mobi_file in duplicates:
            try:
                mobi_file.unlink()
                print(f"✅ Deleted: {mobi_file.name}")
            except Exception as e:
                print(f"❌ Failed to delete {mobi_file.name}: {e}")

        print()
        print(f"📊 Removed {len(duplicates)} duplicate .mobi files")
        print()

    # Now check for newly converted .epub files that are duplicates
    print("=" * 80)
    print("CHECKING FOR NEWLY CONVERTED DUPLICATE .EPUB FILES")
    print("=" * 80)
    print()

    # Files that were just converted (created in last hour)
    import time
    one_hour_ago = time.time() - 3600

    recent_epubs = []
    for epub_file in EPUB_DIR.glob("*.epub"):
        if epub_file.stat().st_mtime > one_hour_ago:
            recent_epubs.append(epub_file)

    print(f"📊 Recently created .epub files: {len(recent_epubs)}")
    print()

    if recent_epubs:
        print("🔍 Checking if these are duplicates of books already extracted...")
        print()

        # Check against books we already extracted
        duplicate_epubs = []

        for epub_file in recent_epubs:
            # Generate book_id from filename (same logic as extraction script)
            import hashlib
            book_id = f"book_{hashlib.md5(epub_file.name.encode()).hexdigest()[:12]}"

            if book_id in extracted_books:
                duplicate_epubs.append(epub_file)

        if duplicate_epubs:
            print(f"⚠️  Found {len(duplicate_epubs)} newly converted .epub files that are duplicates!")
            print("These books were already extracted in the full corpus run.")
            print()

            response = input("Delete these duplicate .epub files? [y/N]: ").strip().lower()

            if response in ['y', 'yes']:
                for epub_file in duplicate_epubs:
                    try:
                        epub_file.unlink()
                        print(f"✅ Deleted: {epub_file.name}")
                    except Exception as e:
                        print(f"❌ Failed to delete {epub_file.name}: {e}")
            else:
                print("⏭️  Skipping duplicate .epub deletion")
        else:
            print("✅ No duplicate .epub files found")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Duplicate .mobi files removed: {len(duplicates)}")
    print(f"Unique .mobi files remaining: {len(unique_mobis)}")
    print()

    if unique_mobis:
        print("📋 Unique .mobi files to convert:")
        for mobi in unique_mobis[:10]:
            print(f"  - {mobi.name}")
        if len(unique_mobis) > 10:
            print(f"  ... and {len(unique_mobis) - 10} more")

    print("=" * 80)

if __name__ == "__main__":
    main()
