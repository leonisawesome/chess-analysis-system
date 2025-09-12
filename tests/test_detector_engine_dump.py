from chess_rag_system.analysis.instructional_detector import detect_instructional


def test_engine_dump_is_non_instructional():
    txt = (
        "info depth 28 seldepth 38 multipv 1 score cp 47 nodes 18437762 nps 6400000 "
        "hashfull 972 time 2879 pv e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7\n"
        "bestmove e4 ponder e5"
    )
    assert detect_instructional(txt) is False

