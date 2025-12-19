#!/usr/bin/env python3
"""
Concatenate many PGN files into one giant PGN (no dedupe, no filtering).

Key properties:
- Recursively scans one or more roots for *.pgn files
- Ignores macOS AppleDouble sidecars (._*)
- Binary copy (does not re-encode PGNs)
- Adds a blank-line separator between files
- Heartbeat logging for long-running jobs
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


def normalize_path(path: str) -> Path:
    return Path(path).expanduser()


def iter_pgn_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if not root.exists():
            raise FileNotFoundError(f"Root directory not found: {root}")
        for path in root.rglob("*.pgn"):
            if not path.is_file():
                continue
            # Never touch macOS metadata sidecars.
            if path.name.startswith("._"):
                continue
            yield path


def human_bytes(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{num_bytes} B"


@dataclass(frozen=True)
class Stats:
    files_total: int
    files_written: int
    bytes_written: int
    files_skipped: int


def concat_files(
    *,
    roots: List[Path],
    output: Path,
    manifest_path: Optional[Path],
    log_every_files: int,
    dry_run: bool,
) -> Stats:
    files = list(iter_pgn_files(roots))
    files.sort(key=lambda p: str(p))

    if manifest_path:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("w", encoding="utf-8") as handle:
            for path in files:
                try:
                    size = path.stat().st_size
                except OSError:
                    size = -1
                handle.write(f"{size}\t{path}\n")

    if dry_run:
        return Stats(files_total=len(files), files_written=0, bytes_written=0, files_skipped=0)

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    files_written = 0
    files_skipped = 0
    bytes_written = 0
    last_log_time = time.time()
    start_time = time.time()

    separator = b"\n\n"

    with output.open("wb") as out_handle:
        for idx, path in enumerate(files, start=1):
            try:
                with path.open("rb") as in_handle:
                    chunk = in_handle.read(1024 * 1024)
                    if not chunk:
                        files_skipped += 1
                        continue

                    # Ensure file separation even if a source doesn't end with newline.
                    if files_written > 0:
                        out_handle.write(separator)
                        bytes_written += len(separator)

                    out_handle.write(chunk)
                    bytes_written += len(chunk)

                    while True:
                        chunk = in_handle.read(1024 * 1024)
                        if not chunk:
                            break
                        out_handle.write(chunk)
                        bytes_written += len(chunk)

                files_written += 1
            except Exception as exc:  # noqa: BLE001
                files_skipped += 1
                print(f"⚠️  Skipping unreadable file: {path} ({exc})", file=sys.stderr)

            if log_every_files and idx % log_every_files == 0:
                now = time.time()
                elapsed = now - start_time
                rate = (files_written / elapsed) if elapsed > 0 else 0.0
                since_last = now - last_log_time
                last_log_time = now
                print(
                    f"[heartbeat] scanned={idx:,}/{len(files):,} | "
                    f"written={files_written:,} | skipped={files_skipped:,} | "
                    f"out={human_bytes(bytes_written)} | "
                    f"rate={rate:.1f} files/sec | +{since_last:.1f}s"
                )

    return Stats(
        files_total=len(files),
        files_written=files_written,
        bytes_written=bytes_written,
        files_skipped=files_skipped,
    )


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Concatenate many PGN files into one giant PGN (no dedupe).")
    parser.add_argument(
        "--root",
        action="append",
        required=True,
        help="Root directory containing PGN files (repeatable).",
    )
    parser.add_argument("--output", required=True, help="Destination master PGN file.")
    parser.add_argument(
        "--manifest",
        help="Optional path to write a TSV manifest: <bytes>\\t<path> per PGN file.",
    )
    parser.add_argument(
        "--log-every-files",
        type=int,
        default=200,
        help="Heartbeat interval in scanned files (default: 200).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files (and optionally write manifest) but do not write the output PGN.",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    roots = [normalize_path(r) for r in args.root]
    output = normalize_path(args.output)
    manifest_path = normalize_path(args.manifest) if args.manifest else None

    print("=" * 80)
    print("PGN CORPUS CONCAT (NO DEDUPE)")
    print("=" * 80)
    for idx, root in enumerate(roots, start=1):
        print(f"Root {idx:02d}: {root}")
    print(f"Output  : {output}")
    if manifest_path:
        print(f"Manifest: {manifest_path}")
    print(f"Dry run : {args.dry_run}")
    print("=" * 80)

    start = time.time()
    stats = concat_files(
        roots=roots,
        output=output,
        manifest_path=manifest_path,
        log_every_files=args.log_every_files,
        dry_run=args.dry_run,
    )
    elapsed = time.time() - start

    print()
    print("=" * 80)
    print("FINAL STATISTICS")
    print("=" * 80)
    print(f"Files found     : {stats.files_total:,}")
    print(f"Files written   : {stats.files_written:,}")
    print(f"Files skipped   : {stats.files_skipped:,}")
    if not args.dry_run:
        print(f"Output bytes    : {human_bytes(stats.bytes_written)}")
        print(f"Output path     : {output}")
    print(f"Elapsed         : {elapsed:.1f}s")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

