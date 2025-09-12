import importlib, os, re, sys
MOD='chess_rag_system.analysis.instructional_vocabulary_hotfix'
def _reload(flag='1', langs='en,es'):
    if flag:
        os.environ['ENHANCED_VOCAB_PATTERNS']=flag
        os.environ['DETECTOR_LANGS']=langs
    else:
        os.environ.pop('ENHANCED_VOCAB_PATTERNS', None)
        os.environ.pop('DETECTOR_LANGS', None)
    sys.modules.pop(MOD,None); return importlib.import_module(MOD)
def _any(lex,cats,txt):
    pats=[]; [pats.extend(list(lex.get(c,()))) for c in cats]
    return any(re.search(p,txt,re.I) for p in pats)
def test_es_positive():
    m=_reload('1'); txt='Capítulo 3 — Plan estratégico. Juegan las Blancas. Encuentra la mejor jugada. Ver el diagrama y explica la idea.'
    assert _any(m.INSTRUCTIONAL_LEXICON,('planning_patterns','teaching_method','strategic_concepts','intent_patterns'),txt)
def test_en_positive():
    m=_reload('1'); txt='The main idea is to control the center; Exercise 5. This section explains how to proceed.'
    assert _any(m.INSTRUCTIONAL_LEXICON,('planning_patterns','teaching_method','strategic_concepts','intent_patterns'),txt)
def test_engine_negative():
    m=_reload('1'); txt='info depth 20 multipv 3 nps 5M score cp 23'
    assert not _any(m.INSTRUCTIONAL_LEXICON,('planning_patterns','teaching_method','strategic_concepts','intent_patterns'),txt)
