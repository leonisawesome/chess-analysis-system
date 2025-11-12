#!/usr/bin/env python3
"""
Check Qdrant for duplicate book chunks after removing duplicate .mobi files.
"""

from qdrant_client import QdrantClient
from collections import Counter
from pathlib import Path
import json

EPUB_DIR = Path("/Volumes/T7 Shield/rag/books/epub")

def get_removed_mobi_filenames():
    """Get list of .mobi filenames that were removed as duplicates."""
    # These are the 113 .mobi files that had corresponding .epub versions
    removed_mobis = []

    # Read the list from remove_duplicate_mobis.py output
    # Since we removed all .mobi files with corresponding .epub files,
    # we need to identify which books these were

    # Get all current .epub files
    epub_files = list(EPUB_DIR.glob("*.epub"))

    # For each .epub, check if it likely had a .mobi counterpart
    # (we'll check Qdrant for books that exist twice)

    return [epub.stem for epub in epub_files]  # Get filenames without extension

def main():
    print("=" * 80)
    print("CHECKING QDRANT FOR DUPLICATE BOOKS")
    print("=" * 80)
    print()

    client = QdrantClient(host='localhost', port=6333)

    # First, get collection info
    collection_info = client.get_collection("chess_production")
    print(f"📊 Collection: chess_production")
    print(f"   Total chunks: {collection_info.points_count}")
    print()

    # Scroll through all points with ALL payload
    print("🔍 Scanning all chunks for book information...")
    print()

    book_chunks = {}  # book_id -> list of chunk IDs
    book_metadata = {}  # book_id -> {title, filename}

    offset = None
    scanned = 0

    while True:
        result = client.scroll(
            collection_name="chess_production",
            limit=100,
            offset=offset,
            with_payload=True,  # Get ALL payload fields
            with_vectors=False
        )

        points, next_offset = result

        if not points:
            break

        for point in points:
            scanned += 1

            if point.payload:
                # Extract book identifier from payload
                # Check various possible field names
                book_id = (
                    point.payload.get('book_id') or
                    point.payload.get('source_book') or
                    point.payload.get('book_name') or
                    'unknown'
                )

                book_title = (
                    point.payload.get('book_title') or
                    point.payload.get('title') or
                    'Unknown'
                )

                filename = (
                    point.payload.get('filename') or
                    point.payload.get('file') or
                    'Unknown'
                )

                # Track this chunk
                if book_id not in book_chunks:
                    book_chunks[book_id] = []
                    book_metadata[book_id] = {
                        'title': book_title,
                        'filename': filename
                    }

                book_chunks[book_id].append(point.id)

        if scanned % 10000 == 0:
            print(f"   Scanned {scanned:,} chunks...")

        offset = next_offset
        if offset is None:
            break

    print(f"\n✅ Scanned {scanned:,} total chunks")
    print(f"📚 Found {len(book_chunks)} unique books")
    print()

    # Check for duplicate books by title/filename
    print("=" * 80)
    print("CHECKING FOR DUPLICATE BOOKS")
    print("=" * 80)
    print()

    # Group by normalized title
    title_groups = {}
    for book_id, metadata in book_metadata.items():
        title = metadata['title'].lower().strip()

        if title not in title_groups:
            title_groups[title] = []

        title_groups[title].append({
            'book_id': book_id,
            'title': metadata['title'],
            'filename': metadata['filename'],
            'chunk_count': len(book_chunks[book_id])
        })

    # Find duplicates
    duplicates = []
    for title, books in title_groups.items():
        if len(books) > 1:
            duplicates.append((title, books))

    if duplicates:
        print(f"⚠️  Found {len(duplicates)} duplicate book groups:")
        print()

        total_duplicate_chunks = 0
        books_to_remove = []

        for title, books in duplicates:
            print(f"📖 Title: {books[0]['title']}")
            print(f"   Instances: {len(books)}")
            print()

            for i, book in enumerate(books, 1):
                print(f"   {i}. Book ID: {book['book_id']}")
                print(f"      Filename: {book['filename']}")
                print(f"      Chunks: {book['chunk_count']}")

            print()

            # Keep the version with most chunks, remove others
            books_sorted = sorted(books, key=lambda x: x['chunk_count'], reverse=True)

            for book in books_sorted[1:]:  # All except first (highest chunk count)
                books_to_remove.append(book)
                total_duplicate_chunks += book['chunk_count']

        print("=" * 80)
        print(f"📊 DUPLICATE SUMMARY")
        print("=" * 80)
        print(f"Duplicate book instances to remove: {len(books_to_remove)}")
        print(f"Total chunks to remove: {total_duplicate_chunks:,}")
        print()

        if books_to_remove:
            print("🗑️  Books to remove:")
            for book in books_to_remove:
                print(f"   - {book['book_id']} ({book['chunk_count']} chunks): {book['filename']}")
            print()

            # Save removal list
            removal_data = {
                'books_to_remove': books_to_remove,
                'total_chunks': total_duplicate_chunks
            }

            with open('qdrant_duplicates_to_remove.json', 'w') as f:
                json.dump(removal_data, f, indent=2)

            print("💾 Saved removal list to: qdrant_duplicates_to_remove.json")
            print()

            response = input("🗑️  Delete these duplicate books from Qdrant? [y/N]: ").strip().lower()

            if response in ['y', 'yes']:
                print()
                print("🗑️  REMOVING DUPLICATE BOOKS FROM QDRANT")
                print("=" * 80)

                removed_count = 0

                for book in books_to_remove:
                    book_id = book['book_id']
                    chunk_ids = book_chunks[book_id]

                    print(f"Deleting {len(chunk_ids)} chunks from: {book['filename']}")

                    try:
                        # Delete all chunks for this book
                        client.delete(
                            collection_name="chess_production",
                            points_selector=chunk_ids
                        )
                        removed_count += len(chunk_ids)
                        print(f"   ✅ Deleted {len(chunk_ids)} chunks")
                    except Exception as e:
                        print(f"   ❌ Failed: {e}")

                print()
                print(f"✅ Removed {removed_count:,} duplicate chunks from Qdrant")
            else:
                print("⏭️  Skipping duplicate removal")
    else:
        print("✅ No duplicate books found in Qdrant")

    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
