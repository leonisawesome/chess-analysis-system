#!/usr/bin/env python3
"""
System A Web UI
Flask web interface for chess knowledge retrieval with interactive diagrams
"""

import os
import re
import time
import json
import chess
import chess.pgn
import chess.svg
import spacy
from io import StringIO
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from qdrant_client import QdrantClient
from query_system_a import query_system_a, COLLECTION_NAME, QDRANT_PATH, embed_query, semantic_search, gpt5_rerank, TOP_K, TOP_N
from opening_data import detect_opening
import fen_validator
import query_classifier

from chess_positions import detect_fen, parse_moves_to_fen, extract_chess_positions, filter_relevant_positions, create_lichess_url
from diagram_processor import extract_moves_from_description, extract_diagram_markers, replace_markers_with_ids
from opening_validator import extract_contamination_details, generate_section_with_retry, validate_stage2_diagrams, validate_and_fix_diagrams
from synthesis_pipeline import stage1_generate_outline, stage2_expand_sections, stage3_final_assembly, synthesize_answer

# Feature flag for dynamic middlegame pipeline
USE_DYNAMIC_PIPELINE = True  # Set to False to disable middlegame handling

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize clients at module level (created ONCE on startup)
print("Initializing clients...")
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set!")

OPENAI_CLIENT = OpenAI(api_key=api_key)
QDRANT_CLIENT = QdrantClient(path=QDRANT_PATH)
print(f"✓ Clients initialized (Qdrant: {QDRANT_CLIENT.count(COLLECTION_NAME).count} vectors)")

# Load spaCy model for smart caption extraction
print("Loading spaCy model...")
try:
    NLP = spacy.load("en_core_web_sm")
    print("✓ spaCy model loaded")
except OSError:
    print("⚠️  spaCy model not found. Run: python -m spacy download en_core_web_sm")
    NLP = None

# Load canonical FENs for middlegame concepts
print("Loading canonical FENs...")
CANONICAL_FENS = {}
try:
    with open('canonical_fens.json', 'r') as f:
        CANONICAL_FENS = json.load(f)
    print(f"✓ Loaded {len(CANONICAL_FENS)} canonical FEN concepts")
except FileNotFoundError:
    print("⚠️  canonical_fens.json not found - middlegame queries will use RAG only")

# ============================================================================
# MULTI-STAGE SYNTHESIS PIPELINE
# ============================================================================

import json

def index():
    """Main page."""
    return render_template('index.html')

@app.route('/test', methods=['POST'])
def test():
    """Test endpoint."""
    return jsonify({'status': 'ok', 'message': 'test works'})

@app.route('/query', methods=['POST'])
def query():
    """Handle query requests with detailed timing."""
    print("=" * 80)
    print("QUERY ENDPOINT CALLED")
    print("=" * 80)
    try:
        start = time.time()

        # Step 1: Parse request
        data = request.get_json()
        query_text = data.get('query', '').strip()
        t1 = time.time()
        print(f"⏱  Request parsing: {t1-start:.2f}s")

        if not query_text:
            return jsonify({'error': 'Query cannot be empty'}), 400

        # Step 1.5: Classify query and get canonical FEN if available
        query_type, concept_key, canonical_fen = query_classifier.get_canonical_fen_for_query(
            query_text,
            CANONICAL_FENS
        )
        print(f"📋 Query type: {query_type}")
        if concept_key:
            print(f"📋 Concept: {concept_key}")
        if canonical_fen:
            print(f"✓ Using canonical FEN: {canonical_fen}")

        # Step 2: Generate embedding
        query_vector = embed_query(OPENAI_CLIENT, query_text)
        t2 = time.time()
        print(f"⏱  Embedding: {t2-t1:.2f}s")

        # Step 3: Search Qdrant
        candidates = semantic_search(QDRANT_CLIENT, query_vector, top_k=TOP_K)
        t3 = time.time()
        print(f"⏱  Qdrant search: {t3-t2:.2f}s")

        # Step 4: Rerank with GPT-5
        ranked_results = gpt5_rerank(OPENAI_CLIENT, query_text, candidates, top_k=TOP_N)
        t4 = time.time()
        print(f"⏱  GPT-5 reranking: {t4-t3:.2f}s")

        # Step 5: Format results for web display
        results = []
        for candidate, score in ranked_results:
            payload = candidate.payload

            # Extract metadata
            book_name = payload.get('book_name', 'Unknown')
            if book_name.endswith('.epub') or book_name.endswith('.mobi'):
                book_name = book_name[:-5]

            text = payload.get('text', '')
            chapter = payload.get('chapter_title', '')

            # Extract chess positions from text (pass query for relevance filtering)
            positions = extract_chess_positions(text, query=query_text)

            # Format result
            result = {
                'score': round(score, 1),
                'book_name': book_name,
                'book': book_name,  # Keep for backwards compatibility
                'chapter_title': chapter,
                'chapter': chapter,  # Keep for backwards compatibility
                'text': text,
                'positions': positions,
                'has_positions': len(positions) > 0
            }
            results.append(result)

        t5 = time.time()
        print(f"⏱  Response formatting: {t5-t4:.2f}s")

        # DEBUG: Check position extraction
        print("\n=== POSITION EXTRACTION DEBUG ===")
        for i, result in enumerate(results[:5]):
            chunk_text = result.get('text', '')
            print(f"\nSource {i+1}:")
            print(f"  Book: {result.get('book_name', 'unknown')}")
            print(f"  Text preview: {chunk_text[:100]}...")

            # Check what position data exists
            if 'positions' in result:
                print(f"  ✅ Positions array length: {len(result['positions'])}")
                if len(result['positions']) > 0:
                    print(f"     First position: {result['positions'][0]}")
            else:
                print(f"  ❌ No 'positions' key")

            if 'has_positions' in result:
                print(f"  has_positions flag: {result['has_positions']}")
            else:
                print(f"  ❌ No 'has_positions' key")

            # Try to detect patterns in text
            import re
            fen_pattern = r'[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}/[rnbqkpRNBQKP1-8]{1,8}'
            moves_pattern = r'1\.\s*e4\s+c5'

            if re.search(fen_pattern, chunk_text):
                print(f"  📋 FEN detected in text")
            if re.search(moves_pattern, chunk_text, re.IGNORECASE):
                print(f"  ♟ Moves '1.e4 c5' detected in text")
        print("=== END POSITION DEBUG ===\n")

        # Step 6: Synthesize coherent answer using 3-stage pipeline
        print(f"⏱  Starting 3-stage synthesis pipeline...")
        synthesis_start = time.time()

        # Prepare context with canonical FEN if available
        context_chunks = [r['text'] for r in results[:8]]
        if canonical_fen:
            context_chunks.insert(0, f"[CANONICAL POSITION: {canonical_fen}]")
            print(f"📋 Injected canonical FEN into synthesis context")

        # Call the new 3-stage synthesis function
        synthesized_answer = synthesize_answer(
            OPENAI_CLIENT,
            query_text,
            context_chunks
        )

        t6 = time.time()
        print(f"⏱  3-stage synthesis complete: {t6-synthesis_start:.2f}s")

        # Step 6.5: Extract and parse diagram markers from synthesized text
        print(f"\n⏱  Extracting diagram markers...")
        diagram_start = time.time()

        diagram_positions = extract_diagram_markers(synthesized_answer)
        synthesized_answer = replace_markers_with_ids(synthesized_answer, diagram_positions)

        diagram_time = time.time() - diagram_start
        print(f"⏱  Diagram extraction complete: {diagram_time:.2f}s")
        print(f"📋 Extracted {len(diagram_positions)} diagram positions from synthesis")

        total = time.time() - start
        print(f"🎯 TOTAL: {total:.2f}s")
        print("=" * 80)

        # DEBUG: Check what's actually being sent to frontend
        print("\n" + "="*60)
        print("FINAL RESPONSE TO FRONTEND - POSITION DEBUG")
        print("="*60)

        for i, source in enumerate(results[:5]):
            print(f"\nSource {i+1}:")
            print(f"  Book: {source.get('book_name', 'unknown')[:50]}")
            print(f"  Has 'positions' key: {'positions' in source}")
            print(f"  Has 'has_positions' key: {'has_positions' in source}")

            if 'positions' in source:
                positions = source['positions']
                print(f"  positions value: {positions}")
                print(f"  positions type: {type(positions)}")
                print(f"  positions length: {len(positions) if positions else 0}")

                if positions:
                    print(f"  First position: {positions[0]}")

            if 'has_positions' in source:
                print(f"  has_positions: {source['has_positions']}")

        print("\n" + "="*60)
        print("END POSITION DEBUG")
        print("="*60 + "\n")

        # Collect positions from top sources for answer section
        synthesized_positions = []
        for result in results[:5]:
            if result.get('has_positions') and result.get('positions'):
                for pos in result['positions']:
                    # Avoid duplicates (same FEN)
                    if not any(p['fen'] == pos['fen'] for p in synthesized_positions):
                        synthesized_positions.append(pos)
                        if len(synthesized_positions) >= 2:  # Max 2 boards in answer
                            break
            if len(synthesized_positions) >= 2:
                break

        print(f"📋 Collected {len(synthesized_positions)} positions for answer section")

        # Prepare response
        response_data = {
            'success': True,
            'query': query_text,
            'answer': synthesized_answer,
            'positions': synthesized_positions,  # Positions extracted from source chunks
            'diagram_positions': diagram_positions,  # NEW: Positions from [DIAGRAM: ...] markers in synthesis
            'sources': results[:5],
            'results': results,  # Keep for backwards compatibility
            'timing': {
                'embedding': round(t2 - t1, 2),
                'search': round(t3 - t2, 2),
                'reranking': round(t4 - t3, 2),
                'formatting': round(t5 - t4, 2),
                'synthesis': round(t6 - synthesis_start, 2),
                'diagrams': round(diagram_time, 2),
                'total': round(total, 2)
            }
        }

        # DEBUG: Log final response structure
        print("\n" + "="*80)
        print("=== FINAL RESPONSE STRUCTURE ===")
        print(f"Response keys: {list(response_data.keys())}")
        print(f"Has 'positions' key: {'positions' in response_data}")
        if 'positions' in response_data:
            print(f"Number of positions: {len(response_data['positions'])}")
            if len(response_data['positions']) > 0:
                print(f"First position keys: {list(response_data['positions'][0].keys())}")
                print(f"First position FEN: {response_data['positions'][0].get('fen', 'N/A')}")
                print(f"First position has SVG: {bool(response_data['positions'][0].get('svg'))}")
        print("="*80 + "\n")

        return jsonify(response_data)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR IN /query ENDPOINT:")
        print(error_details)
        return jsonify({'error': str(e), 'details': error_details}), 500

@app.route('/fen_to_lichess', methods=['POST'])
def fen_to_lichess():
    """Convert FEN to Lichess URL."""
    try:
        data = request.get_json()
        fen = data.get('fen', '')

        if not fen:
            return jsonify({'error': 'FEN cannot be empty'}), 400

        url = create_lichess_url(fen)
        return jsonify({'url': url})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set!")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        exit(1)

    print("=" * 80)
    print("SYSTEM A WEB UI")
    print("=" * 80)
    print(f"Corpus: 357,957 chunks from 1,052 books")
    print(f"Starting server at http://127.0.0.1:5001")
    print("=" * 80)

    app.run(debug=False, host='0.0.0.0', port=5001)
