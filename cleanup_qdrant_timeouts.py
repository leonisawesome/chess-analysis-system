#!/usr/bin/env python3
"""
Properly clean up books that previously timed out from Qdrant.
Using longer timeout and verification.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import time

# Increase timeout to 5 minutes
client = QdrantClient(host="localhost", port=6333, timeout=300)

# Books that timed out during previous deletion attempts
books_to_delete = [
    "pavlovic_2017_reloaded_weapons_in_the_benoni_thinkers.epub",
    "unknown_author_2018_arthur_van_de_oudeweeterig_chess_pattern_recognition_for_beginners_new_in_chess.epub",
]

print("=" * 80)
print("QDRANT CLEANUP - Books that Previously Timed Out")
print("=" * 80)

total_deleted = 0

for book_name in books_to_delete:
    print(f"\n[{books_to_delete.index(book_name) + 1}/{len(books_to_delete)}] Processing: {book_name}")

    try:
        # Count with timeout
        print("  Counting chunks...")
        count_result = client.count(
            collection_name="chess_production",
            count_filter=Filter(
                must=[FieldCondition(key="book_name", match=MatchValue(value=book_name))]
            )
        )

        print(f"  Found {count_result.count:,} chunks")

        if count_result.count > 0:
            # Delete with longer timeout
            print(f"  Deleting {count_result.count:,} chunks (this may take a minute)...")
            start_time = time.time()

            client.delete(
                collection_name="chess_production",
                points_selector=Filter(
                    must=[FieldCondition(key="book_name", match=MatchValue(value=book_name))]
                )
            )

            elapsed = time.time() - start_time
            print(f"  ✓ Deleted {count_result.count:,} chunks in {elapsed:.1f}s")
            total_deleted += count_result.count

            # Verify deletion
            print("  Verifying deletion...")
            verify_count = client.count(
                collection_name="chess_production",
                count_filter=Filter(
                    must=[FieldCondition(key="book_name", match=MatchValue(value=book_name))]
                )
            )

            if verify_count.count == 0:
                print("  ✓ Verified: 0 chunks remaining")
            else:
                print(f"  ⚠️  WARNING: {verify_count.count} chunks still remain!")
        else:
            print(f"  ℹ  No chunks found (already deleted or never ingested)")

    except Exception as e:
        print(f"  ✗ Error: {e}")
        print(f"  This book still needs manual cleanup!")

print(f"\n{'=' * 80}")
print(f"CLEANUP SUMMARY")
print(f"{'=' * 80}")
print(f"Total chunks deleted: {total_deleted:,}")

# Get final collection count
try:
    final_count = client.count(collection_name="chess_production")
    print(f"Final collection size: {final_count.count:,} chunks")
except Exception as e:
    print(f"Could not get final count: {e}")
