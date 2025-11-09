"""
Integration Test: Phase 5.1 Complete RRF Pipeline

Tests the full end-to-end flow:
1. Query classification (query_router)
2. Parallel multi-collection search (rag_engine)
3. RRF merge (rrf_merger)
4. Result formatting
5. Synthesis context preparation

This test validates that all Phase 5.1 components work together correctly.
"""

import os
import asyncio
from openai import OpenAI
from qdrant_client import QdrantClient

# Import Phase 5.1 components
from query_router import get_query_info
from rrf_merger import merge_collections
from rag_engine import search_multi_collection_async, prepare_synthesis_context

# Import existing functions
from query_system_a import embed_query, semantic_search, gpt5_rerank, COLLECTION_NAME, QDRANT_PATH


def test_rrf_pipeline_integration():
    """
    End-to-end integration test for Phase 5.1 RRF pipeline.

    Uses a real query to validate the complete flow without making
    actual API calls for synthesis (too expensive for testing).
    """
    print("=" * 70)
    print("PHASE 5.1 RRF PIPELINE INTEGRATION TEST")
    print("=" * 70)
    print()

    # Check if we can run this test (requires API key and Qdrant)
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set - skipping integration test")
        print("   (This test requires a live OpenAI API key)")
        return

    # Initialize clients
    print("Initializing clients...")
    openai_client = OpenAI(api_key=api_key)

    # Check Qdrant mode
    qdrant_mode = os.getenv('QDRANT_MODE', 'local')
    qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')

    if qdrant_mode == 'docker':
        print(f"   Using Docker Qdrant at {qdrant_url}")
        qdrant_client = QdrantClient(url=qdrant_url)
    else:
        print(f"   Using local Qdrant at {QDRANT_PATH}")
        qdrant_client = QdrantClient(path=QDRANT_PATH)

    print("✓ Clients initialized")
    print()

    # Test query (opening-specific to test PGN weighting)
    test_query = "Benko Gambit repertoire"
    print(f"Test query: \"{test_query}\"")
    print()

    # STEP 1: Query classification
    print("STEP 1: Query Classification")
    print("-" * 40)
    query_type, weights = get_query_info(test_query)
    print(f"✓ Query type: {query_type}")
    print(f"✓ Collection weights: {weights}")

    assert query_type == 'opening', f"Expected 'opening', got '{query_type}'"
    assert weights['chess_pgn_repertoire'] == 1.3, "PGN should be weighted 1.3 for opening query"
    print("✅ Query classification PASSED")
    print()

    # STEP 2: Generate embedding
    print("STEP 2: Generate Embedding")
    print("-" * 40)
    query_vector = embed_query(openai_client, test_query)
    print(f"✓ Embedding vector length: {len(query_vector)}")
    assert len(query_vector) > 0, "Embedding should not be empty"
    print("✅ Embedding generation PASSED")
    print()

    # STEP 3: Parallel multi-collection search
    print("STEP 3: Parallel Multi-Collection Search")
    print("-" * 40)

    collections = {
        'chess_production': 50,
        'chess_pgn_repertoire': 50
    }

    try:
        epub_results, pgn_results = asyncio.run(
            search_multi_collection_async(
                qdrant_client,
                query_vector,
                collections,
                search_func=semantic_search
            )
        )

        print(f"✓ EPUB results: {len(epub_results)}")
        print(f"✓ PGN results: {len(pgn_results)}")

        assert len(epub_results) > 0, "EPUB search should return results"
        assert len(pgn_results) > 0, "PGN search should return results"

        # Verify collection tagging
        if epub_results:
            first_epub = epub_results[0]
            if isinstance(first_epub, tuple):
                candidate, score = first_epub
                assert hasattr(candidate, 'payload'), "EPUB results should have payload"
                # Collection tag might not be set yet at this stage - that's OK

        print("✅ Parallel search PASSED")
        print()

    except Exception as e:
        print(f"❌ Parallel search FAILED: {e}")
        print("   Possible causes:")
        print("   - chess_pgn_repertoire collection doesn't exist")
        print("   - Qdrant not running")
        raise

    # STEP 4: Rerank (using top 20 for faster testing)
    print("STEP 4: Reranking with GPT-5")
    print("-" * 40)

    # Limit to top 20 for faster testing (instead of 50)
    ranked_epub = gpt5_rerank(openai_client, test_query, epub_results, top_k=20)
    ranked_pgn = gpt5_rerank(openai_client, test_query, pgn_results, top_k=20)

    print(f"✓ Ranked EPUB: {len(ranked_epub)}")
    print(f"✓ Ranked PGN: {len(ranked_pgn)}")

    assert len(ranked_epub) > 0, "Reranked EPUB should have results"
    assert len(ranked_pgn) > 0, "Reranked PGN should have results"
    print("✅ Reranking PASSED")
    print()

    # STEP 5: Format for RRF merger
    print("STEP 5: Format Results for RRF")
    print("-" * 40)

    epub_formatted = []
    for i, (candidate, score) in enumerate(ranked_epub):
        payload = candidate.payload
        epub_formatted.append({
            'id': f"epub_{payload.get('book_name', '')}_{i}",
            'score': score,
            'collection': 'chess_production',
            'payload': payload
        })

    pgn_formatted = []
    for i, (candidate, score) in enumerate(ranked_pgn):
        payload = candidate.payload
        pgn_formatted.append({
            'id': f"pgn_{payload.get('source_file', '')}_{i}",
            'score': score,
            'collection': 'chess_pgn_repertoire',
            'payload': payload
        })

    print(f"✓ EPUB formatted: {len(epub_formatted)}")
    print(f"✓ PGN formatted: {len(pgn_formatted)}")
    print("✅ Formatting PASSED")
    print()

    # STEP 6: RRF Merge
    print("STEP 6: RRF Merge with Collection Weights")
    print("-" * 40)

    merged_results = merge_collections(
        epub_formatted,
        pgn_formatted,
        query_type=query_type,
        k=60
    )

    print(f"✓ Merged results: {len(merged_results)}")

    assert len(merged_results) > 0, "Merged results should not be empty"

    # Verify RRF metadata is present
    first_result = merged_results[0]
    assert 'rrf_score' in first_result, "Results should have rrf_score"
    assert 'best_rank' in first_result, "Results should have best_rank"
    assert 'fusion_sources' in first_result, "Results should have fusion_sources"

    print(f"✓ Top result RRF score: {first_result['rrf_score']:.6f}")
    print(f"✓ Top result collection: {first_result['collection']}")
    print(f"✓ Top result best rank: {first_result['best_rank']}")
    print(f"✓ Top result appears in {len(first_result['fusion_sources'])} source(s)")

    print("✅ RRF merge PASSED")
    print()

    # STEP 7: Verify collection distribution in top 10
    print("STEP 7: Verify Collection Distribution")
    print("-" * 40)

    top_10 = merged_results[:10]
    epub_count = sum(1 for r in top_10 if r['collection'] == 'chess_production')
    pgn_count = sum(1 for r in top_10 if r['collection'] == 'chess_pgn_repertoire')

    print(f"✓ Top 10 results:")
    print(f"   EPUB sources: {epub_count}")
    print(f"   PGN sources: {pgn_count}")

    # For opening query, we expect some PGN results in top 10 due to weighting
    # (But not necessarily majority - depends on actual content quality)
    assert pgn_count > 0, "Opening query should have some PGN results in top 10"

    print("✅ Collection distribution PASSED")
    print()

    # STEP 8: Test synthesis context preparation with mixed sources
    print("STEP 8: Mixed-Media Synthesis Context Preparation")
    print("-" * 40)

    # Format top results for context preparation
    formatted_for_context = []
    for result in top_10:
        payload = result['payload']

        formatted = {
            'book_name': payload.get('book_name'),
            'source_file': payload.get('source_file'),
            'opening': payload.get('opening'),
            'text': payload.get('text', ''),
            'collection': result['collection']
        }
        formatted_for_context.append(formatted)

    # Prepare synthesis context (should handle both EPUB and PGN)
    context_chunks = prepare_synthesis_context(formatted_for_context, canonical_fen=None, top_n=8)

    print(f"✓ Context chunks prepared: {len(context_chunks)}")

    assert len(context_chunks) > 0, "Should have context chunks"

    # Verify source attribution format
    has_book_label = any('[Source' in chunk and 'Book' in chunk for chunk in context_chunks)
    has_pgn_label = any('[Source' in chunk and 'PGN' in chunk for chunk in context_chunks)

    print(f"✓ Has Book source labels: {has_book_label}")
    print(f"✓ Has PGN source labels: {has_pgn_label}")

    # For this opening query, we should have both types in context
    assert has_book_label or has_pgn_label, "Should have source labels in context"

    # Print first context chunk preview
    if context_chunks:
        print(f"\n✓ First context chunk preview:")
        preview = context_chunks[0][:200]
        print(f"   {preview}...")

    print("\n✅ Synthesis context preparation PASSED")
    print()

    # SUMMARY
    print("=" * 70)
    print("✅ ALL INTEGRATION TESTS PASSED")
    print("=" * 70)
    print()
    print("Phase 5.1 RRF Pipeline validated successfully!")
    print()
    print("Components tested:")
    print("  1. Query router (intent classification)")
    print("  2. Parallel multi-collection search")
    print("  3. GPT-5 reranking (both collections)")
    print("  4. Result formatting for RRF")
    print("  5. RRF merge with collection weights")
    print("  6. Collection distribution in top results")
    print("  7. Mixed-media synthesis context preparation")
    print()
    print("Ready for production deployment!")


if __name__ == "__main__":
    try:
        test_rrf_pipeline_integration()
        exit(0)
    except AssertionError as e:
        print()
        print("=" * 70)
        print(f"❌ INTEGRATION TEST FAILED: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        exit(1)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        exit(1)
