#!/usr/bin/env python3
"""Remove one or more books from disk, SQLite, and Qdrant in one shot."""

import argparse
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest_models

EPUB_DIR = Path("/Volumes/T7 Shield/rag/books/epub")
IMAGES_DIR = Path("/Volumes/T7 Shield/rag/books/images")
DB_PATH = Path("epub_analysis.db")
DIAGRAM_METADATA = Path("diagram_metadata_full.json")
COLLECTION_NAME = "chess_production"
DEFAULT_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

_metadata_index: Optional[Dict[str, str]] = None

def load_metadata_index() -> Dict[str, str]:
    global _metadata_index
    if _metadata_index is not None:
        return _metadata_index

    index: Dict[str, str] = {}
    if not DIAGRAM_METADATA.exists():
        _metadata_index = index
        return index

    with open(DIAGRAM_METADATA, "r") as f:
        data = json.load(f)
        for diagram in data.get("diagrams", []):
            epub_filename = diagram.get("epub_filename")
            book_id = diagram.get("book_id")
            if epub_filename and book_id and epub_filename not in index:
                index[epub_filename] = book_id

    _metadata_index = index
    return index

def remove_epub_file(filename: str, dry_run: bool) -> bool:
    target = EPUB_DIR / filename
    if not target.exists():
        print(f"   ℹ EPUB not found on disk: {target}")
        return False
    if dry_run:
        print(f"   🧪 DRY RUN: would delete {target}")
        return True
    target.unlink()
    print(f"   ✅ Deleted EPUB: {target}")
    return True

def remove_image_dir(filename: str, dry_run: bool) -> None:
    index = load_metadata_index()
    book_id = index.get(filename)
    if not book_id:
        print(f"   ℹ No diagram entry for {filename}; skipping image folder")
        return
    image_dir = IMAGES_DIR / book_id
    if not image_dir.exists():
        print(f"   ℹ Image directory already missing: {image_dir}")
        return
    if dry_run:
        print(f"   🧪 DRY RUN: would delete image folder {image_dir}")
        return
    shutil.rmtree(image_dir)
    print(f"   ✅ Deleted image folder: {image_dir}")

def remove_sqlite_row(filename: str, dry_run: bool) -> None:
    if not DB_PATH.exists():
        print(f"   ⚠️ SQLite DB not found ({DB_PATH}); skipping")
        return
    if dry_run:
        print(f"   🧪 DRY RUN: would delete SQLite row for {filename}")
        return
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM epub_analysis WHERE filename = ?", (filename,))
        removed = cursor.rowcount
        conn.commit()
    if removed:
        print(f"   ✅ Removed {removed} row(s) from epub_analysis")
    else:
        print(f"   ℹ No SQLite rows matched {filename}")

def remove_qdrant_chunks(filename: str, qdrant_url: str, dry_run: bool) -> None:
    if dry_run:
        print(f"   🧪 DRY RUN: would delete Qdrant chunks for {filename}")
        return
    client = QdrantClient(url=qdrant_url)
    selector = rest_models.FilterSelector(
        filter=rest_models.Filter(
            must=[rest_models.FieldCondition(
                key="book_name",
                match=rest_models.MatchValue(value=filename)
            )]
        )
    )
    deleted = client.delete(collection_name=COLLECTION_NAME, points_selector=selector)
    print(f"   ✅ Qdrant delete requested for {filename}: {deleted}")

def process_book(filename: str, qdrant_url: str, dry_run: bool) -> None:
    print(f"\n=== Removing {filename} ===")
    remove_epub_file(filename, dry_run)
    remove_image_dir(filename, dry_run)
    remove_sqlite_row(filename, dry_run)
    try:
        remove_qdrant_chunks(filename, qdrant_url, dry_run)
    except Exception as exc:
        print(f"   ⚠️ Qdrant deletion failed for {filename}: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Remove books from disk + SQLite + Qdrant")
    parser.add_argument("filenames", nargs="+", help="EPUB filenames to remove (e.g. aagaard_2010.epub)")
    parser.add_argument("--qdrant-url", default=DEFAULT_QDRANT_URL, help="Qdrant endpoint (default: %(default)s)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without deleting")
    args = parser.parse_args()

    for filename in args.filenames:
        process_book(filename, args.qdrant_url, args.dry_run)


if __name__ == "__main__":
    main()
