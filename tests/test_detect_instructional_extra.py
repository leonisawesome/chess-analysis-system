from chess_rag_system.analysis.instructional_detector import detect_instructional, _get_detector


def test_detect_normalization_and_compilation():
    # Ensures unicode dash normalization + manoeuvre detection path is covered
    txt = "Typical manoeuvre: Nd2–f1–g3 to pressure the kingside"
    assert detect_instructional(txt) is True

    # Touch compilation diagnostics path
    det = _get_detector()
    det._ensure_compiled()
    assert hasattr(det, 'compiled_patterns') and det.compiled_patterns

