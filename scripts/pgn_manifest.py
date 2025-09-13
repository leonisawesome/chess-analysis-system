#!/usr/bin/env python3
import os
import sys
import time
import json
import argparse
import random
import re
import tempfile
import heapq
from pathlib import Path


# ------------------ Key functions ------------------

_NUM_RE = re.compile(r"\d+")


def numeric_key_str(name: str) -> str:
    """Return a natural-sort-friendly key as a single string.

    - Lowercases the name
    - Zero-pads all digit runs to fixed width so lexicographic compare matches numeric
    """
    name = name.lower()
    return _NUM_RE.sub(lambda m: f"{int(m.group(0)):020d}", name)


def splitmix64(x: int) -> int:
    x = (x + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9 & 0xFFFFFFFFFFFFFFFF
    x = (x ^ (x >> 27)) * 0x94D049BB133111EB & 0xFFFFFFFFFFFFFFFF
    return x ^ (x >> 31)


def shuffle_key(seed: int, s: str) -> int:
    """Deterministic 64-bit integer key from seed + UTF-8 bytes of path string."""
    b = s.encode("utf-8", "surrogatepass")
    h = seed & 0xFFFFFFFFFFFFFFFF
    for byte in b:
        h = splitmix64(h ^ byte)
    return h


# ------------------ Discovery ------------------


def list_pgns(src: Path):
    for root, _dirs, files in os.walk(src, followlinks=False):
        for n in files:
            if not n.lower().endswith(".pgn"):
                continue
            p = Path(root) / n
            try:
                if p.is_file():
                    yield p
            except OSError:
                # permission / transient FS issues → skip
                continue


# ------------------ Sorting ------------------


def external_sort(paths_iter, out_path: Path, mode: str, seed: int, chunk_max: int = 500_000):
    """Chunked external sort using a key-aware merge.

    Writes only path lines to temp files; during merge we recompute the key
    from each line so that the global order respects the intended key.
    """
    tmps = []
    cur = []
    cnt = 0

    if mode == "numeric":
        key_path = lambda s: numeric_key_str(Path(s).name)
    else:
        key_path = lambda s: shuffle_key(seed, s)

    # Build and spill sorted chunks
    for p in paths_iter:
        s = str(p)
        cur.append((key_path(s), s))
        cnt += 1
        if len(cur) >= chunk_max:
            cur.sort(key=lambda t: t[0])
            fd, tname = tempfile.mkstemp(prefix="pgn_chunk_", suffix=".txt")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for _k, spath in cur:
                    f.write(spath + "\n")
            tmps.append(tname)
            cur.clear()
    if cur:
        cur.sort(key=lambda t: t[0])
        fd, tname = tempfile.mkstemp(prefix="pgn_chunk_", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for _k, spath in cur:
                f.write(spath + "\n")
        tmps.append(tname)
        cur.clear()

    # Merge chunks with the same key logic applied to each line
    files = [open(t, "r", encoding="utf-8") for t in tmps]
    try:
        iters = ((line.rstrip("\n") for line in fh) for fh in files)
        merged = heapq.merge(*iters, key=key_path)
        with open(out_path, "w", encoding="utf-8") as out:
            for line in merged:
                out.write(line + "\n")
    finally:
        for fh in files:
            try:
                fh.close()
            except Exception:
                pass
        for t in tmps:
            try:
                os.unlink(t)
            except Exception:
                pass
    return cnt


# ------------------ CLI ------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=["numeric", "shuffle"], default="shuffle")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--external", action="store_true", help="use chunked external merge")
    ap.add_argument("--chunk-size-mb", type=int, default=0, help="approximate memory per chunk")
    ap.add_argument("--report-json", default="")
    args = ap.parse_args()

    t0 = time.time()
    src = Path(args.src).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "pgn_manifest.txt"

    it = list_pgns(src)
    if args.external:
        # Derive an approximate chunk size from MB hint; keep a sane minimum
        if args.chunk_size_mb and args.chunk_size_mb > 0:
            approx_per_path = 220  # conservative average bytes per in-memory tuple
            chunk_max = max(1_000, (args.chunk_size_mb * 1024 * 1024) // approx_per_path)
        else:
            chunk_max = 500_000
        n = external_sort(it, manifest, mode=args.mode, seed=args.seed, chunk_max=chunk_max)
    else:
        paths = list(it)
        if args.mode == "numeric":
            paths.sort(key=lambda p: numeric_key_str(p.name))
        else:
            random.seed(args.seed)
            random.shuffle(paths)
        with open(manifest, "w", encoding="utf-8") as f:
            for p in paths:
                f.write(str(p) + "\n")
        n = len(paths)

    report = {
        "src": str(src),
        "out": str(out_dir),
        "mode": args.mode,
        "seed": args.seed,
        "external": args.external,
        "files_manifested": n,
        "duration_sec": round(time.time() - t0, 3),
    }
    if args.report_json:
        with open(args.report_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

