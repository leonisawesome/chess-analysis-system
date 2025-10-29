#!/usr/bin/env python3
"""
Check all Qdrant databases to find the Week 1 database
"""

from qdrant_client import QdrantClient

databases = [
    './qdrant_validation_db',      # 11:32 (earliest)
    './qdrant_optimized_db',       # 14:08
    './qdrant_quick_test',         # 14:10
    './qdrant_full_validation'     # 14:15 (latest)
]

print("="*80)
print("QDRANT DATABASE INVESTIGATION")
print("="*80)

for db_path in databases:
    print(f"\n{'='*80}")
    print(f"DATABASE: {db_path}")
    print("="*80)

    try:
        client = QdrantClient(path=db_path)
        collections = client.get_collections()

        for coll in collections.collections:
            count = client.count(collection_name=coll.name)
            print(f"  Collection: {coll.name}")
            print(f"  Vector count: {count.count}")

    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "="*80)
