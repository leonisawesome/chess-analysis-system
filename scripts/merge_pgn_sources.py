#!/usr/bin/env python3
"""
Merge every unique PGN under a selected directory into a dated master file.

The script always:
- Prompts for the PGN source directory (1. /Users/leon/Downloads/ZListo, 2. /Volumes/chess/zTemp, or a custom path)
- Recursively scans the chosen directory for *.pgn files (skipping ._* metadata)
- Hashes each file via MD5 to deduplicate content
- Writes unique PGNs (UTF-8 text) into /Volumes/T7 Shield/rag/databases/pgn/1new/<MM-DD-YY>_new.pgn
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Tuple

DEST_DIR = Path("/Volumes/T7 Shield/rag/databases/pgn/1new")
DATE_FORMAT = "%m-%d-%y"
SOURCE_CHOICES: Tuple[Tuple[str, Path], ...] = (
    ("1", Path("/Users/leon/Downloads/ZListo")),
    ("2", Path("/Volumes/chess/zTemp")),
)


def iter_pgn_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        raise FileNotFoundError(f"Source directory not found: {root}")
    for path in root.rglob("*.pgn"):
        if path.is_file() and not path.name.startswith("._"):
            yield path


def md5_file(path: Path, chunk_size: int = 8192) -> str:
    hasher = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_master_file(source_root: Path, destination: Path) -> Dict[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)

    seen_hashes: Dict[str, str] = {}
    stats = {"total_files": 0, "unique_files": 0}

    with destination.open("w", encoding="utf-8") as master:
        for file_path in iter_pgn_files(source_root):
            stats["total_files"] += 1
            digest = md5_file(file_path)
            if digest in seen_hashes:
                continue

            text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                continue

            seen_hashes[digest] = str(file_path)
            stats["unique_files"] += 1
            if stats["unique_files"] > 1:
                master.write("\n\n")
            master.write(text)

    return stats


def prompt_source_root() -> Path:
    print("Where are the staged PGNs located?")
    for key, path in SOURCE_CHOICES:
        print(f"  {key}: {path}")
    print("  3: Enter a custom absolute path")

    while True:
        selection = input("Enter selection (1, 2, or 3 for custom): ").strip()
        for key, path in SOURCE_CHOICES:
            if selection == key:
                return path
        if selection == "3":
            custom = input("Enter absolute directory path: ").strip()
            custom_path = Path(custom).expanduser()
            if not custom_path.exists():
                print(f"Path not found: {custom_path}")
                continue
            if not custom_path.is_dir():
                print(f"Not a directory: {custom_path}")
                continue
            return custom_path
        print("Invalid choice. Please enter 1, 2, or 3.")


def resolve_output_name(custom_name: str | None) -> Path:
    if custom_name:
        return DEST_DIR / custom_name
    today = datetime.now().strftime(DATE_FORMAT)
    return DEST_DIR / f"{today}_new.pgn"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Merge unique PGNs into a single file.")
    parser.add_argument(
        "--output-name",
        help="Override default output filename (e.g., chessable_merge.pgn).",
    )
    args = parser.parse_args()

    source_root = prompt_source_root()
    destination = resolve_output_name(args.output_name)

    print("=" * 72)
    print("ZLISTO PGN MERGER")
    print("=" * 72)
    print(f"Source directory : {source_root}")
    print(f"Destination file : {destination}")

    stats = write_master_file(source_root, destination)
    print(
        f"✅ Done. Processed {stats['total_files']:,} files "
        f"({stats['unique_files']:,} unique)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
