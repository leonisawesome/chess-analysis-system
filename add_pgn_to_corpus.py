#!/usr/bin/env python3
"""
PGN to Corpus Ingestion Script

Takes chunks created by analyze_pgn_games.py, generates embeddings,
and uploads to Qdrant vector database.

Usage:
    python add_pgn_to_corpus.py pgn_chunks.json --collection chess_pgn_test
    python add_pgn_to_corpus.py pgn_chunks.json --collection chess_pgn_test --dry-run
"""

import json
import argparse
import sys
import time
from pathlib import Path
from typing import List, Dict
from datetime import datetime

import openai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


class PGNCorpusBuilder:
    """Builds vector corpus from PGN chunks."""

    def __init__(self, openai_api_key: str, qdrant_mode: str = "docker", qdrant_url: str = "http://localhost:6333"):
        self.openai_api_key = openai_api_key
        openai.api_key = openai_api_key

        # Initialize Qdrant client
        if qdrant_mode == "docker":
            print(f"Connecting to Docker Qdrant at {qdrant_url}")
            self.qdrant_client = QdrantClient(url=qdrant_url)
        else:
            print("Using local Qdrant")
            self.qdrant_client = QdrantClient(path="./qdrant_pgn_db")

        self.stats = {
            "chunks_processed": 0,
            "chunks_embedded": 0,
            "chunks_uploaded": 0,
            "total_tokens_used": 0,
            "total_cost": 0.0,
            "start_time": time.time()
        }

    def create_collection(self, collection_name: str):
        """Create Qdrant collection for PGN chunks."""
        # Check if collection exists
        collections = self.qdrant_client.get_collections().collections
        existing = [c.name for c in collections]

        if collection_name in existing:
            print(f"⚠️  Collection '{collection_name}' already exists")
            response = input("Delete and recreate? (yes/no): ")
            if response.lower() == "yes":
                self.qdrant_client.delete_collection(collection_name)
                print(f"✅ Deleted existing collection")
            else:
                print("Keeping existing collection, will append points")
                return

        # Create new collection
        self.qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=1536,  # OpenAI text-embedding-3-small
                distance=Distance.COSINE
            )
        )
        print(f"✅ Created collection: {collection_name}")

    def load_chunks(self, chunks_file: Path) -> Dict:
        """Load chunks from JSON file."""
        with open(chunks_file) as f:
            data = json.load(f)

        print(f"\n{'='*80}")
        print(f"Loaded chunks from: {chunks_file}")
        print(f"  Chunks: {len(data['chunks'])}")
        print(f"  Estimated tokens: {data['stats']['total_tokens_estimated']:,}")
        print(f"  Games processed: {data['stats']['games_processed']}")
        print(f"{'='*80}\n")

        return data

    def generate_embeddings(self, chunks: List[Dict], batch_size: int = 100) -> List[Dict]:
        """Generate embeddings for chunks using OpenAI API."""
        print(f"Generating embeddings for {len(chunks)} chunks...")
        print(f"Batch size: {batch_size}\n")

        embedded_chunks = []
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1

            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)...", end=" ")

            try:
                # Extract texts for embedding
                texts = [chunk["text"] for chunk in batch]

                # Call OpenAI API
                response = openai.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts
                )

                # Add embeddings to chunks
                for chunk, embedding_data in zip(batch, response.data):
                    chunk_copy = chunk.copy()
                    chunk_copy["embedding"] = embedding_data.embedding
                    embedded_chunks.append(chunk_copy)

                # Update stats
                tokens_used = response.usage.total_tokens
                self.stats["total_tokens_used"] += tokens_used
                self.stats["chunks_embedded"] += len(batch)

                print(f"✓ ({tokens_used} tokens)")

            except Exception as e:
                print(f"✗ Error: {e}")
                continue

        # Calculate cost ($0.02 per 1M tokens for text-embedding-3-small)
        self.stats["total_cost"] = self.stats["total_tokens_used"] * 0.02 / 1_000_000

        print(f"\n✅ Embedded {len(embedded_chunks)} chunks")
        print(f"   Tokens used: {self.stats['total_tokens_used']:,}")
        print(f"   Cost: ${self.stats['total_cost']:.4f}\n")

        return embedded_chunks

    def upload_to_qdrant(self, chunks: List[Dict], collection_name: str, batch_size: int = 100):
        """Upload embedded chunks to Qdrant."""
        print(f"Uploading {len(chunks)} chunks to Qdrant collection '{collection_name}'...")

        total_batches = (len(chunks) + batch_size - 1) // batch_size

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1

            print(f"Uploading batch {batch_num}/{total_batches} ({len(batch)} chunks)...", end=" ")

            # Create points
            points = []
            for idx, chunk in enumerate(batch):
                point_id = i + idx  # Simple incrementing ID

                # Prepare payload (metadata)
                payload = chunk["metadata"].copy()
                payload["chunk_id"] = chunk["chunk_id"]
                payload["token_estimate"] = chunk["token_estimate"]
                payload["chunk_text"] = chunk["text"][:500]  # Store first 500 chars for display

                point = PointStruct(
                    id=point_id,
                    vector=chunk["embedding"],
                    payload=payload
                )
                points.append(point)

            # Upload batch
            try:
                self.qdrant_client.upsert(
                    collection_name=collection_name,
                    points=points
                )
                self.stats["chunks_uploaded"] += len(batch)
                print("✓")

            except Exception as e:
                print(f"✗ Error: {e}")
                continue

        print(f"\n✅ Uploaded {self.stats['chunks_uploaded']} chunks to Qdrant\n")

    def print_final_stats(self):
        """Print final processing statistics."""
        elapsed = time.time() - self.stats["start_time"]

        print(f"\n{'='*80}")
        print("FINAL STATISTICS")
        print(f"{'='*80}")
        print(f"Chunks embedded: {self.stats['chunks_embedded']}")
        print(f"Chunks uploaded: {self.stats['chunks_uploaded']}")
        print(f"Total tokens: {self.stats['total_tokens_used']:,}")
        print(f"Total cost: ${self.stats['total_cost']:.4f}")
        print(f"Processing time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description="Add PGN chunks to Qdrant corpus")
    parser.add_argument("chunks_file", type=str, help="JSON file with chunks from analyze_pgn_games.py")
    parser.add_argument("--collection", type=str, default="chess_pgn_test", help="Qdrant collection name")
    parser.add_argument("--qdrant-mode", type=str, default="docker", choices=["docker", "local"], help="Qdrant mode")
    parser.add_argument("--qdrant-url", type=str, default="http://localhost:6333", help="Qdrant URL (for docker mode)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument("--dry-run", action="store_true", help="Generate embeddings but don't upload")
    parser.add_argument("--limit", type=int, help="Only process first N chunks (for testing)")

    args = parser.parse_args()

    # Check for OpenAI API key
    import os
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    # Validate chunks file
    chunks_file = Path(args.chunks_file)
    if not chunks_file.exists():
        print(f"Error: Chunks file not found: {chunks_file}")
        sys.exit(1)

    # Initialize builder
    builder = PGNCorpusBuilder(
        openai_api_key=openai_key,
        qdrant_mode=args.qdrant_mode,
        qdrant_url=args.qdrant_url
    )

    # Load chunks
    data = builder.load_chunks(chunks_file)
    chunks = data["chunks"]

    # Apply limit if specified
    if args.limit:
        chunks = chunks[:args.limit]
        print(f"⚠️  Limited to first {args.limit} chunks for testing\n")

    # Create collection (if not dry-run)
    if not args.dry_run:
        builder.create_collection(args.collection)

    # Generate embeddings
    embedded_chunks = builder.generate_embeddings(chunks, batch_size=args.batch_size)

    # Upload to Qdrant (if not dry-run)
    if not args.dry_run:
        builder.upload_to_qdrant(embedded_chunks, args.collection, batch_size=args.batch_size)
    else:
        print("⚠️  DRY RUN: Skipping Qdrant upload")

    # Print final stats
    builder.print_final_stats()

    if not args.dry_run:
        # Verify collection
        collection_info = builder.qdrant_client.get_collection(args.collection)
        print(f"✅ Collection '{args.collection}' now contains {collection_info.points_count} points")


if __name__ == "__main__":
    main()
