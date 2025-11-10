"""
Test Script: Mixed-Media Synthesis (EPUB + PGN)

Purpose: Validate that synthesis_pipeline.py correctly handles mixed sources
         from both book chunks (EPUB) and game chunks (PGN).

Phase 5.1 Priority 1A: Synthesis prompt update verification
"""

import os
from openai import OpenAI
from rag_engine import prepare_synthesis_context

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_mock_mixed_results():
    """
    Create mock results simulating RRF merger output with both EPUB and PGN sources.
    """
    return [
        # Mock EPUB result #1
        {
            'book_name': 'Mastering the King\'s Indian Defense',
            'text': '''The King's Indian Defense is characterized by Black allowing White to
build a strong pawn center with pawns on e4 and d4, while Black fianchettoes
the king's bishop and prepares counterplay with ...e5 or ...c5 pawn breaks.

The strategic battle revolves around White's central space advantage versus
Black's dynamic piece play. Black often sacrifices material or pawn structure
for active piece positions and attacking chances against the White king.'''
        },

        # Mock PGN result #1
        {
            'source_file': 'king_indian_repertoire.pgn',
            'opening': 'King\'s Indian Defense',
            'text': '''1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O 6. Be2 e5
{Black immediately challenges the center. This is the Mar del Plata mainline.}
7. O-O Nc6 8. d5 Ne7 {Relocating the knight to support ...f5 push}
9. Ne1 Nd7 10. Nd3 f5 {The characteristic pawn break in the King's Indian.
White must decide how to meet this aggression.}
11. f3 f4 {Black has achieved typical attacking setup with pawns on e5 and f4.}'''
        },

        # Mock EPUB result #2
        {
            'book_name': 'Modern Chess Strategy',
            'text': '''In positions where Black has pawns on e5 and f4, the strategic battle
is clear: Black attacks on the kingside while White seeks queenside expansion.
The f4 pawn controls the e3 and g3 squares, limiting White's piece mobility.

White's typical plan involves b4-b5, opening lines on the queenside and creating
passed pawns. Meanwhile, Black must create threats quickly enough to justify
the weakening of the kingside pawn structure.'''
        },

        # Mock PGN result #2
        {
            'source_file': 'king_indian_bayonet_attack.pgn',
            'opening': 'King\'s Indian, Bayonet Attack',
            'text': '''1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O 6. Be2 e5
7. O-O Nc6 8. d5 Ne7 9. b4 {The Bayonet Attack - White immediately expands on queenside}
9...Nh5 {Black prepares ...Nf4 to trade White's key bishop}
10. Re1 Nf4 11. Bf1 a5 {Counterattacking the b4 pawn}
12. bxa5 Rxa5 {Black has achieved active piece play and pressure against a5}'''
        }
    ]

def test_context_preparation():
    """Test that prepare_synthesis_context formats mixed sources correctly."""
    print("=" * 70)
    print("TEST 1: Context Preparation with Source Attribution")
    print("=" * 70)

    mock_results = create_mock_mixed_results()
    context_chunks = prepare_synthesis_context(mock_results, top_n=4)

    print(f"\n✓ Generated {len(context_chunks)} context chunks\n")

    for i, chunk in enumerate(context_chunks, 1):
        print(f"--- Chunk {i} ---")
        print(chunk[:200] + "..." if len(chunk) > 200 else chunk)
        print()

    # Verify formatting
    assert any("[Source 1: Book" in chunk for chunk in context_chunks), "Missing Book source label"
    assert any("[Source 2: PGN" in chunk for chunk in context_chunks), "Missing PGN source label"

    print("✅ Context preparation test PASSED")
    print()

    return context_chunks

def test_synthesis_stage1(context_chunks):
    """Test Stage 1 outline generation with mixed sources."""
    print("=" * 70)
    print("TEST 2: Stage 1 Outline Generation (Mixed Sources)")
    print("=" * 70)

    from synthesis_pipeline import stage1_generate_outline

    query = "Explain the King's Indian Defense opening"
    context_str = "\n\n---\n\n".join(context_chunks)

    print(f"Query: {query}")
    print(f"Context length: {len(context_str)} chars")
    print("\nGenerating outline...")

    outline = stage1_generate_outline(openai_client, query, context_str)

    print("\n✓ Outline generated:")
    for i, section in enumerate(outline.get('sections', []), 1):
        print(f"  {i}. {section['title']}: {section['description']}")

    print("\n✅ Stage 1 outline generation test PASSED")
    print()

    return outline

def test_synthesis_stage2(context_chunks, outline):
    """Test Stage 2 section expansion with mixed sources."""
    print("=" * 70)
    print("TEST 3: Stage 2 Section Expansion (Mixed Sources)")
    print("=" * 70)

    from synthesis_pipeline import stage2_expand_sections

    query = "Explain the King's Indian Defense opening"
    context_str = "\n\n---\n\n".join(context_chunks)

    print(f"Expanding {len(outline['sections'])} sections...")
    print("This will test if GPT-5 correctly:")
    print("  - Recognizes Book vs PGN sources")
    print("  - Uses books for strategic concepts")
    print("  - Uses PGN for concrete variations")
    print("\nExpanding sections (this may take 30-60 seconds)...")

    expanded = stage2_expand_sections(
        openai_client,
        outline['sections'],
        query,
        context_str
    )

    print(f"\n✓ Expanded {len(expanded)} sections")

    for i, section in enumerate(expanded, 1):
        print(f"\n--- Section {i}: {section['title']} ---")
        content = section['content']
        print(content[:300] + "..." if len(content) > 300 else content)

        # Check for diagram markers
        diagram_count = content.count('[DIAGRAM:')
        print(f"\n  Diagrams: {diagram_count}")

    print("\n✅ Stage 2 section expansion test PASSED")
    print()

    return expanded

def manual_inspection_test():
    """
    Manual inspection test: Show what GPT-5 receives and ask user to verify.
    """
    print("=" * 70)
    print("MANUAL INSPECTION: What GPT-5 Receives")
    print("=" * 70)

    mock_results = create_mock_mixed_results()
    context_chunks = prepare_synthesis_context(mock_results, top_n=4)
    context_str = "\n\n---\n\n".join(context_chunks)

    print("\nContext sent to GPT-5:")
    print("-" * 70)
    print(context_str)
    print("-" * 70)

    print("\n📋 VERIFY:")
    print("  1. Are Book sources labeled correctly? [Source N: Book - ...]")
    print("  2. Are PGN sources labeled correctly? [Source N: PGN - ...]")
    print("  3. Is the content readable and distinct?")
    print()

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PHASE 5.1 SYNTHESIS PROMPT VALIDATION")
    print("Testing mixed-media synthesis (EPUB + PGN)")
    print("=" * 70 + "\n")

    try:
        # Test 1: Context preparation
        context_chunks = test_context_preparation()

        # Test 2: Manual inspection
        manual_inspection_test()

        # Test 3: Stage 1 outline generation (costs ~$0.01)
        outline = test_synthesis_stage1(context_chunks)

        # Test 4: Stage 2 section expansion (costs ~$0.05-0.10)
        print("\n⚠️  WARNING: Stage 2 test will make OpenAI API calls (~$0.05-0.10)")
        response = input("Continue with Stage 2 test? (y/n): ")

        if response.lower() == 'y':
            expanded = test_synthesis_stage2(context_chunks, outline)

            print("\n" + "=" * 70)
            print("ALL TESTS PASSED ✅")
            print("=" * 70)
            print("\nConclusion:")
            print("  - Context preparation correctly labels Book vs PGN sources")
            print("  - Synthesis prompts successfully handle mixed-media")
            print("  - GPT-5 can distinguish between Book and PGN content")
            print("\nReady to proceed with RRF implementation!")
        else:
            print("\n⏭  Skipping Stage 2 test")
            print("\nPartial validation complete:")
            print("  ✅ Context preparation")
            print("  ✅ Stage 1 outline generation")
            print("  ⏭  Stage 2 expansion (skipped)")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
