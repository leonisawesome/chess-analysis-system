#!/usr/bin/env python3
"""
Verify ALL books that were deleted from disk are also gone from Qdrant.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(host="localhost", port=6333, timeout=300)

# All books deleted from disk this session
deleted_books = [
    "pavlovic_2017_reloaded_weapons_in_the_benoni_thinkers.epub",
    "tan_0000_1e4_the_chess_bible.epub",
    "unknown_author_2018_arthur_van_de_oudeweeterig_chess_pattern_recognition_for_beginners_new_in_chess.epub",
    "moskalenko_2019_an_attacking_repertoire_for_white_with_1d4_nic_no_dg.epub",
]

print("=" * 80)
print("VERIFICATION: Deleted Books in Qdrant")
print("=" * 80)

total_remaining = 0
issues = []

for book_name in deleted_books:
    try:
        count_result = client.count(
            collection_name="chess_production",
            count_filter=Filter(
                must=[FieldCondition(key="book_name", match=MatchValue(value=book_name))]
            )
        )

        if count_result.count == 0:
            print(f"✓ {book_name}: CLEAN (0 chunks)")
        else:
            print(f"✗ {book_name}: {count_result.count} chunks STILL EXIST!")
            total_remaining += count_result.count
            issues.append((book_name, count_result.count))

    except Exception as e:
        print(f"⚠ {book_name}: Error checking: {e}")
        issues.append((book_name, "error"))

print(f"\n{'=' * 80}")
print(f"VERIFICATION SUMMARY")
print(f"{'=' * 80}")

if total_remaining == 0 and len(issues) == 0:
    print("✅ SUCCESS: All deleted books are clean in Qdrant!")
else:
    print(f"⚠️  WARNING: {total_remaining} chunks still exist from deleted books")
    if issues:
        print("\nBooks with remaining data:")
        for book, count in issues:
            print(f"  - {book}: {count} chunks")

# Get final collection count
final_count = client.count(collection_name="chess_production")
print(f"\nFinal Qdrant collection size: {final_count.count:,} chunks")
