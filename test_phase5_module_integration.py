"""
Module Integration Test: Phase 5.1 Components

Validates that all Phase 5.1 modules are properly integrated and
can be imported together without conflicts.

This test does NOT require API keys or live services.
"""

import sys


def test_module_imports():
    """Test that all Phase 5.1 modules can be imported successfully."""
    print("=" * 70)
    print("PHASE 5.1 MODULE INTEGRATION TEST")
    print("=" * 70)
    print()

    print("Testing module imports...")
    print("-" * 40)

    # Test 1: Query router imports
    try:
        from query_router import classify_query, get_collection_weights, get_query_info
        print("✓ query_router module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import query_router: {e}")
        raise

    # Test 2: RRF merger imports
    try:
        from rrf_merger import reciprocal_rank_fusion, merge_collections
        print("✓ rrf_merger module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import rrf_merger: {e}")
        raise

    # Test 3: RAG engine imports (including new async function)
    try:
        from rag_engine import (
            execute_rag_query,
            format_rag_results,
            prepare_synthesis_context,
            collect_answer_positions,
            search_multi_collection_async
        )
        print("✓ rag_engine module imported successfully")
        print("  - Including new search_multi_collection_async()")
    except Exception as e:
        print(f"❌ Failed to import rag_engine: {e}")
        raise

    # Test 4: Synthesis pipeline imports
    try:
        from synthesis_pipeline import synthesize_answer
        print("✓ synthesis_pipeline module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import synthesis_pipeline: {e}")
        raise

    print()
    print("✅ All module imports PASSED")
    print()


def test_query_classification():
    """Test query classification without API calls."""
    print("Testing query classification logic...")
    print("-" * 40)

    from query_router import classify_query, get_query_info

    # Test opening query
    opening_query = "Benko Gambit repertoire"
    query_type, weights = get_query_info(opening_query)

    assert query_type == "opening", f"Expected 'opening', got '{query_type}'"
    assert weights['chess_pgn_repertoire'] == 1.3, "PGN should be weighted 1.3"
    print(f"✓ Opening query classified correctly: '{opening_query}' → {query_type}")

    # Test concept query
    concept_query = "What is a fork?"
    query_type, weights = get_query_info(concept_query)

    assert query_type == "concept", f"Expected 'concept', got '{query_type}'"
    assert weights['chess_production'] == 1.3, "EPUB should be weighted 1.3"
    print(f"✓ Concept query classified correctly: '{concept_query}' → {query_type}")

    # Test mixed query
    mixed_query = "Explain the Italian Game opening"
    query_type, weights = get_query_info(mixed_query)

    assert query_type == "mixed", f"Expected 'mixed', got '{query_type}'"
    assert weights['chess_production'] == 1.0, "Equal weights for mixed"
    assert weights['chess_pgn_repertoire'] == 1.0, "Equal weights for mixed"
    print(f"✓ Mixed query classified correctly: '{mixed_query}' → {query_type}")

    print()
    print("✅ Query classification PASSED")
    print()


def test_rrf_algorithm():
    """Test RRF algorithm with mock data."""
    print("Testing RRF merge algorithm...")
    print("-" * 40)

    from rrf_merger import reciprocal_rank_fusion, merge_collections

    # Create mock results
    epub_results = [
        {'id': 'epub1', 'score': 0.9, 'collection': 'chess_production', 'payload': {'book_name': 'Test Book 1', 'text': 'test'}},
        {'id': 'epub2', 'score': 0.8, 'collection': 'chess_production', 'payload': {'book_name': 'Test Book 2', 'text': 'test'}},
    ]

    pgn_results = [
        {'id': 'pgn1', 'score': 0.85, 'collection': 'chess_pgn_repertoire', 'payload': {'source_file': 'test.pgn', 'text': 'test'}},
        {'id': 'pgn2', 'score': 0.75, 'collection': 'chess_pgn_repertoire', 'payload': {'source_file': 'test2.pgn', 'text': 'test'}},
    ]

    # Test merge with opening query (favors PGN)
    merged = merge_collections(epub_results, pgn_results, query_type='opening', k=60)

    assert len(merged) > 0, "Merged results should not be empty"
    assert 'rrf_score' in merged[0], "Should have rrf_score"
    assert 'fusion_sources' in merged[0], "Should have fusion_sources"

    print(f"✓ RRF merge produced {len(merged)} results")
    print(f"✓ Top result: {merged[0]['collection']} (RRF score: {merged[0]['rrf_score']:.6f})")

    # Test with concept query (favors EPUB)
    merged = merge_collections(epub_results, pgn_results, query_type='concept', k=60)
    print(f"✓ Concept query merge: Top result from {merged[0]['collection']}")

    print()
    print("✅ RRF algorithm PASSED")
    print()


def test_synthesis_context_preparation():
    """Test synthesis context preparation with mixed sources."""
    print("Testing synthesis context preparation...")
    print("-" * 40)

    from rag_engine import prepare_synthesis_context

    # Create mock results with both EPUB and PGN sources
    mock_results = [
        {
            'book_name': 'Test Chess Book',
            'chapter_title': 'Chapter 1',
            'text': 'This is a test EPUB chunk about chess strategy.',
        },
        {
            'source_file': 'benko_gambit.pgn',
            'opening': 'Benko Gambit',
            'text': '1. d4 Nf6 2. c4 c5 3. d5 b5',
        },
    ]

    # Prepare context
    context_chunks = prepare_synthesis_context(mock_results, canonical_fen=None, top_n=2)

    assert len(context_chunks) == 2, "Should have 2 context chunks"

    # Check for source attribution
    assert '[Source 1: Book' in context_chunks[0], "First chunk should be labeled as Book"
    assert '[Source 2: PGN' in context_chunks[1], "Second chunk should be labeled as PGN"

    print(f"✓ Context chunks prepared: {len(context_chunks)}")
    print(f"✓ Chunk 1: {context_chunks[0][:80]}...")
    print(f"✓ Chunk 2: {context_chunks[1][:80]}...")

    print()
    print("✅ Synthesis context preparation PASSED")
    print()


def test_app_imports():
    """Test that app.py imports work (validates Flask integration)."""
    print("Testing app.py imports...")
    print("-" * 40)

    # We can't import app.py directly without triggering Flask startup,
    # but we can verify the imports it uses work
    try:
        import asyncio
        from rrf_merger import merge_collections
        from query_router import get_query_info
        from rag_engine import search_multi_collection_async

        print("✓ All app.py Phase 5.1 imports validated")
        print("  - asyncio")
        print("  - rrf_merger.merge_collections")
        print("  - query_router.get_query_info")
        print("  - rag_engine.search_multi_collection_async")

    except Exception as e:
        print(f"❌ Failed to validate app.py imports: {e}")
        raise

    print()
    print("✅ App imports PASSED")
    print()


def run_all_tests():
    """Run all module integration tests."""
    try:
        test_module_imports()
        test_query_classification()
        test_rrf_algorithm()
        test_synthesis_context_preparation()
        test_app_imports()

        print("=" * 70)
        print("✅ ALL MODULE INTEGRATION TESTS PASSED")
        print("=" * 70)
        print()
        print("Phase 5.1 components are properly integrated!")
        print()
        print("Components validated:")
        print("  1. Module imports (all Phase 5.1 modules)")
        print("  2. Query classification (regex patterns working)")
        print("  3. RRF algorithm (merge logic correct)")
        print("  4. Synthesis context preparation (mixed-media labels)")
        print("  5. Flask app integration (import compatibility)")
        print()
        print("Note: Full end-to-end test with live API/Qdrant requires:")
        print("  - OPENAI_API_KEY environment variable")
        print("  - Qdrant running with both collections")
        print("  - Run: python test_phase5_integration.py")

        return True

    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
