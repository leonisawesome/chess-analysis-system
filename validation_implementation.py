# CHESS RAG SYSTEM - INSTRUCTIONAL LANGUAGE ENHANCEMENT
# Complete Deployment Instructions
# Incorporates all AI partner recommendations for EVS improvement

# ============================================================================
# PHASE 1: DEPENDENCY INSTALLATION
# ============================================================================

# Install optional dependency for better performance (recommended but not required)
pip
install
pyahocorasick

# If pyahocorasick installation fails, the system will use the fallback implementation
# No additional dependencies are strictly required beyond existing ones

# ============================================================================
# PHASE 2: FILE MODIFICATIONS
# ============================================================================

# 1. CREATE NEW FILE: Instructional Language Detector
# Location: chess_rag_system/analysis/instructional_detector.py
# Content: Use the "Instructional Language Detector - Core Component" artifact
echo
"Creating instructional_detector.py..."

# 2. MODIFY EXISTING FILE: Constants (Vocabulary Extension)
# Location: chess_rag_system/core/constants.py
# Action: Add the new vocabulary categories to get_chess_concepts() method
echo
"Extending constants.py with instructional vocabulary..."

# SPECIFIC INSTRUCTIONS FOR constants.py:
# - Locate the existing get_chess_concepts() method in ChessVocabulary class
# - Add the new vocabulary categories from the constants extension artifact
# - Preserve all existing categories unchanged
# - The method should return the merged dictionary

# 3. MODIFY EXISTING FILE: Semantic Analyzer Integration
# Location: chess_rag_system/analysis/semantic_analyzer.py
# Action: Integrate instructional language detection into explanation_clarity
echo
"Integrating instructional detector into semantic_analyzer.py..."

# SPECIFIC INSTRUCTIONS FOR semantic_analyzer.py:
# - Add imports for InstructionalLanguageDetector
# - Modify __init__ method to initialize the detector
# - Replace _analyze_explanation_clarity with enhanced version
# - Add _analyze_generic_clarity method (move existing logic there)
# - Add get_instructional_analysis_details method for debugging

# ============================================================================
# PHASE 3: VALIDATION SETUP
# ============================================================================

# Create validation script for testing the implementation
cat > validate_implementation.py << 'EOF'
# !/usr/bin/env python3
"""
Validation script for instructional language enhancement
Tests EVS improvement on GM content
"""

import sys
import logging
from pathlib import Path

# Add chess_rag_system to path
sys.path.insert(0, str(Path.cwd()))

from chess_rag_system.analysis.semantic_analyzer import ChessSemanticAnalyzer
from chess_rag_system.core.models import SemanticAnalysisRequest


def test_instructional_detection():
    """Test the instructional language detection on sample content"""

    # Initialize analyzer with instructional detection enabled
    analyzer = ChessSemanticAnalyzer(enable_instructional_detection=True)

    # Test content: GM-style instructional text
    sample_gm_content = """
    The key idea behind 1.d4 is to control the center immediately. 
    This move aims to grab space and prepare piece development.
    Our plan involves improving the worst piece - the light-squared bishop.
    A fundamental principle is to complete development before launching attacks.
    The typical pattern in this structure requires a minority attack on the queenside.
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

    request1 = SemanticAnalysisRequest(
        text=sample_gm_content,
        file_path="test_gm_content.txt"
    )

    result1 = analyzer.analyze_chess_content(sample_gm_content)

    print(f"Explanation Clarity: {result1.explanation_clarity:.3f}")
    print(f"Instructional Value: {result1.instructional_value:.3f}")
    print(f"Content Quality: {result1.content_quality_score:.3f}")

    # Get detailed breakdown if available
    if hasattr(analyzer, 'get_instructional_analysis_details'):
        details1 = analyzer.get_instructional_analysis_details(sample_gm_content)
        print(f"Instructional Score: {details1.get('instructional_score', 'N/A')}")
        print(f"Plan Chain Bonus: {details1.get('plan_chain_bonus', 'N/A')}")

    # Test 2: Non-instructional content
    print("\nTest 2: Non-Instructional Content")
    print("-" * 40)

    result2 = analyzer.analyze_chess_content(sample_non_instructional)

    print(f"Explanation Clarity: {result2.explanation_clarity:.3f}")
    print(f"Instructional Value: {result2.instructional_value:.3f}")
    print(f"Content Quality: {result2.content_quality_score:.3f}")

    if hasattr(analyzer, 'get_instructional_analysis_details'):
        details2 = analyzer.get_instructional_analysis_details(sample_non_instructional)
        print(f"Instructional Score: {details2.get('instructional_score', 'N/A')}")
        print(f"Plan Chain Bonus: {details2.get('plan_chain_bonus', 'N/A')}")

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
        sys.exit(1)
EOF

chmod + x
validate_implementation.py

# ============================================================================
# PHASE 4: DEPLOYMENT EXECUTION
# ============================================================================

echo
"Starting deployment..."

# 1. Backup existing files
echo
"Creating backups..."
cp
chess_rag_system / core / constants.py
chess_rag_system / core / constants.py.backup
cp
chess_rag_system / analysis / semantic_analyzer.py
chess_rag_system / analysis / semantic_analyzer.py.backup

# 2. Deploy new instructional detector
echo
"Deploying instructional detector..."
# Copy the instructional_detector.py content to the file
# (User will need to create this file with the artifact content)

# 3. Update constants.py
echo
"Updating vocabulary..."
# User will need to manually integrate the vocabulary extensions

# 4. Update semantic_analyzer.py
echo
"Updating semantic analyzer..."
# User will need to manually integrate the analyzer modifications

# ============================================================================
# PHASE 5: VALIDATION TESTING
# ============================================================================

echo
"Running validation tests..."

# Test 1: Basic functionality
echo
"Testing basic functionality..."
python
validate_implementation.py

# Test 2: Original GM Shankland content
echo
"Testing on GM Shankland content..."
python - m
chess_rag_system - -test - evs - integration
'/Volumes/T7 Shield/1PGN/1test/1.d4 - GM Sam Shankland - (Part 1) (3)_1.pgn'

# Expected results after implementation:
# - Explanation Clarity: 0.163 → 0.60+ (target improvement)
# - Final EVS Score: 79.7 → 85+ (target TIER_1)
# - Quality Tier: TIER_3 → TIER_1

# Test 3: Quality breakdown analysis
echo
"Getting detailed quality breakdown..."
python - m
chess_rag_system - -quality - breakdown
'/Volumes/T7 Shield/1PGN/1test/1.d4 - GM Sam Shankland - (Part 1) (3)_1.pgn'

# ============================================================================
# PHASE 6: ROLLBACK PROCEDURE (if needed)
# ============================================================================

# If something goes wrong, restore from backups:
rollback_implementation()
{
    echo
"Rolling back implementation..."

# Restore original files
cp
chess_rag_system / core / constants.py.backup
chess_rag_system / core / constants.py
cp
chess_rag_system / analysis / semantic_analyzer.py.backup
chess_rag_system / analysis / semantic_analyzer.py

# Remove new files
rm - f
chess_rag_system / analysis / instructional_detector.py
rm - f
validate_implementation.py

echo
"Rollback complete. System restored to original state."
}

# ============================================================================
# PHASE 7: SUCCESS METRICS & MONITORING
# ============================================================================

# After successful deployment, monitor these metrics:

echo
"Implementation complete! Monitor these success metrics:"
echo
""
echo
"PRIMARY SUCCESS CRITERIA:"
echo
"- GM Shankland EVS: 79.7 → 85+ (TIER_1)"
echo
"- Explanation Clarity: 0.163 → 0.60+"
echo
"- No regression on other content types"
echo
""
echo
"SECONDARY METRICS:"
echo
"- False positive rate on non-instructional content < 5%"
echo
"- Performance impact < 10% latency increase"
echo
"- Instructional language detection working across different GM authors"
echo
""
echo
"DEBUGGING COMMANDS:"
echo
"- Enable debug logging: --log-level DEBUG"
echo
"- Get detailed breakdown: --quality-breakdown [file]"
echo
"- Test specific content: python validate_implementation.py"
echo
""
echo
"If issues arise, run: rollback_implementation"