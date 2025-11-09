"""
Unit Tests: Query Router Module

Tests:
- Opening query classification
- Concept query classification
- Mixed query classification
- Weight assignment correctness
"""

from query_router import classify_query, get_collection_weights, get_query_info


def test_opening_queries():
    """Test that opening-specific queries are classified correctly."""
    opening_queries = [
        ("Benko Gambit repertoire", "opening"),
        ("Italian Game opening", "opening"),
        ("Najdorf variation", "opening"),
        ("E60 ECO code", "opening"),
        ("After 10...d5", "opening"),  # No "what" question word
        ("Sicilian Defense repertoire", "opening"),
        ("King's Gambit line", "opening"),
        ("Show me the mainline", "opening"),
    ]

    for query, expected_type in opening_queries:
        result = classify_query(query)
        assert result == expected_type, f"Query '{query}' classified as '{result}', expected '{expected_type}'"

    print("✅ test_opening_queries PASSED (8/8)")


def test_concept_queries():
    """Test that concept/strategy queries are classified correctly."""
    concept_queries = [
        ("What is a fork?", "concept"),
        ("Explain pawn structure", "concept"),
        ("How to play against an isolated queen pawn?", "concept"),
        ("What are the main strategic ideas?", "concept"),
        ("Why is this position good for White?", "concept"),
        ("Understand the principles of the endgame", "concept"),
        ("What is the plan in this position?", "concept"),
    ]

    for query, expected_type in concept_queries:
        result = classify_query(query)
        assert result == expected_type, f"Query '{query}' classified as '{result}', expected '{expected_type}'"

    print("✅ test_concept_queries PASSED (7/7)")


def test_mixed_queries():
    """Test that ambiguous/mixed queries are classified correctly."""
    mixed_queries = [
        ("Explain the Italian Game opening", "mixed"),  # Has both "explain" and "opening"
        ("What is the main idea in the King's Indian Defense?", "mixed"),  # Concept + opening name
        ("What is the main line after 1.e4 c5?", "mixed"),  # "what is" + move notation
        ("How do I play the Sicilian?", "mixed"),  # "how" + opening name
    ]

    for query, expected_type in mixed_queries:
        result = classify_query(query)
        assert result == expected_type, f"Query '{query}' classified as '{result}', expected '{expected_type}'"

    print("✅ test_mixed_queries PASSED (4/4)")


def test_weight_assignment_opening():
    """Test that opening queries get correct weights (PGN favored)."""
    query = "Benko Gambit repertoire"
    weights = get_collection_weights(query)

    assert weights['chess_production'] == 1.0, "EPUB should have weight 1.0 for opening query"
    assert weights['chess_pgn_repertoire'] == 1.3, "PGN should have weight 1.3 for opening query"

    print("✅ test_weight_assignment_opening PASSED")


def test_weight_assignment_concept():
    """Test that concept queries get correct weights (EPUB favored)."""
    query = "What is a fork?"
    weights = get_collection_weights(query)

    assert weights['chess_production'] == 1.3, "EPUB should have weight 1.3 for concept query"
    assert weights['chess_pgn_repertoire'] == 1.0, "PGN should have weight 1.0 for concept query"

    print("✅ test_weight_assignment_concept PASSED")


def test_weight_assignment_mixed():
    """Test that mixed queries get equal weights (no bias)."""
    query = "Explain the Italian Game opening"
    weights = get_collection_weights(query)

    assert weights['chess_production'] == 1.0, "EPUB should have weight 1.0 for mixed query"
    assert weights['chess_pgn_repertoire'] == 1.0, "PGN should have weight 1.0 for mixed query"

    print("✅ test_weight_assignment_mixed PASSED")


def test_get_query_info_convenience():
    """Test the convenience function that returns both classification and weights."""
    query = "Najdorf Variation repertoire"
    query_type, weights = get_query_info(query)

    assert query_type == "opening", f"Expected 'opening', got '{query_type}'"
    assert weights['chess_pgn_repertoire'] == 1.3, "PGN should be weighted higher for opening query"

    print("✅ test_get_query_info_convenience PASSED")


def test_real_world_queries():
    """Test with realistic user queries to validate classification."""
    test_cases = [
        # Opening queries
        ("Show me the main line of the Sicilian Dragon", "opening"),
        ("What should I play after 1.d4?", "opening"),
        ("Caro-Kann advance variation", "opening"),

        # Concept queries
        ("Why is controlling the center important?", "concept"),
        ("Explain the concept of weak squares", "concept"),

        # Mixed queries
        ("How do I improve my middlegame play?", "mixed"),  # "how" is concept word, but ambiguous
        ("What's the strategy in the French Defense?", "mixed"),
        ("Explain how to play the Ruy Lopez", "concept"),  # "explain how" are concept words
    ]

    passed = 0
    for query, expected_type in test_cases:
        result = classify_query(query)
        if result == expected_type:
            passed += 1
        else:
            print(f"  ⚠️  '{query}' → {result} (expected {expected_type})")

    assert passed == len(test_cases), f"Only {passed}/{len(test_cases)} real-world queries classified correctly"

    print(f"✅ test_real_world_queries PASSED ({passed}/{len(test_cases)})")


if __name__ == "__main__":
    print("=" * 70)
    print("QUERY ROUTER UNIT TESTS")
    print("=" * 70)
    print()

    try:
        test_opening_queries()
        test_concept_queries()
        test_mixed_queries()
        test_weight_assignment_opening()
        test_weight_assignment_concept()
        test_weight_assignment_mixed()
        test_get_query_info_convenience()
        test_real_world_queries()

        print()
        print("=" * 70)
        print("✅ ALL 8 TESTS PASSED")
        print("=" * 70)
        print()
        print("Query router module is working correctly!")
        print("Ready to proceed with parallel search implementation.")

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
