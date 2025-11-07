#!/usr/bin/env python3
"""
Migrate Qdrant from Local File Storage to Docker

This script:
1. Creates a snapshot of the current local Qdrant collection
2. Uploads the snapshot to Docker Qdrant
3. Recovers the collection in Docker
4. Verifies the migration

Prerequisites:
- Docker must be running
- Qdrant container must be started (docker-compose up -d)
- Python environment with qdrant-client installed

Usage:
    python migrate_to_docker_qdrant.py
"""

import os
import time
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Configuration
LOCAL_QDRANT_PATH = "./qdrant_production_db"
DOCKER_QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "chess_production"
SNAPSHOT_DIR = "./qdrant_snapshots"


def check_docker_qdrant():
    """Check if Docker Qdrant is accessible."""
    try:
        client = QdrantClient(url=DOCKER_QDRANT_URL)
        collections = client.get_collections()
        print(f"✅ Docker Qdrant is accessible")
        print(f"   Current collections: {[c.name for c in collections.collections]}")
        return client
    except Exception as e:
        print(f"❌ Cannot connect to Docker Qdrant: {e}")
        print(f"\n💡 Make sure Docker is running:")
        print(f"   1. Start Docker Desktop")
        print(f"   2. Run: docker-compose up -d")
        print(f"   3. Wait 10-15 seconds for Qdrant to start")
        print(f"   4. Check: curl http://localhost:6333/health")
        return None


def create_snapshot(local_client):
    """Create a snapshot of the local collection."""
    print(f"\n📸 Creating snapshot of local collection '{COLLECTION_NAME}'...")

    try:
        # Create snapshot
        snapshot_info = local_client.create_snapshot(collection_name=COLLECTION_NAME)
        snapshot_name = snapshot_info.name
        print(f"✅ Snapshot created: {snapshot_name}")

        # Get snapshot file path
        snapshot_path = Path(LOCAL_QDRANT_PATH) / "snapshots" / COLLECTION_NAME / snapshot_name

        if not snapshot_path.exists():
            print(f"❌ Snapshot file not found: {snapshot_path}")
            return None

        size_mb = snapshot_path.stat().st_size / (1024 * 1024)
        print(f"   Snapshot size: {size_mb:.1f} MB")
        print(f"   Location: {snapshot_path}")

        return snapshot_path

    except Exception as e:
        print(f"❌ Failed to create snapshot: {e}")
        return None


def upload_and_recover(docker_client, snapshot_path):
    """Upload snapshot to Docker Qdrant and recover collection."""
    print(f"\n📤 Uploading snapshot to Docker Qdrant...")

    try:
        # Read snapshot file
        with open(snapshot_path, 'rb') as f:
            snapshot_data = f.read()

        print(f"   Read {len(snapshot_data) / (1024*1024):.1f} MB")

        # Upload and recover
        print(f"   Uploading and recovering collection...")
        docker_client.recover_snapshot(
            collection_name=COLLECTION_NAME,
            snapshot=snapshot_data,
            wait=True
        )

        print(f"✅ Snapshot uploaded and collection recovered")
        return True

    except Exception as e:
        print(f"❌ Failed to upload/recover snapshot: {e}")
        return False


def verify_migration(local_client, docker_client):
    """Verify the migration was successful."""
    print(f"\n🔍 Verifying migration...")

    try:
        # Get collection info from both
        local_info = local_client.get_collection(COLLECTION_NAME)
        docker_info = docker_client.get_collection(COLLECTION_NAME)

        local_count = local_info.points_count
        docker_count = docker_info.points_count

        print(f"\n📊 Comparison:")
        print(f"   Local Qdrant:  {local_count:,} points")
        print(f"   Docker Qdrant: {docker_count:,} points")

        if local_count == docker_count:
            print(f"\n✅ Migration successful! Counts match.")

            # Test a sample query
            print(f"\n🧪 Testing sample query...")
            results = docker_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=[0.1] * 1536,  # Dummy vector
                limit=1
            )
            print(f"✅ Query test successful (found {len(results)} results)")

            return True
        else:
            diff = abs(local_count - docker_count)
            print(f"\n⚠️  Counts differ by {diff:,} points")
            return False

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def main():
    """Main migration workflow."""
    print("=" * 80)
    print("QDRANT MIGRATION: LOCAL → DOCKER")
    print("=" * 80)

    # Step 1: Connect to local Qdrant
    print(f"\n1️⃣  Connecting to local Qdrant...")
    try:
        local_client = QdrantClient(path=LOCAL_QDRANT_PATH)
        local_info = local_client.get_collection(COLLECTION_NAME)
        print(f"✅ Connected to local Qdrant")
        print(f"   Collection: {COLLECTION_NAME}")
        print(f"   Points: {local_info.points_count:,}")
        print(f"   Size: {Path(LOCAL_QDRANT_PATH).stat().st_size / (1024**3):.2f} GB")
    except Exception as e:
        print(f"❌ Cannot connect to local Qdrant: {e}")
        return False

    # Step 2: Check Docker Qdrant
    print(f"\n2️⃣  Checking Docker Qdrant...")
    docker_client = check_docker_qdrant()
    if not docker_client:
        return False

    # Step 3: Create snapshot
    print(f"\n3️⃣  Creating snapshot...")
    snapshot_path = create_snapshot(local_client)
    if not snapshot_path:
        return False

    # Step 4: Upload and recover
    print(f"\n4️⃣  Migrating to Docker...")
    if not upload_and_recover(docker_client, snapshot_path):
        return False

    # Step 5: Verify
    print(f"\n5️⃣  Verifying migration...")
    if not verify_migration(local_client, docker_client):
        return False

    # Success
    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE ✅")
    print("=" * 80)
    print(f"\nDocker Qdrant is now running with your chess corpus!")
    print(f"\nNext steps:")
    print(f"1. Update Flask to use Docker Qdrant (QDRANT_URL='http://localhost:6333')")
    print(f"2. Restart Flask server")
    print(f"3. Test queries")
    print(f"4. (Optional) Backup local Qdrant and free up 5.5GB disk space")
    print(f"\n💡 Qdrant Dashboard: http://localhost:6333/dashboard")

    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
