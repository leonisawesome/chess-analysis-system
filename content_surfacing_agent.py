import sqlite3
import re
import uuid
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from chess_positions import extract_chess_positions

# DEFAULT EXTERNAL PATH
DEFAULT_DB_PATH = "/Volumes/T7 Shield/rag/databases/chess_text.db"

class ContentSurfacingAgent:
    """
    RAG Agent for retrieving and synthesizing chess knowledge.
    Includes robust FTS5 searching and multi-provider (Gemini/OpenAI) fallback logic.
    """
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._validate_db()

    def _validate_db(self):
        if not Path(self.db_path).exists():
            # Fallback to local data dir if external not found (for portability check)
            local_path = Path(__file__).parent / "data" / "chess_text.db"
            if local_path.exists():
                self.db_path = str(local_path)
            else:
                print(f"⚠️  Knowledge Bank not found at {self.db_path}. Search will fail.")

    def search_library(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Searches the Knowledge Bank using FTS5 with robust filtering and deduplication.
        """
        if not Path(self.db_path).exists():
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            
            # Sanitize query for FTS5
            safe_query = "".join(c for c in query if c.isalnum() or c.isspace() or c == '"' or c == '-')
            
            # Stop words to prevent restrictive ANDs on "instructional" fluff
            stop_words = {
                "the", "is", "what", "who", "where", "how", "when", "a", "an", "in", "on", "of", "to", "for", "with", "by", "from", "about",
                "tell", "me", "show", "give", "explain", "please", "can", "you", "does", "do", "did", "which", "are",
                "key", "concepts", "ideas", "topics", "essential", "main", "principle", "principles"
            }
            terms = [t for t in safe_query.split() if t.replace('-', '').isalnum() or t.startswith('"')]
            filtered_terms = [t for t in terms if t.lower() not in stop_words]
            
            if not filtered_terms:
                return []

            # Stage 1: Try Phrase Search + AND
            quoted_terms = ['"' + t.replace('"', '') + '"' for t in filtered_terms]
            strict_query = " AND ".join(quoted_terms)
            clean_terms = [t.replace('"', '') for t in filtered_terms]
            phrase_query = f'"{ " ".join(clean_terms) }"'
            
            final_query = f'{phrase_query} OR {strict_query}'
            if '"' in safe_query:
                final_query = safe_query
            
            # Filter noise chunks (indices, etc.)
            filter_keywords = ['%index%', '%bibliography%', '%contents%', '%about the author%', '%game list%']
            filter_clause = " AND ".join([f"(d.title NOT LIKE '{k}' AND d.chapter NOT LIKE '{k}')" for k in filter_keywords])

            def execute_search(q):
                internal_limit = limit * 8
                c.execute(f"""
                    SELECT 
                        d.title, d.chapter, d.content, d.source_type,
                        snippet(knowledge_fts, 2, '**', '**', '...', 160) as snippet,
                        f.rank
                    FROM knowledge_fts f
                    JOIN knowledge_docs d ON f.rowid = d.doc_id
                    WHERE knowledge_fts MATCH ? 
                    AND ({filter_clause})
                    ORDER BY f.rank 
                    LIMIT ?
                """, (q, internal_limit))
                return c.fetchall()

            rows = execute_search(final_query)
            
            # Fallback to OR Search if zero results
            if not rows and len(filtered_terms) > 1:
                fallback_query = " OR ".join(quoted_terms)
                rows = execute_search(fallback_query)

            results = []
            
            # Content-based noise patterns
            NOISE_PREFIXES = ['index of', 'index (', 'bibliography', 'copyright', 'contents', 'preface']
            
            for row in rows:
                full_content = row['content']
                content_lower = full_content[:100].lower().strip()
                if any(content_lower.startswith(prefix) for prefix in NOISE_PREFIXES):
                    continue
                
                # Deduplication logic
                is_duplicate = False
                # Simple check: compare titles and first 100 chars
                for existing in results:
                    if existing['title'] == row['title'] and existing['content'][:100] == full_content[:100]:
                        is_duplicate = True
                        break
                if is_duplicate:
                    continue

                results.append({
                    "title": row['title'],
                    "chapter": row['chapter'],
                    "content": full_content,
                    "snippet": row['snippet'],
                    "score": round(row['rank'], 2),
                    "source_type": row['source_type']
                })
                
                if len(results) >= limit:
                    break
            
            return results
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()

    def answer_question(self, query: str, gemini_key: str, openai_key: str = None, results: Optional[List[Dict]] = None) -> Tuple[str, List[Dict]]:
        """
        Synthesizes a high-value answer.
        FALLBACK: If Gemini fails (429), it automatically attempts ChatGPT (OpenAI) if the key is provided.
        """
        if results is None:
            results = self.search_library(query, limit=12)
            
        if not results:
            return "I could not find any relevant information in your library.", []

        # 1. Prepare Diagrams
        diagram_map = {}
        diagram_list = []
        for res in results:
            found_positions = extract_chess_positions(res.get('content', ''), query=query)
            for pos in found_positions:
                fen = pos['fen']
                if fen not in diagram_map:
                    diag_id = str(uuid.uuid4())
                    diagram_map[fen] = diag_id
                    diagram_list.append({
                        'id': diag_id, 'fen': fen, 
                        'title': res['title'], 'caption': pos.get('caption', f"Position from: {res['title']}")
                    })

        # 2. Build Prompt
        context_str = ""
        diagram_instructions = ""
        if diagram_list:
            diagram_instructions = "\nAVAILABLE INTERACTIVE DIAGRAMS (Insert [DIAGRAM_ID:UUID] to render):\n"
            for d in diagram_list:
                diagram_instructions += f"- [DIAGRAM_ID:{d['id']}] : {d['title']}\n"

        for i, res in enumerate(results):
            context_str += f"SOURCE {i}: [{res['title']}] ({res['chapter']})\n{res['content']}\n\n"

        system_instruction = (
            "You are a World-Class Grandmaster Chess Coach. Provide a detailed, Masterclass-level lesson. "
            "CITATIONS MANDATORY: Use [Source X] format. "
            "DIAGRAMS MANDATORY: Insert [DIAGRAM_ID:UUID] tags to illustrate key positions."
        )
        full_prompt = f"Context:\n{context_str}\n{diagram_instructions}\n\nQuestion: {query}"

        # 3. Execution with Fallback Logic
        print(f"  [Agent] Attempting Gemini synthesis...")
        answer, diag_out = self._call_gemini(full_prompt, system_instruction, gemini_key, diagram_list)
        
        # Check for failure / 429
        if "rate limit" in answer.lower() or "error" in answer.lower():
            if openai_key:
                print(f"  [Agent] ⚠️ Gemini failed or limited. Falling back to OpenAI (GPT-4o)...")
                answer, diag_out = self._call_openai(full_prompt, system_instruction, openai_key, diagram_list)
            else:
                print(f"  [Agent] ❌ Gemini failed and NO OpenAI key available.")
        
        return answer, diag_out

    def _call_gemini(self, prompt: str, system_instruction: str, api_key: str, diagram_list: List[Dict]) -> Tuple[str, List[Dict]]:
        import time
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt,
                config=genai.types.GenerateContentConfig(system_instruction=system_instruction)
            )
            return response.text, diagram_list
        except Exception as e:
            return f"Gemini Error: {e}", []

    def _call_openai(self, prompt: str, system_instruction: str, api_key: str, diagram_list: List[Dict]) -> Tuple[str, List[Dict]]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content, diagram_list
        except Exception as e:
            return f"OpenAI Error: {e}", []

if __name__ == "__main__":
    # Diagnostic test
    agent = ContentSurfacingAgent()
    print(f"Library Search Test (Isolation):")
    hits = agent.search_library("Isolated Queen Pawn")
    for hit in hits[:2]:
        print(f" - {hit['title']} ({hit['chapter']})")
