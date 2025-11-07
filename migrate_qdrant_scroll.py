#!/usr/bin/env python3
"""
Migrate Qdrant from Local to Docker using scroll API
Since local Qdrant doesn't support snapshots, we'll:
1. Create collection in Docker Qdrant
2. Scroll through all points in local Qdrant
3. Upload them in batches to Docker Qdrant
"""

import sys
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

LOCAL_QDRANT_PATH = "./qdrant_production_db"
DOCKER_QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "chess_production"
BATCH_SIZE = 100  # Reduced for better reliability

def main():
    print("=" * 80)
    print("QDRANT MIGRATION: LOCAL → DOCKER (Scroll Method)")
    print("=" * 80)

    # Connect to local Qdrant
    print("\n1️⃣  Connecting to local Qdrant...")
    try:
        local_client = QdrantClient(path=LOCAL_QDRANT_PATH)
        local_info = local_client.get_collection(COLLECTION_NAME)
        total_points = local_info.points_count
        print(f"✅ Connected to local Qdrant")
        print(f"   Collection: {COLLECTION_NAME}")
        print(f"   Points: {total_points:,}")
        print(f"   Vector size: {local_info.config.params.vectors.size}")
        print(f"   Distance: {local_info.config.params.vectors.distance}")
    except Exception as e:
        print(f"❌ Failed to connect to local Qdrant: {e}")
        return False

    # Connect to Docker Qdrant
    print("\n2️⃣  Connecting to Docker Qdrant...")
    try:
        docker_client = QdrantClient(url=DOCKER_QDRANT_URL, timeout=60)
        # Test connection
        docker_client.get_collections()
        print(f"✅ Connected to Docker Qdrant (60s timeout)")
    except Exception as e:
        print(f"❌ Failed to connect to Docker Qdrant: {e}")
        print("   Make sure Docker container is running: docker-compose up -d")
        return False

    # Create collection in Docker
    print("\n3️⃣  Creating collection in Docker Qdrant...")
    try:
        docker_client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=local_info.config.params.vectors.size,
                distance=local_info.config.params.vectors.distance
            )
        )
        print(f"✅ Collection created")
    except Exception as e:
        print(f"❌ Failed to create collection: {e}")
        return False

    # Migrate data
    print(f"\n4️⃣  Migrating {total_points:,} points...")
    print(f"   Batch size: {BATCH_SIZE}")

    try:
        offset = None
        migrated = 0

        while True:
            # Scroll through local Qdrant
            scroll_result, next_offset = local_client.scroll(
                collection_name=COLLECTION_NAME,
                limit=BATCH_SIZE,
                offset=offset,
                with_payload=True,
                with_vectors=True
            )

            if not scroll_result:
                break

            # Convert Record objects to PointStruct
            points_to_upload = []
            for record in scroll_result:
                point = PointStruct(
                    id=record.id,
                    vector=record.vector,
                    payload=record.payload
                )
                points_to_upload.append(point)

            # Upload batch to Docker Qdrant
            docker_client.upsert(
                collection_name=COLLECTION_NAME,
                points=points_to_upload
            )

            migrated += len(scroll_result)
            progress = (migrated / total_points) * 100
            print(f"   Progress: {migrated:,}/{total_points:,} ({progress:.1f}%)", end='\r')

            # Check if we're done
            if next_offset is None:
                break

            offset = next_offset

        print(f"\n✅ Migration complete: {migrated:,} points transferred")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify migration
    print("\n5️⃣  Verifying migration...")
    try:
        docker_info = docker_client.get_collection(COLLECTION_NAME)
        docker_count = docker_info.points_count

        print(f"\n📊 Comparison:")
        print(f"   Local Qdrant:  {total_points:,} points")
        print(f"   Docker Qdrant: {docker_count:,} points")

        if docker_count == total_points:
            print(f"\n✅ Migration successful! Counts match.")
            return True
        else:
            diff = abs(total_points - docker_count)
            print(f"\n⚠️  Counts differ by {diff:,} points")
            return False

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == '__main__':
    success = main()

    if success:
        print("\n" + "=" * 80)
        print("MIGRATION COMPLETE ✅")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Update Flask: export QDRANT_MODE=docker")
        print("2. Restart Flask: python app.py")
        print("3. Test queries")
        print(f"\n💡 Qdrant Dashboard: http://localhost:6333/dashboard")
        sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print("MIGRATION FAILED ❌")
        print("=" * 80)
        sys.exit(1)
