#!/usr/bin/env python3
"""Debug the instructional value function specifically"""

from the_evaluator import ChessSemanticAnalyzer
import re


def debug_instructional_value():
    analyzer = ChessSemanticAnalyzer()

    # Path to your Shankland file
    file_path = '/Volumes/T7 Shield/1PGN/1test/1.d4 - GM Sam Shankland - (Part 1) (3)_1.pgn'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print("DEBUGGING INSTRUCTIONAL VALUE FUNCTION")
    print("=" * 50)

    # Split content into chunks (same way the main analyzer does it)
    chunk_size = 500
    chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]

    print(f"Total chunks: {len(chunks)}")
    print(f"Sample chunk length: {len(chunks[0]) if chunks else 0}")

    # Show first chunk content
    if chunks:
        print(f"\nFirst chunk preview:")
        print(chunks[0][:200] + "...")

    # Test the instructional value function directly
    instructional_score = analyzer._analyze_instructional_value(chunks)
    print(f"\nInstructional Value Score: {instructional_score}")

    # Let's manually test what should be found
    full_text = content.lower()

    # Test for key instructional terms
    key_terms = ['grandmaster', 'explain', 'understand', 'technique', 'analyze', 'lesson', 'course']
    found_terms = []

    for term in key_terms:
        if term in full_text:
            count = full_text.count(term)
            found_terms.append(f"{term}: {count}")

    print(f"\nKey instructional terms found: {found_terms}")

    # Check if "shankland" appears (should be author name)
    if 'shankland' in full_text:
        print(f"✅ 'Shankland' found - this should boost scores")

    # Check for GM/grandmaster
    gm_patterns = ['grandmaster', 'gm ', ' gm']
    gm_found = any(pattern in full_text for pattern in gm_patterns)
    print(f"✅ GM indicators found: {gm_found}")

    return instructional_score


if __name__ == "__main__":
    debug_instructional_value()