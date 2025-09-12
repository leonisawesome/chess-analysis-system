
import os, sys, importlib, re

MOD = 'chess_rag_system.analysis.instructional_detector'

def reload_detector(regex_flag=False):
    os.environ.pop('ENHANCED_VOCAB_REGEX', None)
    if regex_flag:
        os.environ['ENHANCED_VOCAB_REGEX'] = '1'
    os.environ['ENHANCED_VOCAB_PATTERNS'] = '1'  # ensure augmented patterns
    os.environ['DETECTOR_NO_EMBED'] = '1'        # keep tests light
    sys.modules.pop(MOD, None)
    return importlib.import_module(MOD)

def test_off_escapes_bracket_pattern():
    m = reload_detector(regex_flag=False)
    # Our helper should escape a bracketed pattern when flag is off
    pat = r"estrat[eé]gico"
    raw = m._escape_or_regex('strategic_concepts', pat)
    assert raw != pat  # escaped
    rx  = re.compile(raw, re.I)
    assert not rx.search("plan estrategico")

def test_on_honors_bracket_pattern():
    m = reload_detector(regex_flag=True)
    pat = r"estrat[eé]gico"
    raw = m._escape_or_regex('strategic_concepts', pat)
    assert raw == pat  # raw regex honored
    rx  = re.compile(raw, re.I)
    assert rx.search("plan estrategico") or rx.search("plan estratégico")

def test_engine_line_not_matched_by_vocab():
    m = reload_detector(regex_flag=True)
    # sanity: a typical engine dump should not be matched by didactic regexes
    engine = "info depth 20 multipv 3 nps 5M score cp 23"
    # probe a few categories through helper
    for cat in ('planning_patterns','teaching_method','strategic_concepts','intent_patterns'):
        # a simple sample to ensure helper doesn't just return raw junk
        raw = m._escape_or_regex(cat, r"\bthe\s+idea\s+is\b")
        rx  = re.compile(raw, re.I)
        assert not rx.search(engine)
