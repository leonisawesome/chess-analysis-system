#!/usr/bin/env python3
"""
Sample Qdrant payload to see actual field structure.
"""

from qdrant_client import QdrantClient

client = QdrantClient(host='localhost', port=6333)

# Get a sample point
result = client.scroll(
    collection_name="chess_production",
    limit=1,
    with_payload=True,
    with_vectors=False
)

points = result[0]

if points:
    point = points[0]
    print("=" * 80)
    print("SAMPLE QDRANT POINT PAYLOAD")
    print("=" * 80)
    print()
    print(f"Point ID: {point.id}")
    print()
    print("Payload fields:")
    for key, value in point.payload.items():
        # Truncate long text
        if isinstance(value, str) and len(value) > 200:
            value = value[:200] + "..."
        print(f"  {key}: {value}")
    print()
    print("=" * 80)
else:
    print("No points found")
