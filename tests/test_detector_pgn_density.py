from chess_rag_system.analysis.instructional_detector import detect_instructional


def test_high_pgn_ratio_is_non_instructional():
    txt = "1.e4 e5 2.Nf3 Nc6 3.Bb5 a6 4.Ba4 Nf6 5.O-O Be7 6.Re1 b5 7.Bb3 d6"
    assert detect_instructional(txt) is False


def test_didactic_boost_is_instructional():
    txt = (
        "Typical plan: improve the worst-placed piece, remember the key idea "
        "and avoid common mistakes."
    )
    assert detect_instructional(txt) is True


def test_mixed_text_runs_without_exception():
    txt = (
        "Plan: attack the center with c4; but 1...e5 2.Nf3 is also common. "
        "Typical principle: fight for the center."
    )
    out = detect_instructional(txt)
    assert out in (True, False)

