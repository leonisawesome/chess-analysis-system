import multiprocessing as mp
from chess_rag_system.analysis.instructional_detector import InstructionalLanguageDetector

SAMPLE = "The idea is to improve the worst piece after Nf3."

def _worker_check(_):
    det = InstructionalLanguageDetector.factory()
    cats = list(det.compiled_patterns.keys())
    total = sum(len(v) for v in det.compiled_patterns.values())
    raw = det.debug_raw_matches(SAMPLE)
    hits = sum(len(v) for v in raw.values())
    return {"cats": len(cats), "total": total, "hits": hits}

def test_multiprocess_factory_compiles_patterns():
    with mp.Pool(processes=2) as pool:
        rs = pool.map(_worker_check, [None, None])
    assert all(r["cats"] >= 1 and r["total"] >= 1 for r in rs), rs
    assert all(r["hits"] >= 1 for r in rs), rs
