#!/usr/bin/env python3
"""
Find .mobi files in Qdrant that should be removed (duplicates of .epub files).
"""

from qdrant_client import QdrantClient
from pathlib import Path

def main():
    print("=" * 80)
    print("FINDING .MOBI FILES IN QDRANT")
    print("=" * 80)
    print()

    client = QdrantClient(host='localhost', port=6333)

    # Get collection info
    collection_info = client.get_collection("chess_production")
    print(f"📊 Collection: chess_production")
    print(f"   Total chunks: {collection_info.points_count}")
    print()

    # Scroll through and find .mobi files
    print("🔍 Scanning for .mobi file chunks...")
    print()

    mobi_books = {}  # book_id -> list of chunk IDs
    offset = None
    scanned = 0

    while True:
        result = client.scroll(
            collection_name="chess_production",
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        points, next_offset = result

        if not points:
            break

        for point in points:
            scanned += 1

            if point.payload:
                # Get book_id which is the filename
                book_id = (
                    point.payload.get('book_id') or
                    point.payload.get('source_book') or
                    point.payload.get('book_name') or
                    'unknown'
                )

                # Check if this is a .mobi file
                if book_id.endswith('.mobi'):
                    if book_id not in mobi_books:
                        mobi_books[book_id] = []
                    mobi_books[book_id].append(point.id)

        if scanned % 10000 == 0:
            print(f"   Scanned {scanned:,} chunks...")

        offset = next_offset
        if offset is None:
            break

    print(f"\n✅ Scanned {scanned:,} total chunks")
    print()

    if mobi_books:
        print("=" * 80)
        print(f"⚠️  FOUND {len(mobi_books)} .MOBI FILES IN QDRANT")
        print("=" * 80)
        print()

        total_chunks = 0
        for book_id, chunk_ids in sorted(mobi_books.items()):
            total_chunks += len(chunk_ids)
            print(f"📖 {book_id}")
            print(f"   Chunks: {len(chunk_ids)}")
            print()

        print("=" * 80)
        print(f"📊 SUMMARY")
        print("=" * 80)
        print(f"Total .mobi files: {len(mobi_books)}")
        print(f"Total chunks to remove: {total_chunks:,}")
        print()

        response = input("🗑️  Delete these .mobi file chunks from Qdrant? [y/N]: ").strip().lower()

        if response in ['y', 'yes']:
            print()
            print("🗑️  REMOVING .MOBI FILE CHUNKS FROM QDRANT")
            print("=" * 80)

            removed_count = 0

            for book_id, chunk_ids in mobi_books.items():
                print(f"Deleting {len(chunk_ids)} chunks from: {book_id}")

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
            print(f"✅ Removed {removed_count:,} .mobi file chunks from Qdrant")
            print()

            # Update collection info
            collection_info = client.get_collection("chess_production")
            print(f"📊 Updated collection stats:")
            print(f"   Total chunks remaining: {collection_info.points_count:,}")
        else:
            print("⏭️  Skipping .mobi chunk removal")
    else:
        print("✅ No .mobi files found in Qdrant")

    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
