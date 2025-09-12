#!/usr/bin/env python3
import json, os, subprocess

FIXTURE = "tests/fixtures/toc_heavy_sample.txt"
ENV = dict(os.environ, DETECTOR_NO_EMBED="1")

def run(args):
    out = subprocess.check_output(["python", "scripts/spotcheck.py", *args, FIXTURE], env=ENV)
    return json.loads(out)

def main():
    prod = run(["--mode", "production"])
    diag = run(["--diagnostic"])

    pr = prod["results"][0]; dr = diag["results"][0]
    pa = pr["metrics"]["toc_hits"]; pb = dr["metrics"]["toc_hits"]
    cap = dr.get("toc_diag_cap"); mode = dr.get("mode")

    print(f"file={pr['label']}")
    print(f"prod_toc_hits={pa} diag_toc_hits={pb} cap={cap} mode={mode}")

    # Assertions: diag metadata present; cap sane; diag never exceeds cap
    assert mode == "diagnostic"
    assert isinstance(cap, int) and 1 <= cap <= 200
    assert pb <= cap
    print("OK")

if __name__ == "__main__":
    main()

