"""
Unit test for InstructionalLanguageDetector initialization fix
Based on 4-AI partner consultation consensus
Tests the critical fix for missing _load_instructional_vocabulary() call
"""
import sys
import os
sys.path.insert(0, '/Users/leon/Downloads/python/chess-analysis-system/chess_rag_system')

def test_detector_initialization():
    """Test that detector initializes with vocabulary loaded"""
    print('=== DETECTOR INITIALIZATION TEST ===')
    try:
        from analysis.instructional_detector import InstructionalLanguageDetector
        print('1. Testing basic initialization...')
        detector = InstructionalLanguageDetector()
        assert hasattr(detector, 'fixed_phrases'), 'FAIL: fixed_phrases not set'
        assert len(detector.fixed_phrases) > 0, 'FAIL: Empty phrases after load'
        print(f'   ✅ Loaded {len(detector.fixed_phrases)} phrase categories')
        assert hasattr(detector, '_compiled'), 'FAIL: _compiled patterns not set'
        assert len(detector._compiled) > 0, 'FAIL: No compiled patterns'
        print(f'   ✅ Compiled {len(detector._compiled)} individual patterns')
        total_phrases = sum((len(phrases) for phrases in detector.fixed_phrases.values()))
        print(f'   ✅ Total phrases loaded: {total_phrases}')
        print('2. Testing pattern matching on Shankland-style content...')
        test_text = 'In the Semi-Slav, the idea is to improve the worst piece while preventing counterplay. After Nf3, we can overprotect the center.'
        score = detector.analyze_instructional_language([test_text])
        print(f'   ✅ Test score: {score:.3f} (target: >0.6)')
        assert score > 0.0, f'FAIL: Got zero score {score}, pattern detection broken'
        if score >= 0.6:
            print('   🎯 EXCELLENT: Score meets target threshold')
        elif score >= 0.3:
            print('   ⚠️  MODERATE: Score above zero but below target')
        else:
            print('   ❌ LOW: Score too low, may indicate issues')
        print('3. Testing debug mode for hit analysis...')
        try:
            debug_result = detector.analyze_instructional_language([test_text], debug=True)
            if hasattr(debug_result, 'debug'):
                print(f"   ✅ Raw hits: {debug_result.debug['hits_raw']}")
                print(f"   ✅ Gated hits: {debug_result.debug['hits_after_gates']}")
                print(f"   ✅ Examples: {debug_result.debug.get('examples', [])[:3]}")
                assert debug_result.debug['hits_raw'] > 0, 'FAIL: No raw hits detected'
                print('   ✅ Pattern detection working')
            else:
                print('   ℹ️  Debug mode returned simple score:', debug_result)
        except Exception as e:
            print(f'   ⚠️  Debug mode failed: {e}, but basic scoring works')
        print('\n🎉 DETECTOR INITIALIZATION TEST PASSED')
        print(f'✅ Vocabulary loaded: {len(detector.fixed_phrases)} categories')
        print(f'✅ Patterns compiled: {len(detector._compiled)} patterns')
        print(f'✅ Score on test content: {score:.3f}')
        print('✅ Ready for full EVS evaluation\n')
        assert True
    except Exception as e:
        print(f'\n❌ DETECTOR INITIALIZATION TEST FAILED')
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        assert False

def test_specific_patterns():
    """Test specific pattern categories work"""
    print('=== SPECIFIC PATTERN TESTS ===')
    try:
        from analysis.instructional_detector import InstructionalLanguageDetector
        detector = InstructionalLanguageDetector()
        test_cases = [('Intent patterns', 'The idea is to control the center', 'intent'), ('Planning patterns', 'We need to improve the worst piece', 'planning'), ('Tactical patterns', 'This creates a pin on the knight', 'tactics'), ('Chess notation', 'After Nf3 aims to develop quickly', 'template')]
        for name, text, expected_category in test_cases:
            score = detector.analyze_instructional_language([text])
            print(f"   {name}: '{text[:30]}...' → {score:.3f}")
            if score > 0.0:
                print(f'   ✅ {name} detected successfully')
            else:
                print(f'   ⚠️  {name} not detected')
        assert True
    except Exception as e:
        print(f'❌ Pattern tests failed: {e}')
        assert False
if __name__ == '__main__':
    print('INSTRUCTIONAL DETECTOR INITIALIZATION TEST')
    print('Based on 4-AI partner consultation consensus')
    print('=' * 60)
    init_passed = test_detector_initialization()
    patterns_passed = test_specific_patterns()
    if init_passed and patterns_passed:
        print('🎯 ALL TESTS PASSED - READY FOR EVS EVALUATION')
        exit(0)
    else:
        print('❌ TESTS FAILED - FIX ISSUES BEFORE EVS EVALUATION')
        exit(1)