from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(host="localhost", port=6333)

book_name = "moskalenko_2019_an_attacking_repertoire_for_white_with_1d4_nic_no_dg.epub"

# Count chunks
count_result = client.count(
    collection_name="chess_production",
    count_filter=Filter(
        must=[FieldCondition(key="book_name", match=MatchValue(value=book_name))]
    )
)

print(f"Found {count_result.count} chunks for: {book_name}")

if count_result.count > 0:
    # Delete
    client.delete(
        collection_name="chess_production",
        points_selector=Filter(
            must=[FieldCondition(key="book_name", match=MatchValue(value=book_name))]
        )
    )
    print(f"✓ Deleted {count_result.count} chunks")
    
    # Verify
    new_count = client.count(collection_name="chess_production")
    print(f"New total chunks in collection: {new_count.count:,}")
else:
    print("No chunks to delete")
