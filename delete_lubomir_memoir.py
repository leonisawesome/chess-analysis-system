#!/usr/bin/env python3
"""
Delete Lubomir memoir from all locations (EPUB, images, Qdrant).
"""
import hashlib
import subprocess
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Book to delete
filename = "lubomir_2022_life_at_play_a_chess_memoir_new_in_chess.epub"

epub_dir = Path("/Volumes/T7 Shield/books/epub")
images_dir = Path("/Volumes/T7 Shield/books/images")

print("=" * 80)
print("DELETING MEMOIR BOOK")
print("=" * 80)
print(f"Deleting: {filename}\n")

# Generate book_id
book_id = f"book_{hashlib.md5(filename.encode()).hexdigest()[:12]}"
print(f"Book ID: {book_id}\n")

# Connect to Qdrant
client = QdrantClient(host="localhost", port=6333, timeout=300)

# 1. Delete EPUB file
epub_path = epub_dir / filename
if epub_path.exists():
    epub_path.unlink()
    print(f"✓ Deleted EPUB")
else:
    print(f"ℹ EPUB not found")

# 2. Delete image directory
image_path = images_dir / book_id
if image_path.exists():
    subprocess.run(['rm', '-rf', str(image_path)], check=True)
    print(f"✓ Deleted images ({book_id})")
else:
    print(f"ℹ No image directory")

# 3. Delete from Qdrant
try:
    count_result = client.count(
        collection_name="chess_production",
        count_filter=Filter(
            must=[FieldCondition(key="book_name", match=MatchValue(value=filename))]
        )
    )

    if count_result.count > 0:
        print(f"Deleting {count_result.count} chunks from Qdrant...")
        client.delete(
            collection_name="chess_production",
            points_selector=Filter(
                must=[FieldCondition(key="book_name", match=MatchValue(value=filename))]
            )
        )

        # Verify
        verify = client.count(
            collection_name="chess_production",
            count_filter=Filter(
                must=[FieldCondition(key="book_name", match=MatchValue(value=filename))]
            )
        )

        if verify.count == 0:
            print(f"✓ Deleted {count_result.count} chunks (verified)")
        else:
            print(f"⚠ WARNING: {verify.count} chunks still remain!")
    else:
        print(f"ℹ No Qdrant chunks")
except Exception as e:
    print(f"✗ Qdrant error: {e}")

# Get final counts
print(f"\n{'=' * 80}")
try:
    final_count = client.count(collection_name="chess_production")
    print(f"Final Qdrant collection size: {final_count.count:,} chunks")
except Exception as e:
    print(f"Could not get final count: {e}")

# Count remaining EPUBs
remaining_epubs = len(list(epub_dir.glob("*.epub")))
print(f"Remaining EPUB files: {remaining_epubs}")
