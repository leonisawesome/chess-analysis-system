from chess_rag_system.analysis.instructional_detector import detect_instructional


def test_toc_like_text_is_non_instructional():
    txt = (
        "Contents\n"
        "Chapter 1  Introduction .......... 1\n"
        "Chapter 2  Strategy .............. 17\n"
        "Capítulo 3  Estructuras .......... 25\n"
        "Appendix A  Endgames ............. 201\n"
        "pp. 210–214\n"
    )
    assert detect_instructional(txt) is False

