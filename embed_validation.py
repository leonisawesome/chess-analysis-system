#!/usr/bin/env python3
"""
Embed Validation Chunks with OpenAI
Stores embeddings in Qdrant local database.
"""

import json
import os
from pathlib import Path
from typing import List, Dict
import time

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


# Configuration
EMBEDDING_MODEL = "text-embedding-3-small"  # $0.02 per 1M tokens
EMBEDDING_DIM = 1536  # dimension for text-embedding-3-small
COLLECTION_NAME = "chess_validation"
BATCH_SIZE = 100


def load_chunks(json_path: str = "validation_chunks.json") -> List[Dict]:
    """Load chunks from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def embed_text(client: OpenAI, text: str) -> List[float]:
    """Embed a single text using OpenAI API."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def embed_chunks_batch(client: OpenAI, chunks: List[Dict]) -> List[Dict]:
    """
    Embed chunks in batches.

    Returns:
        List of chunks with 'embedding' field added
    """
    print(f"\nEmbedding {len(chunks)} chunks...")
    print(f"Model: {EMBEDDING_MODEL}")
    print(f"Estimated cost: ${(sum(c['token_count'] for c in chunks) / 1_000_000 * 0.02):.4f}\n")

    embedded_chunks = []
    total = len(chunks)

    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        batch_texts = [c['text'] for c in batch]

        try:
            # Embed batch
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch_texts
            )

            # Add embeddings to chunks
            for j, chunk in enumerate(batch):
                chunk_with_embedding = chunk.copy()
                chunk_with_embedding['embedding'] = response.data[j].embedding
                embedded_chunks.append(chunk_with_embedding)

            # Progress
            processed = min(i + BATCH_SIZE, total)
            print(f"   Embedded {processed}/{total} chunks ({processed/total*100:.1f}%)")

            # Rate limiting (OpenAI has 3M TPM limit for tier 1)
            time.sleep(0.2)

        except Exception as e:
            print(f"\n❌ Error embedding batch {i}-{i+BATCH_SIZE}: {e}")
            break

    print(f"\n✅ Embedded {len(embedded_chunks)} chunks successfully")
    return embedded_chunks


def create_qdrant_collection(client: QdrantClient):
    """Create Qdrant collection for validation."""
    # Delete existing collection if exists
    collections = client.get_collections().collections
    if any(c.name == COLLECTION_NAME for c in collections):
        print(f"Deleting existing collection: {COLLECTION_NAME}")
        client.delete_collection(COLLECTION_NAME)

    # Create new collection
    print(f"Creating collection: {COLLECTION_NAME}")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,
            distance=Distance.COSINE
        )
    )


def upload_to_qdrant(qdrant_client: QdrantClient, chunks: List[Dict]):
    """Upload embedded chunks to Qdrant."""
    print(f"\nUploading {len(chunks)} chunks to Qdrant...")

    points = []
    for i, chunk in enumerate(chunks):
        point = PointStruct(
            id=i,
            vector=chunk['embedding'],
            payload={
                'chunk_id': chunk['chunk_id'],
                'doc_id': chunk['doc_id'],
                'book_name': chunk['book_name'],
                'category': chunk['category'],
                'chapter_title': chunk['chapter_title'],
                'chapter_order': chunk['chapter_order'],
                'chunk_index': chunk['chunk_index'],
                'text': chunk['text'],
                'token_count': chunk['token_count'],
                'word_count': chunk['word_count']
            }
        )
        points.append(point)

    # Upload in batches
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch
        )
        print(f"   Uploaded {min(i + batch_size, len(points))}/{len(points)} chunks")

    print(f"\n✅ Upload complete!")


def main():
    """Main embedding pipeline."""
    print("=" * 80)
    print("CHESS RAG VALIDATION - EMBEDDING PIPELINE")
    print("=" * 80)

    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ OPENAI_API_KEY environment variable not set!")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        return

    # Initialize clients
    print("\n1. Initializing OpenAI client...")
    openai_client = OpenAI(api_key=api_key)

    print("2. Initializing Qdrant client...")
    qdrant_client = QdrantClient(path="./qdrant_validation_db")

    # Load chunks
    print("3. Loading chunks...")
    chunks = load_chunks()
    print(f"   Loaded {len(chunks)} chunks")

    # Create collection
    print("\n4. Setting up Qdrant collection...")
    create_qdrant_collection(qdrant_client)

    # Embed chunks
    print("\n5. Embedding chunks with OpenAI...")
    embedded_chunks = embed_chunks_batch(openai_client, chunks)

    if not embedded_chunks:
        print("\n❌ No chunks were embedded. Aborting.")
        return

    # Upload to Qdrant
    print("\n6. Uploading to Qdrant...")
    upload_to_qdrant(qdrant_client, embedded_chunks)

    # Save embedded chunks to file (for backup)
    output_path = 'validation_chunks_embedded.json'
    print(f"\n7. Saving embedded chunks to {output_path}...")
    # Don't save embeddings to JSON (too large), just metadata
    chunks_metadata = [{k: v for k, v in c.items() if k != 'embedding'}
                       for c in embedded_chunks]
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks_metadata, f, indent=2, ensure_ascii=False)

    # Summary
    print("\n" + "=" * 80)
    print("EMBEDDING COMPLETE")
    print("=" * 80)
    print(f"✅ Embedded {len(embedded_chunks)} chunks")
    print(f"✅ Stored in Qdrant collection: {COLLECTION_NAME}")
    print(f"✅ Database location: ./qdrant_validation_db/")
    print("\nReady for validation testing!")
    print("=" * 80)


if __name__ == '__main__':
    main()
