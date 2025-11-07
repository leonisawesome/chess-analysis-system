#!/usr/bin/env python3
"""
Batch EPUB Processing with SQLite Storage
Processes all 1,112+ EPUBs and stores results in database
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import json

# Import the fast analyzer
from analyze_chess_books import analyze_epub_fast


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS epub_analysis (
    filename TEXT PRIMARY KEY,
    full_path TEXT,
    format TEXT,
    score INTEGER,
    tier TEXT,
    word_count INTEGER,
    diagram_count INTEGER,
    prose_notation_ratio REAL,
    notation_ratio_score INTEGER,
    word_count_score INTEGER,
    diagram_score INTEGER,
    structure_score INTEGER,
    keyword_score INTEGER,
    author_score INTEGER,
    text_quality_score INTEGER,
    processing_time REAL,
    timestamp TEXT,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_score ON epub_analysis(score DESC);
CREATE INDEX IF NOT EXISTS idx_tier ON epub_analysis(tier);
CREATE INDEX IF NOT EXISTS idx_author_score ON epub_analysis(author_score DESC);
CREATE INDEX IF NOT EXISTS idx_format ON epub_analysis(format);
"""


def init_database(db_path: str):
    """Initialize SQLite database with schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(DB_SCHEMA)
    conn.commit()
    return conn


def store_result(conn: sqlite3.Connection, result: dict):
    """Store analysis result in database."""
    cursor = conn.cursor()

    if result['success']:
        metrics = result['metrics']
        file_format = Path(result['file']).suffix.upper().replace('.', '')
        cursor.execute("""
            INSERT OR REPLACE INTO epub_analysis (
                filename, full_path, format, score, tier, word_count, diagram_count,
                prose_notation_ratio, notation_ratio_score, word_count_score,
                diagram_score, structure_score, keyword_score, author_score,
                text_quality_score, processing_time, timestamp, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """, (
            Path(result['file']).name,
            result['file'],
            file_format,
            result['total_score'],
            result['tier'],
            metrics['word_count'],
            metrics['diagram_count'],
            metrics['notation_ratio'],
            metrics['prose_notation_score'],
            metrics['word_count_score'],
            metrics['diagram_score'],
            metrics['structure_score'],
            metrics['instructional_score'],
            metrics['author_score'],
            metrics['text_quality_score'],
            result['processing_time'],
            datetime.now().isoformat()
        ))
    else:
        # Store error
        file_format = Path(result['file']).suffix.upper().replace('.', '')
        cursor.execute("""
            INSERT OR REPLACE INTO epub_analysis (
                filename, full_path, format, score, tier, error, timestamp
            ) VALUES (?, ?, ?, 0, 'ERROR', ?, ?)
        """, (
            Path(result['file']).name,
            result['file'],
            file_format,
            result.get('error', 'Unknown error'),
            datetime.now().isoformat()
        ))

    conn.commit()


def find_epub_files(directory: str) -> list:
    """Find all EPUB and MOBI files in directory."""
    ebook_files = []
    for pattern in ['*.epub', '*.mobi']:
        for file in Path(directory).glob(pattern):
            # Skip macOS metadata files
            if file.name.startswith('._'):
                continue
            ebook_files.append(str(file))
    return sorted(ebook_files)


def generate_summary_report(conn: sqlite3.Connection) -> dict:
    """Generate comprehensive summary statistics."""
    cursor = conn.cursor()

    # Overall stats
    cursor.execute("SELECT COUNT(*) FROM epub_analysis WHERE error IS NULL")
    successful = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM epub_analysis WHERE error IS NOT NULL")
    failed = cursor.fetchone()[0]

    # Tier distribution
    cursor.execute("""
        SELECT tier, COUNT(*)
        FROM epub_analysis
        WHERE error IS NULL
        GROUP BY tier
    """)
    tier_dist = dict(cursor.fetchall())

    # Average scores by tier
    cursor.execute("""
        SELECT tier,
               AVG(score) as avg_score,
               AVG(processing_time) as avg_time
        FROM epub_analysis
        WHERE error IS NULL
        GROUP BY tier
    """)
    tier_stats = {row[0]: {'avg_score': row[1], 'avg_time': row[2]}
                  for row in cursor.fetchall()}

    # Processing time stats
    cursor.execute("""
        SELECT
            AVG(processing_time) as avg_time,
            MIN(processing_time) as min_time,
            MAX(processing_time) as max_time,
            SUM(processing_time) as total_time
        FROM epub_analysis
        WHERE error IS NULL
    """)
    time_stats = cursor.fetchone()

    # Top 20 books
    cursor.execute("""
        SELECT filename, score, tier, word_count, author_score
        FROM epub_analysis
        WHERE error IS NULL
        ORDER BY score DESC
        LIMIT 20
    """)
    top_20 = cursor.fetchall()

    # Bottom 20 books
    cursor.execute("""
        SELECT filename, score, tier, word_count, error
        FROM epub_analysis
        ORDER BY score ASC
        LIMIT 20
    """)
    bottom_20 = cursor.fetchall()

    # Author reputation analysis
    cursor.execute("""
        SELECT
            COUNT(*) as count,
            AVG(score) as avg_score
        FROM epub_analysis
        WHERE error IS NULL AND author_score = 10
    """)
    renowned_stats = cursor.fetchone()

    cursor.execute("""
        SELECT
            COUNT(*) as count,
            AVG(score) as avg_score
        FROM epub_analysis
        WHERE error IS NULL AND author_score = 0
    """)
    unknown_stats = cursor.fetchone()

    # Format comparison
    cursor.execute("""
        SELECT format, COUNT(*), AVG(score)
        FROM epub_analysis
        WHERE error IS NULL
        GROUP BY format
    """)
    format_stats = {row[0]: {'count': row[1], 'avg_score': row[2]}
                    for row in cursor.fetchall()}

    return {
        'total': successful + failed,
        'successful': successful,
        'failed': failed,
        'tier_distribution': tier_dist,
        'tier_stats': tier_stats,
        'time_stats': {
            'avg': time_stats[0],
            'min': time_stats[1],
            'max': time_stats[2],
            'total': time_stats[3]
        },
        'top_20': top_20,
        'bottom_20': bottom_20,
        'renowned_authors': {
            'count': renowned_stats[0],
            'avg_score': renowned_stats[1]
        },
        'unknown_authors': {
            'count': unknown_stats[0],
            'avg_score': unknown_stats[1]
        },
        'format_stats': format_stats
    }


def print_summary_report(summary: dict):
    """Print formatted summary report."""
    print(f"\n{'='*80}")
    print("BATCH PROCESSING SUMMARY")
    print(f"{'='*80}\n")

    print(f"📊 Overall Stats:")
    print(f"   Total Books: {summary['total']}")
    print(f"   ✅ Successfully processed: {summary['successful']}")
    print(f"   ❌ Failed/Errors: {summary['failed']}")
    print(f"   Success rate: {(summary['successful']/summary['total']*100):.1f}%\n")

    print(f"⏱️  Processing Time:")
    print(f"   Average: {summary['time_stats']['avg']:.2f}s per book")
    print(f"   Fastest: {summary['time_stats']['min']:.2f}s")
    print(f"   Slowest: {summary['time_stats']['max']:.2f}s")
    print(f"   Total: {summary['time_stats']['total']/60:.1f} minutes\n")

    print(f"🎯 Tier Distribution:")
    for tier in ['HIGH', 'MEDIUM', 'LOW']:
        count = summary['tier_distribution'].get(tier, 0)
        pct = (count / summary['successful'] * 100) if summary['successful'] > 0 else 0
        avg_score = summary['tier_stats'].get(tier, {}).get('avg_score', 0)
        print(f"   {tier:8s}: {count:4d} books ({pct:5.1f}%) - Avg score: {avg_score:.1f}")
    print()

    print(f"👤 Author Analysis:")
    print(f"   Renowned authors: {summary['renowned_authors']['count']} books "
          f"(avg score: {summary['renowned_authors']['avg_score']:.1f})")
    print(f"   Unknown authors:  {summary['unknown_authors']['count']} books "
          f"(avg score: {summary['unknown_authors']['avg_score']:.1f})")
    print(f"   Author reputation impact: +{summary['renowned_authors']['avg_score'] - summary['unknown_authors']['avg_score']:.1f} points\n")

    # Format comparison
    if 'format_stats' in summary and summary['format_stats']:
        print(f"📚 Format Comparison:")
        for fmt in sorted(summary['format_stats'].keys()):
            stats = summary['format_stats'][fmt]
            count = stats['count']
            avg_score = stats['avg_score']
            pct = (count / summary['successful'] * 100) if summary['successful'] > 0 else 0
            print(f"   {fmt:6s}: {count:4d} books ({pct:5.1f}%) - Avg score: {avg_score:.1f}")
        print()

    print(f"🏆 Top 20 Books (for manual validation):")
    for i, (filename, score, tier, word_count, author_score) in enumerate(summary['top_20'], 1):
        author_mark = "⭐" if author_score == 10 else "  "
        filename_short = filename[:65]
        print(f"   {i:2d}. {int(score):3d} {author_mark} {filename_short}")
    print()

    print(f"⚠️  Bottom 20 Books (candidates for quarantine):")
    for i, (filename, score, tier, word_count, error) in enumerate(summary['bottom_20'], 1):
        filename_short = filename[:65]
        if error:
            print(f"   {i:2d}. ERR    {filename_short}")
            print(f"           Error: {error[:60]}")
        else:
            print(f"   {i:2d}. {int(score):3d}    {filename_short}")
    print()


def batch_process_epubs(epub_directory: str, db_path: str = "epub_analysis.db"):
    """
    Batch process all EPUBs in directory.

    Args:
        epub_directory: Path to directory containing EPUBs
        db_path: Path to SQLite database file
    """
    print(f"Initializing database: {db_path}")
    conn = init_database(db_path)

    print(f"Scanning directory: {epub_directory}")
    epub_files = find_epub_files(epub_directory)
    print(f"Found {len(epub_files)} EPUB files\n")

    if not epub_files:
        print("No EPUB files found!")
        return

    print("Processing EPUBs...")
    results = []

    # Process with progress bar
    for epub_path in tqdm(epub_files, desc="Analyzing", unit="book"):
        try:
            result = analyze_epub_fast(epub_path, verbose=False)
            store_result(conn, result)
            results.append(result)
        except Exception as e:
            # Handle unexpected errors
            error_result = {
                'success': False,
                'file': epub_path,
                'error': f"Unexpected error: {str(e)}",
                'processing_time': 0
            }
            store_result(conn, error_result)
            results.append(error_result)

    # Generate and display summary
    summary = generate_summary_report(conn)
    print_summary_report(summary)

    # Save summary to JSON
    summary_file = Path(db_path).with_suffix('.summary.json')
    with open(summary_file, 'w') as f:
        # Convert to JSON-serializable format
        summary_json = {
            k: v for k, v in summary.items()
            if k not in ['top_20', 'bottom_20']  # Skip large lists
        }
        json.dump(summary_json, f, indent=2)
    print(f"💾 Summary saved to: {summary_file}")

    conn.close()
    print(f"\n✅ Database saved to: {db_path}")
    print(f"📊 Use SQL queries to explore results further")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python batch_process_epubs.py <epub_directory> [db_path]")
        print("\nExample:")
        print('  python batch_process_epubs.py "/Volumes/T7 Shield/epub/"')
        print('  python batch_process_epubs.py "/Volumes/T7 Shield/epub/" "results.db"')
        sys.exit(1)

    epub_directory = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else "epub_analysis.db"

    batch_process_epubs(epub_directory, db_path)


if __name__ == '__main__':
    main()
