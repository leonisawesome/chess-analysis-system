"""
Test Script: Mixed-Media Context Formatting

Purpose: Validate that rag_engine.prepare_synthesis_context() correctly formats
         mixed EPUB + PGN sources with structured attribution.

Phase 5.1 Priority 1A: Verify context preparation without API calls
"""

from rag_engine import prepare_synthesis_context

def create_mock_mixed_results():
    """
    Create mock results simulating RRF merger output with both EPUB and PGN sources.
    """
    return [
        # Mock EPUB result #1
        {
            'book_name': 'Mastering the King\'s Indian Defense',
            'chapter_title': 'Chapter 3: Classical Variation',
            'text': '''The King's Indian Defense is characterized by Black allowing White to
build a strong pawn center with pawns on e4 and d4, while Black fianchettoes
the king's bishop and prepares counterplay with ...e5 or ...c5 pawn breaks.

The strategic battle revolves around White's central space advantage versus
Black's dynamic piece play.'''
        },

        # Mock PGN result #1
        {
            'source_file': 'king_indian_repertoire.pgn',
            'opening': 'King\'s Indian Defense',
            'text': '''1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O 6. Be2 e5
{Black immediately challenges the center. This is the Mar del Plata mainline.}
7. O-O Nc6 8. d5 Ne7 {Relocating the knight to support ...f5 push}
9. Ne1 Nd7 10. Nd3 f5 {The characteristic pawn break in the King's Indian.}'''
        },

        # Mock EPUB result #2
        {
            'book_name': 'Modern Chess Strategy',
            'chapter_title': 'Pawn Storms and King Safety',
            'text': '''In positions where Black has pawns on e5 and f4, the strategic battle
is clear: Black attacks on the kingside while White seeks queenside expansion.
The f4 pawn controls the e3 and g3 squares, limiting White's piece mobility.'''
        },

        # Mock PGN result #2
        {
            'source_file': 'king_indian_bayonet_attack.pgn',
            'opening': 'King\'s Indian, Bayonet Attack',
            'text': '''1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O 6. Be2 e5
7. O-O Nc6 8. d5 Ne7 9. b4 {The Bayonet Attack - White immediately expands on queenside}
9...Nh5 {Black prepares ...Nf4 to trade White's key bishop}
10. Re1 Nf4 11. Bf1 a5 {Counterattacking the b4 pawn}'''
        }
    ]

def test_context_formatting():
    """
    Test that prepare_synthesis_context() formats mixed sources with proper attribution.
    """
    print("=" * 80)
    print("TEST: Mixed-Media Context Formatting (EPUB + PGN)")
    print("=" * 80)
    print()

    mock_results = create_mock_mixed_results()

    print(f"Input: {len(mock_results)} mock results")
    print(f"  - 2 EPUB (book) sources")
    print(f"  - 2 PGN (game) sources")
    print()

    # Prepare context with source attribution
    context_chunks = prepare_synthesis_context(mock_results, top_n=4)

    print(f"Output: {len(context_chunks)} formatted context chunks")
    print()

    # Display formatted chunks
    for i, chunk in enumerate(context_chunks, 1):
        print("-" * 80)
        print(f"CHUNK {i}:")
        print("-" * 80)
        print(chunk)
        print()

    # Validation checks
    print("=" * 80)
    print("VALIDATION CHECKS:")
    print("=" * 80)

    checks = [
        ("[Source 1: Book" in context_chunks[0], "✅ Chunk 1 labeled as Book source"),
        ("[Source 2: PGN" in context_chunks[1], "✅ Chunk 2 labeled as PGN source"),
        ("[Source 3: Book" in context_chunks[2], "✅ Chunk 3 labeled as Book source"),
        ("[Source 4: PGN" in context_chunks[3], "✅ Chunk 4 labeled as PGN source"),
        ("Mastering the King's Indian Defense" in context_chunks[0], "✅ Book title preserved"),
        ("king_indian_repertoire.pgn" in context_chunks[1], "✅ PGN filename preserved"),
        ("1. d4" in context_chunks[1], "✅ PGN move notation preserved"),
    ]

    all_passed = True
    for passed, message in checks:
        if passed:
            print(f"  {message}")
        else:
            print(f"  ❌ FAILED: {message}")
            all_passed = False

    print()

    if all_passed:
        print("=" * 80)
        print("✅ ALL CHECKS PASSED")
        print("=" * 80)
        print()
        print("Conclusion:")
        print("  - Context preparation correctly labels Book vs PGN sources")
        print("  - Source attribution format: [Source N: Type - \"Title\"]")
        print("  - Content is preserved exactly as provided")
        print("  - Ready for GPT-5 synthesis with mixed-media understanding")
        print()
        print("Next step: Update synthesis_pipeline.py prompts to handle these labels")
        return True
    else:
        print("❌ SOME CHECKS FAILED")
        return False

if __name__ == "__main__":
    success = test_context_formatting()
    exit(0 if success else 1)
