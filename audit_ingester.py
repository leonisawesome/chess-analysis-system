import sqlite3
import os
from epub_ingester import ChessBookParser

def audit():
    db_path = "/Volumes/T7 Shield/rag/databases/chess_text.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    parser = ChessBookParser(db_path=db_path)
    
    test_books = [
        # 1. Instructional (Move by Move)
        "/Volumes/T7 Shield/rag/books/epub/Collins, Sam - Karpov. Move by Move [Everyman, 2015].epub",
        # 2. Opening Repertoire (Data Dense)
        "/Volumes/T7 Shield/rag/books/epub/Demuth, Adrien - The Modernized Dutch Defence [Thinkers, 2019].epub",
        # 3. Tactics/Puzzles (Less prose)
        "/Volumes/T7 Shield/rag/books/epub/Drill Your Chess Strategy! 2 - Miloje Ratkovic, Milovan Ratkovic and Petar Ratkovic.epub"
    ]
    
    print("\n🔍 STARTING INGESTION AUDIT...\n")
    
    for book_path in test_books:
        if os.path.exists(book_path):
            parser.process_book(book_path)
        else:
            print(f"❌ Missing test book: {book_path}")

    # Inspect Results
    print("\n📊 AUDIT RESULTS\n" + "="*80)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        books = c.execute("SELECT * FROM books").fetchall()
        for b in books:
            print(f"\n📖 BOOK: {b['title']}")
            print(f"   Quality Score: {b['quality_score']:.2f}/100")
            
            # Chunks
            chunks = c.execute("SELECT count(*) as count, avg(quality_score) as avg_q, sum(is_instructional) as inst FROM chunks WHERE book_id=?", (b['book_id'],)).fetchone()
            print(f"   Chunks: {chunks['count']} (Avg Quality: {chunks['avg_q']:.2f}, High-Value: {chunks['inst']})")
            
            # Diagrams
            diagrams = c.execute("SELECT count(*) as count, sum(is_ocr_based) as ocr FROM diagrams d JOIN chunks c ON d.chunk_id = c.chunk_id WHERE c.book_id=?", (b['book_id'],)).fetchone()
            print(f"   Diagrams: {diagrams['count']} (OCR Fallback: {diagrams['ocr']})")
            
            # FEN Progression Check
            fen_sequence = c.execute("SELECT fen FROM chunks WHERE book_id=? ORDER BY chunk_id LIMIT 10", (b['book_id'],)).fetchall()
            fens = [f['fen'] for f in fen_sequence]
            unique_fens = len(set(fens))
            print(f"   FEN Progression: {unique_fens} unique states in first 10 chunks")
            
            # Middle-Book Sample (Skip first 20 chunks to avoid TOC/Symbols)
            sample = c.execute("""
                SELECT text_content, quality_score, fen FROM chunks 
                WHERE book_id=? AND is_instructional=1 
                LIMIT 1 OFFSET 30
            """, (b['book_id'],)).fetchone()
            if sample:
                print(f"   Middle-Book Sample (Score {sample['quality_score']:.1f}):")
                print(f"   FEN: {sample['fen']}")
                clean_sample = sample['text_content'][:300].replace('\n', ' ')
                print(f"   > {clean_sample}...")
            else:
                print("   ⚠️ No middle-book instructional samples found.")

if __name__ == "__main__":
    audit()
