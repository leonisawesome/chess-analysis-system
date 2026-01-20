import os
import time
import threading
from flask import Flask, render_template, request, jsonify, send_file, abort
from content_surfacing_agent import ContentSurfacingAgent
from diagram_service import diagram_index

# Phase 6.1a: Static EPUB diagram integration
METADATA_PATH = "diagram_metadata_full.json"

def load_diagram_index():
    if os.path.exists(METADATA_PATH):
        print(f"📊 [BACKGROUND] Loading heavy diagram index ({METADATA_PATH})...")
        start = time.time()
        diagram_index.load(METADATA_PATH)
        print(f"✅ [BACKGROUND] Diagram index loaded in {time.time() - start:.2f}s")
    else:
        print(f"⚠️ [BACKGROUND] {METADATA_PATH} not found. Static book diagrams will be unavailable.")

# Start background load
threading.Thread(target=load_diagram_index, daemon=True).start()

from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import chess
import chess.svg
from chess_positions import clean_caption

# Configuration
DB_PATH = "/Volumes/T7 Shield/rag/databases/chess_text.db"
app = Flask(__name__)

# Initialize Agent
print(f"🔌 Connecting to Knowledge Bank at {DB_PATH}...")
try:
    agent = ContentSurfacingAgent(DB_PATH)
    print("✅ Knowledge Bank Connected.")
except Exception as e:
    print(f"❌ Failed to connect to DB: {e}")
    agent = None

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@app.route('/stats')
def stats():
    """Return live database statistics."""
    if not agent:
        return jsonify({'error': 'No DB Connection'}), 500
    return jsonify(agent.get_stats())

@app.route('/board')
def render_board():
    """Renders an SVG chessboard from a valid FEN string."""
    fen = request.args.get('fen')
    if not fen:
        return "Missing FEN", 400
    try:
        board = chess.Board(fen)
        return chess.svg.board(board=board, size=350)
    except ValueError:
        return "Invalid FEN", 400

@app.route('/query_merged', methods=['POST'])
def query_merged():
    """
    Mocking the 'merged' endpoint for compatibility with the existing frontend.
    Currently maps directly to the ContentSurfacingAgent (SQLite).
    """
    if not agent:
        return jsonify({'error': 'Database connection failed'}), 500

    data = request.json
    query_text = data.get('query', '')
    
    print(f"🔍 Received Query: {query_text}")
    start_time = time.time()

    # 2. Format for Frontend
    # The existing frontend expects a specific JSON structure (see app.py lines 720+)
    formatted_results = []
    diagram_positions = []
    
    # 1. Retrieve Results from SQLite (Increased limit for better RAG context)
    try:
        results = agent.search_library(query_text, limit=15)
    except Exception as e:
        print(f"Search failed: {e}")
        return jsonify({'error': str(e)}), 500

    for index, res in enumerate(results):
        # Convert snippet to text for display
        text_content = res['snippet'].replace('<b>', '**').replace('</b>', '**')
        
        has_pos = False
        if res.get('fen'):
            has_pos = True
            diagram_positions.append({'fen': res['fen'], 'title': res['title']})
        
        formatted_results.append({
            'book_title': res['title'],
            'book_name': res['title'], 
            'book': res['title'],      
            'chapter_title': res['chapter'],
            'chapter': res['chapter'], 
            'text': text_content, 
            'score': res['score'],
            'rrf_score': round(1.0 / (index + 1), 4), # Mock RRF for UI consistency
            'has_positions': has_pos, 
            'positions': [{'fen': res['fen']}] if res.get('fen') else [],
            'collection': 'production' # Mock collection for badge icon
        })

    # 3. Generate High-Value Answer via Gemini
    import markdown
    api_key = os.getenv("GOOGLE_API_KEY")

    # Try to find relevant static diagrams from the source books
    epub_diagrams = []
    try:
        # Extract book IDs from results to fetch diagrams
        book_ids = set()
        for r in results:
            # Use source_name or title to match book_id
            bid = diagram_index.get_book_id_from_name(r.get('title', ''))
            if bid:
                book_ids.add(bid)
        
        for bid in book_ids:
            all_diags = diagram_index.get_diagrams_for_book(bid)
            if all_diags:
                # Just grab top 1-2 diagrams for now to keep it lite
                # In a full app we'd rank them by chunk text
                for d in all_diags[:2]:
                    raw_cap = d.get('context_after') or d.get('context_before') or "Chess Diagram"
                    epub_diagrams.append({
                        'id': d['diagram_id'],
                        'url': f"/diagram/{d['diagram_id']}",
                        'caption': clean_caption(raw_cap),
                        'book_title': d.get('book_title')
                    })
    except Exception as e:
        print(f"Error fetching static diagrams: {e}")

    # Add these to the source metadata for the first result that matches
    for res in formatted_results:
        res['epub_diagrams'] = [d for d in epub_diagrams if d['book_title'] == res.get('book')]

    if not api_key:
        answer_html = "<p style='color:red'>⚠️ API Key Missing. Please restart server with GOOGLE_API_KEY set.</p>"
    else:
        print(f"🧠 Synthesizing Answer for: {query_text}")
        try:
            raw_answer, answer_diagrams = agent.answer_question(query_text, api_key, results=results)
            answer_html = markdown.markdown(raw_answer)
            # Add Gemini-generated diagrams to the list
            if answer_diagrams:
                diagram_positions.extend(answer_diagrams)
        except Exception as e:
            answer_html = f"<p>Error generating answer: {e}</p>"

    response = {
        'answer': answer_html,
        'sources': formatted_results,
        'diagram_positions': diagram_positions,
        'timing': {'total': round(time.time() - start_time, 2)}
    }

    return jsonify(response)

@app.route('/diagram/<diagram_id>')
def serve_diagram(diagram_id):
    """Serve a static diagram image from the EPUB corpus."""
    diagram = diagram_index.get_diagram_by_id(diagram_id)
    if not diagram or not diagram.get('file_path'):
        abort(404)
    
    file_path = diagram['file_path']
    if not os.path.exists(file_path):
        abort(404)
        
    return send_file(file_path)

if __name__ == "__main__":
    print("🚀 Starting Chess Coach Lite on http://localhost:5001")
    app.run(debug=False, port=5001)
