#!/usr/bin/env python3
"""
Validation script for instructional language enhancement
Tests EVS improvement on GM content
"""

import sys
import logging
from pathlib import Path

# Add chess_rag_system to path
sys.path.insert(0, str(Path.cwd()))

def test_instructional_detection():
    """Test the instructional language detection on sample content"""
    
    # Initialize analyzer with instructional detection enabled
    from chess_rag_system.analysis.semantic_analyzer import ChessSemanticAnalyzer
    analyzer = ChessSemanticAnalyzer()
    
    # Test content: GM-style instructional text
    sample_gm_content = """
    The key idea behind 1.d4 is to control the center immediately. 
    This move aims to grab space and prepare piece development.
    Our plan involves improving the worst piece - the light-squared bishop.
    A fundamental principle is to complete development before launching attacks.
    """
    
    # Test content: Non-instructional chess text  
    sample_non_instructional = """
    1.d4 d5 2.c4 e6 3.Nc3 Nf6 4.Bg5 Be7 5.e3 O-O
    White plays 6.Nf3 and Black responds with 6...Nbd7.
    The position is approximately equal.
    """
    
    print("=" * 60)
    print("INSTRUCTIONAL LANGUAGE DETECTION VALIDATION")
    print("=" * 60)
    
    # Test 1: GM instructional content
    print("\nTest 1: GM Instructional Content")
    print("-" * 40)
    
    result1 = analyzer.analyze_chess_content(sample_gm_content)
    
    print(f"Explanation Clarity: {result1.explanation_clarity:.3f}")
    print(f"Instructional Value: {result1.instructional_value:.3f}")
    print(f"Content Quality: {result1.content_quality_score:.3f}")
    
    # Test 2: Non-instructional content
    print("\nTest 2: Non-Instructional Content")  
    print("-" * 40)
    
    result2 = analyzer.analyze_chess_content(sample_non_instructional)
    
    print(f"Explanation Clarity: {result2.explanation_clarity:.3f}")
    print(f"Instructional Value: {result2.instructional_value:.3f}")
    print(f"Content Quality: {result2.content_quality_score:.3f}")
    
    # Comparison
    print("\nComparison Results:")
    print("-" * 40)
    print(f"Explanation Clarity Difference: {result1.explanation_clarity - result2.explanation_clarity:.3f}")
    print(f"Content Quality Difference: {result1.content_quality_score - result2.content_quality_score:.3f}")
    
    # Success criteria
    clarity_improved = result1.explanation_clarity > result2.explanation_clarity
    quality_improved = result1.content_quality_score > result2.content_quality_score
    
    print(f"\nValidation Results:")
    print(f"✓ Instructional content scored higher clarity: {clarity_improved}")
    print(f"✓ Instructional content scored higher quality: {quality_improved}")
    
    return clarity_improved and quality_improved

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        success = test_instructional_detection()
        if success:
            print("\n🎉 VALIDATION PASSED - Implementation working correctly!")
            sys.exit(0)
        else:
            print("\n❌ VALIDATION FAILED - Check implementation")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 VALIDATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
