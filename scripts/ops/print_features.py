#!/usr/bin/env python3
import sys, json, pathlib
sys.path.insert(0, '.')
from chess_rag_system.analysis.instructional_detector import detect_instructional
from chess_rag_system.analysis._signals import pgn_ratio

def main(paths):
    out=[]
    for p in paths:
        P=pathlib.Path(p);
        if not P.exists(): continue
        text = P.read_text(encoding='utf-8', errors='ignore')
        decision = detect_instructional(text)
        pr = pgn_ratio(text)
        out.append({"path":str(P), "pgn_ratio":round(pr,4), "decision": decision})
    print(json.dumps(out, indent=2))

if __name__=="__main__":
    main(sys.argv[1:])