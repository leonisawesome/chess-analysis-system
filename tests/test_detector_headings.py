from chess_rag_system.analysis.instructional_detector import detect_instructional

def test_multiple_headings_triggers_instructional():
    txt = (
        "Capítulo 1: Introducción\n"
        "Sección 1.1 — Objetivos\n"
        "Resumen del capítulo: ideas clave y plan general."
    )
    assert detect_instructional(txt) is True
