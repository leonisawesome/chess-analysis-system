#!/usr/bin/env python3
"""
Validation Chunker for Chess RAG System
Extracts and chunks 5 test books for validation testing.
"""

import json
import re
import uuid
from pathlib import Path
from typing import List, Dict
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import tiktoken

from figurine_normalizer import normalize_figurines


# Target tokens per chunk (roughly 750-1250 words)
TARGET_TOKENS = 1000
MIN_TOKENS = 500
MAX_TOKENS = 1500


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count tokens using tiktoken."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def extract_chapters_from_epub(epub_path: str) -> List[Dict]:
    """
    Extract chapters from EPUB using HTML structure.

    Returns:
        List of dicts with {title, content, order}
    """
    try:
        book = epub.read_epub(epub_path)
        chapters = []
        order = 0

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Parse HTML
                soup = BeautifulSoup(item.get_content(), 'html.parser')

                # Look for chapter title in h1, h2, or title tags
                title = None
                for tag in ['h1', 'h2', 'title']:
                    title_elem = soup.find(tag)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break

                if not title:
                    title = f"Chapter {order + 1}"

                # Extract text
                text = soup.get_text(separator='\n', strip=True)

                # Apply figurine normalization
                text = normalize_figurines(text)

                # Skip very short chapters (likely copyright, TOC, etc.)
                if len(text.split()) < 100:
                    continue

                chapters.append({
                    'title': title,
                    'content': text,
                    'order': order
                })
                order += 1

        return chapters

    except Exception as e:
        print(f"Error extracting chapters: {e}")
        return []


def chunk_chapter(chapter_text: str, chapter_title: str, max_tokens: int = MAX_TOKENS) -> List[str]:
    """
    Split a chapter into chunks of ~TARGET_TOKENS.

    Strategy:
    1. Split by paragraphs (double newline)
    2. Combine paragraphs until reaching target tokens
    3. Include chapter title context in each chunk
    """
    paragraphs = chapter_text.split('\n\n')
    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_tokens = count_tokens(para)

        # If single paragraph exceeds max, split by sentences
        if para_tokens > max_tokens:
            sentences = re.split(r'([.!?])\s+', para)
            for i in range(0, len(sentences), 2):
                if i + 1 < len(sentences):
                    sentence = sentences[i] + sentences[i + 1]
                else:
                    sentence = sentences[i]

                sent_tokens = count_tokens(sentence)

                if current_tokens + sent_tokens > max_tokens and current_chunk:
                    # Save current chunk
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append(chunk_text)
                    current_chunk = [sentence]
                    current_tokens = sent_tokens
                else:
                    current_chunk.append(sentence)
                    current_tokens += sent_tokens
        else:
            # Normal paragraph handling
            if current_tokens + para_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(chunk_text)
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens

    # Add remaining content
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        chunks.append(chunk_text)

    return chunks


def process_book(epub_path: str, book_short_name: str) -> List[Dict]:
    """
    Process a single book into chunks with metadata.

    Returns:
        List of chunk dicts with metadata
    """
    print(f"\n📖 Processing: {book_short_name}")
    print(f"   Path: {epub_path}")

    # Extract chapters
    chapters = extract_chapters_from_epub(epub_path)
    print(f"   Extracted {len(chapters)} chapters")

    all_chunks = []
    chunk_index = 0

    for chapter in chapters:
        chapter_title = chapter['title']
        chapter_content = chapter['content']
        chapter_order = chapter['order']

        # Chunk the chapter
        chunks = chunk_chapter(chapter_content, chapter_title)

        # Create metadata for each chunk
        for i, chunk_text in enumerate(chunks):
            chunk_dict = {
                'chunk_id': str(uuid.uuid4()),
                'doc_id': book_short_name,
                'book_name': book_short_name,
                'chapter_title': chapter_title,
                'chapter_order': chapter_order,
                'chunk_index': chunk_index,
                'chunk_within_chapter': i,
                'text': chunk_text,
                'token_count': count_tokens(chunk_text),
                'word_count': len(chunk_text.split())
            }
            all_chunks.append(chunk_dict)
            chunk_index += 1

    print(f"   Created {len(all_chunks)} chunks")
    print(f"   Avg tokens/chunk: {sum(c['token_count'] for c in all_chunks) / len(all_chunks):.0f}")

    return all_chunks


def process_all_validation_books() -> List[Dict]:
    """Process all 5 validation books."""

    # Load book list
    books = [
        {
            'filename': 'lakdawala_2016_first_steps_the_french_everyman.epub',
            'short_name': 'french_defense',
            'category': 'opening'
        },
        {
            'filename': 'unknown_author_2015_jesus_de_la_villa_100_endgames_you_must_know_vital_lessons_for_every_chess_player_improved_and_expanded_new_in_chess.epub',
            'short_name': '100_endgames',
            'category': 'endgame'
        },
        {
            'filename': 'antonio_2017_fundamental_chess_tactics_gambit_publications.epub',
            'short_name': 'fundamental_tactics',
            'category': 'tactics'
        },
        {
            'filename': 'soltis_2021_500_chess_questions_answered_batsford.epub',
            'short_name': '500_questions',
            'category': 'general'
        },
        {
            'filename': 'capablanca_2016_chess_fundamentals_anboco.epub',
            'short_name': 'chess_fundamentals',
            'category': 'general'
        }
    ]

    base_path = Path("/Volumes/T7 Shield/epub/")
    all_chunks = []

    print("=" * 80)
    print("VALIDATION CHUNKING - SYSTEM A")
    print("=" * 80)

    for book in books:
        epub_path = base_path / book['filename']

        if not epub_path.exists():
            print(f"\n❌ Book not found: {book['filename']}")
            continue

        chunks = process_book(str(epub_path), book['short_name'])

        # Add category to each chunk
        for chunk in chunks:
            chunk['category'] = book['category']

        all_chunks.extend(chunks)

    # Save all chunks to JSON
    output_path = 'validation_chunks.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 80)
    print("CHUNKING SUMMARY")
    print("=" * 80)
    print(f"Total books processed: {len(books)}")
    print(f"Total chunks created: {len(all_chunks)}")
    print(f"Output saved to: {output_path}")

    # Stats by category
    from collections import Counter
    category_counts = Counter(c['category'] for c in all_chunks)
    print("\nChunks by category:")
    for cat, count in category_counts.items():
        print(f"   {cat:12s}: {count:4d} chunks")

    # Token stats
    tokens = [c['token_count'] for c in all_chunks]
    print(f"\nToken statistics:")
    print(f"   Min:  {min(tokens):4d} tokens")
    print(f"   Max:  {max(tokens):4d} tokens")
    print(f"   Avg:  {sum(tokens) / len(tokens):6.1f} tokens")
    print(f"   Total: {sum(tokens):,} tokens")

    print("=" * 80)

    return all_chunks


if __name__ == '__main__':
    chunks = process_all_validation_books()
