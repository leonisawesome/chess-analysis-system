#!/usr/bin/env python3
"""
Incremental Book Addition to Chess RAG Corpus

Add new books to existing Qdrant production database without rebuilding.

Usage:
    # Docker mode (default, recommended)
    export QDRANT_MODE=docker
    export QDRANT_URL=http://localhost:6333
    export OPENAI_API_KEY='your-key-here'
    python add_books_to_corpus.py book1.epub book2.epub book3.epub

    # Alternative syntax
    python add_books_to_corpus.py --books "book1.epub" "book2.epub"

    # Add all books not yet in Qdrant
    python add_books_to_corpus.py --all-new

    # Local mode (not recommended for large collections)
    export QDRANT_MODE=local
    python add_books_to_corpus.py book1.epub book2.epub

Requirements:
    - OPENAI_API_KEY environment variable set
    - QDRANT_MODE environment variable ('docker' or 'local', default: 'docker')
    - QDRANT_URL environment variable (default: 'http://localhost:6333')
    - Books must be in /Volumes/T7 Shield/epub/ directory
    - Books must be analyzed in epub_analysis.db
"""

import argparse
import sqlite3
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Set
import time
from tqdm import tqdm

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

# Import shared utilities
from epub_to_analyzer import extract_epub_text
import tiktoken


# ============================================================================
# CONFIGURATION (Must match production corpus settings)
# ============================================================================

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
COLLECTION_NAME = "chess_production"
DB_PATH = "epub_analysis.db"
QDRANT_MODE = os.getenv('QDRANT_MODE', 'docker')  # 'docker' or 'local'
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
QDRANT_PATH = "./qdrant_production_db"
EPUB_DIR = "/Volumes/T7 Shield/books/epub"  # Fixed Nov 10, 2025 - was missing /books/

# Chunking parameters (MUST match build_production_corpus.py)
CHUNK_SIZE = 512  # tokens per chunk
CHUNK_OVERLAP = 64  # token overlap

# Embedding batch size
EMBED_BATCH_SIZE = 100

# Cost estimation
COST_PER_1M_TOKENS = 0.02


# ============================================================================
# BOOK SELECTION
# ============================================================================

def get_books_in_qdrant(qdrant_client: QdrantClient) -> Set[str]:
    """
    Get set of book names already in Qdrant.

    Returns:
        Set of book_name strings
    """
    print("   Scanning existing Qdrant collection...")

    # Get sample of points to see what books are already there
    scroll_result = qdrant_client.scroll(
        collection_name=COLLECTION_NAME,
        limit=10000,  # Sample first 10K chunks
        with_payload=True,
        with_vectors=False
    )

    books_in_db = set()
    for point in scroll_result[0]:
        if 'book_name' in point.payload:
            books_in_db.add(point.payload['book_name'])

    return books_in_db


def get_book_info(book_filename: str, db_path: str = DB_PATH) -> Dict:
    """
    Get book info from SQLite database.

    Args:
        book_filename: Just the filename (e.g., "dreev_2019_book.epub")

    Returns:
        Dict with filename, full_path, tier, score, word_count
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """
        SELECT filename, full_path, tier, score, word_count
        FROM epub_analysis
        WHERE filename = ?
        AND error IS NULL
    """

    cursor.execute(query, (book_filename,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'filename': row[0],
        'full_path': row[1],
        'tier': row[2],
        'score': row[3],
        'word_count': row[4]
    }


def resolve_book_paths(book_args: List[str], epub_dir: str = EPUB_DIR) -> List[str]:
    """
    Convert book arguments to full paths.

    Args:
        book_args: List of filenames or partial paths
        epub_dir: Base directory for EPUBs

    Returns:
        List of full paths to EPUB files
    """
    resolved = []

    for book_arg in book_args:
        # If it's already a full path, use it
        if Path(book_arg).exists():
            resolved.append(book_arg)
            continue

        # Try in epub_dir
        epub_path = Path(epub_dir) / book_arg
        if epub_path.exists():
            resolved.append(str(epub_path))
            continue

        print(f"⚠️  Warning: Book not found: {book_arg}")

    return resolved


# ============================================================================
# CHUNKING (Same as build_production_corpus.py)
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
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)

    chunks = []
    stride = chunk_size - overlap

    for i in range(0, len(tokens), stride):
        chunk_tokens = tokens[i:i + chunk_size]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text)

        if i + chunk_size >= len(tokens):
            break

    return chunks


def extract_chunks_from_book(book_path: str, book_metadata: Dict) -> List[Dict]:
    """
    Extract chunks from a single book.

    Returns:
        List of chunk dicts with text, metadata
    """
    try:
        text, error = extract_epub_text(book_path)

        if error or not text or not text.strip():
            return []

        chunks = chunk_text_by_tokens(
            text,
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP
        )

        if not chunks:
            return []

        all_chunks = []
        for chunk_idx, chunk_text in enumerate(chunks):
            chunk_data = {
                'text': chunk_text,
                'book_name': book_metadata['filename'],
                'book_path': book_metadata['full_path'],
                'book_tier': book_metadata['tier'],
                'book_score': book_metadata['score'],
                'chapter_title': book_metadata['filename'],
                'chapter_index': 0,
                'chunk_index': chunk_idx
            }
            all_chunks.append(chunk_data)

        return all_chunks

    except Exception as e:
        print(f"   ❌ Error extracting {book_metadata['filename']}: {e}")
        return []


# ============================================================================
# EMBEDDING
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
            response = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch_texts
            )

            for j, chunk in enumerate(batch):
                chunk_with_embedding = chunk.copy()
                chunk_with_embedding['embedding'] = response.data[j].embedding
                embedded_chunks.append(chunk_with_embedding)

            time.sleep(0.1)  # Rate limiting

        except Exception as e:
            print(f"\n❌ Error embedding batch {i}-{i+EMBED_BATCH_SIZE}: {e}")
            continue

    return embedded_chunks


# ============================================================================
# QDRANT OPERATIONS
# ============================================================================

def get_max_point_id(qdrant_client: QdrantClient) -> int:
    """
    Get the maximum point ID currently in Qdrant collection.

    Returns:
        Max ID, or -1 if collection is empty
    """
    try:
        # Scroll through collection to find max ID
        scroll_result = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=10000,
            with_payload=False,
            with_vectors=False
        )

        if not scroll_result[0]:
            return -1

        max_id = max(point.id for point in scroll_result[0])

        # Check if there are more points
        offset = scroll_result[1]
        while offset:
            scroll_result = qdrant_client.scroll(
                collection_name=COLLECTION_NAME,
                limit=10000,
                offset=offset,
                with_payload=False,
                with_vectors=False
            )

            if scroll_result[0]:
                batch_max = max(point.id for point in scroll_result[0])
                max_id = max(max_id, batch_max)

            offset = scroll_result[1]

        return max_id

    except Exception as e:
        print(f"   ⚠️  Warning: Could not determine max ID: {e}")
        return -1


def add_chunks_to_qdrant(qdrant_client: QdrantClient, chunks: List[Dict], start_id: int):
    """
    Add new chunks to existing Qdrant collection.

    Args:
        chunks: List of chunks with embeddings
        start_id: Starting ID for new points
    """
    print(f"   Adding {len(chunks)} chunks starting from ID {start_id}...")

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

    print(f"   ✅ Added {len(points)} chunks (IDs {start_id} to {start_id + len(points) - 1})")


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Main incremental addition pipeline."""
    parser = argparse.ArgumentParser(
        description='Add new books to existing Chess RAG corpus',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add specific books by filename
  python add_books_to_corpus.py dreev_2019_endgame.epub dreev_2018_middlegame.epub

  # Add using --books flag
  python add_books_to_corpus.py --books "book1.epub" "book2.epub" "book3.epub"

  # Add all books not yet in Qdrant
  python add_books_to_corpus.py --all-new

Note: OPENAI_API_KEY environment variable must be set
        """
    )

    parser.add_argument('books', nargs='*', help='Book filenames to add')
    parser.add_argument('--books', dest='books_flag', nargs='+', help='Book filenames (alternative syntax)')
    parser.add_argument('--all-new', action='store_true', help='Add all books not yet in Qdrant')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be added without actually adding')

    args = parser.parse_args()

    # Combine book arguments
    book_args = args.books or []
    if args.books_flag:
        book_args.extend(args.books_flag)

    if not book_args and not args.all_new:
        parser.print_help()
        return

    print("=" * 80)
    print("INCREMENTAL BOOK ADDITION TO CHESS RAG CORPUS")
    print("=" * 80)

    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set!")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        return

    # Initialize clients
    print("\n1️⃣  Initializing clients...")
    openai_client = OpenAI(api_key=api_key)

    if QDRANT_MODE == 'docker':
        qdrant_client = QdrantClient(url=QDRANT_URL)
        print(f"   Using Docker Qdrant at {QDRANT_URL}")
    else:
        qdrant_client = QdrantClient(path=QDRANT_PATH)
        print(f"   Using local Qdrant at {QDRANT_PATH}")

    # Check collection exists
    collections = qdrant_client.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        print(f"❌ Collection '{COLLECTION_NAME}' does not exist!")
        print(f"   Run build_production_corpus.py first to create the collection.")
        return

    # Get current corpus stats
    collection_info = qdrant_client.get_collection(COLLECTION_NAME)
    current_count = collection_info.points_count
    print(f"   ✅ Collection '{COLLECTION_NAME}' found")
    print(f"   Current chunks: {current_count:,}")

    # Get max ID
    print("\n2️⃣  Finding maximum point ID...")
    max_id = get_max_point_id(qdrant_client)
    next_id = max_id + 1
    print(f"   ✅ Max ID: {max_id:,}, next ID will be: {next_id:,}")

    # Determine which books to add
    print("\n3️⃣  Determining books to add...")

    if args.all_new:
        print("   Scanning for new books...")
        existing_books = get_books_in_qdrant(qdrant_client)
        print(f"   Found {len(existing_books)} books already in Qdrant")

        # Get all books from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM epub_analysis WHERE error IS NULL")
        all_books = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Find new books
        book_args = [b for b in all_books if b not in existing_books]
        print(f"   Found {len(book_args)} new books to add")

    # Resolve book paths
    book_paths = resolve_book_paths(book_args, EPUB_DIR)

    if not book_paths:
        print("❌ No valid books found to add!")
        return

    # Get book metadata
    books_to_add = []
    for book_path in book_paths:
        filename = Path(book_path).name
        book_info = get_book_info(filename, DB_PATH)

        if not book_info:
            print(f"   ⚠️  Warning: {filename} not in database, skipping")
            continue

        books_to_add.append(book_info)

    print(f"   ✅ Prepared {len(books_to_add)} books for addition")
    for book in books_to_add:
        print(f"      • {book['filename']} (score: {book['score']}, tier: {book['tier']})")

    # Estimate costs
    estimated_tokens = sum(b['word_count'] * 1.3 for b in books_to_add)
    estimated_cost = estimated_tokens / 1_000_000 * COST_PER_1M_TOKENS
    estimated_chunks = estimated_tokens / CHUNK_SIZE

    print(f"\n   Estimates:")
    print(f"   • Tokens: ~{estimated_tokens:,.0f}")
    print(f"   • Chunks: ~{estimated_chunks:,.0f}")
    print(f"   • Cost: ~${estimated_cost:.3f}")
    print(f"   • Time: ~{estimated_chunks / EMBED_BATCH_SIZE * 0.1 / 60:.1f} minutes")

    if args.dry_run:
        print("\n🏁 DRY RUN - No changes made")
        return

    # Extract chunks
    print(f"\n4️⃣  Extracting chunks from {len(books_to_add)} books...")
    all_chunks = []

    for book in tqdm(books_to_add, desc="Extracting", unit="book"):
        chunks = extract_chunks_from_book(book['full_path'], book)
        if chunks:
            all_chunks.extend(chunks)
            print(f"   • {book['filename']}: {len(chunks)} chunks")
        else:
            print(f"   ❌ {book['filename']}: extraction failed")

    if not all_chunks:
        print("❌ No chunks extracted, nothing to add!")
        return

    print(f"   ✅ Extracted {len(all_chunks):,} total chunks")

    # Generate embeddings
    print(f"\n5️⃣  Generating embeddings...")
    embedded_chunks = embed_chunks_batch(openai_client, all_chunks)
    print(f"   ✅ Generated {len(embedded_chunks):,} embeddings")

    # Add to Qdrant
    print(f"\n6️⃣  Adding to Qdrant collection...")
    add_chunks_to_qdrant(qdrant_client, embedded_chunks, next_id)

    # Verify
    print(f"\n7️⃣  Verifying addition...")
    final_info = qdrant_client.get_collection(COLLECTION_NAME)
    final_count = final_info.points_count
    added_count = final_count - current_count

    print(f"   ✅ Chunks before: {current_count:,}")
    print(f"   ✅ Chunks after: {final_count:,}")
    print(f"   ✅ Chunks added: {added_count:,}")

    # Summary
    print("\n" + "=" * 80)
    print("INCREMENTAL ADDITION COMPLETE")
    print("=" * 80)
    print(f"✅ Books added: {len(books_to_add)}")
    print(f"✅ Chunks added: {added_count:,}")
    print(f"✅ New corpus size: {final_count:,} chunks")
    print(f"✅ Collection: {COLLECTION_NAME}")
    print()
    print("Next steps:")
    print("1. Restart Flask server: pkill -f 'python.*app.py' && python app.py")
    print("2. Test queries on new book content")
    print("3. Verify new books appear in sources")
    print("=" * 80)


if __name__ == '__main__':
    main()
