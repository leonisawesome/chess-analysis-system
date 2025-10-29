#!/usr/bin/env python3
"""
Source Metadata Tracking for Chess RAG System
Populates metadata database with book information.
"""

import sqlite3
import hashlib
import uuid
from pathlib import Path
from datetime import datetime


METADATA_SCHEMA = """
CREATE TABLE IF NOT EXISTS source_metadata (
    doc_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    format TEXT NOT NULL,
    quality_score INTEGER,
    tier TEXT,
    word_count INTEGER,
    diagram_count INTEGER,
    author_reputation INTEGER,
    file_hash TEXT,
    extraction_date TEXT,
    status TEXT DEFAULT 'ready',
    ingested_to_rag BOOLEAN DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_status ON source_metadata(status);
CREATE INDEX IF NOT EXISTS idx_ingested ON source_metadata(ingested_to_rag);
CREATE INDEX IF NOT EXISTS idx_tier ON source_metadata(tier);
"""


def generate_file_hash(filename: str) -> str:
    """Generate MD5 hash from filename."""
    return hashlib.md5(filename.encode('utf-8')).hexdigest()


def populate_metadata(db_path: str = "epub_analysis.db"):
    """Populate source_metadata table from epub_analysis table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table
    cursor.executescript(METADATA_SCHEMA)
    conn.commit()

    # Get all HIGH and MEDIUM tier books
    cursor.execute("""
        SELECT
            filename,
            format,
            score,
            tier,
            word_count,
            diagram_count,
            author_score
        FROM epub_analysis
        WHERE tier IN ('HIGH', 'MEDIUM')
        ORDER BY score DESC
    """)

    books = cursor.fetchall()
    inserted = 0
    skipped = 0

    print(f"Found {len(books)} books to process...")
    print("Generating metadata entries...\n")

    for filename, fmt, score, tier, word_count, diagram_count, author_score in books:
        # Generate unique doc_id
        doc_id = str(uuid.uuid4())

        # Generate file hash
        file_hash = generate_file_hash(filename)

        # Insert into source_metadata
        try:
            cursor.execute("""
                INSERT INTO source_metadata (
                    doc_id,
                    filename,
                    format,
                    quality_score,
                    tier,
                    word_count,
                    diagram_count,
                    author_reputation,
                    file_hash,
                    extraction_date,
                    status,
                    ingested_to_rag
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                filename,
                fmt,
                score,
                tier,
                word_count,
                diagram_count,
                author_score,
                file_hash,
                datetime.now().isoformat(),
                'ready',
                0
            ))
            inserted += 1

            if inserted % 100 == 0:
                print(f"  Processed {inserted}/{len(books)} books...")

        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()

    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM source_metadata")
    total_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT tier, COUNT(*)
        FROM source_metadata
        GROUP BY tier
    """)
    tier_dist = dict(cursor.fetchall())

    cursor.execute("""
        SELECT format, COUNT(*)
        FROM source_metadata
        GROUP BY format
    """)
    format_dist = dict(cursor.fetchall())

    conn.close()

    # Print summary
    print()
    print("=" * 80)
    print("METADATA POPULATION COMPLETE")
    print("=" * 80)
    print()
    print(f"📊 Results:")
    print(f"   Inserted: {inserted} records")
    print(f"   Skipped:  {skipped} records (duplicates)")
    print(f"   Total:    {total_count} records in source_metadata")
    print()

    print(f"📚 Tier Distribution:")
    for tier in ['HIGH', 'MEDIUM']:
        count = tier_dist.get(tier, 0)
        print(f"   {tier:8s}: {count:4d} books")
    print()

    print(f"📖 Format Distribution:")
    for fmt, count in sorted(format_dist.items()):
        print(f"   {fmt:6s}: {count:4d} books")
    print()

    print("✅ All books marked as status='ready', ingested_to_rag=0")
    print("=" * 80)


def show_metadata_sample(db_path: str = "epub_analysis.db", limit: int = 10):
    """Display sample of metadata table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Show schema
    print("=" * 80)
    print("METADATA TABLE SCHEMA")
    print("=" * 80)
    cursor.execute("PRAGMA table_info(source_metadata)")
    schema = cursor.fetchall()
    for col in schema:
        col_id, name, type_, notnull, default, pk = col
        pk_str = " PRIMARY KEY" if pk else ""
        null_str = " NOT NULL" if notnull else ""
        default_str = f" DEFAULT {default}" if default else ""
        print(f"   {name:20s} {type_:10s}{null_str}{default_str}{pk_str}")
    print()

    # Show first N rows
    print("=" * 80)
    print(f"FIRST {limit} METADATA RECORDS")
    print("=" * 80)
    cursor.execute(f"""
        SELECT
            substr(doc_id, 1, 8) as id_short,
            substr(filename, 1, 50) as filename_short,
            format,
            quality_score,
            tier,
            author_reputation,
            status,
            ingested_to_rag
        FROM source_metadata
        ORDER BY quality_score DESC
        LIMIT {limit}
    """)

    rows = cursor.fetchall()
    print(f"{'ID':<10} {'Filename':<52} {'Fmt':<6} {'Score':<6} {'Tier':<8} {'Auth':<5} {'Status':<8} {'RAG'}")
    print("-" * 120)
    for row in rows:
        doc_id_short, filename, fmt, score, tier, author, status, ingested = row
        filename_display = filename[:50]
        print(f"{doc_id_short:<10} {filename_display:<52} {fmt:<6} {score:<6} {tier:<8} {author:<5} {status:<8} {ingested}")

    conn.close()


if __name__ == '__main__':
    print("Populating metadata database...\n")
    populate_metadata()
    print()
    show_metadata_sample(limit=10)
