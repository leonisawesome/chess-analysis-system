import os
import multiprocessing as mp
from chess_rag_system.analysis.instructional_detector import InstructionalLanguageDetector, detect_instructional


def _worker_check(text):
    det = InstructionalLanguageDetector()
    compiled = len(getattr(det, '_compiled', []))
    label = detect_instructional(text)
    return compiled, label


def test_multiprocessing_detector():
    mp.set_start_method('spawn', force=True)
    text = 'The idea is to improve the worst piece and overprotect the center.'
    with mp.Pool(processes=2) as pool:
        results = pool.map(_worker_check, [text, text])
    for compiled, label in results:
        assert compiled > 0 and isinstance(label, bool)
