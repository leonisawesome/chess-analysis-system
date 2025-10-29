#!/usr/bin/env python3
"""
Test Query 4 against all databases to find the Week 1 database
Query 4: "How do I create weaknesses in my opponent's position?"
Week 1 expected: 90% precision (4y + 1p)
"""

from openai import OpenAI
from qdrant_client import QdrantClient

EMBEDDING_MODEL = "text-embedding-3-small"
QUERY = "How do I create weaknesses in my opponent's position?"

databases = [
    ('./qdrant_validation_db', 'chess_validation'),           # 11:32 (WEEK 1?)
    ('./qdrant_optimized_db', 'chess_validation_optimized'),  # 14:08
    ('./qdrant_quick_test', 'chess_quick_test'),              # 14:10
    ('./qdrant_full_validation', 'chess_full_validation')     # 14:15
]

openai_client = OpenAI()

print("="*80)
print("QUERY 4 TEST ACROSS ALL DATABASES")
print("="*80)
print(f"\nQuery: {QUERY}")
print("\nWeek 1 Expected: 90% precision (4 relevant + 1 partial)")
print("="*80)

# Embed the query once
query_vector = openai_client.embeddings.create(
    model=EMBEDDING_MODEL,
    input=QUERY
).data[0].embedding

for db_path, collection_name in databases:
    print(f"\n{'='*80}")
    print(f"DATABASE: {db_path}")
    print(f"COLLECTION: {collection_name}")
    print("="*80)

    try:
        qdrant_client = QdrantClient(path=db_path)

        results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=5
        )

        for i, result in enumerate(results, 1):
            print(f"\n--- RESULT {i} ---")
            print(f"Score: {result.score:.4f}")
            print(f"Book: {result.payload.get('book_name', 'unknown')}")
            print(f"Chapter: {result.payload.get('chapter_title', 'unknown')}")
            print(f"\nText preview:")
            text = result.payload['text']
            print(text[:300])
            if len(text) > 300:
                print("...")

    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "="*80)
print("ANALYSIS")
print("="*80)
print("\nCompare results to Week 1 expectations:")
print("- Which database returns highly relevant results about weaknesses?")
print("- Which database has irrelevant/low-quality results?")
print("\nExpected: qdrant_validation_db (11:32) should return good results")
print("="*80)
