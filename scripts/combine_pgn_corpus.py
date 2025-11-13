#!/usr/bin/env python3
"""
Combine multiple PGN files into a single deduplicated master file.

Features:
- Recursively walks directory tree to find all .pgn files
- Detects duplicates using MD5 hash of file contents
- Streams unique files into output master PGN
- Generates CSV reports for duplicates and skipped files
- Progress heartbeat logging for long-running operations
"""

import os
import sys
import argparse
import hashlib
import csv
from pathlib import Path
from typing import Set, Dict, Tuple, List


def compute_file_hash(file_path: str) -> str:
    """Compute MD5 hash of file contents for duplicate detection."""
    md5_hash = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b''):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except Exception as e:
        raise IOError(f"Failed to hash file: {e}")


def find_pgn_files(root_dir: str) -> List[str]:
    """Recursively find all .pgn files in directory tree."""
    pgn_files = []
    root_path = Path(root_dir)

    if not root_path.exists():
        raise FileNotFoundError(f"Root directory does not exist: {root_dir}")

    for file_path in root_path.rglob("*.pgn"):
        if file_path.is_file():
            pgn_files.append(str(file_path))

    return sorted(pgn_files)


def combine_pgn_files(
    root_dir: str,
    output_file: str,
    duplicates_csv: str,
    skipped_csv: str,
    log_every: int = 200
) -> Tuple[int, int, int]:
    """
    Combine PGN files with deduplication.

    Returns:
        (unique_count, duplicate_count, skipped_count)
    """
    print(f"🔍 Scanning for PGN files in: {root_dir}")
    pgn_files = find_pgn_files(root_dir)
    total_files = len(pgn_files)
    print(f"📊 Found {total_files} PGN files")

    if total_files == 0:
        print("⚠️  No PGN files found")
        return 0, 0, 0

    # Track seen hashes and their original file paths
    seen_hashes: Dict[str, str] = {}
    duplicates: List[Tuple[str, str]] = []
    skipped: List[Tuple[str, str]] = []
    unique_count = 0

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    print(f"📝 Writing unique PGN files to: {output_file}")
    print(f"⏱  Progress updates every {log_every} files...")
    print()

    with open(output_file, 'w', encoding='utf-8') as out_f:
        for idx, pgn_path in enumerate(pgn_files, 1):
            # Heartbeat logging
            if idx % log_every == 0:
                print(f"[heartbeat] Processed {idx}/{total_files} files "
                      f"({unique_count} unique, {len(duplicates)} duplicates, "
                      f"{len(skipped)} skipped)")

            try:
                # Compute hash for duplicate detection
                file_hash = compute_file_hash(pgn_path)

                if file_hash in seen_hashes:
                    # Duplicate detected
                    original_path = seen_hashes[file_hash]
                    duplicates.append((pgn_path, original_path))
                    continue

                # New unique file - add to output
                seen_hashes[file_hash] = pgn_path

                # Read and append content
                with open(pgn_path, 'r', encoding='utf-8') as in_f:
                    content = in_f.read()

                    # Ensure proper spacing between games
                    if unique_count > 0:
                        out_f.write('\n\n')

                    out_f.write(content)
                    unique_count += 1

            except UnicodeDecodeError as e:
                skipped.append((pgn_path, f"Encoding error: {e}"))
                print(f"⚠️  Skipped (encoding): {pgn_path}")
            except PermissionError as e:
                skipped.append((pgn_path, f"Permission denied: {e}"))
                print(f"⚠️  Skipped (permission): {pgn_path}")
            except Exception as e:
                skipped.append((pgn_path, f"Error: {e}"))
                print(f"⚠️  Skipped (error): {pgn_path} - {e}")

    # Final progress
    print()
    print(f"[heartbeat] Processed {total_files}/{total_files} files "
          f"({unique_count} unique, {len(duplicates)} duplicates, "
          f"{len(skipped)} skipped)")
    print()

    # Write duplicates report
    if duplicates:
        print(f"📋 Writing duplicates report: {duplicates_csv}")
        with open(duplicates_csv, 'w', newline='', encoding='utf-8') as csv_f:
            writer = csv.writer(csv_f)
            writer.writerow(['duplicate_path', 'original_path'])
            writer.writerows(duplicates)

    # Write skipped files report
    if skipped:
        print(f"📋 Writing skipped files report: {skipped_csv}")
        with open(skipped_csv, 'w', newline='', encoding='utf-8') as csv_f:
            writer = csv.writer(csv_f)
            writer.writerow(['skipped_path', 'reason'])
            writer.writerows(skipped)

    return unique_count, len(duplicates), len(skipped)


def main():
    parser = argparse.ArgumentParser(
        description='Combine PGN files with deduplication',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python combine_pgn_corpus.py \\
      --root "/Volumes/chess/1Chessable" \\
      --output "/Volumes/T7 Shield/rag/pgn/1new/chessable_master.pgn" \\
      --duplicates "chessable_duplicates.csv" \\
      --skipped "chessable_skipped.csv" \\
      --log-every 200
        """
    )

    parser.add_argument(
        '--root',
        required=True,
        help='Root directory to scan for PGN files'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output master PGN file path'
    )
    parser.add_argument(
        '--duplicates',
        required=True,
        help='CSV file for duplicate files report'
    )
    parser.add_argument(
        '--skipped',
        required=True,
        help='CSV file for skipped files report'
    )
    parser.add_argument(
        '--log-every',
        type=int,
        default=200,
        help='Heartbeat logging interval (default: 200)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("PGN CORPUS COMBINER")
    print("=" * 80)
    print(f"Root directory: {args.root}")
    print(f"Output file: {args.output}")
    print(f"Duplicates CSV: {args.duplicates}")
    print(f"Skipped CSV: {args.skipped}")
    print("=" * 80)
    print()

    try:
        unique, duplicates, skipped = combine_pgn_files(
            args.root,
            args.output,
            args.duplicates,
            args.skipped,
            args.log_every
        )

        print()
        print("=" * 80)
        print("FINAL STATISTICS")
        print("=" * 80)
        print(f"✅ Unique files written: {unique}")
        print(f"🔄 Duplicates detected: {duplicates}")
        print(f"⚠️  Files skipped: {skipped}")
        print(f"📁 Total files processed: {unique + duplicates + skipped}")
        print("=" * 80)

        if duplicates > 0:
            print(f"📋 Duplicate details: {args.duplicates}")
        if skipped > 0:
            print(f"📋 Skipped file details: {args.skipped}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
