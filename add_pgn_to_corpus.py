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
import threading
import queue
from pathlib import Path
from typing import List, Dict
from datetime import datetime

import openai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


def log(message: str):
    """Print immediately so long-running jobs show progress."""
    print(message, flush=True)


class PGNCorpusBuilder:
    """Builds vector corpus from PGN chunks."""

    def __init__(
        self,
        openai_api_key: str,
        qdrant_mode: str = "docker",
        qdrant_url: str = "http://localhost:6333",
        force_recreate: bool = False,
    ):
        self.openai_api_key = openai_api_key
        openai.api_key = openai_api_key

        # Initialize Qdrant client
        if qdrant_mode == "docker":
            log(f"Connecting to Docker Qdrant at {qdrant_url}")
            self.qdrant_client = QdrantClient(url=qdrant_url)
        else:
            log("Using local Qdrant")
            self.qdrant_client = QdrantClient(path="./qdrant_pgn_db")

        self.stats = {
            "chunks_processed": 0,
            "chunks_embedded": 0,
            "chunks_uploaded": 0,
            "total_tokens_used": 0,
            "total_cost": 0.0,
            "start_time": time.time()
        }
        self.total_chunks = 0
        self.force_recreate = force_recreate
        self._heartbeat_queue: "queue.Queue[str]" = queue.Queue()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self._heartbeat_running = False

    def create_collection(self, collection_name: str):
        """Create Qdrant collection for PGN chunks."""
        # Check if collection exists
        collections = self.qdrant_client.get_collections().collections
        existing = [c.name for c in collections]

        if collection_name in existing:
            log(f"⚠️  Collection '{collection_name}' already exists")
            if self.force_recreate:
                response = "yes"
            else:
                response = input("Delete and recreate? (yes/no): ")
            if response.lower() == "yes":
                self.qdrant_client.delete_collection(collection_name)
                log("✅ Deleted existing collection")
            else:
                log("Keeping existing collection, will append points")
                return

        # Create new collection
        self.qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=1536,  # OpenAI text-embedding-3-small
                distance=Distance.COSINE
            )
        )
        log(f"✅ Created collection: {collection_name}")

    def load_chunks(self, chunks_file: Path) -> Dict:
        """Load chunks from JSON file."""
        with open(chunks_file) as f:
            data = json.load(f)

        self.total_chunks = len(data["chunks"])
        log(f"\n{'='*80}")
        log(f"Loaded chunks from: {chunks_file}")
        log(f"  Chunks: {self.total_chunks}")
        log(f"  Estimated tokens: {data['stats']['total_tokens_estimated']:,}")
        log(f"  Games processed: {data['stats']['games_processed']}")
        log(f"{'='*80}\n")
        return data

    def generate_embeddings(self, chunks: List[Dict], batch_size: int = 100) -> List[Dict]:
        """Generate embeddings for chunks using OpenAI API."""
        total = len(chunks)
        log(f"Generating embeddings for {total} chunks...")
        log(f"Batch size: {batch_size}\n")

        embedded_chunks = []
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        stage_start = time.time()
        self._start_heartbeat("embedding", total)

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1

            log(f"[Embeddings] Batch {batch_num}/{total_batches} ({len(batch)} chunks)")
            attempts = 0
            while True:
                try:
                    texts = [chunk["text"] for chunk in batch]
                    response = openai.embeddings.create(
                        model="text-embedding-3-small",
                        input=texts
                    )
                    tokens_used = response.usage.total_tokens

                    for chunk, embedding_data in zip(batch, response.data):
                        chunk_copy = chunk.copy()
                        chunk_copy["embedding"] = embedding_data.embedding
                        embedded_chunks.append(chunk_copy)

                    self.stats["total_tokens_used"] += tokens_used
                    self.stats["chunks_embedded"] += len(batch)

                    percent = (self.stats["chunks_embedded"] / total) * 100
                    elapsed = time.time() - stage_start
                    avg_per_chunk = elapsed / self.stats["chunks_embedded"]
                    remaining = max(total - self.stats["chunks_embedded"], 0)
                    eta_minutes = (remaining * avg_per_chunk) / 60 if self.stats["chunks_embedded"] else 0
                    log(
                        f"   ✓ Tokens +{tokens_used:,} | "
                        f"{self.stats['chunks_embedded']}/{total} chunks ({percent:.2f}%) | "
                        f"ETA ~{eta_minutes:.1f} min"
                    )
                    break

                except Exception as e:
                    attempts += 1
                    wait = min(60, 2 ** attempts)
                    log(f"   ✗ Error: {e}")
                    log(f"   ↻ Retrying batch {batch_num} in {wait}s (attempt {attempts})")
                    time.sleep(wait)
                finally:
                    self._heartbeat_queue.put(
                        f"[heartbeat] embedding {self.stats['chunks_embedded']}/{total} chunks"
                    )
                if attempts >= 5:
                    log(f"   ⚠️  Giving up on batch {batch_num} after {attempts} attempts")
                    break

        # Calculate cost ($0.02 per 1M tokens for text-embedding-3-small)
        self.stats["total_cost"] = self.stats["total_tokens_used"] * 0.02 / 1_000_000
        self._stop_heartbeat()

        log(f"\n✅ Embedded {len(embedded_chunks)} chunks")
        log(f"   Tokens used: {self.stats['total_tokens_used']:,}")
        log(f"   Cost: ${self.stats['total_cost']:.4f}\n")

        return embedded_chunks

    def upload_to_qdrant(self, chunks: List[Dict], collection_name: str, batch_size: int = 100):
        """Upload embedded chunks to Qdrant."""
        log(f"Uploading {len(chunks)} chunks to Qdrant collection '{collection_name}'...")

        total_batches = (len(chunks) + batch_size - 1) // batch_size
        stage_start = time.time()
        self._start_heartbeat("upload", len(chunks))

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1

            log(f"[Upload] Batch {batch_num}/{total_batches} ({len(batch)} chunks)")

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
                percent = (self.stats["chunks_uploaded"] / len(chunks)) * 100
                elapsed = time.time() - stage_start
                avg_per_chunk = elapsed / self.stats["chunks_uploaded"]
                remaining = max(len(chunks) - self.stats["chunks_uploaded"], 0)
                eta_minutes = (remaining * avg_per_chunk) / 60 if self.stats["chunks_uploaded"] else 0
                log(
                    f"   ✓ Uploaded total {self.stats['chunks_uploaded']}/{len(chunks)} chunks "
                    f"({percent:.2f}%) | ETA ~{eta_minutes:.1f} min"
                )

            except Exception as e:
                log(f"   ✗ Error: {e}")
                continue
            finally:
                self._heartbeat_queue.put(
                    f"[heartbeat] upload {self.stats['chunks_uploaded']}/{len(chunks)} chunks"
                )

        self._stop_heartbeat()
        log(f"\n✅ Uploaded {self.stats['chunks_uploaded']} chunks to Qdrant\n")

    def print_final_stats(self):
        """Print final processing statistics."""
        elapsed = time.time() - self.stats["start_time"]

        log(f"\n{'='*80}")
        log("FINAL STATISTICS")
        log(f"{'='*80}")
        log(f"Chunks embedded: {self.stats['chunks_embedded']}")
        log(f"Chunks uploaded: {self.stats['chunks_uploaded']}")
        log(f"Total tokens: {self.stats['total_tokens_used']:,}")
        log(f"Total cost: ${self.stats['total_cost']:.4f}")
        log(f"Processing time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        log(f"{'='*80}\n")

    def _heartbeat_worker(self):
        """Print heartbeat messages every ~30s to avoid 'hung' perception."""
        while self._heartbeat_running:
            try:
                message = self._heartbeat_queue.get(timeout=30)
                log(message)
            except queue.Empty:
                log("[heartbeat] still running…")

    def _start_heartbeat(self, label: str, total: int):
        if self._heartbeat_running:
            return
        self._heartbeat_running = True
        log(f"[heartbeat] Started for {label} ({total} chunks)")
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self._heartbeat_thread.start()

    def _stop_heartbeat(self):
        if not self._heartbeat_running:
            return
        self._heartbeat_running = False
        self._heartbeat_queue.put("[heartbeat] stopping")
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=1)


def main():
    parser = argparse.ArgumentParser(description="Add PGN chunks to Qdrant corpus")
    parser.add_argument("chunks_file", type=str, help="JSON file with chunks from analyze_pgn_games.py")
    parser.add_argument("--collection", type=str, default="chess_pgn_test", help="Qdrant collection name")
    parser.add_argument("--qdrant-mode", type=str, default="docker", choices=["docker", "local"], help="Qdrant mode")
    parser.add_argument("--qdrant-url", type=str, default="http://localhost:6333", help="Qdrant URL (for docker mode)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument("--dry-run", action="store_true", help="Generate embeddings but don't upload")
    parser.add_argument("--limit", type=int, help="Only process first N chunks (for testing)")
    parser.add_argument("--force-recreate", action="store_true", help="Skip prompt and recreate collection if it exists")

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
        qdrant_url=args.qdrant_url,
        force_recreate=args.force_recreate,
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
