import importlib, os, re, sys
MOD='chess_rag_system.analysis.instructional_vocabulary_hotfix'
def _reload(flag='1', langs='en,es'):
    if flag:
        os.environ['ENHANCED_VOCAB_PATTERNS']=flag
        os.environ['DETECTOR_LANGS']=langs
    else:
        os.environ.pop('ENHANCED_VOCAB_PATTERNS', None)
        os.environ.pop('DETECTOR_LANGS', None)
    sys.modules.pop(MOD, None); return importlib.import_module(MOD)
def _any(lex,cats,txt):
    pats=[]; [pats.extend(list(lex.get(c,()))) for c in cats]
    return any(re.search(p, txt, re.I) for p in pats)

def test_en_extra_phrases():
    m=_reload('1')
    txt = 'Encuentra la mejor jugada. Ver el diagrama.'
    assert _any(m.INSTRUCTIONAL_LEXICON, ('planning_patterns','teaching_method','intent_patterns'), txt)

def test_es_extra_phrases():
    m=_reload('1')
    txt = 'Juegan las Blancas. Observa la idea y ver el diagrama.'
    assert _any(m.INSTRUCTIONAL_LEXICON, ('planning_patterns','teaching_method','intent_patterns'), txt)
