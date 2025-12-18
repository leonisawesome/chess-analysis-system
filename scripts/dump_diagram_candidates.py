#!/usr/bin/env python3
"""
Utility script to inspect static EPUB diagrams for a list of queries.

It loads diagram_metadata_full.json, runs the ranking heuristic for each query,
and writes a JSON report (plus optional Markdown table) so we can see exactly
which diagrams are being selected, their dimensions, and whether the files
actually exist on disk.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure repository root is on sys.path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from PIL import Image, UnidentifiedImageError  # type: ignore
except ImportError:  # pragma: no cover - pillow is optional
    Image = None
    UnidentifiedImageError = Exception

from diagram_service import DiagramIndex

logger = logging.getLogger("dump_diagram_candidates")


def get_image_dims(path: Path) -> Optional[Tuple[int, int]]:
    """Return (width, height) using Pillow if available."""
    if not Image or not path.exists():
        return None
    try:
        with Image.open(path) as img:
            return img.size
    except (UnidentifiedImageError, OSError):
        return None


def sample_diagrams_for_query(
    index: DiagramIndex,
    query: str,
    top_books: int,
    top_diagrams: int
) -> Dict:
    """Collect ranked diagrams for a single query."""
    entry = {"query": query, "books": []}
    book_ids = index.search_books_by_query(query, max_matches=top_books)
    for book_id in book_ids:
        diagrams = index.get_diagrams_for_book(book_id) or []
        if not diagrams:
            continue
        pseudo_chunk = {
            "text": query,
            "book_title": index.get_book_title(book_id) or query,
            "chapter_title": query,
            "section_path": "",
            "chunk_index": 0
        }
        ranked = index.rank_diagrams_for_chunk(
            diagrams,
            pseudo_chunk,
            query=query,
            max_k=top_diagrams
        )

        ranked_summaries = []
        for diag in ranked:
            file_path = Path(diag.get("file_path", ""))
            dims = get_image_dims(file_path) if file_path else None
            ranked_summaries.append({
                "diagram_id": diag.get("diagram_id"),
                "file_path": str(file_path) if file_path else None,
                "book_title": diag.get("book_title"),
                "position_in_document": diag.get("position_in_document"),
                "width": diag.get("width") or diag.get("image_width"),
                "height": diag.get("height") or diag.get("image_height"),
                "actual_width": dims[0] if dims else None,
                "actual_height": dims[1] if dims else None,
                "size_bytes": diag.get("size_bytes"),
                "context_before": (diag.get("context_before") or "")[:200],
                "context_after": (diag.get("context_after") or "")[:200],
            })

        entry["books"].append({
            "book_id": book_id,
            "book_title": index.get_book_title(book_id),
            "total_diagrams": len(diagrams),
            "ranked_diagrams": ranked_summaries
        })

    return entry


def write_markdown_table(report: Dict, path: Path, max_rows: int = 25) -> None:
    """Render a small Markdown table for quick eyeballing."""
    lines = [
        "| Query | Book | Diagram ID | Exists | Meta WxH | Actual WxH | Size KB | Context |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |"
    ]
    rows_added = 0
    for query in report.get("queries", []):
        for book in query.get("books", []):
            for diag in book.get("ranked_diagrams", []):
                if rows_added >= max_rows:
                    break
                exists = "yes" if diag.get("file_path") and os.path.exists(diag["file_path"]) else "no"
                meta_dims = f"{diag.get('width') or '?'}x{diag.get('height') or '?'}"
                actual_dims = f"{diag.get('actual_width') or '?'}x{diag.get('actual_height') or '?'}"
                size_kb = f"{(diag.get('size_bytes') or 0)/1024:.1f}"
                context = (diag.get("context_after") or diag.get("context_before") or "").replace("|", "/")
                lines.append(
                    f"| {query['query']} | {book['book_title'][:40]} | {diag['diagram_id']} | "
                    f"{exists} | {meta_dims} | {actual_dims} | {size_kb} | {context[:120]} |"
                )
                rows_added += 1
            if rows_added >= max_rows:
                break
        if rows_added >= max_rows:
            break

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    logger.info("Markdown sample saved to %s (%d rows)", path, rows_added)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dump ranked static diagrams for debugging."
    )
    parser.add_argument(
        "queries",
        nargs="+",
        help="One or more queries to inspect (quote multi-word queries)."
    )
    parser.add_argument(
        "--metadata",
        default="diagram_metadata_full.json",
        help="Path to diagram metadata JSON (default: diagram_metadata_full.json)"
    )
    parser.add_argument(
        "--output",
        default="diagnostics/diagram_debug.json",
        help="Where to write the JSON report (default: diagnostics/diagram_debug.json)"
    )
    parser.add_argument(
        "--markdown",
        default="",
        help="Optional Markdown summary path."
    )
    parser.add_argument(
        "--top-books",
        type=int,
        default=5,
        help="How many books to sample per query."
    )
    parser.add_argument(
        "--top-diagrams",
        type=int,
        default=8,
        help="How many diagrams to keep per book."
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=2000,
        help="Minimum bytes when loading metadata (matches app.py default)."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("Loading diagram metadata from %s (min_size=%d)", args.metadata, args.min_size)

    index = DiagramIndex()
    index.load(args.metadata, min_size_bytes=args.min_size)

    report = {
        "queries": [],
        "total_books": len(index.by_book),
    }

    for query in args.queries:
        logger.info("⬇️  Sampling diagrams for query: %s", query)
        report["queries"].append(
            sample_diagrams_for_query(index, query, args.top_books, args.top_diagrams)
        )

    output_path.write_text(json.dumps(report, indent=2))
    logger.info("✅ Wrote JSON report to %s", output_path)

    if args.markdown:
        write_markdown_table(report, Path(args.markdown))


if __name__ == "__main__":
    main()
