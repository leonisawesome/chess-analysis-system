#!/usr/bin/env python3
"""
Ingest PGN Games to Qdrant - Phase 3 Implementation
===================================================

Uses the new variation splitter to chunk PGN games and upload to Qdrant.

Features:
- Uses split_oversized_game.py for intelligent chunking
- Handles transposition metadata
- Creates chess_pgn_repertoire collection
- Generates OpenAI embeddings
- Option B: Test data (will wipe and reload for production)

Usage:
    # Test with 4 split games:
    python ingest_pgn_to_qdrant.py --test

    # Full corpus:
    python ingest_pgn_to_qdrant.py --full
"""

import argparse
import asyncio
import chess.pgn
import hashlib
import io
import json
import openai
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from split_oversized_game import split_oversized_game, count_tokens


# Configuration
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "chess_pgn_repertoire"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536
ZLISTO_DIR = Path("/Users/leon/Downloads/ZListo")

# Test game subset (4 split games)
TEST_GAMES = [
    {
        'file': 'EN - Elite Najdorf Repertoire for Black - Part 1.pgn',
        'game_number': 3
    },
    {
        'file': "Queen's Gambit with ...h7-h6 - Universal Rep. vs. 1.d4, 1.Nf3, 1.Nf3 & 1.c4 - Ioannis Papaioannou (MCM).pgn",
        'game_number': 15
    },
    {
        'file': "Queen's Gambit with ...h7-h6 - Universal Rep. vs. 1.d4, 1.Nf3, 1.Nf3 & 1.c4 - Ioannis Papaioannou (MCM).pgn",
        'game_number': 24
    },
    {
        'file': 'The Correspondence Chess Today.pgn',
        'game_number': 9
    }
]


def chunk_id_to_uuid(chunk_id: str) -> str:
    """
    Convert chunk_id string to deterministic UUID.

    Uses SHA-256 hash to ensure:
    - Deterministic (same input → same output)
    - No collisions (uses first 128 bits = UUID size)
    - Compatible with Qdrant's UUID format
    """
    hash_bytes = hashlib.sha256(chunk_id.encode()).digest()
    # Use first 16 bytes (128 bits) to create UUID
    return str(uuid.UUID(bytes=hash_bytes[:16]))


class PGNIngester:
    """Ingests PGN games to Qdrant using the variation splitter."""

    def __init__(self, qdrant_url: str = QDRANT_URL):
        """Initialize ingester with Qdrant client."""
        self.qdrant_client = QdrantClient(url=qdrant_url)
        self.stats = {
            'games_processed': 0,
            'games_failed': 0,
            'chunks_created': 0,
            'points_uploaded': 0,
            'embedding_cost': 0.0,
            'errors': []
        }

        # Get OpenAI API key
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY environment variable not set")

    def create_collection(self):
        """Create the chess_pgn_repertoire collection."""
        print(f"\n{'='*80}")
        print(f"Creating Qdrant Collection: {COLLECTION_NAME}")
        print(f"{'='*80}\n")

        # Check if collection exists
        collections = self.qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]

        if COLLECTION_NAME in collection_names:
            print(f"⚠️  Collection '{COLLECTION_NAME}' already exists")
            response = input(f"   Delete and recreate? (yes/no): ")
            if response.lower() == 'yes':
                self.qdrant_client.delete_collection(COLLECTION_NAME)
                print(f"   ✅ Deleted existing collection")
            else:
                print(f"   Keeping existing collection")
                return

        # Create new collection
        self.qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMS,
                distance=Distance.COSINE
            )
        )

        print(f"✅ Created collection: {COLLECTION_NAME}")
        print(f"   Vector size: {EMBEDDING_DIMS}")
        print(f"   Distance: COSINE")

    async def process_test_games(self):
        """Process the 4 test split games."""
        print(f"\n{'='*80}")
        print(f"Processing Test Games (4 split games, ~17 chunks)")
        print(f"{'='*80}\n")

        all_chunks = []

        for test_case in TEST_GAMES:
            pgn_path = ZLISTO_DIR / test_case['file']

            if not pgn_path.exists():
                print(f"❌ File not found: {pgn_path}")
                continue

            print(f"Processing: {test_case['file']} (game {test_case['game_number']})")

            # Read the specific game
            with open(pgn_path) as f:
                game = None
                for i in range(test_case['game_number']):
                    game = chess.pgn.read_game(f)
                    if not game:
                        print(f"   ❌ Could not read game {test_case['game_number']}")
                        self.stats['games_failed'] += 1
                        break

                if game:
                    # Split the game
                    chunks = split_oversized_game(game, test_case['file'], test_case['game_number'])
                    all_chunks.extend(chunks)
                    self.stats['games_processed'] += 1
                    self.stats['chunks_created'] += len(chunks)
                    print(f"   ✅ Split into {len(chunks)} chunks")

        # Upload chunks
        if all_chunks:
            await self.upload_chunks(all_chunks)

        return all_chunks

    async def process_full_corpus(self):
        """Process all 1,778 games from ZListo."""
        print(f"\n{'='*80}")
        print(f"Processing Full Corpus (1,778 games)")
        print(f"{'='*80}\n")

        all_chunks = []
        pgn_files = sorted(ZLISTO_DIR.glob("*.pgn"))

        print(f"Found {len(pgn_files)} PGN files\n")

        for file_idx, pgn_file in enumerate(pgn_files, 1):
            print(f"[{file_idx}/{len(pgn_files)}] {pgn_file.name}")

            # Try different encodings
            file_content = None
            for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'windows-1252']:
                try:
                    with open(pgn_file, encoding=encoding) as f:
                        file_content = f.read()
                    break
                except UnicodeDecodeError:
                    continue

            if file_content is None:
                print(f"   ❌ Could not decode file")
                self.stats['games_failed'] += 1
                continue

            # Process games in file
            game_num = 0
            with io.StringIO(file_content) as f:
                while True:
                    try:
                        game = chess.pgn.read_game(f)
                        if not game:
                            break

                        game_num += 1

                        # Split the game
                        chunks = split_oversized_game(game, pgn_file.name, game_num)
                        all_chunks.extend(chunks)
                        self.stats['games_processed'] += 1
                        self.stats['chunks_created'] += len(chunks)

                        if len(chunks) > 1:
                            print(f"   Game {game_num}: SPLIT into {len(chunks)} chunks")

                    except Exception as e:
                        self.stats['games_failed'] += 1
                        self.stats['errors'].append(f"{pgn_file.name} game {game_num}: {str(e)}")
                        continue

            print(f"   ✅ {game_num} games, {self.stats['chunks_created']} total chunks")

        # Upload all chunks
        if all_chunks:
            await self.upload_chunks(all_chunks)

        return all_chunks

    async def upload_chunks(self, chunks: List[Dict[str, Any]]):
        """Generate embeddings and upload chunks to Qdrant."""
        print(f"\n{'='*80}")
        print(f"Uploading {len(chunks)} chunks to Qdrant")
        print(f"{'='*80}\n")

        # Generate embeddings in batches
        BATCH_SIZE = 100
        points = []

        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i+BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

            print(f"Batch {batch_num}/{total_batches}: Generating embeddings for {len(batch)} chunks...")

            # Extract texts for embedding
            texts = [chunk['content'] for chunk in batch]

            # Generate embeddings
            try:
                response = self.openai_client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts
                )

                # Calculate cost (text-embedding-3-small: $0.02 per 1M tokens)
                total_tokens = sum(chunk['token_count'] for chunk in batch)
                cost = total_tokens * 0.02 / 1_000_000
                self.stats['embedding_cost'] += cost

                # Create points
                for chunk, embedding_obj in zip(batch, response.data):
                    chunk_id = chunk['metadata']['chunk_id']
                    point = PointStruct(
                        id=chunk_id_to_uuid(chunk_id),  # Convert to deterministic UUID
                        vector=embedding_obj.embedding,
                        payload={
                            **chunk['metadata'],
                            'content': chunk['content'],
                            'token_count': chunk['token_count']
                        }
                    )
                    points.append(point)

                print(f"   ✅ Generated {len(batch)} embeddings (${cost:.4f})")

            except Exception as e:
                print(f"   ❌ Embedding failed: {e}")
                self.stats['errors'].append(f"Embedding batch {batch_num}: {str(e)}")
                continue

        # Upload points to Qdrant in batches
        if points:
            UPLOAD_BATCH_SIZE = 200
            total_points = len(points)
            print(f"\nUploading {total_points} points to Qdrant in batches of {UPLOAD_BATCH_SIZE}...")

            for i in range(0, total_points, UPLOAD_BATCH_SIZE):
                batch = points[i:i+UPLOAD_BATCH_SIZE]
                batch_num = (i // UPLOAD_BATCH_SIZE) + 1
                total_batches = (total_points + UPLOAD_BATCH_SIZE - 1) // UPLOAD_BATCH_SIZE

                try:
                    self.qdrant_client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=batch
                    )
                    self.stats['points_uploaded'] += len(batch)
                    print(f"  Batch {batch_num}/{total_batches}: Uploaded {len(batch)} points")
                except Exception as e:
                    print(f"  ❌ Batch {batch_num} upload failed: {e}")
                    self.stats['errors'].append(f"Qdrant upload batch {batch_num}: {str(e)}")

            print(f"✅ Total uploaded: {self.stats['points_uploaded']}/{total_points} points")

    def print_stats(self):
        """Print ingestion statistics."""
        print(f"\n{'='*80}")
        print("INGESTION STATISTICS")
        print(f"{'='*80}")
        print(f"Games processed:  {self.stats['games_processed']}")
        print(f"Games failed:     {self.stats['games_failed']}")
        print(f"Chunks created:   {self.stats['chunks_created']}")
        print(f"Points uploaded:  {self.stats['points_uploaded']}")
        print(f"Embedding cost:   ${self.stats['embedding_cost']:.4f}")

        if self.stats['errors']:
            print(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:10]:
                print(f"  - {error}")

        print(f"{'='*80}\n")

    def verify_collection(self):
        """Verify the collection was created successfully."""
        print(f"\n{'='*80}")
        print(f"Verifying Collection")
        print(f"{'='*80}\n")

        try:
            collection_info = self.qdrant_client.get_collection(COLLECTION_NAME)
            print(f"✅ Collection: {COLLECTION_NAME}")
            print(f"   Points: {collection_info.points_count}")
            print(f"   Vectors: {collection_info.vectors_count}")
            print(f"   Status: {collection_info.status}")
        except Exception as e:
            print(f"❌ Verification failed: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Ingest PGN games to Qdrant")
    parser.add_argument('--test', action='store_true', help='Process test games only (4 split games)')
    parser.add_argument('--full', action='store_true', help='Process full corpus (1,778 games)')
    parser.add_argument('--skip-create', action='store_true', help='Skip collection creation')

    args = parser.parse_args()

    if not args.test and not args.full:
        print("Error: Must specify --test or --full")
        sys.exit(1)

    # Initialize ingester
    ingester = PGNIngester()

    # Create collection
    if not args.skip_create:
        ingester.create_collection()

    # Process games
    if args.test:
        await ingester.process_test_games()
    elif args.full:
        await ingester.process_full_corpus()

    # Print statistics
    ingester.print_stats()

    # Verify collection
    ingester.verify_collection()


if __name__ == "__main__":
    asyncio.run(main())
