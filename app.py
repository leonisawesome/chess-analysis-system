#!/usr/bin/env python3
"""
System A Web UI
Flask web interface for chess knowledge retrieval with interactive diagrams
"""

import os
import re
import time
import json
from typing import Dict, List
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
from synthesis_pipeline import synthesize_answer, LENGTH_PRESETS
from rag_engine import execute_rag_query, format_rag_results, prepare_synthesis_context, collect_answer_positions, debug_position_extraction, search_multi_collection_async

# Phase 5.1: RRF multi-collection merge
import asyncio
from rrf_merger import merge_collections
import uuid

print("\n*** [CANARY] app.py VERSION: 6.1a-2025-11-10 LOADED ***\n")
from query_router import get_query_info

# Phase 6.1a: Static EPUB diagram integration
from diagram_service import diagram_index, normalize_caption

# Feature flag for dynamic middlegame pipeline
USE_DYNAMIC_PIPELINE = True  # Set to False to disable middlegame handling
ENABLE_PGN_COLLECTION = True  # PGN corpus rebuild complete (233,211 chunks ingested Nov 13, 2025)
DEFAULT_LENGTH_MODE = "balanced"
LENGTH_MODE_CHOICES = set(LENGTH_PRESETS.keys())

FEATURED_MARKER_PATTERN = re.compile(r'\[FEATURED_DIAGRAM_\d+\]')
SECTION_HEADING_PATTERN = re.compile(r'(##\s+[^\n]+\n)')


def enforce_featured_diagram_markers(answer: str, diagram_count: int) -> str:
    """
    Ensure the synthesized answer has exactly `diagram_count` [FEATURED_DIAGRAM_X] markers.

    Strategy:
    1. Strip any existing markers (LLM may emit 0 or 20 of them arbitrarily)
    2. Reinsert markers after headings and long sections so that the count
       matches the number of diagrams we actually collected.
    3. If no diagrams available, remove stale markers entirely so the UI
       doesn't show literal [FEATURED_DIAGRAM_N] text.
    """
    if not answer:
        return answer

    # Remove any markers the model generated (keeps text clean)
    cleaned = FEATURED_MARKER_PATTERN.sub('', answer)

    if diagram_count <= 0:
        if cleaned != answer:
            print("🧹 Removed stale inline diagram markers (0 diagrams available)")
        return cleaned

    segments = SECTION_HEADING_PATTERN.split(cleaned)
    result_segments = []
    marker_index = 1
    inserted_markers = 0

    def next_marker(wrap: bool = True) -> str:
        nonlocal marker_index, inserted_markers
        marker = f'[FEATURED_DIAGRAM_{marker_index}]'
        marker_index += 1
        inserted_markers += 1
        return f'\n{marker}\n\n' if wrap else marker

    for segment in segments:
        if not segment:
            continue

        if SECTION_HEADING_PATTERN.match(segment):
            result_segments.append(segment)
            if inserted_markers < diagram_count:
                result_segments.append(next_marker())
            continue

        body = segment
        if inserted_markers < diagram_count and len(body.strip()) >= 200:
            paragraphs = body.split('\n\n')
            insert_at = max(1, len(paragraphs) // 2)
            paragraphs.insert(insert_at, next_marker(wrap=False))
            body = '\n\n'.join(paragraphs)

        result_segments.append(body)

    while inserted_markers < diagram_count:
        result_segments.append(next_marker())

    print(f"📍 Inline diagram markers inserted: {inserted_markers}/{diagram_count}")
    return ''.join(result_segments)


def format_diagram_caption(diagram: Dict) -> str:
    """Generate a clean caption for a static EPUB diagram."""
    raw = (diagram.get('caption')
           or diagram.get('diagram_caption')
           or diagram.get('context_before')
           or diagram.get('context_after')
           or 'Chess diagram')
    return normalize_caption(raw, max_len=220)


def build_featured_diagrams(results: List[Dict], fallback_diagrams: List[Dict], limit: int = 6) -> List[Dict]:
    """
    Build a featured diagram list prioritizing top results, then using fallback pools.
    Ensures we always return up to `limit` unique diagrams so the UI can render a
    consistent number of inline boards.
    """

    def add_from(diagrams: List[Dict], cap: int | None = None) -> bool:
        nonlocal featured
        if not diagrams:
            return False
        selection = diagrams if cap is None else diagrams[:cap]
        for diagram in selection:
            diagram_id = diagram.get('id') or diagram.get('diagram_id')
            if diagram_id and diagram_id in seen:
                continue
            featured.append(diagram)
            if diagram_id:
                seen.add(diagram_id)
            if len(featured) >= limit:
                return True
        return False

    if limit <= 0:
        return []

    featured: List[Dict] = []
    seen = set()

    # Pass 1: top 3 results (max 2 diagrams each to avoid dominance)
    for result in results[:3]:
        if add_from(result.get('epub_diagrams', []), cap=2):
            return featured

    # Pass 2: remaining top results (positions 4-5) any diagrams available
    for result in results[3:5]:
        if add_from(result.get('epub_diagrams', [])):
            return featured

    # Pass 3: use fallback pool to pad out the carousel
    add_from(fallback_diagrams or [])
    return featured[:limit]


def estimate_diagram_slots(answer: str, base_limit: int = 8) -> int:
    """
    Estimate how many inline diagrams we should target based on the size of
    the synthesized answer. Long paragraphs (>=120 chars) count as slots.
    """
    if not answer:
        return base_limit
    paragraphs = [p for p in answer.split('\n\n') if len(p.strip()) >= 120]
    estimated = max(6, min(base_limit, len(paragraphs)))
    return estimated

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize clients at module level (created ONCE on startup)
print("Initializing clients...")
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set!")

OPENAI_CLIENT = OpenAI(api_key=api_key)

# Initialize Qdrant (support both local and Docker modes)
# DEFAULT: Docker mode (better performance for large collections)
QDRANT_MODE = os.getenv('QDRANT_MODE', 'docker')  # 'local' or 'docker'
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')

if QDRANT_MODE == 'docker':
    print(f"   Using Docker Qdrant at {QDRANT_URL}")
    QDRANT_CLIENT = QdrantClient(url=QDRANT_URL)
else:
    print(f"   Using local Qdrant at {QDRANT_PATH}")
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

# Dynamic diagram generation REMOVED (Phase 6.1b abandoned)
# Using static EPUB diagrams only (Phase 6.1a)

# Phase 6.1a: Load static EPUB diagram metadata
print("Loading EPUB diagram metadata...")
try:
    diagram_index.load('diagram_metadata_full.json', min_size_bytes=2000)
    print("✓ Diagram service ready (EPUB)")
except FileNotFoundError:
    print("⚠️  diagram_metadata_full.json not found - static diagrams disabled")
except Exception as e:
    print(f"⚠️  Error loading diagram metadata: {e}")

PGN_DIAGRAM_METADATA = os.getenv("PGN_DIAGRAM_METADATA", "diagram_metadata_pgn.json")
PGN_DIAGRAM_METADATA = os.path.abspath(PGN_DIAGRAM_METADATA)
if os.path.exists(PGN_DIAGRAM_METADATA):
    try:
        print(f"Loading PGN diagram metadata from {PGN_DIAGRAM_METADATA}...")
        diagram_index.load(
            PGN_DIAGRAM_METADATA,
            min_size_bytes=512,
            allow_small_source_types={"pgn"},
        )
        print("✓ PGN diagram metadata merged")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"⚠️  Failed to load PGN diagram metadata: {exc}")
else:
    print(f"ℹ️  PGN diagram metadata not found ({PGN_DIAGRAM_METADATA}) - skipping appendix load")

# ============================================================================
# MULTI-STAGE SYNTHESIS PIPELINE
# ============================================================================

import json

@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


# ============================================================================
# PHASE 6.1a: STATIC EPUB DIAGRAM SERVING
# ============================================================================

@app.route('/diagrams/<diagram_id>')
def serve_diagram(diagram_id):
    """
    Serve a static EPUB diagram by ID.

    Security: Uses metadata whitelist validation (no user-controlled paths).

    Args:
        diagram_id: Diagram identifier (e.g., "book_a857fac20ce3_0042")

    Returns:
        Image file with caching headers or 404/410
    """
    from flask import send_file, abort, Response

    # Validate against whitelist
    if not diagram_index.is_valid_diagram_id(diagram_id):
        app.logger.warning(f"Invalid diagram ID requested: {diagram_id}")
        abort(404)

    # Get trusted file path from metadata
    diagram_info = diagram_index.get_diagram_by_id(diagram_id)
    if not diagram_info:
        abort(404)

    file_path = diagram_info['file_path']

    # Check if file exists
    if not os.path.exists(file_path):
        app.logger.error(f"Diagram file missing: {file_path}")
        return Response("Diagram file unavailable (drive may be unmounted)", status=410)

    # Serve with caching headers
    try:
        response = send_file(file_path, conditional=True)  # Adds ETag/Last-Modified
        response.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours
        return response
    except Exception as e:
        app.logger.error(f"Error serving diagram {diagram_id}: {e}")
        abort(500)

@app.route('/test_pgn')
def test_pgn_page():
    """PGN collection test interface."""
    return render_template('test_pgn.html')

@app.route('/rrf_demo')
def rrf_demo_page():
    """Phase 5.1 RRF multi-collection demo interface."""
    return render_template('rrf_demo.html')

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
        data = request.get_json() or {}
        query_text = data.get('query', '').strip()
        requested_length_mode = data.get('length_mode', DEFAULT_LENGTH_MODE)
        length_mode = requested_length_mode if requested_length_mode in LENGTH_MODE_CHOICES else DEFAULT_LENGTH_MODE
        length_config = LENGTH_PRESETS.get(length_mode, LENGTH_PRESETS[DEFAULT_LENGTH_MODE])
        print(f"📝 Length preference: {length_mode}")
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

        # Detect opening for ITEM-008 validation (Sicilian contamination prevention)
        opening_name, expected_signature, _ = detect_opening(query_text)
        if opening_name:
            print(f"📋 Detected opening: {opening_name}")
        if expected_signature:
            print(f"✓ Expected signature: {expected_signature}")

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

        # Call the 3-stage synthesis function with full ITEM-008 validation
        synthesized_answer = synthesize_answer(
            OPENAI_CLIENT,
            query_text,
            "\n\n".join(context_chunks),  # Join context properly
            opening_name=opening_name,
            expected_signature=expected_signature,
            validate_stage2_diagrams_func=None,  # Dynamic diagram validation removed
            generate_section_with_retry_func=None,  # Dynamic diagram validation removed
            canonical_fen=canonical_fen,
            length_mode=DEFAULT_LENGTH_MODE
        )

        rag_timing['synthesis'] = round(time.time() - synthesis_start, 2)
        print(f"⏱  3-stage synthesis complete: {rag_timing['synthesis']}s")

        # Dynamic diagram generation removed - using static EPUB diagrams only
        diagram_positions = []

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

        synthesized_answer = enforce_featured_diagram_markers(synthesized_answer, 0)

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


@app.route('/query_merged', methods=['POST'])
def query_merged():
    """
    Phase 5.1: RRF multi-collection merge endpoint.

    Handles queries across both EPUB books and PGN game collections using
    Reciprocal Rank Fusion to merge results.

    Features:
    - Intent-based query classification (opening vs concept)
    - Parallel multi-collection search
    - Collection-specific weighting based on query type
    - Mixed-media synthesis (books + games)
    """
    print("=" * 80)
    print("QUERY_MERGED ENDPOINT CALLED (Phase 5.1 - RRF)")
    print("=" * 80)

    try:
        start = time.time()

        # Step 1: Parse request
        data = request.get_json()
        query_text = data.get('query', '').strip()
        requested_length_mode = data.get('length_mode', DEFAULT_LENGTH_MODE)
        length_mode = requested_length_mode if requested_length_mode in LENGTH_MODE_CHOICES else DEFAULT_LENGTH_MODE
        length_config = LENGTH_PRESETS.get(length_mode, LENGTH_PRESETS[DEFAULT_LENGTH_MODE])
        print(f"📝 Length preference: {length_mode}")
        t1 = time.time()
        print(f"⏱  Request parsing: {t1-start:.2f}s")

        if not query_text:
            return jsonify({'error': 'Query cannot be empty'}), 400

        # Step 2: Classify query and determine collection weights
        print(f"📋 Classifying query intent...")
        query_type, weights = get_query_info(query_text)
        print(f"   Query type: {query_type}")
        print(f"   Collection weights: {weights}")

        # Step 3: Generate embedding (compute once, shared across collections)
        print(f"⏱  Generating embedding...")
        embed_start = time.time()
        query_vector = embed_query(OPENAI_CLIENT, query_text)
        embed_time = time.time() - embed_start
        print(f"   Embedding: {embed_time:.2f}s")

        # Step 4: Parallel search across collections
        print(f"⏱  Searching collections in parallel...")
        search_start = time.time()

        # Define collections with balanced retrieval (50+50)
        collections = {
            'chess_production': 50  # EPUB books
        }
        if ENABLE_PGN_COLLECTION:
            collections['chess_pgn_repertoire'] = 50  # PGN games

        if ENABLE_PGN_COLLECTION:
            epub_results, pgn_results = asyncio.run(
                search_multi_collection_async(
                    QDRANT_CLIENT,
                    query_vector,
                    collections,
                    search_func=semantic_search
                )
            )
        else:
            epub_results = semantic_search(
                QDRANT_CLIENT,
                query_vector,
                top_k=collections['chess_production'],
                collection_name='chess_production'
            )
            pgn_results = []

        search_time = time.time() - search_start
        print(f"   Parallel search: {search_time:.2f}s")
        print(f"   EPUB candidates: {len(epub_results)}")
        if ENABLE_PGN_COLLECTION:
            print(f"   PGN candidates: {len(pgn_results)}")
        else:
            print("   PGN collection disabled (skipping)")

        # Step 5: Rerank each collection independently with GPT-5
        print(f"⏱  Reranking collections...")
        rerank_start = time.time()

        # Rerank EPUB results
        ranked_epub = gpt5_rerank(OPENAI_CLIENT, query_text, epub_results, top_k=50)

        # Rerank PGN results (if enabled)
        ranked_pgn = []
        if ENABLE_PGN_COLLECTION and pgn_results:
            ranked_pgn = gpt5_rerank(OPENAI_CLIENT, query_text, pgn_results, top_k=50)

        rerank_time = time.time() - rerank_start
        print(f"   Reranking: {rerank_time:.2f}s")

        # Step 6: Format results for RRF merger
        print(f"⏱  Formatting results for RRF...")

        # Convert reranked results to dict format for RRF
        epub_formatted = []
        for i, (candidate, score) in enumerate(ranked_epub):
            payload = candidate.payload
            epub_formatted.append({
                'id': f"epub_{payload.get('book_name', '')}_{payload.get('chapter_title', '')}_{i}",
                'score': score,
                'collection': 'chess_production',
                'payload': payload
            })

        pgn_formatted = []
        if ENABLE_PGN_COLLECTION:
            for i, (candidate, score) in enumerate(ranked_pgn):
                payload = candidate.payload
                pgn_formatted.append({
                    'id': f"pgn_{payload.get('source_file', '')}_{i}",
                    'score': score,
                    'collection': 'chess_pgn_repertoire',
                    'payload': payload
                })

        # Step 7: Apply RRF merge with collection weights
        print(f"⏱  Applying RRF merge (k=60)...")
        merge_start = time.time()

        merged_results = merge_collections(
            epub_formatted,
            pgn_formatted,
            query_type=query_type,
            k=60
        )

        merge_time = time.time() - merge_start
        print(f"   RRF merge: {merge_time:.2f}s")
        print(f"   Merged results: {len(merged_results)}")

        # Step 8: Take top 10 after RRF merge
        top_merged = merged_results[:10]

        # Step 9: Convert back to format_rag_results format
        print(f"⏱  Final formatting...")
        final_results = []
        for result in top_merged:
            payload = result['payload']

            # Extract metadata (handle both EPUB and PGN formats)
            book_name = payload.get('book_name', payload.get('source_file', 'Unknown'))
            if book_name.endswith('.epub') or book_name.endswith('.mobi'):
                book_name = book_name[:-5]

            # Handle both EPUB ('text') and PGN ('content') fields
            text = payload.get('text') or payload.get('content', '')
            chapter = payload.get('chapter_title', payload.get('opening', ''))

            # Extract chess positions if requested
            positions = extract_chess_positions(text, query=query_text)

            # Format result with RRF metadata
            formatted = {
                'score': round(result['max_similarity'], 1),  # Use GPT-5 reranking score (0-10 scale)
                'book_name': book_name,
                'book_title': payload.get('book_title', book_name),
                'book': book_name,
                'chapter_title': chapter,
                'chapter': chapter,
                'text': text,
                'positions': positions,
                'has_positions': len(positions) > 0,
                'collection': result['collection'],
                'rrf_score': result['rrf_score'],
                'best_rank': result['best_rank'],
                'fusion_sources': result['fusion_sources'],
                'max_similarity': result['max_similarity']  # Keep for filtering
            }
            # Note: epub_diagrams added later at line 536 (after formatting)
            # Filter out results with 0 relevance (completely irrelevant)
            if result['max_similarity'] > 0:
                final_results.append(formatted)

        # Step 10: Prepare synthesis context with mixed-media support
        print(f"⏱  Preparing synthesis context...")
        context_chunks = prepare_synthesis_context(final_results, canonical_fen=None, top_n=8)

        # Step 11: Synthesize answer using 3-stage pipeline
        print(f"⏱  Starting 3-stage synthesis pipeline...")
        synthesis_start = time.time()

        synthesized_answer = synthesize_answer(
            OPENAI_CLIENT,
            query_text,
            "\n\n".join(context_chunks),
            opening_name=None,
            expected_signature=None,
            validate_stage2_diagrams_func=None,  # Dynamic diagram validation removed
            generate_section_with_retry_func=None,  # Dynamic diagram validation removed
            canonical_fen=None,
            length_mode=length_mode
        )

        synthesis_time = time.time() - synthesis_start
        print(f"⏱  3-stage synthesis complete: {synthesis_time:.2f}s")

        # Dynamic diagram generation removed - using static EPUB diagrams only
        diagram_positions = []

        # Step 14: Collect positions from top sources
        synthesized_positions = collect_answer_positions(final_results, max_positions=2)

        total = time.time() - start
        print(f"🎯 TOTAL: {total:.2f}s")
        print("=" * 80)

        # Phase 6.1a: Attach static EPUB diagrams to results
        print(f"📷 Attaching static EPUB diagrams...")
        diagram_attach_start = time.time()

        for idx, result in enumerate(final_results[:10]):  # Top 10 results only
            book_name = (result.get('book_name') or '').strip()
            book_title = (result.get('book_title') or '').strip()

            lookup_candidates = []
            if book_name:
                lookup_candidates.append(book_name)
                if not book_name.endswith(('.epub', '.mobi', '.pgn')):
                    lookup_candidates.extend([
                        f"{book_name}.epub",
                        f"{book_name}.mobi"
                    ])
            if book_title:
                lookup_candidates.extend([book_title, book_title.lower()])
                title_slug = re.sub(r'[^a-z0-9]+', '_', book_title.lower()).strip('_')
                if title_slug:
                    lookup_candidates.append(title_slug)

            book_id = None
            for candidate in lookup_candidates:
                if not candidate:
                    continue
                book_id = diagram_index.get_book_id_from_name(candidate)
                if book_id:
                    break

            if book_id:
                all_diagrams = diagram_index.get_diagrams_for_book(book_id)
                if all_diagrams:
                    ranked_diagrams = diagram_index.rank_diagrams_for_chunk(
                        all_diagrams,
                        result,
                        query=query_text,
                        max_k=5
                    )

                    result['epub_diagrams'] = [
                        {
                            'id': d['diagram_id'],
                            'url': f"/diagrams/{d['diagram_id']}",
                            'caption': format_diagram_caption(d),
                            'book_title': d.get('book_title', 'Unknown'),
                            'position': d.get('position_in_document', 0)
                        }
                        for d in ranked_diagrams
                    ]
                else:
                    result['epub_diagrams'] = []
            else:
                result['epub_diagrams'] = []

            if not result['epub_diagrams']:
                print(f"[DIAGRAM] No static diagrams found for result {idx}: {book_name or book_title}")

        diagram_attach_time = time.time() - diagram_attach_start
        total_diagrams = sum(len(r.get('epub_diagrams', [])) for r in final_results[:10])
        print(f"📷 Attached {total_diagrams} diagrams across {len([r for r in final_results[:10] if r.get('epub_diagrams')])} results: {diagram_attach_time:.2f}s")

        # Fallback: if no diagrams attached (e.g., PGN-heavy results), source them directly by query
        fallback_epub_diagrams = []
        missing_results = [r for r in final_results[:5] if not r.get('epub_diagrams')]
        if total_diagrams == 0 or missing_results:
            # Always pull a healthy fallback pool so the synthesized answer can
            # show multiple diagrams even when top results already have some.
            needed = max(8, (len(missing_results) * 2) or 8)
            fallback_books = diagram_index.search_books_by_query(query_text, max_matches=needed)
            if fallback_books:
                print(f"📷 Fallback diagram search triggered for books: {fallback_books}")
            for book_id in fallback_books:
                diagrams = diagram_index.get_diagrams_for_book(book_id)
                if not diagrams:
                    continue
                pseudo_chunk = {
                    'text': query_text,
                    'book_title': diagram_index.get_book_title(book_id) or query_text,
                    'chapter_title': query_text,
                    'section_path': '',
                    'chunk_index': 0
                }
                ranked = diagram_index.rank_diagrams_for_chunk(
                    diagrams,
                    pseudo_chunk,
                    query=query_text,
                    max_k=3
                )
                for d in ranked:
                    fallback_epub_diagrams.append({
                        'id': d['diagram_id'],
                        'url': f"/diagrams/{d['diagram_id']}",
                        'caption': format_diagram_caption(d),
                        'book_title': d.get('book_title', 'Unknown'),
                        'position': d.get('position_in_document', 0)
                    })

            if fallback_epub_diagrams:
                print(f"📷 Added {len(fallback_epub_diagrams)} fallback diagrams based on query keywords")

        # Per-result backfill: ensure each top result has at least 1 diagram if available
        fallback_queue = list(fallback_epub_diagrams)
        for result in final_results[:5]:
            if result.get('epub_diagrams') or not fallback_queue:
                continue
            result['epub_diagrams'] = [fallback_queue.pop(0)]

        # Collect featured diagrams from top 3 EPUB sources for prominent display
        target_diagram_slots = estimate_diagram_slots(
            synthesized_answer,
            base_limit=length_config.get('diagram_target', 8)
        )
        featured_diagrams = build_featured_diagrams(
            final_results,
            fallback_epub_diagrams,
            limit=target_diagram_slots
        )
        print(f"📷 Featured diagrams for display: {len(featured_diagrams)} / target {target_diagram_slots} (fallback pool size: {len(fallback_epub_diagrams)})")

        # Normalize inline markers so the count matches what we actually have
        synthesized_answer = enforce_featured_diagram_markers(
            synthesized_answer,
            len(featured_diagrams)
        )

        # Prepare response
        response_data = {
            'success': True,
            'query': query_text,
            'answer': synthesized_answer,
            'positions': synthesized_positions,
            'diagram_positions': diagram_positions,
            'featured_diagrams': featured_diagrams,  # Add featured diagrams
            'sources': final_results[:5],
            'results': final_results,
            'length_mode': length_mode,
            'timing': {
                'embedding': round(embed_time, 2),
                'search': round(search_time, 2),
                'reranking': round(rerank_time, 2),
                'rrf_merge': round(merge_time, 2),
                'synthesis': round(synthesis_time, 2),
                'diagrams': round(diagram_attach_time, 2),
                'total': round(total, 2)
            },
            'rrf_metadata': {
                'query_type': query_type,
                'collection_weights': weights,
                'epub_candidates': len(epub_results),
                'pgn_candidates': len(pgn_results) if ENABLE_PGN_COLLECTION else 0,
                'merged_count': len(merged_results),
                'top_n': len(top_merged)
            }
        }

        return jsonify(response_data)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR IN /query_merged ENDPOINT:")
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

@app.route('/query_pgn', methods=['POST', 'GET'])
def query_pgn():
    """Test endpoint for querying PGN collection only."""
    if not ENABLE_PGN_COLLECTION:
        return jsonify({'error': 'PGN collection is currently disabled'}), 503
    try:
        # Get query from POST or GET
        if request.method == 'POST':
            data = request.get_json()
            query_text = data.get('query', '')
        else:
            query_text = request.args.get('query', '')

        if not query_text:
            return jsonify({'error': 'Query cannot be empty'}), 400

        print(f"\n{'='*80}")
        print(f"PGN TEST QUERY: {query_text}")
        print(f"{'='*80}\n")

        # Generate embedding
        print("Generating embedding...")
        response = OPENAI_CLIENT.embeddings.create(
            model="text-embedding-3-small",
            input=[query_text]
        )
        query_vector = response.data[0].embedding

        # Search PGN collection
        print("Searching chess_pgn_repertoire collection...")
        results = QDRANT_CLIENT.search(
            collection_name="chess_pgn_repertoire",
            query_vector=query_vector,
            limit=10
        )

        # Format results
        formatted_results = []
        for i, hit in enumerate(results, 1):
            payload = hit.payload

            # Get content and skip PGN headers to show instructional content
            full_content = payload.get('content', '')

            # Find where the actual game starts (after headers)
            lines = full_content.split('\n')
            content_start = 0
            for idx, line in enumerate(lines):
                # Skip header lines that start with [
                if not line.strip().startswith('['):
                    content_start = idx
                    break

            # Get content starting from where moves/annotations begin
            instructional_content = '\n'.join(lines[content_start:])
            preview = instructional_content[:1000].strip()
            if len(instructional_content) > 1000:
                preview += '...'

            formatted_results.append({
                'rank': i,
                'score': round(hit.score, 4),
                'source_file': payload.get('source_file', 'Unknown'),
                'game_number': payload.get('game_number', '?'),
                'course_name': payload.get('course_name', ''),
                'chapter': payload.get('chapter', ''),
                'section': payload.get('section', ''),
                'eco': payload.get('eco', ''),
                'opening': payload.get('opening', ''),
                'white': payload.get('white', ''),
                'black': payload.get('black', ''),
                'content_preview': preview
            })

        print(f"✓ Found {len(results)} results\n")

        return jsonify({
            'query': query_text,
            'collection': 'chess_pgn_repertoire',
            'total_results': len(results),
            'results': formatted_results
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR IN /query_pgn ENDPOINT:")
        print(error_details)
        return jsonify({'error': str(e), 'details': error_details}), 500

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
    print(f"Corpus: 358,529 chunks from 1,055 books")
    print(f"Starting server at http://127.0.0.1:5001")
    print("=" * 80)

    app.run(debug=False, host='0.0.0.0', port=5001)
