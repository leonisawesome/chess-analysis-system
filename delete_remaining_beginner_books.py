#!/usr/bin/env python3
"""
Delete remaining beginner books from disk, images, and Qdrant.
"""
import hashlib
import subprocess
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Books to delete
books_to_delete = [
    "unknown_author_2019_franco_masetti_roberto_messa_chess_exercises_for_beginners_new_in_chess.epub",
    "unknown_author_2019_franco_masetti_roberto_messa_richard_jones_chess_exercises_for_beginners_the_tactics_workbook_that_explains_the_basic_concepts_too_new_in_chess.epub",
    "vincent_2016_my_first_chess_opening_repertoire_for_white_a_turnkey_package_for_ambitious_beginners_new_in.epub",
    "yaroslav_2014_chess_training_for_postbeginners_new_in_chess.epub",
    "unknown_author_2018_international_master_arthur_van_de_oudeweetering_chess_pattern_recognition_for_beginners_the_fundamental_guide_to_spotting_key_moves_in_the_middlegame_new_in_chess.epub",
]

epub_dir = Path("/Volumes/T7 Shield/rag/books/epub")
images_dir = Path("/Volumes/T7 Shield/rag/books/images")

print("=" * 80)
print("DELETING REMAINING BEGINNER BOOKS")
print("=" * 80)
print(f"Total books to delete: {len(books_to_delete)}\n")

# Connect to Qdrant with longer timeout
client = QdrantClient(host="localhost", port=6333, timeout=300)

total_epub_deleted = 0
total_images_deleted = 0
total_chunks_deleted = 0

for i, filename in enumerate(books_to_delete, 1):
    print(f"\n[{i}/{len(books_to_delete)}] {filename}")

    # Generate book_id
    book_id = f"book_{hashlib.md5(filename.encode()).hexdigest()[:12]}"

    # 1. Delete EPUB file
    epub_path = epub_dir / filename
    if epub_path.exists():
        epub_path.unlink()
        print(f"  ✓ Deleted EPUB")
        total_epub_deleted += 1
    else:
        print(f"  ℹ EPUB not found (may have been deleted already)")

    # 2. Delete image directory
    image_path = images_dir / book_id
    if image_path.exists():
        subprocess.run(['rm', '-rf', str(image_path)], check=True)
        print(f"  ✓ Deleted images ({book_id})")
        total_images_deleted += 1
    else:
        print(f"  ℹ No image directory")

    # 3. Delete from Qdrant
    try:
        count_result = client.count(
            collection_name="chess_production",
            count_filter=Filter(
                must=[FieldCondition(key="book_name", match=MatchValue(value=filename))]
            )
        )

        if count_result.count > 0:
            print(f"  Deleting {count_result.count} chunks from Qdrant...")
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
                print(f"  ✓ Deleted {count_result.count} chunks (verified)")
                total_chunks_deleted += count_result.count
            else:
                print(f"  ⚠ WARNING: {verify.count} chunks still remain!")
        else:
            print(f"  ℹ No Qdrant chunks (already removed or never ingested)")
    except Exception as e:
        print(f"  ✗ Qdrant error: {e}")

print(f"\n{'=' * 80}")
print(f"DELETION SUMMARY")
print(f"{'=' * 80}")
print(f"EPUB files deleted: {total_epub_deleted}")
print(f"Image directories deleted: {total_images_deleted}")
print(f"Qdrant chunks deleted: {total_chunks_deleted}")

# Get final counts
try:
    final_count = client.count(collection_name="chess_production")
    print(f"\nFinal Qdrant collection size: {final_count.count:,} chunks")
except Exception as e:
    print(f"Could not get final count: {e}")

# Count remaining EPUBs
remaining_epubs = len(list(epub_dir.glob("*.epub")))
print(f"Remaining EPUB files: {remaining_epubs}")
