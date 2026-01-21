import sqlite3
import os
import re
import json
import warnings
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Set

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import chess
import chess.pgn

# Suppress warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# CONFIG
DB_PATH = "/Volumes/T7 Shield/rag/databases/chess_text.db"
BOOKS_DIR = "/Volumes/T7 Shield/rag/books/epub"
VOCAB_PATH = Path(__file__).parent / "assets" / "coaching_vocab.json"
CHUNK_SIZE = 2500

@dataclass
class Chunk:
    text: str
    fen: str
    vocab_score: float
    prose_ratio: float
    is_instructional: bool
    diagrams: List[Tuple[str, str, bool]]  # (src, fen, needs_ocr)

class ChessBookParser:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.vocab = self._load_vocab()
        self.board = chess.Board()
        self._init_db()
        
    def _load_vocab(self) -> Dict[str, Dict[str, int]]:
        """Loads the weighted instructional vocabulary."""
        try:
            with open(VOCAB_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Warning: Could not load vocabulary ({e}). Scoring will be disabled.")
            return {}

    def _init_db(self):
        """Initializes the Graph-Ready Schema."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            c.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    book_id INTEGER PRIMARY KEY,
                    title TEXT,
                    author TEXT,
                    quality_score REAL,
                    processed_date TEXT
                )
            """)
            
            c.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id INTEGER PRIMARY KEY,
                    book_id INTEGER,
                    text_content TEXT,
                    fen TEXT,
                    quality_score REAL,
                    vocab_density REAL,
                    is_instructional BOOLEAN
                )
            """)
            
            c.execute("""
                CREATE TABLE IF NOT EXISTS diagrams (
                    diagram_id INTEGER PRIMARY KEY,
                    chunk_id INTEGER,
                    image_path TEXT,
                    fen TEXT,
                    is_ocr_based BOOLEAN DEFAULT 0
                )
            """)
            
            # FTS5 for full-text search
            try:
                c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(text_content, content='chunks', content_rowid='chunk_id')")
                c.execute("""
                    CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                        INSERT INTO chunks_fts(rowid, text_content) VALUES (new.chunk_id, new.text_content);
                    END;
                """)
            except:
                pass

    def process_book(self, epub_path: str) -> bool:
        """Main entry point for processing a single EPUB."""
        try:
            book = epub.read_epub(epub_path, options={'ignore_ncx': True})
            title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else Path(epub_path).stem
            author = book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else "Unknown"
            
            print(f"📖 Processing: {title}...")
            
            # Reset Board for new book
            self.board.reset()
            
            # --- IMAGE EXTRACTION ---
            # Extract images to a public directory for the frontend
            image_map = {} # package_path -> web_path
            output_img_dir = Path(__file__).parent / "frontend" / "public" / "diagrams"
            output_img_dir.mkdir(parents=True, exist_ok=True)
            
            for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
                ext = Path(item.file_name).suffix
                # Create a unique name based on book title and original filename
                safe_title = re.sub(r'\W+', '_', title).lower()
                safe_filename = re.sub(r'\W+', '_', Path(item.file_name).stem).lower()
                new_filename = f"{safe_title}_{safe_filename}{ext}"
                
                with open(output_img_dir / new_filename, 'wb') as f:
                    f.write(item.get_content())
                
                image_map[item.file_name] = f"/diagrams/{new_filename}"
            
            all_chunks = []
            
            # Iterate documents (chapters)
            for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                content = item.get_content()
                # Pass image_map to the parser so it can resolve package paths to web paths
                chunks = self._parse_chapter(content, image_map)
                all_chunks.extend(chunks)
            
            # Commit to DB
            self._save_book_data(title, author, all_chunks)
            return True
            
        except Exception as e:
            print(f"❌ Error processing {epub_path}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _parse_chapter(self, html_content: bytes, image_map: Dict[str, str]) -> List[Chunk]:
        """
        Stateful Parsing Logic:
        - Tokenizes stream: Prose <-> Moves <-> Images.
        - Updates self.board on valid moves.
        - Links images to current board state.
        """
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Current Chunk Builders
        current_text = []
        current_diagrams = [] # (src, fen, needs_ocr)
        current_fen = self.board.fen()
        
        chunks = []
        
        # We will iterate recursively or use a linear breakdown
        # For robustness, let's treat the body as a sequence of paragraphs and images
        
        elements = soup.find_all(['p', 'div', 'img', 'h1', 'h2', 'h3'])
        
        for el in elements:
            if el.name == 'img':
                # DIAGRAM FOUND
                src = el.get('src', '')
                if not src: continue
                
                # Resolve src using image_map
                # EPUB src might be '../images/foo.png' or 'images/foo.png' 
                # We need to find the match in image_map keys
                web_path = None
                for pkg_path, mapped_path in image_map.items():
                    if src.endswith(pkg_path) or pkg_path.endswith(src):
                        web_path = mapped_path
                        break
                
                if not web_path:
                    # Fallback: maybe it's a relative path we can semi-guess
                    web_path = f"/diagrams/{src.split('/')[-1]}"
                
                needs_ocr = (len(self.board.move_stack) == 0)
                current_diagrams.append((web_path, self.board.fen(), needs_ocr))
                
            else:
                # TEXT BLOCK (Prose or Moves)
                text = el.get_text().strip()
                if not text: continue
                
                # Tokenize and State-Update
                tokens = text.split()
                clean_tokens = []
                
                for token in tokens:
                    # Clean punctuation for move parsing (e.g. "e4," -> "e4")
                    clean_token = token.strip(".,;:?!()")
                    
                    # Try as move
                    try:
                        move = self.board.parse_san(clean_token)
                        self.board.push(move)
                        # It is a move! Add to text in standard notation?
                        # Or just keep raw token? Keep raw token for readability.
                        clean_tokens.append(token) 
                    except ValueError:
                        # Not a move (or ambiguous/illegal) -> Prose
                        clean_tokens.append(token)
                
                # Reassemble text line
                line = " ".join(clean_tokens)
                current_text.append(line)
                
                # Chunk boundary check
                current_len = sum(len(t) for t in current_text)
                if current_len >= CHUNK_SIZE:
                    chunk = self._finalize_chunk(current_text, current_diagrams, current_fen)
                    chunks.append(chunk)
                    
                    # Reset buffers
                    current_text = []
                    current_diagrams = []
                    # Update FEN for next chunk to current state
                    current_fen = self.board.fen()
        
        # Final flush
        if current_text or current_diagrams:
            chunk = self._finalize_chunk(current_text, current_diagrams, current_fen)
            chunks.append(chunk)
            
        return chunks

    def _finalize_chunk(self, text_lines: List[str], diagrams: List, start_fen: str) -> Chunk:
        full_text = "\n".join(text_lines)
        
        # SCORING
        # 1. Prose Ratio
        # Quick heuristic: Moves are typically short (2-4 chars). distinct words > 4 chars vs < 4?
        # Better: We rely on the vocab score mostly.
        
        # 2. Vocab Score
        vocab_score = self._calculate_vocab_score(full_text)
        
        # 3. Decision
        is_instructional = (vocab_score > 50.0) # Threshold from RFC
        
        return Chunk(
            text=full_text,
            fen=start_fen,
            vocab_score=vocab_score,
            prose_ratio=0.0, # Placeholder, can refine
            is_instructional=is_instructional,
            diagrams=diagrams[:]
        )

    def _calculate_vocab_score(self, text: str) -> float:
        """Weighted sum of instructional keywords per 1000 words."""
        if not self.vocab: return 0.0
        
        text_lower = text.lower()
        words = text_lower.split()
        if not words: return 0.0
        
        total_score = 0.0
        
        # Flatten vocab
        for category, terms in self.vocab.items():
            for term, weight in terms.items():
                # Simple substring match (could be optimized with regex)
                term_clean = term.replace("_", " ")
                count = text_lower.count(term_clean)
                total_score += count * weight
                
        # Normalize: Score per 1000 words
        per_1k = (total_score / len(words)) * 1000
        return min(per_1k, 100.0) # Cap at 100

    def _save_book_data(self, title: str, author: str, chunks: List[Chunk]):
        if not chunks: return
        
        # Avg Quality
        avg_quality = sum(c.vocab_score for c in chunks) / len(chunks)
        
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            
            c.execute("INSERT INTO books (title, author, quality_score, processed_date) VALUES (?, ?, ?, date('now'))",
                     (title, author, avg_quality))
            book_id = c.lastrowid
            
            for chunk in chunks:
                c.execute("""
                    INSERT INTO chunks (book_id, text_content, fen, quality_score, vocab_density, is_instructional)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (book_id, chunk.text, chunk.fen, chunk.vocab_score, chunk.vocab_score, chunk.is_instructional))
                chunk_table_id = c.lastrowid
                
                for src, d_fen, needs_ocr in chunk.diagrams:
                    c.execute("INSERT INTO diagrams (chunk_id, image_path, fen, is_ocr_based) VALUES (?, ?, ?, ?)",
                             (chunk_table_id, src, d_fen, needs_ocr))

def main():
    parser = ChessBookParser()
    print(f"📚 Book Parser Initialized. Vocab loaded with {len(parser.vocab)} categories.")
    
    # Simple CLI for now - process all in directory
    if os.path.exists(BOOKS_DIR):
        print(f"Scanning {BOOKS_DIR}...")
        for filename in os.listdir(BOOKS_DIR):
            if filename.endswith(".epub") and not filename.startswith("._"):
                path = os.path.join(BOOKS_DIR, filename)
                parser.process_book(path)
    else:
        print(f"Directory {BOOKS_DIR} not found. Create it and add .epub files.")

if __name__ == "__main__":
    main()
