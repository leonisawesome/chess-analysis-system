#!/usr/bin/env python3
"""
Combine multiple PGN files into a deduplicated master PGN.

Features:
- Recursively scans a root directory for .pgn files
- Detects duplicates via MD5 hash
- Skips non-English/Spanish PGNs by default (logged + copied to foreign dir)
- Copies skipped files (encoding/permission errors) for manual triage
- Emits CSV reports for duplicates, skipped files, and foreign-language files
- Heartbeat logging for long-running jobs

Example:
python scripts/combine_pgn_corpus.py \\
    --root "/Volumes/chess/1Modern Chess" \\
    --output "/Volumes/T7 Shield/rag/databases/pgn/1new/modern.pgn" \\
    --duplicates "/Volumes/T7 Shield/rag/databases/pgn/1new/modern_duplicates.csv" \\
    --skipped "/Volumes/T7 Shield/rag/databases/pgn/1new/modern_skipped.csv" \\
    --foreign "/Volumes/T7 Shield/rag/databases/pgn/1new/modern_foreign.csv" \\
    --skipped-dir "/Volumes/T7 Shield/rag/databases/pgn/1new/skipped_pgns" \\
    --foreign-dir "/Volumes/T7 Shield/rag/databases/pgn/1new/foreign_pgns"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    from langdetect import detect as detect_language  # type: ignore
except ImportError:  # pragma: no cover
    detect_language = None

ALLOWED_LANGS = {"en", "es"}


def normalize_path(path: str) -> Path:
    return Path(path).expanduser()


def iter_pgn_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        raise FileNotFoundError(f"Root directory not found: {root}")
    for path in root.rglob("*.pgn"):
        if path.is_file():
            yield path


def md5_file(path: Path, chunk_size: int = 8192) -> str:
    hasher = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_csv(path: Path, rows: Iterable[Tuple[str, str]], headers: Tuple[str, str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)


def guess_language(text: str) -> Optional[str]:
    if not detect_language:
        return None
    snippet = text[:10_000]
    try:
        return detect_language(snippet)
    except Exception:
        return None


def safe_copy(src: Path, dst_dir: Optional[str]):
    if not dst_dir:
        return
    try:
        target_dir = Path(dst_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        dst = target_dir / src.name
        try:
            shutil.copy2(src, dst)
        except PermissionError:
            shutil.copy(src, dst)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  Failed to copy {src} -> {dst_dir}: {exc}")


def combine_pgns(
    root: Path,
    output: Path,
    duplicates_report: Path,
    skipped_report: Path,
    foreign_report: Path,
    *,
    log_every: int = 200,
    keep_foreign: bool = False,
    skipped_dir: Optional[str] = None,
    foreign_dir: Optional[str] = None,
) -> Dict[str, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    seen_hashes: Dict[str, str] = {}
    duplicates: List[Tuple[str, str]] = []
    skipped: List[Tuple[str, str]] = []
    foreign: List[Tuple[str, str]] = []
    total = 0
    unique = 0

    if output.exists():
        output.unlink()

    with output.open("w", encoding="utf-8") as master:
        for file_path in iter_pgn_files(root):
            total += 1
            if log_every and total % log_every == 0:
                print(
                    f"[heartbeat] Processed {total:,} files | "
                    f"unique={unique:,} | duplicates={len(duplicates):,} | "
                    f"skipped={len(skipped):,} | foreign={len(foreign):,}"
                )

            try:
                digest = md5_file(file_path)
            except Exception as exc:  # noqa: BLE001
                skipped.append((str(file_path), f"hash_error: {exc}"))
                safe_copy(file_path, skipped_dir)
                continue

            if digest in seen_hashes:
                duplicates.append((str(file_path), seen_hashes[digest]))
                continue

            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception as exc:  # noqa: BLE001
                skipped.append((str(file_path), f"read_error: {exc}"))
                safe_copy(file_path, skipped_dir)
                continue

            lang = guess_language(text)
            if lang and lang not in ALLOWED_LANGS:
                foreign.append((str(file_path), lang))
                safe_copy(file_path, foreign_dir)
                if not keep_foreign:
                    continue

            seen_hashes[digest] = str(file_path)
            unique += 1
            if unique > 1:
                master.write("\n\n")
            master.write(text)

    write_csv(duplicates_report, duplicates, headers=("duplicate_path", "original_path"))
    write_csv(skipped_report, skipped, headers=("path", "error"))
    write_csv(foreign_report, foreign, headers=("path", "language"))

    return {
        "total": total,
        "unique": unique,
        "duplicates": len(duplicates),
        "skipped": len(skipped),
        "foreign": len(foreign),
    }


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Combine PGNs with deduplication and language filtering.")
    parser.add_argument("--root", required=True, help="Root directory containing PGN files.")
    parser.add_argument("--output", required=True, help="Destination master PGN file.")
    parser.add_argument("--duplicates", required=True, help="CSV path for duplicate report.")
    parser.add_argument("--skipped", required=True, help="CSV path for skipped files.")
    parser.add_argument("--foreign", required=True, help="CSV path for foreign-language files.")
    parser.add_argument("--skipped-dir", help="Directory to copy skipped files into.")
    parser.add_argument("--foreign-dir", help="Directory to copy foreign-language files into.")
    parser.add_argument("--keep-foreign", action="store_true", help="Include foreign-language files in master PGN.")
    parser.add_argument("--log-every", type=int, default=200, help="Heartbeat interval (default: 200 files).")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    root = normalize_path(Path(args.root))
    output = normalize_path(Path(args.output))
    duplicates = normalize_path(Path(args.duplicates))
    skipped = normalize_path(Path(args.skipped))
    foreign = normalize_path(Path(args.foreign))

    print("=" * 80)
    print("PGN CORPUS COMBINER")
    print("=" * 80)
    print(f"Root directory : {root}")
    print(f"Output PGN     : {output}")
    print(f"Duplicates CSV : {duplicates}")
    print(f"Skipped CSV    : {skipped}")
    print(f"Foreign CSV    : {foreign}")
    print("=" * 80)

    stats = combine_pgns(
        root,
        output,
        duplicates,
        skipped,
        foreign,
        log_every=args.log_every,
        keep_foreign=args.keep_foreign,
        skipped_dir=args.skipped_dir,
        foreign_dir=args.foreign_dir,
    )

    print()
    print("=" * 80)
    print("FINAL STATISTICS")
    print("=" * 80)
    print(f"✅ Unique files written : {stats['unique']:,}")
    print(f"🔄 Duplicates detected  : {stats['duplicates']:,}")
    print(f"⚠️  Files skipped        : {stats['skipped']:,}")
    print(f"🌐 Foreign-language skip : {stats['foreign']:,}")
    print(f"📁 Total files processed : {stats['total']:,}")
    print("=" * 80)

    if stats["duplicates"]:
        print(f"📋 Duplicate details: {duplicates}")
    if stats["skipped"]:
        print(f"📋 Skipped file details: {skipped}")
    if stats["foreign"]:
        print(f"📋 Foreign-language details: {foreign}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
