from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(host="localhost", port=6333)

books_to_delete = [
    "pavlovic_2017_reloaded_weapons_in_the_benoni_thinkers.epub",
    "tan_0000_1e4_the_chess_bible.epub"
]

total_deleted = 0

for book_name in books_to_delete:
    print(f"\nProcessing: {book_name}")

    try:
        count_result = client.count(
            collection_name="chess_production",
            count_filter=Filter(
                must=[FieldCondition(key="book_name", match=MatchValue(value=book_name))]
            )
        )

        print(f"  Found {count_result.count} chunks")

        if count_result.count > 0:
            client.delete(
                collection_name="chess_production",
                points_selector=Filter(
                    must=[FieldCondition(key="book_name", match=MatchValue(value=book_name))]
                )
            )
            print(f"  ✓ Deleted {count_result.count} chunks")
            total_deleted += count_result.count
        else:
            print(f"  ℹ No chunks found")
    except Exception as e:
        print(f"  ✗ Error: {e}")

print(f"\n{'='*60}")
print(f"Total chunks deleted: {total_deleted}")

# Get final count
try:
    final_count = client.count(collection_name="chess_production")
    print(f"Remaining chunks in collection: {final_count.count:,}")
except Exception as e:
    print(f"Could not get final count: {e}")
