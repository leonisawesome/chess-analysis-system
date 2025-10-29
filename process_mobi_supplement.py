#!/usr/bin/env python3
"""
Process MOBI Supplement - Add 102 MOBI files to existing corpus
Extract chunks from MOBI files and append to existing Qdrant collection
"""

import sqlite3
import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import time
from tqdm import tqdm

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

import mobi
from bs4 import BeautifulSoup
import tiktoken


# ============================================================================
# CONFIGURATION
# ============================================================================

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
COLLECTION_NAME = "chess_production"
DB_PATH = "epub_analysis.db"
QDRANT_PATH = "./qdrant_production_db"

TIERS_TO_INCLUDE = ['HIGH', 'MEDIUM']

# Chunking parameters (same as EPUB processing)
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

# Embedding batch size
EMBED_BATCH_SIZE = 100


# ============================================================================
# MOBI EXTRACTION
# ============================================================================

def extract_mobi_text(mobi_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract text from MOBI file using mobi library.

    Args:
        mobi_path: Path to the MOBI file

    Returns:
        tuple: (text, error_message)
        - text is None if extraction failed
        - error_message explains why extraction failed
    """
    try:
        # Extract using mobi library
        tempdir, filepath = mobi.extract(mobi_path)

        # Read the extracted HTML/text
        html_file = Path(tempdir) / "mobi7" / "book.html"
        if not html_file.exists():
            # Try alternative path
            html_file = Path(tempdir) / "book.html"

        if not html_file.exists():
            return None, "No HTML content found after extraction"

        # Read and parse HTML
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)

        # Clean up temp directory
        shutil.rmtree(tempdir, ignore_errors=True)

        # Basic quality check
        word_count = len(text.split())
        if word_count < 500:
            return None, f"Insufficient text: {word_count} words"

        return text, None

    except FileNotFoundError:
        return None, f"File not found: {mobi_path}"
    except Exception as e:
        return None, f"MOBI extraction error: {str(e)}"


# ============================================================================
# BOOK SELECTION
# ============================================================================

def get_mobi_books(db_path: str, tiers: List[str]) -> List[Dict]:
    """
    Get list of MOBI books from SQLite database by tier.

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
        AND filename LIKE '%.mobi'
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
    Extract chunks from a single MOBI book.

    Returns:
        List of chunk dicts with text, metadata
    """
    try:
        # Extract text from MOBI
        text, error = extract_mobi_text(book_path)

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

def get_next_point_id(qdrant_client: QdrantClient) -> int:
    """Get the next available point ID for appending."""
    collection_info = qdrant_client.get_collection(COLLECTION_NAME)
    return collection_info.points_count


def append_to_qdrant(qdrant_client: QdrantClient, chunks: List[Dict], start_id: int):
    """Append embedded chunks to existing Qdrant collection."""
    print(f"\n📤 Appending {len(chunks)} chunks to Qdrant (starting ID: {start_id})...")

    points = []
    for i, chunk in enumerate(chunks):
        point = PointStruct(
            id=start_id + i,
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

        if (i + batch_size) % 1000 == 0:
            print(f"   Uploaded {min(i + batch_size, len(points)):,}/{len(points):,} chunks")

    print(f"✅ Append complete: {len(points):,} chunks added")


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Main MOBI supplement processing pipeline."""
    print("=" * 80)
    print("MOBI SUPPLEMENT: ADD 102 MOBI FILES TO EXISTING CORPUS")
    print("=" * 80)
    print(f"Target: MOBI files from {', '.join(TIERS_TO_INCLUDE)} tier books")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"Collection: {COLLECTION_NAME} (APPEND MODE)")
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

    # Check existing collection
    collections = qdrant_client.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        print(f"   ❌ Collection '{COLLECTION_NAME}' not found!")
        return

    collection_info = qdrant_client.get_collection(COLLECTION_NAME)
    existing_points = collection_info.points_count
    print(f"   ✅ Existing collection has {existing_points:,} chunks")

    # Get MOBI books to process
    print(f"\n2️⃣  Loading MOBI books from database...")
    books = get_mobi_books(DB_PATH, TIERS_TO_INCLUDE)
    print(f"   ✅ Found {len(books)} MOBI books to process")
    print(f"   Total words: {sum(b['word_count'] for b in books):,}")

    # Extract chunks from all MOBI books
    print(f"\n3️⃣  Extracting chunks from {len(books)} MOBI books...")
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
    print(f"\n4️⃣  Saving MOBI chunks to JSON...")
    chunks_file = 'mobi_chunks.json'
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

    # Append to Qdrant collection
    print(f"\n6️⃣  Appending to Qdrant collection...")
    next_id = get_next_point_id(qdrant_client)
    append_to_qdrant(qdrant_client, embedded_chunks, next_id)

    # Final verification
    final_collection_info = qdrant_client.get_collection(COLLECTION_NAME)
    final_points = final_collection_info.points_count

    # Summary
    print("\n" + "=" * 80)
    print("MOBI SUPPLEMENT COMPLETE")
    print("=" * 80)
    print(f"✅ MOBI books processed: {len(books) - len(failed_books):,}/{len(books):,}")
    print(f"✅ Chunks extracted: {len(all_chunks):,}")
    print(f"✅ Embeddings generated: {len(embedded_chunks):,}")
    print(f"✅ Chunks added to Qdrant: {len(embedded_chunks):,}")
    print()
    print(f"📊 Collection stats:")
    print(f"   Before: {existing_points:,} chunks")
    print(f"   Added:  {len(embedded_chunks):,} chunks")
    print(f"   After:  {final_points:,} chunks")
    print()
    print(f"✅ Final corpus: {final_points:,} chunks from 1,052 books")
    print(f"✅ Database location: {QDRANT_PATH}/")
    print("=" * 80)


if __name__ == '__main__':
    main()
