import os
from chess_rag_system.analysis.instructional_detector import InstructionalLanguageDetector

SAMPLE = "The idea is to improve the worst piece after Nf3."

def test_compilation_counts_present():
    det = InstructionalLanguageDetector.factory()
    assert hasattr(det, "compiled_patterns")
    cats = list(det.compiled_patterns.keys())
    assert len(cats) >= 1
    total = sum(len(v) for v in det.compiled_patterns.values())
    assert total >= 1

def test_raw_matches_and_nonzero_hits():
    det = InstructionalLanguageDetector.factory()
    raw = det.debug_raw_matches(SAMPLE)
    hits = sum(len(v) for v in raw.values())
    assert hits >= 1, f"Expected >=1 raw hits, got {hits}, raw={raw}"
