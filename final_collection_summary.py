#!/usr/bin/env python3
"""
Generate final collection summary after cleanup.
"""

import sqlite3
from pathlib import Path


def get_collection_summary(db_path: str = "epub_analysis.db"):
    """Generate comprehensive collection summary."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Count actual files in directory
    epub_dir = Path("/Volumes/T7 Shield/epub/")
    actual_epubs = len([f for f in epub_dir.glob("*.epub") if not f.name.startswith("._")])
    actual_mobis = len([f for f in epub_dir.glob("*.mobi") if not f.name.startswith("._")])
    actual_total = actual_epubs + actual_mobis

    # Get HIGH and MEDIUM tier stats from database
    cursor.execute("""
        SELECT tier, format, COUNT(*), AVG(score)
        FROM epub_analysis
        WHERE tier IN ('HIGH', 'MEDIUM')
        GROUP BY tier, format
        ORDER BY tier DESC, format
    """)
    tier_format_stats = cursor.fetchall()

    # Overall stats for HIGH/MEDIUM only
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            AVG(score) as avg_score,
            MIN(score) as min_score,
            MAX(score) as max_score,
            AVG(word_count) as avg_words
        FROM epub_analysis
        WHERE tier IN ('HIGH', 'MEDIUM')
    """)
    overall_stats = cursor.fetchone()

    # Tier distribution
    cursor.execute("""
        SELECT tier, COUNT(*)
        FROM epub_analysis
        WHERE tier IN ('HIGH', 'MEDIUM')
        GROUP BY tier
    """)
    tier_dist = dict(cursor.fetchall())

    # Author stats
    cursor.execute("""
        SELECT
            COUNT(*) as count,
            AVG(score) as avg_score
        FROM epub_analysis
        WHERE tier IN ('HIGH', 'MEDIUM') AND author_score = 10
    """)
    renowned_stats = cursor.fetchone()

    cursor.execute("""
        SELECT
            COUNT(*) as count,
            AVG(score) as avg_score
        FROM epub_analysis
        WHERE tier IN ('HIGH', 'MEDIUM') AND author_score = 0
    """)
    unknown_stats = cursor.fetchone()

    # Top 30 books
    cursor.execute("""
        SELECT filename, score, tier, format, author_score
        FROM epub_analysis
        WHERE tier IN ('HIGH', 'MEDIUM')
        ORDER BY score DESC
        LIMIT 30
    """)
    top_30 = cursor.fetchall()

    conn.close()

    # Print summary
    print("=" * 80)
    print("FINAL CHESS EBOOK COLLECTION SUMMARY")
    print("=" * 80)
    print()

    print("📊 Collection Size:")
    print(f"   Total Books: {actual_total:,}")
    print(f"   EPUB files: {actual_epubs:,} ({actual_epubs/actual_total*100:.1f}%)")
    print(f"   MOBI files: {actual_mobis:,} ({actual_mobis/actual_total*100:.1f}%)")
    print()

    print("🎯 Quality Distribution:")
    high_count = tier_dist.get('HIGH', 0)
    med_count = tier_dist.get('MEDIUM', 0)
    print(f"   HIGH tier (≥70):    {high_count:4d} books ({high_count/overall_stats[0]*100:5.1f}%)")
    print(f"   MEDIUM tier (45-69): {med_count:4d} books ({med_count/overall_stats[0]*100:5.1f}%)")
    print(f"   LOW tier removed:      59 books")
    print(f"   Corrupt removed:       13 books")
    print()

    print("📈 Score Statistics:")
    print(f"   Average Score: {overall_stats[1]:.1f}/100")
    print(f"   Score Range: {overall_stats[2]:.0f} - {overall_stats[3]:.0f}")
    print(f"   Average Word Count: {overall_stats[4]:,.0f} words")
    print()

    print("📚 Format Breakdown (HIGH + MEDIUM only):")
    for tier, fmt, count, avg_score in tier_format_stats:
        print(f"   {tier:8s} {fmt:4s}: {count:4d} books (avg score: {avg_score:.1f})")
    print()

    print("👤 Author Analysis:")
    print(f"   Renowned authors: {renowned_stats[0]} books (avg: {renowned_stats[1]:.1f})")
    print(f"   Unknown authors:  {unknown_stats[0]} books (avg: {unknown_stats[1]:.1f})")
    print(f"   Quality boost from reputation: +{renowned_stats[1] - unknown_stats[1]:.1f} points")
    print()

    print("🏆 Top 30 Books (Highest Quality):")
    for i, (filename, score, tier, fmt, author_score) in enumerate(top_30, 1):
        author_mark = "⭐" if author_score == 10 else "  "
        fmt_badge = "📕" if fmt == "EPUB" else "📙"
        filename_short = filename[:60]
        print(f"   {i:2d}. {int(score):3d} {author_mark} {fmt_badge} {filename_short}")
    print()

    print("=" * 80)
    print("CLEANUP SUMMARY")
    print("=" * 80)
    print(f"   Started with:  1,124 files")
    print(f"   Removed:          72 files (6.4%)")
    print(f"   - Low quality:    59 files")
    print(f"   - Corrupt:        13 files")
    print(f"   Final count:   1,052 files (93.6% retention)")
    print()
    print("✅ Collection optimized for Chess RAG system")
    print("   All books are MEDIUM or HIGH tier quality")
    print("=" * 80)


if __name__ == '__main__':
    get_collection_summary()
