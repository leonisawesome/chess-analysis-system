from chess_rag_system.analysis.instructional_detector import detect_instructional


def test_annotation_symbols_trigger_instructional():
    # Keep moves short so pgn_ratio stays below the heavy cutoff,
    # but include clear annotation markers and comments.
    txt = (
        "{Idea: central control} 1.e4 e5 2.Nf3 Nc6 3.Bb5 a6?! "
        "{Avoid ...d6? early} 4.Ba4 Nf6!! +="
    )
    assert detect_instructional(txt) is True

