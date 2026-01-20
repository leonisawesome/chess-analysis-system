import sqlite3
from pathlib import Path
from typing import List, Dict, Optional

class ContentSurfacingAgent:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._validate_db()

    def _validate_db(self):
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Knowledge Bank not found at {self.db_path}")

    def search_library(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Searches the Knowledge Bank using FTS5.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            
            # Sanitize query for FTS5 (preserve quotes for phrase searching)
            safe_query = "".join(c for c in query if c.isalnum() or c.isspace() or c == '"')
            
            # Simple stop word removal to improve FTS relevance (don't remove if inside quotes)
            stop_words = {
                "the", "is", "what", "who", "where", "how", "when", "a", "an", "in", "on", "of", "to", "for", "with", "by", "from", "about",
                "tell", "me", "show", "give", "explain", "please", "can", "you", "does", "do", "did", "which", "are", "about"
            }
            terms = safe_query.split()
            filtered_terms = [t for t in terms if t.lower() not in stop_words or t.startswith('"')]
            
            if filtered_terms:
                safe_query_clean = " ".join(filtered_terms).replace('"', '')
                # If the user didn't use quotes, apply phrase boosting
                if '"' not in safe_query:
                    final_query = f'"{safe_query_clean}" OR {safe_query_clean}'
                else:
                    final_query = safe_query
            else:
                final_query = safe_query
            
            # Exclude chunks that are just indices, bibliographies, or game lists to improve RAG quality
            # These are common in digital books and waste valuable context slots.
            filter_keywords = [
                '%index%', '%bibliography%', '%contents%', '%about the author%', 
                '%game list%', '%license%', '%copyright%', '%preface%'
            ]
            filter_clause = " AND ".join([f"title NOT LIKE '{k}' AND chapter NOT LIKE '{k}'" for k in filter_keywords])

            c.execute(f"""
                SELECT 
                    title, 
                    chapter, 
                    content,
                    snippet(knowledge_fts, 2, '**', '**', '...', 160) as snippet,
                    rank
                FROM knowledge_fts 
                WHERE knowledge_fts MATCH ? 
                AND ({filter_clause})
                ORDER BY rank 
                LIMIT ?
            """, (final_query, limit))
            
            results = []
            import re
            # Basic FEN (approximate) - broadened to catch more diagrams
            fen_pattern = re.compile(r'\b([rnbqkBNQKR1-8]{1,8}/){7}[rnbqkBNQKR1-8]{1,8} [w b] [KQkq-]{1,4} [a-h0-9-]{1,2}\b')
            
            for row in c.fetchall():
                full_content = row['content']
                snippet_text = row['snippet']
                match = fen_pattern.search(full_content)
                fen = match.group(0) if match else None
                
                results.append({
                    "title": row['title'],
                    "chapter": row['chapter'],
                    "content": full_content,
                    "snippet": snippet_text,
                    "score": round(row['rank'], 2),
                    "fen": fen
                })
            return results
        except sqlite3.OperationalError as e:
            print(f"Search Error: {e}")
            return []
        finally:
            conn.close()

    def get_full_content(self, title: str) -> Optional[str]:
        """ Retrieves full content of a specific book/game. """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT content FROM knowledge_docs WHERE title = ?", (title,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def get_stats(self) -> dict:
        """Returns counts of indexed items."""
        stats = {
            'epubs': 0,
            'pgn_games': 0,
            'chunks': 0
        }
        conn = None # Initialize conn to None
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Count PGN Games
            c.execute("SELECT count(*) FROM knowledge_docs WHERE source_type='pgn_game'")
            stats['pgn_games'] = c.fetchone()[0]

            # Count EPUBs (Books) and Chunks
            c.execute("SELECT count(DISTINCT source_name), count(*) FROM knowledge_docs WHERE source_type='epub'")
            res = c.fetchone()
            stats['epubs'] = res[0]
            stats['chunks'] = res[1]
        except Exception as e:
            print(f"Stats Error: {e}")
        finally:
            if conn:
                conn.close()
        return stats

    def answer_question(self, query: str, api_key: str, results: Optional[List[Dict]] = None) -> str:
        """
        Synthesizes a high-value answer using Gemini 2.0 based on retrieved context.
        """
        # 1. Retrieve Context if not provided
        if results is None:
            results = self.search_library(query, limit=15)
            
        if not results:
            return "I could not find any relevant information in the library."

        # 2. Build Prompt
        context_str = ""
        for i, res in enumerate(results, 1):
            # Use full content but truncate slightly to avoid overwhelming context if many results
            # Gemini has a huge window but let's keep it focused.
            text = res['content']
            if len(text) > 8000:
                text = text[:8000] + "..."
            context_str += f"SOURCE {i}: [{res['title']}] ({res['chapter']})\n{text}\n\n"

        system_instruction = (
            "You are a Grandmaster-level Chess Coach. "
            "Analyze the provided source material to provide a COMPREHENSIVE, LONG-FORM, IN-DEPTH LESSON on the user's topic. "
            "Aim for a detailed reference-style article (600-1000+ words) if the context is rich enough. "
            "Include specific variations (moves), strategic plans, and deep positional evaluations found in the text. "
            "CITATIONS ARE MANDATORY: Every single claim, variation, or strategic idea must be cited using [Source X] format. "
            "If the sources provide conflicting advice or different variations, explain the nuances and trade-offs. "
            "If the sources provide actual move sequences (PGN), break them down into a clear move-by-move explanation with coaching commentary. "
            "Structure your answer with clear, bold headings (e.g., **The Main Strategic Idea**, **Key Variations and Theory**, **Common Pitfalls**). "
            "Important: Use ONLY the provided sources. Do not hallucinate outside move theory."
        )
        
        full_prompt = f"Context:\n{context_str}\n\nUser Question: {query}\n\nDetailed Analysis and Coaching:"

        # 3. Call Gemini
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=full_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction
                )
            )
            return response.text
        except Exception as e:
            return f"Error generating answer: {e}"

if __name__ == "__main__":
    # Test
    db_path = "/Volumes/T7 Shield/rag/databases/chess_text.db"
    agent = ContentSurfacingAgent(db_path)
    
    print("\n--- Testing Search 'Isolated Queen Pawn' ---")
    hits = agent.search_library("isolated queen pawn")
    for hit in hits:
        print(f"[{hit['title']}] {hit['chapter']}\n{hit['snippet']}\n")
