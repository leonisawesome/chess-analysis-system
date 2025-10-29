#!/usr/bin/env python3
"""
Build Production Corpus - System A
Extract chunks from 1,052 HIGH+MEDIUM books, embed, and load into Qdrant

Pipeline:
1. Query SQLite for HIGH+MEDIUM tier books
2. Extract chunks from each book
3. Generate embeddings (OpenAI text-embedding-3-small)
4. Upload to Qdrant production database

Expected corpus: 1,052 books, ~84M words, ~350K chunks
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict
import time
from tqdm import tqdm

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Import EPUB extraction
from epub_to_analyzer import extract_epub_text
import tiktoken


# ============================================================================
# CONFIGURATION
# ============================================================================

EMBEDDING_MODEL = "text-embedding-3-small"  # Same as validation
EMBEDDING_DIM = 1536
COLLECTION_NAME = "chess_production"
DB_PATH = "epub_analysis.db"
QDRANT_PATH = "./qdrant_production_db"

TIERS_TO_INCLUDE = ['HIGH', 'MEDIUM']  # 1,052 books

# Chunking parameters (same as validation)
CHUNK_SIZE = 512  # tokens per chunk
CHUNK_OVERLAP = 64  # token overlap

# Embedding batch size
EMBED_BATCH_SIZE = 100

# Cost estimation
COST_PER_1M_TOKENS = 0.02  # $0.02 per 1M tokens


# ============================================================================
# BOOK SELECTION
# ============================================================================

def get_books_to_process(db_path: str, tiers: List[str]) -> List[Dict]:
    """
    Get list of books from SQLite database by tier.

    Returns:
        List of dicts with filename, full_path, tier, score
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tier_list = ','.join(f"'{t}'" for t in tiers)

    query = f"""
        SELECT filename, full_path, tier, score, word_count
        FROM epub_analysis
        WHERE tier IN ({tier_list})
        AND error IS NULL
        ORDER BY score DESC
    """

    cursor.execute(query)
    books = []
    for row in cursor.fetchall():
        books.append({
            'filename': row[0],
            'full_path': row[1],
            'tier': row[2],
            'score': row[3],
            'word_count': row[4]
        })

    conn.close()
    return books


# ============================================================================
# CHUNKING UTILITIES
# ============================================================================

def chunk_text_by_tokens(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    """
    Chunk text by token count with overlap.

    Args:
        text: Text to chunk
        chunk_size: Target tokens per chunk
        overlap: Token overlap between chunks

    Returns:
        List of text chunks
    """
    # Initialize tokenizer
    enc = tiktoken.get_encoding("cl100k_base")

    # Tokenize full text
    tokens = enc.encode(text)

    # Create overlapping chunks
    chunks = []
    stride = chunk_size - overlap

    for i in range(0, len(tokens), stride):
        chunk_tokens = tokens[i:i + chunk_size]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text)

        # Break if we're at the end
        if i + chunk_size >= len(tokens):
            break

    return chunks


# ============================================================================
# CHUNK EXTRACTION
# ============================================================================

def extract_chunks_from_book(book_path: str, book_metadata: Dict) -> List[Dict]:
    """
    Extract chunks from a single book.

    Returns:
        List of chunk dicts with text, metadata
    """
    try:
        # Extract text from EPUB
        text, error = extract_epub_text(book_path)

        if error:
            # Silent failure - will be tracked in stats
            return []

        if not text or not text.strip():
            return []

        # Chunk the full text
        chunks = chunk_text_by_tokens(
            text,
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP
        )

        if not chunks:
            return []

        # Add metadata to each chunk
        all_chunks = []
        for chunk_idx, chunk_text in enumerate(chunks):
            chunk_data = {
                'text': chunk_text,
                'book_name': book_metadata['filename'],
                'book_path': book_metadata['full_path'],
                'book_tier': book_metadata['tier'],
                'book_score': book_metadata['score'],
                'chapter_title': book_metadata['filename'],  # Use filename as chapter
                'chapter_index': 0,
                'chunk_index': chunk_idx
            }
            all_chunks.append(chunk_data)

        return all_chunks

    except Exception as e:
        # Silent failure - errors tracked in stats
        return []


# ============================================================================
# EMBEDDING GENERATION
# ============================================================================

def embed_chunks_batch(openai_client: OpenAI, chunks: List[Dict]) -> List[Dict]:
    """
    Embed chunks in batches using OpenAI API.

    Returns:
        Chunks with 'embedding' field added
    """
    embedded_chunks = []
    total = len(chunks)

    for i in range(0, total, EMBED_BATCH_SIZE):
        batch = chunks[i:i + EMBED_BATCH_SIZE]
        batch_texts = [c['text'] for c in batch]

        try:
            # Embed batch
            response = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch_texts
            )

            # Add embeddings to chunks
            for j, chunk in enumerate(batch):
                chunk_with_embedding = chunk.copy()
                chunk_with_embedding['embedding'] = response.data[j].embedding
                embedded_chunks.append(chunk_with_embedding)

            # Rate limiting
            time.sleep(0.1)

        except Exception as e:
            print(f"\n❌ Error embedding batch {i}-{i+EMBED_BATCH_SIZE}: {e}")
            print("   Continuing with next batch...")
            continue

    return embedded_chunks


# ============================================================================
# QDRANT UPLOAD
# ============================================================================

def create_production_collection(qdrant_client: QdrantClient):
    """Create production Qdrant collection."""
    # Check if collection exists
    collections = qdrant_client.get_collections().collections
    if any(c.name == COLLECTION_NAME for c in collections):
        print(f"   Collection '{COLLECTION_NAME}' already exists - deleting...")
        qdrant_client.delete_collection(COLLECTION_NAME)

    # Create new collection
    print(f"   Creating collection: {COLLECTION_NAME}")
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,
            distance=Distance.COSINE
        )
    )


def upload_to_qdrant(qdrant_client: QdrantClient, chunks: List[Dict]):
    """Upload embedded chunks to Qdrant."""
    print(f"\n📤 Uploading {len(chunks)} chunks to Qdrant...")

    points = []
    for i, chunk in enumerate(chunks):
        point = PointStruct(
            id=i,
            vector=chunk['embedding'],
            payload={
                'text': chunk['text'],
                'book_name': chunk['book_name'],
                'book_tier': chunk['book_tier'],
                'book_score': chunk['book_score'],
                'chapter_title': chunk['chapter_title'],
                'chapter_index': chunk['chapter_index'],
                'chunk_index': chunk['chunk_index']
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

        if (i + batch_size) % 10000 == 0:
            print(f"   Uploaded {min(i + batch_size, len(points)):,}/{len(points):,} chunks")

    print(f"✅ Upload complete: {len(points):,} chunks")


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Main production corpus building pipeline."""
    print("=" * 80)
    print("SYSTEM A: PRODUCTION CORPUS BUILDER")
    print("=" * 80)
    print(f"Target: {', '.join(TIERS_TO_INCLUDE)} tier books")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"Collection: {COLLECTION_NAME}")
    print()

    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set!")
        return

    # Initialize clients
    print("1️⃣  Initializing clients...")
    openai_client = OpenAI(api_key=api_key)
    qdrant_client = QdrantClient(path=QDRANT_PATH)
    print("   ✅ OpenAI and Qdrant clients ready")

    # Get books to process
    print(f"\n2️⃣  Loading books from database...")
    books = get_books_to_process(DB_PATH, TIERS_TO_INCLUDE)
    print(f"   ✅ Found {len(books)} books to process")
    print(f"   Total words: {sum(b['word_count'] for b in books):,}")

    # Estimate costs
    estimated_tokens = sum(b['word_count'] * 1.3 for b in books)  # 1.3x word-to-token ratio
    estimated_cost = estimated_tokens / 1_000_000 * COST_PER_1M_TOKENS
    print(f"   Estimated tokens: {estimated_tokens:,.0f}")
    print(f"   Estimated cost: ${estimated_cost:.2f}")
    print(f"\n   Auto-proceeding with corpus build...")

    # Extract chunks from all books
    print(f"\n3️⃣  Extracting chunks from {len(books)} books...")
    all_chunks = []
    failed_books = []

    for book in tqdm(books, desc="Extracting", unit="book"):
        chunks = extract_chunks_from_book(book['full_path'], book)
        if chunks:
            all_chunks.extend(chunks)
        else:
            failed_books.append(book['filename'])

    print(f"   ✅ Extracted {len(all_chunks):,} chunks from {len(books) - len(failed_books)} books")
    if failed_books:
        print(f"   ⚠️  Failed to extract from {len(failed_books)} books")

    # Save chunks to JSON (without embeddings)
    print(f"\n4️⃣  Saving chunks to JSON...")
    chunks_file = 'production_chunks.json'
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Saved to {chunks_file}")

    # Generate embeddings
    print(f"\n5️⃣  Generating embeddings for {len(all_chunks):,} chunks...")
    print(f"   This will take approximately {len(all_chunks) / EMBED_BATCH_SIZE * 0.1 / 60:.1f} minutes")

    embedded_chunks = embed_chunks_batch(openai_client, all_chunks)
    print(f"   ✅ Generated {len(embedded_chunks):,} embeddings")

    if len(embedded_chunks) < len(all_chunks):
        print(f"   ⚠️  Warning: Only {len(embedded_chunks)}/{len(all_chunks)} chunks embedded")

    # Create Qdrant collection
    print(f"\n6️⃣  Setting up Qdrant collection...")
    create_production_collection(qdrant_client)
    print(f"   ✅ Collection ready")

    # Upload to Qdrant
    print(f"\n7️⃣  Uploading to Qdrant...")
    upload_to_qdrant(qdrant_client, embedded_chunks)

    # Summary
    print("\n" + "=" * 80)
    print("PRODUCTION CORPUS BUILD COMPLETE")
    print("=" * 80)
    print(f"✅ Books processed: {len(books) - len(failed_books):,}/{len(books):,}")
    print(f"✅ Chunks extracted: {len(all_chunks):,}")
    print(f"✅ Embeddings generated: {len(embedded_chunks):,}")
    print(f"✅ Qdrant collection: {COLLECTION_NAME}")
    print(f"✅ Database location: {QDRANT_PATH}/")
    print()
    print("Next steps:")
    print("1. Run validation queries on production corpus")
    print("2. Measure precision@5 (target: 86-87%)")
    print("3. Test performance (latency, memory)")
    print("=" * 80)


if __name__ == '__main__':
    main()
