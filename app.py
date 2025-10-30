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
from rag_engine import execute_rag_query, format_rag_results, prepare_synthesis_context, collect_answer_positions, debug_position_extraction

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

        # Step 2-4: Execute RAG pipeline (embed → search → rerank)
        ranked_results, rag_timing = execute_rag_query(
            OPENAI_CLIENT,
            QDRANT_CLIENT,
            query_text,
            COLLECTION_NAME,
            top_k=TOP_K,
            top_n=TOP_N,
            embed_func=embed_query,
            search_func=semantic_search,
            rerank_func=gpt5_rerank
        )

        # Step 5: Format results for web display
        format_start = time.time()
        results = format_rag_results(ranked_results, query_text, extract_positions=True)
        rag_timing['formatting'] = round(time.time() - format_start, 2)
        print(f"⏱  Response formatting: {rag_timing['formatting']}s")

        # DEBUG: Position extraction
        debug_position_extraction(results)

        # Step 6: Synthesize coherent answer using 3-stage synthesis pipeline
        print(f"⏱  Starting 3-stage synthesis pipeline...")
        synthesis_start = time.time()

        # Prepare context with canonical FEN if available
        context_chunks = prepare_synthesis_context(results, canonical_fen, top_n=8)

        # Call the 3-stage synthesis function
        synthesized_answer = synthesize_answer(
            OPENAI_CLIENT,
            query_text,
            "\n\n".join(context_chunks)
        )

        rag_timing['synthesis'] = round(time.time() - synthesis_start, 2)
        print(f"⏱  3-stage synthesis complete: {rag_timing['synthesis']}s")

        # Step 6.5: Extract and parse diagram markers from synthesized text
        print(f"\n⏱  Extracting diagram markers...")
        diagram_start = time.time()

        diagram_positions = extract_diagram_markers(synthesized_answer)
        synthesized_answer = replace_markers_with_ids(synthesized_answer, diagram_positions)

        rag_timing['diagrams'] = round(time.time() - diagram_start, 2)
        print(f"⏱  Diagram extraction complete: {rag_timing['diagrams']}s")
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
        synthesized_positions = collect_answer_positions(results, max_positions=2)
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
                **rag_timing,
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
