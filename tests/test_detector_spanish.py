from chess_rag_system.analysis.instructional_detector import detect_instructional

def test_spanish_didactic_sentence_is_instructional():
    txt = "Plan típico: recuerda la idea clave y evita errores comunes; la estrategia correcta mejora la estructura."
    assert detect_instructional(txt) is True
