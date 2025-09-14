#!/usr/bin/env bash
set -euo pipefail

SRC="/Volumes/T7 Shield/1PGN/1test"
OUT=".local_out"
mkdir -p "$OUT" "$PWD/.tmp" "$PWD/.cache"
export TMPDIR="$PWD/.tmp"
export XDG_CACHE_HOME="$PWD/.cache"

# Build manifest of up to 50 files (bias toward PGN)
{
  find "$SRC" -type f -iname '*.pgn' -print0
  find "$SRC" -type f \( -iname '*.pdf' -o -iname '*.txt' -o -iname '*.md' \) -print0
} | tr '\0' '\n' \
  | awk 'BEGIN{srand()} {print rand(),$0}' \
  | sort -k1,1 \
  | cut -d" " -f2- \
  | head -n 50 > "$OUT/slice_manifest.txt"

# Run production mode
: > "$OUT/prod.jsonl"
DETECTOR_NO_EMBED=1 while IFS= read -r f; do
  python scripts/spotcheck.py --mode production "$f" >> "$OUT/prod.jsonl"
done < "$OUT/slice_manifest.txt"

# Run diagnostic mode
: > "$OUT/diag.jsonl"
DETECTOR_NO_EMBED=1 while IFS= read -r f; do
  python scripts/spotcheck.py --diagnostic "$f" >> "$OUT/diag.jsonl"
done < "$OUT/slice_manifest.txt"

# Produce summary CSV (no jq required)
python - <<'PY'
import json, csv
rows=[["file","decision","pgn_ratio","didactic_per_1k","heading_hits","toc_hits","annot_hits","mode","toc_diag_cap"]]
for fp in (".local_out/prod.jsonl",".local_out/diag.jsonl"):
    with open(fp) as f:
        for line in f:
            d=json.loads(line); r=d["results"][0]; m=r["metrics"]
            rows.append([r["label"], r["decision"], m["pgn_ratio"], m["didactic_per_1k"], m["heading_hits"], m["toc_hits"], m["annot_hits"], r.get("mode",""), r.get("toc_diag_cap","")])
with open(".local_out/summary.csv","w",newline="") as f:
    csv.writer(f).writerows(rows)
print("Wrote .local_out/summary.csv")
PY

# Quick health prints
echo "== Decision counts (prod) ==" && \
python - <<'PY'
import json,collections
c=collections.Counter()
with open(".local_out/prod.jsonl") as f:
    for line in f:
        c[json.loads(line)["results"][0]["decision"]]+=1
print(c)
PY
echo "== Top 10 didactic density (prod) ==" && \
python - <<'PY'
import json
rows=[]
with open(".local_out/prod.jsonl") as f:
    for line in f:
        d=json.loads(line); r=d["results"][0]
        rows.append((r["metrics"]["didactic_per_1k"], r["label"]))
for score,label in sorted(rows, reverse=True)[:10]:
    print(f"{score:>4}  {label}")
PY
