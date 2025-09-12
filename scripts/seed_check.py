import os, csv, sys, importlib, re, json

POS_VALS = {'1','true','yes','y','pos','positive','instructional','instr','didactic'}
NEG_VALS = {'0','false','no','n','neg','negative','non_instructional','non-instructional','noninstructional'}
TEXT_CANDIDATES  = ('text','content','snippet','body')
LABEL_CANDIDATES = ('label','is_instructional','instructional','y','target','class','category','gold','truth')


def load(flag: str):
    os.environ['ENHANCED_VOCAB_PATTERNS'] = flag
    modname = 'chess_rag_system.analysis.instructional_vocabulary_hotfix'
    sys.modules.pop(modname, None)
    m = importlib.import_module(modname)
    lex = m.INSTRUCTIONAL_LEXICON
    pats = []
    for k in ('planning_patterns','teaching_method','strategic_concepts','intent_patterns'):
        pats.extend(list(lex.get(k, ())))
    return [re.compile(p, re.I) for p in pats]


def any_match(pats, text: str) -> bool:
    return any(p.search(text or '') for p in pats)


def pick_col(cands, fieldnames):
    return next((c for c in cands if c in fieldnames), None)


def is_positive(val: str) -> bool:
    v = (val or '').strip().lower()
    if v in POS_VALS:
        return True
    if v in NEG_VALS:
        return False
    # numeric fallback (treat >0 as positive)
    try:
        return float(v) > 0
    except Exception:
        return False


def main():
    p0 = load('0')
    p1 = load('1')
    path = 'data/labels/instructional_seed.csv'
    hits0 = hits1 = pos_total = 0
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        r = csv.DictReader(f)
        text_col  = pick_col(TEXT_CANDIDATES,  r.fieldnames)
        label_col = pick_col(LABEL_CANDIDATES, r.fieldnames)
        if not text_col or not label_col:
            print(json.dumps({'error':'missing expected columns','fields':r.fieldnames}, indent=2))
            return 2
        for row in r:
            if not is_positive(row.get(label_col,'')):
                continue
            pos_total += 1
            txt = row.get(text_col,'')
            if any_match(p0, txt):
                hits0 += 1
            if any_match(p1, txt):
                hits1 += 1

    print(json.dumps({
        'csv': path,
        'text_col': text_col,
        'label_col': label_col,
        'positives_total': pos_total,
        'legacy_hits_on_positives': hits0,
        'enhanced_hits_on_positives': hits1,
        'delta': hits1 - hits0
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
