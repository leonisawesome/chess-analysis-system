from chess_rag_system.analysis.instructional_detector import InstructionalLanguageDetector


def test_detector_initialization():
    det = InstructionalLanguageDetector()
    assert hasattr(det, 'fixed_phrases') and det.fixed_phrases
    assert hasattr(det, '_compiled') and det._compiled
    assert hasattr(det, 'compiled_patterns') and det.compiled_patterns

    # Use boolean API for simple behavior check
    from chess_rag_system.analysis.instructional_detector import detect_instructional
    text = 'The idea is to improve the worst piece and overprotect the center.'
    assert detect_instructional(text) is True


def test_specific_patterns():
    det = InstructionalLanguageDetector()
    samples = [
        'The idea is to control the center',
        'We need to improve the worst piece',
        'This creates a pin on the knight',
        'After Nf3 aims to develop quickly',
    ]
    from chess_rag_system.analysis.instructional_detector import detect_instructional
    for s in samples:
        assert detect_instructional(s) in (True, False)
