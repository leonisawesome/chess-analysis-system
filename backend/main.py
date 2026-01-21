from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import chess
import os

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Chess Coach API", description="Backend for the AI Chess Coach")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. Restricted in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DB_PATH = "/Volumes/T7 Shield/rag/databases/chess_text.db"

class DiagramResponse(BaseModel):
    image_path: str
    fen: str
    is_ocr_based: bool

class ChunkResponse(BaseModel):
    chunk_id: int
    book_title: str
    text: str
    fen: str
    quality_score: float
    is_instructional: bool
    diagrams: List[DiagramResponse] = []

class SearchResult(BaseModel):
    results: List[ChunkResponse]
    total: int

def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database not found")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_diagrams(cursor, chunk_id):
    query = "SELECT image_path, fen, is_ocr_based FROM diagrams WHERE chunk_id = ?"
    rows = cursor.execute(query, (chunk_id,)).fetchall()
    return [DiagramResponse(image_path=r['image_path'], fen=r['fen'], is_ocr_based=bool(r['is_ocr_based'])) for r in rows]

@app.get("/health")
def health_check():
    return {"status": "healthy", "database": os.path.exists(DB_PATH)}

@app.get("/search/fen", response_model=SearchResult)
def search_by_fen(fen: str, limit: int = 10):
    try:
        board = chess.Board(fen)
        clean_fen = board.fen()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT c.chunk_id, b.title, c.text_content, c.fen, c.quality_score, c.is_instructional
                FROM chunks c
                JOIN books b ON c.book_id = b.book_id
                WHERE c.fen = ?
                ORDER BY c.quality_score DESC
                LIMIT ?
            """
            rows = cursor.execute(query, (clean_fen, limit)).fetchall()
            results = []
            for row in rows:
                diagrams = fetch_diagrams(cursor, row['chunk_id'])
                results.append(ChunkResponse(
                    chunk_id=row['chunk_id'],
                    book_title=row['title'],
                    text=row['text_content'],
                    fen=row['fen'],
                    quality_score=row['quality_score'],
                    is_instructional=bool(row['is_instructional']),
                    diagrams=diagrams
                ))
            return SearchResult(results=results, total=len(results))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid FEN string")

@app.get("/search/concept", response_model=SearchResult)
def search_by_concept(query: str, limit: int = 10):
    fillers = {"tell", "me", "about", "the", "a", "an", "what", "is"}
    words = [w for w in query.lower().split() if w not in fillers]
    if not words: words = query.split()
    fts_query = " ".join(words)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        sql_query = """
            SELECT c.chunk_id, b.title, c.text_content, c.fen, c.quality_score, c.is_instructional
            FROM chunks_fts f
            JOIN chunks c ON f.rowid = c.chunk_id
            JOIN books b ON c.book_id = b.book_id
            WHERE chunks_fts MATCH ?
            ORDER BY bm25(chunks_fts), c.quality_score DESC
            LIMIT ?
        """
        try:
            print(f"DEBUG: Searching FTS5 for '{fts_query}'")
            rows = cursor.execute(sql_query, (fts_query, limit)).fetchall()
            if not rows:
                print("DEBUG: FTS5 returned no results. Falling back to LIKE.")
                like_query = f"%{query}%"
                sql_fallback = """
                    SELECT c.chunk_id, b.title, c.text_content, c.fen, c.quality_score, c.is_instructional
                    FROM chunks c
                    JOIN books b ON c.book_id = b.book_id
                    WHERE c.text_content LIKE ?
                    LIMIT ?
                """
                rows = cursor.execute(sql_fallback, (like_query, limit)).fetchall()
        except sqlite3.OperationalError as e:
            print(f"DEBUG: FTS5 Error: {e}. Falling back to basic LIKE.")
            rows = cursor.execute(sql_fallback, (f"%{query}%", limit)).fetchall()
        
        print(f"DEBUG: Found {len(rows)} results")
        results = []
        for row in rows:
            diagrams = fetch_diagrams(cursor, row['chunk_id'])
            results.append(ChunkResponse(
                chunk_id=row['chunk_id'],
                book_title=row['title'],
                text=row['text_content'],
                fen=row['fen'],
                quality_score=row['quality_score'],
                is_instructional=bool(row['is_instructional']),
                diagrams=diagrams
            ))
        return SearchResult(results=results, total=len(results))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
