#!/usr/bin/env python3
"""
Process only books not already in database.
"""

import sqlite3
import sys
from pathlib import Path
from tqdm import tqdm

from fast_epub_analyzer import analyze_epub_fast
from batch_process_epubs import store_result, find_epub_files, generate_summary_report, print_summary_report


def get_processed_files(conn: sqlite3.Connection):
    """Get set of already processed filenames."""
    cursor = conn.cursor()
    cursor.execute("SELECT filename FROM epub_analysis")
    return {row[0] for row in cursor.fetchall()}


def main():
    epub_directory = "/Volumes/T7 Shield/epub/"
    db_path = "epub_analysis.db"

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)

    print(f"Finding all ebook files...")
    all_files = find_epub_files(epub_directory)
    print(f"Total files found: {len(all_files)}")

    print(f"Checking which files are already processed...")
    processed_filenames = get_processed_files(conn)
    print(f"Already processed: {len(processed_filenames)}")

    # Filter to unprocessed files
    unprocessed = []
    for filepath in all_files:
        filename = Path(filepath).name
        if filename not in processed_filenames:
            unprocessed.append(filepath)

    print(f"\n🔄 Files remaining to process: {len(unprocessed)}")

    if not unprocessed:
        print("✅ All files already processed!")
        summary = generate_summary_report(conn)
        print_summary_report(summary)
        conn.close()
        return

    print("\nProcessing remaining files...\n")

    for epub_path in tqdm(unprocessed, desc="Analyzing", unit="book"):
        try:
            result = analyze_epub_fast(epub_path, verbose=False)
            store_result(conn, result)
        except Exception as e:
            error_result = {
                'success': False,
                'file': epub_path,
                'error': f"Unexpected error: {str(e)}",
                'processing_time': 0
            }
            store_result(conn, error_result)

    print("\n✅ Processing complete!\n")

    # Generate final summary
    summary = generate_summary_report(conn)
    print_summary_report(summary)

    conn.close()


if __name__ == '__main__':
    main()
