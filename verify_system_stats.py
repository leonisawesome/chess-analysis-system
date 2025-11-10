#!/usr/bin/env python3
"""
System Stats Verification Script

RUN THIS BEFORE UPDATING ANY DOCUMENTATION!

This script verifies the actual state of the system by querying:
- Actual EPUB files on disk
- Actual Qdrant collections
- Actual diagram directories

DO NOT trust documentation - always run this script to get truth.
"""

from pathlib import Path
from qdrant_client import QdrantClient


def verify_system_stats():
    """Verify actual system statistics."""

    print("=" * 80)
    print("SYSTEM STATS VERIFICATION")
    print("=" * 80)
    print("\n⚠️  WARNING: ALWAYS USE THESE STATS, NOT DOCUMENTATION!\n")

    # 1. Count EPUB files
    epub_dir = Path("/Volumes/T7 Shield/books/epub")
    if not epub_dir.exists():
        print(f"❌ ERROR: EPUB directory not found: {epub_dir}")
        return

    epub_files = [f for f in epub_dir.glob("*.epub") if not f.name.startswith('._')]
    print(f"📚 EPUB Books: {len(epub_files)}")

    # 2. Count Qdrant collections
    try:
        qdrant = QdrantClient(url="http://localhost:6333")
        collections = qdrant.get_collections()

        print(f"\n🗄️  Qdrant Collections:")
        total_chunks = 0
        for coll in collections.collections:
            info = qdrant.get_collection(coll.name)
            print(f"   {coll.name}: {info.points_count:,} points")
            total_chunks += info.points_count

        # Get specific collections
        epub_collection = qdrant.get_collection("chess_production")
        pgn_collection = qdrant.get_collection("chess_pgn_repertoire")

        # Production collections only
        production_total = epub_collection.points_count + pgn_collection.points_count

        print(f"\n   EPUB Chunks (production): {epub_collection.points_count:,}")
        print(f"   PGN Chunks (production): {pgn_collection.points_count:,}")
        print(f"   Production Total: {production_total:,}")
        print(f"   All Collections Total: {total_chunks:,}")

    except Exception as e:
        print(f"❌ ERROR connecting to Qdrant: {e}")
        print("   Make sure Docker Qdrant is running: docker-compose up -d")
        return

    # 3. Count diagrams
    diagram_dir = Path("/Volumes/T7 Shield/books/images")
    if not diagram_dir.exists():
        print(f"❌ ERROR: Diagram directory not found: {diagram_dir}")
        return

    book_dirs = list(diagram_dir.glob("book_*"))
    diagram_count = 0
    for bd in book_dirs:
        # IMPORTANT: Filter out ._* files (macOS metadata - DO NOT DELETE THEM!)
        diagrams = [f for f in bd.glob("*.*") if not f.name.startswith('._')]
        diagram_count += len(diagrams)

    print(f"\n🖼️  Diagrams:")
    print(f"   Book directories: {len(book_dirs)}")
    print(f"   Total diagrams: {diagram_count:,}")

    # 4. Summary
    production_total = epub_collection.points_count + pgn_collection.points_count

    print("\n" + "=" * 80)
    print("📋 SUMMARY - COPY THESE TO DOCUMENTATION")
    print("=" * 80)
    print(f"Books: {len(epub_files)}")
    print(f"Production Chunks: {production_total:,} ({epub_collection.points_count:,} EPUB + {pgn_collection.points_count:,} PGN)")
    print(f"Diagrams: {diagram_count:,}")
    print("\n⚠️  CRITICAL NOTES:")
    print("   - These stats are from ACTUAL queries, not documentation")
    print("   - macOS ._* files are FILTERED OUT (DO NOT DELETE THEM!)")
    print("   - Update README/SESSION_NOTES with these numbers")
    print("=" * 80)


if __name__ == '__main__':
    verify_system_stats()
