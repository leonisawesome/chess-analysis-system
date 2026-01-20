import os
import time
from flask import Flask, render_template, request, jsonify
from content_surfacing_agent import ContentSurfacingAgent
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import chess
import chess.svg

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
    
    # We get the API key from args or env (passed via command line when running the script)
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        answer_html = "<p style='color:red'>⚠️ API Key Missing. Please restart server with GOOGLE_API_KEY set.</p>"
    else:
        print(f"🧠 Synthesizing Answer for: {query_text}")
        try:
            raw_answer = agent.answer_question(query_text, api_key, results=results)
            answer_html = markdown.markdown(raw_answer)
        except Exception as e:
            answer_html = f"<p>Error generating answer: {e}</p>"

    response = {
        'answer': answer_html,
        'sources': formatted_results,
        'diagram_positions': diagram_positions,
        'timing': {'total': round(time.time() - start_time, 2)}
    }

    return jsonify(response)

if __name__ == "__main__":
    print("🚀 Starting Chess Coach Lite on http://localhost:5001")
    app.run(debug=True, port=5001)
