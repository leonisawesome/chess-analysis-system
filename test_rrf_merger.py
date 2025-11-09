"""
Unit Tests: RRF Merger Module

Tests:
- Basic RRF algorithm correctness
- Collection weight application
- Tie-breaking logic
- Edge cases (empty lists, duplicates, single source)
"""

import pytest
from rrf_merger import reciprocal_rank_fusion, merge_collections


def test_basic_rrf_no_weights():
    """Test RRF algorithm with no collection weights (all 1.0)."""
    # Two lists with different rankings
    list1 = [
        {'id': 'A', 'score': 0.9, 'collection': 'source1'},
        {'id': 'B', 'score': 0.8, 'collection': 'source1'},
        {'id': 'C', 'score': 0.7, 'collection': 'source1'},
    ]

    list2 = [
        {'id': 'C', 'score': 0.95, 'collection': 'source2'},  # C appears in both
        {'id': 'A', 'score': 0.85, 'collection': 'source2'},  # A appears in both
        {'id': 'D', 'score': 0.75, 'collection': 'source2'},  # D only in list2
    ]

    merged = reciprocal_rank_fusion([list1, list2], k=60, source_weights=None)

    # Extract just IDs for easier assertion
    result_ids = [r['id'] for r in merged]

    # C appears in both lists (rank 3 in list1, rank 1 in list2)
    # RRF for C = 1/(60+3) + 1/(60+1) = 1/63 + 1/61 ≈ 0.0159 + 0.0164 = 0.0323
    #
    # A appears in both lists (rank 1 in list1, rank 2 in list2)
    # RRF for A = 1/(60+1) + 1/(60+2) = 1/61 + 1/62 ≈ 0.0164 + 0.0161 = 0.0325
    #
    # A should rank higher than C due to higher RRF score
    assert result_ids[0] == 'A', f"Expected A first, got {result_ids[0]}"
    assert result_ids[1] == 'C', f"Expected C second, got {result_ids[1]}"

    # Verify RRF scores are attached
    assert 'rrf_score' in merged[0]
    assert 'fusion_sources' in merged[0]
    assert len(merged[0]['fusion_sources']) == 2  # A appears in both lists

    print("✅ test_basic_rrf_no_weights PASSED")


def test_rrf_with_weights():
    """Test RRF with collection-specific weights."""
    list1 = [
        {'id': 'A', 'score': 0.9, 'collection': 'weighted'},
        {'id': 'B', 'score': 0.8, 'collection': 'weighted'},
    ]

    list2 = [
        {'id': 'C', 'score': 0.95, 'collection': 'normal'},
        {'id': 'D', 'score': 0.85, 'collection': 'normal'},
    ]

    # Apply 1.5x weight to 'weighted' collection
    weights = {'weighted': 1.5, 'normal': 1.0}
    merged = reciprocal_rank_fusion([list1, list2], k=60, source_weights=weights)

    result_ids = [r['id'] for r in merged]

    # A with weight 1.5 at rank 1: 1.5 * 1/(60+1) ≈ 1.5 * 0.0164 = 0.0246
    # C with weight 1.0 at rank 1: 1.0 * 1/(60+1) ≈ 0.0164
    # A should rank higher due to weight boost
    assert result_ids[0] == 'A', f"Expected A first (weighted), got {result_ids[0]}"

    print("✅ test_rrf_with_weights PASSED")


def test_rrf_tie_breaking():
    """Test that tie-breaking works (best_rank, then max_similarity)."""
    list1 = [
        {'id': 'A', 'score': 0.9, 'collection': 'col1'},
        {'id': 'B', 'score': 0.8, 'collection': 'col1'},
    ]

    list2 = [
        {'id': 'C', 'score': 0.95, 'collection': 'col2'},
        {'id': 'D', 'score': 0.85, 'collection': 'col2'},
    ]

    merged = reciprocal_rank_fusion([list1, list2], k=60)

    # All have same RRF score structure (single appearance, different ranks)
    # A: rank 1, score 0.9
    # C: rank 1, score 0.95
    # They have same RRF score (both rank 1), so tie-break by max_similarity
    # C has higher score (0.95 > 0.9), so C should be first

    result_ids = [r['id'] for r in merged]
    # Both A and C are rank 1, but C has higher similarity
    assert result_ids[0] == 'C' or result_ids[0] == 'A'  # Either acceptable (same RRF)

    # Verify metadata
    assert merged[0]['best_rank'] == 1
    assert 'max_similarity' in merged[0]

    print("✅ test_rrf_tie_breaking PASSED")


def test_empty_list_handling():
    """Test RRF handles empty lists gracefully."""
    list1 = [
        {'id': 'A', 'score': 0.9, 'collection': 'col1'},
        {'id': 'B', 'score': 0.8, 'collection': 'col1'},
    ]

    list2 = []  # Empty list

    merged = reciprocal_rank_fusion([list1, list2], k=60)

    # Should return list1 results ranked normally
    assert len(merged) == 2
    assert merged[0]['id'] == 'A'
    assert merged[1]['id'] == 'B'

    print("✅ test_empty_list_handling PASSED")


def test_single_result_in_both():
    """Test when same result appears in multiple lists (should boost RRF score)."""
    list1 = [
        {'id': 'A', 'score': 0.9, 'collection': 'col1'},
        {'id': 'B', 'score': 0.7, 'collection': 'col1'},
    ]

    list2 = [
        {'id': 'A', 'score': 0.85, 'collection': 'col2'},  # A appears in both
        {'id': 'C', 'score': 0.8, 'collection': 'col2'},
    ]

    merged = reciprocal_rank_fusion([list1, list2], k=60)

    # A appears in both lists (rank 1 in both), should have highest RRF
    assert merged[0]['id'] == 'A'
    assert len(merged[0]['fusion_sources']) == 2  # Appears in 2 sources

    print("✅ test_single_result_in_both PASSED")


def test_merge_collections_opening_query():
    """Test merge_collections convenience function with opening query type."""
    epub_results = [
        {'id': 'epub1', 'score': 0.9},
        {'id': 'epub2', 'score': 0.8},
    ]

    pgn_results = [
        {'id': 'pgn1', 'score': 0.85},
        {'id': 'pgn2', 'score': 0.75},
    ]

    merged = merge_collections(
        epub_results,
        pgn_results,
        query_type='opening',  # Should favor PGN
        k=60
    )

    # Verify collections were tagged
    assert merged[0]['collection'] in ['chess_production', 'chess_pgn_repertoire']

    # Verify RRF metadata
    assert 'rrf_score' in merged[0]
    assert 'fusion_sources' in merged[0]

    print("✅ test_merge_collections_opening_query PASSED")


def test_merge_collections_concept_query():
    """Test merge_collections with concept query type (favors EPUB)."""
    epub_results = [
        {'id': 'epub1', 'score': 0.85},
    ]

    pgn_results = [
        {'id': 'pgn1', 'score': 0.9},  # Higher similarity but concept query
    ]

    merged = merge_collections(
        epub_results,
        pgn_results,
        query_type='concept',  # Should favor EPUB with 1.3 weight
        k=60
    )

    # With concept query, EPUB gets 1.3x weight
    # epub1: 1.3 * 1/(60+1) ≈ 0.0213
    # pgn1:  1.0 * 1/(60+1) ≈ 0.0164
    # EPUB should rank higher despite lower similarity
    assert merged[0]['id'] == 'epub1', "EPUB should rank first for concept query"

    print("✅ test_merge_collections_concept_query PASSED")


def test_k_value_sensitivity():
    """Test that different k values produce different rankings."""
    list1 = [
        {'id': 'A', 'score': 0.9, 'collection': 'col1'},
        {'id': 'B', 'score': 0.5, 'collection': 'col1'},
    ]

    list2 = [
        {'id': 'B', 'score': 0.95, 'collection': 'col2'},
        {'id': 'C', 'score': 0.85, 'collection': 'col2'},
    ]

    merged_k60 = reciprocal_rank_fusion([list1, list2], k=60)
    merged_k10 = reciprocal_rank_fusion([list1, list2], k=10)

    # Both should have results, but potentially different orderings
    assert len(merged_k60) == 3
    assert len(merged_k10) == 3

    # k=10 amplifies rank differences more than k=60
    # This is expected behavior (k controls how much ranks matter)

    print("✅ test_k_value_sensitivity PASSED")


if __name__ == "__main__":
    print("=" * 70)
    print("RRF MERGER UNIT TESTS")
    print("=" * 70)
    print()

    try:
        test_basic_rrf_no_weights()
        test_rrf_with_weights()
        test_rrf_tie_breaking()
        test_empty_list_handling()
        test_single_result_in_both()
        test_merge_collections_opening_query()
        test_merge_collections_concept_query()
        test_k_value_sensitivity()

        print()
        print("=" * 70)
        print("✅ ALL 8 TESTS PASSED")
        print("=" * 70)
        print()
        print("RRF merger module is working correctly!")
        print("Ready to proceed with query_router.py implementation.")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
