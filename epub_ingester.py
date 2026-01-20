import sqlite3
import os
import re
from pathlib import Path
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import warnings

# Suppress ebooklib warnings about future versions
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# CONFIG
DB_PATH = "/Volumes/T7 Shield/rag/databases/chess_text.db"
BOOKS_DIR = "/Volumes/T7 Shield/rag/books"
CHUNK_SIZE = 2500  # Target characters per chunk
CHUNK_OVERLAP = 200

def init_db():
    """Initializes the SQLite Knowledge Bank with FTS5."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Standard table for relational lookups
    c.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_docs (
            doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            chapter TEXT,
            content TEXT,
            source_type TEXT,
            source_name TEXT,
            chunk_index INTEGER
        )
    """)
    
    # FTS5 virtual table for lightning-fast search
    try:
        c.execute("CREATE VIRTUAL TABLE knowledge_fts USING fts5(title, chapter, content, content='knowledge_docs', content_rowid='doc_id')")
    except sqlite3.OperationalError:
        print("FTS5 table already exists or error.")
        
    # Triggers to keep FTS5 in sync
    c.execute("""
        CREATE TRIGGER IF NOT EXISTS bu AFTER INSERT ON knowledge_docs BEGIN
            INSERT INTO knowledge_fts(rowid, title, chapter, content) VALUES (new.doc_id, new.title, new.chapter, new.content);
        END;
    """)
    
    conn.commit()
    conn.close()

def clean_html(html_content):
    """Cleans HTML and returns plain text, preserving some structure."""
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.extract()

    # Find headers and mark them for chunking
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        h.insert_before("---CH_HEADER---")
        h.insert_after("---CH_HEADER---")

    text = soup.get_text()
    
    # Collapse multiple whitespaces
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("   "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text

def chunk_text(text, title, chapter_name):
    """Semantic chunking of text."""
    # Split by the header markers we added
    raw_sections = text.split("---CH_HEADER---")
    sections = [s.strip() for s in raw_sections if s.strip()]
    
    final_chunks = []
    current_chapter = chapter_name
    
    for section in sections:
        # If the section is very short, it might be a header we just extracted
        if len(section) < 100 and section in text:
            current_chapter = section
            continue
            
        # Recursive chunking for long sections
        if len(section) > CHUNK_SIZE:
            words = section.split()
            current_chunk = []
            chunk_len = 0
            for word in words:
                current_chunk.append(word)
                chunk_len += len(word) + 1
                if chunk_len >= CHUNK_SIZE:
                    final_chunks.append({
                        "header": current_chapter,
                        "content": " ".join(current_chunk)
                    })
                    # Keep some overlap
                    overlap_words = current_chunk[-30:] # ~200 chars
                    current_chunk = overlap_words
                    chunk_len = sum(len(w) + 1 for w in overlap_words)
            if current_chunk:
                final_chunks.append({
                    "header": current_chapter,
                    "content": " ".join(current_chunk)
                })
        else:
            final_chunks.append({
                "header": current_chapter,
                "content": section
            })
            
    return final_chunks

def process_epub(file_path):
    """Extracts, cleans, and chunks content from a single EPUB."""
    try:
        book = epub.read_epub(file_path)
        title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else os.path.basename(file_path)
        print(f"  📖 Processing: {title}")
        
        all_content = []
        chunk_count = 0
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                html = item.get_content()
                text = clean_html(html)
                
                # Use filename of item as fallback chapter name
                chapter_name = item.get_name()
                
                chunks = chunk_text(text, title, chapter_name)
                for c in chunks:
                    all_content.append({
                        "title": title,
                        "chapter": c['header'],
                        "content": c['content'],
                        "source_type": "epub",
                        "source_name": os.path.basename(file_path),
                        "chunk_index": chunk_count
                    })
                    chunk_count += 1
        return all_content
    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return []

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit number of books to process")
    args = parser.parse_args()

    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get list of .epub files
    epub_files = list(Path(BOOKS_DIR).rglob("*.epub"))
    print(f"Found {len(epub_files)} EPUB files.")
    
    if args.limit:
        epub_files = epub_files[:args.limit]
        print(f"Limiting to first {args.limit} books.")
    
    total_chunks = 0
    for i, file_path in enumerate(epub_files):
        print(f"[{i+1}/{len(epub_files)}] {file_path.name}")
        
        # Check if already processed (simple filename check)
        c.execute("SELECT count(*) FROM knowledge_docs WHERE source_name = ?", (file_path.name,))
        if c.fetchone()[0] > 0:
            print("  ⏩ Already indexed. Skipping.")
            continue
            
        chunks = process_epub(str(file_path))
        if chunks:
            c.executemany("""
                INSERT INTO knowledge_docs (title, chapter, content, source_type, source_name, chunk_index)
                VALUES (:title, :chapter, :content, :source_type, :source_name, :chunk_index)
            """, chunks)
            conn.commit()
            total_chunks += len(chunks)
            print(f"  ✅ Added {len(chunks)} chunks.")
            
    conn.close()
    print(f"\nDone! Added a total of {total_chunks} new chunks to the Knowledge Bank.")

if __name__ == "__main__":
    main()
