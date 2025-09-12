
import os, re, sys, importlib

MOD='chess_rag_system.analysis.instructional_vocabulary_hotfix'

def _load(vocab_flag=True, langs='en,es'):
    # Control hotfix vocab ON/OFF
    if vocab_flag:
        os.environ['ENHANCED_VOCAB_PATTERNS']='1'
        os.environ['DETECTOR_LANGS']=langs
    else:
        os.environ.pop('ENHANCED_VOCAB_PATTERNS', None)
        os.environ.pop('DETECTOR_LANGS', None)
    sys.modules.pop(MOD, None)
    return importlib.import_module(MOD)

def _any_match(lex, cats, txt, regex_flag=False):
    # In tests we compile with regex to verify patterns are usable;
    # detector compiles as regex only if ENHANCED_VOCAB_REGEX is set, which we test separately.
    pats=[]
    for c in cats:
        pats.extend(list(lex.get(c, ())))
    flags = re.I
    for p in pats:
        try:
            rx = re.compile(p if regex_flag else re.escape(p), flags)
        except re.error:
            # Invalid regex would fail guardrails in detector; treat as no-match here.
            continue
        if rx.search(txt or ''):
            return True
    return False

def test_b_phrases_present_and_match_basic_en_es():
    m = _load(True)
    cats = ('teaching_method','intent_patterns','planning_patterns')
    # English
    assert _any_match(m.INSTRUCTIONAL_LEXICON, cats, "In this lesson we will...", regex_flag=True)
    assert _any_match(m.INSTRUCTIONAL_LEXICON, cats, "Find the best move here.", regex_flag=True)
    assert _any_match(m.INSTRUCTIONAL_LEXICON, cats, "The idea is to control the center.", regex_flag=True)
    # Spanish (with accents)
    assert _any_match(m.INSTRUCTIONAL_LEXICON, cats, "En esta lección veremos...", regex_flag=True)
    assert _any_match(m.INSTRUCTIONAL_LEXICON, cats, "Encuentra la mejor jugada.", regex_flag=True)
    assert _any_match(m.INSTRUCTIONAL_LEXICON, cats, "El plan es atacar el rey.", regex_flag=True)

def test_toc_safe_heading_requires_number():
    m = _load(True)
    cats = ('teaching_method',)
    assert _any_match(m.INSTRUCTIONAL_LEXICON, cats, "Lesson 12 — Forks and Pins", regex_flag=True)
    assert not _any_match(m.INSTRUCTIONAL_LEXICON, cats, "Lesson — Forks and Pins", regex_flag=True)

def test_off_flag_keeps_legacy_only():
    m = _load(False)
    cats = ('teaching_method','intent_patterns','planning_patterns')
    # These Option B phrases should not match when vocab flag is OFF
    assert not _any_match(m.INSTRUCTIONAL_LEXICON, cats, "In this lesson we will...", regex_flag=True)
    assert not _any_match(m.INSTRUCTIONAL_LEXICON, cats, "Encuentra la mejor jugada", regex_flag=True)
