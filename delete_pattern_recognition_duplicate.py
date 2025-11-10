from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(host="localhost", port=6333)

book_to_delete = "unknown_author_2018_arthur_van_de_oudeweeterig_chess_pattern_recognition_for_beginners_new_in_chess.epub"

print(f"Processing: {book_to_delete}")

try:
    count_result = client.count(
        collection_name="chess_production",
        count_filter=Filter(
            must=[FieldCondition(key="book_name", match=MatchValue(value=book_to_delete))]
        )
    )

    print(f"  Found {count_result.count} chunks")

    if count_result.count > 0:
        client.delete(
            collection_name="chess_production",
            points_selector=Filter(
                must=[FieldCondition(key="book_name", match=MatchValue(value=book_to_delete))]
            )
        )
        print(f"  ✓ Deleted {count_result.count} chunks")
    else:
        print(f"  ℹ No chunks found")

    # Get final count
    final_count = client.count(collection_name="chess_production")
    print(f"\nRemaining chunks in collection: {final_count.count:,}")
except Exception as e:
    print(f"  ✗ Error: {e}")
