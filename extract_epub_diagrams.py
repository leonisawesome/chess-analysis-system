#!/usr/bin/env python3
"""
EPUB Diagram Extraction Pipeline
Extracts chess diagrams from EPUB files and stores them with metadata for Qdrant linking.

Usage:
    python extract_epub_diagrams.py --epub-dir "/Volumes/T7 Shield/rag/books/epub" \\
                                     --output-dir "/Volumes/T7 Shield/rag/books/images" \\
                                     --metadata-file "diagram_metadata.json"

    # Test on single book
    python extract_epub_diagrams.py --test-mode --limit 1
"""

import argparse
import json
import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from urllib.parse import unquote
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import logging
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DiagramInfo:
    """Metadata for a single diagram."""
    diagram_id: str           # Unique ID: {book_id}_{img_index}
    book_id: str              # Unique book identifier
    book_title: str           # Human-readable book title
    epub_filename: str        # Original EPUB filename
    original_name: str        # Original image filename in EPUB
    file_path: str            # Path to extracted image file
    format: str               # Image format (.png, .jpg, etc.)
    size_bytes: int           # File size
    html_document: str        # HTML document where image appears
    context_before: str       # Text before the diagram (move notation)
    context_after: str        # Text after the diagram (analysis)
    position_in_document: int # Index of this diagram in the HTML document


class DiagramExtractor:
    """Extracts diagrams from a single EPUB file."""

    def __init__(self, epub_path: Path, output_base_dir: Path):
        self.epub_path = epub_path
        self.output_base_dir = output_base_dir
        self.book_id = self._generate_book_id()
        self.book_title = ""
        self.diagrams: List[DiagramInfo] = []

    def _generate_book_id(self) -> str:
        """Generate unique book ID from filename."""
        # Use first 12 chars of MD5 hash of filename for uniqueness
        filename = self.epub_path.stem
        hash_obj = hashlib.md5(filename.encode())
        return f"book_{hash_obj.hexdigest()[:12]}"

    def _is_cover_image(self, image_name: str) -> bool:
        """Check if image is a cover (should be skipped)."""
        name_lower = image_name.lower()
        return (
            'cover' in name_lower or
            name_lower.startswith('cover.') or
            '/cover.' in name_lower
        )

    def _get_book_title(self, book: epub.EpubBook) -> str:
        """Extract book title from EPUB metadata."""
        try:
            title = book.get_metadata('DC', 'title')
            if title:
                return title[0][0]
        except:
            pass
        return self.epub_path.stem

    def _extract_context(self, img_tag, soup) -> tuple:
        """
        Extract text context before and after the diagram.

        Returns:
            (context_before, context_after)
        """
        # Find parent paragraph
        parent = img_tag.parent
        if not parent:
            return "", ""

        # Get preceding siblings (text before diagram)
        context_before = []
        try:
            prev_siblings = parent.find_all_previous_siblings(limit=3)
            if prev_siblings:
                for prev_sib in prev_siblings:
                    if hasattr(prev_sib, 'get_text'):
                        text = prev_sib.get_text(strip=True)
                        if text:
                            context_before.append(text)
        except:
            pass

        context_before_str = ' '.join(reversed(context_before))[-300:] if context_before else ""

        # Get following siblings (text after diagram)
        context_after = []
        try:
            next_siblings = parent.find_next_siblings(limit=3)
            if next_siblings:
                for next_sib in next_siblings:
                    if hasattr(next_sib, 'get_text'):
                        text = next_sib.get_text(strip=True)
                        if text:
                            context_after.append(text)
        except:
            pass

        context_after_str = ' '.join(context_after)[:300] if context_after else ""

        return context_before_str, context_after_str

    def extract(self) -> List[DiagramInfo]:
        """
        Extract all diagrams from the EPUB.

        Returns:
            List of DiagramInfo objects
        """
        try:
            logger.info(f"Processing: {self.epub_path.name}")
            book = epub.read_epub(str(self.epub_path))

            # Get book title
            self.book_title = self._get_book_title(book)

            # Create output directory for this book
            book_output_dir = self.output_base_dir / self.book_id
            book_output_dir.mkdir(parents=True, exist_ok=True)

            # VERIFY directory was created successfully
            if not book_output_dir.exists() or not book_output_dir.is_dir():
                raise RuntimeError(f"Failed to create output directory: {book_output_dir}")

            # Step 1: Extract all images and build lookup
            images_by_name = {}
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_IMAGE:
                    img_name = item.get_name()

                    # Skip covers
                    if self._is_cover_image(img_name):
                        continue

                    images_by_name[img_name] = {
                        'content': item.get_content(),
                        'size': len(item.get_content())
                    }

            logger.info(f"  Found {len(images_by_name)} diagrams (covers excluded)")

            # Step 2: Parse HTML documents to find image references and context
            diagram_index = 0
            extracted_images = set()  # Track which images we've already extracted

            for item in book.get_items():
                if item.get_type() != ebooklib.ITEM_DOCUMENT:
                    continue

                try:
                    content = item.get_content().decode('utf-8', errors='ignore')
                    soup = BeautifulSoup(content, 'html.parser')

                    # Find all img tags in this document
                    img_tags = soup.find_all('img')

                    for position, img_tag in enumerate(img_tags):
                        src = img_tag.get('src', '')
                        if not src:
                            continue

                        # URL decode the source path (handles %20, %2019, etc.)
                        src_decoded = unquote(src)

                        # Normalize path (remove leading ./ or ../)
                        img_path = Path(src_decoded).name

                        # Find matching image in our extracted images
                        # Try exact match first, then fuzzy match
                        img_data = None
                        actual_key = None

                        # Try exact filename match
                        if img_path in images_by_name:
                            img_data = images_by_name[img_path]
                            actual_key = img_path
                        else:
                            # Try to find by matching just the filename (case insensitive)
                            for key in images_by_name.keys():
                                key_name = Path(key).name
                                if key_name.lower() == img_path.lower():
                                    img_data = images_by_name[key]
                                    actual_key = key
                                    break

                        if not img_data:
                            logger.debug(f"  Image not found: {src} (decoded: {src_decoded})")
                            continue

                        # BUGFIX: Skip if we've already extracted this image
                        if actual_key in extracted_images:
                            logger.debug(f"  Skipping duplicate image: {actual_key}")
                            continue

                        extracted_images.add(actual_key)

                        # Extract context
                        context_before, context_after = self._extract_context(img_tag, soup)

                        # Generate diagram ID and save file
                        diagram_id = f"{self.book_id}_{diagram_index:04d}"
                        ext = Path(actual_key).suffix
                        output_filename = f"{diagram_id}{ext}"
                        output_path = book_output_dir / output_filename

                        # Write image file
                        with open(output_path, 'wb') as f:
                            f.write(img_data['content'])

                        # VERIFY file was written successfully
                        if not output_path.exists():
                            raise RuntimeError(f"Failed to write file: {output_path}")

                        # Create metadata
                        diagram_info = DiagramInfo(
                            diagram_id=diagram_id,
                            book_id=self.book_id,
                            book_title=self.book_title,
                            epub_filename=self.epub_path.name,
                            original_name=actual_key,
                            file_path=str(output_path),
                            format=ext,
                            size_bytes=img_data['size'],
                            html_document=item.get_name(),
                            context_before=context_before,
                            context_after=context_after,
                            position_in_document=position
                        )

                        self.diagrams.append(diagram_info)
                        diagram_index += 1

                except Exception as e:
                    logger.error(f"  Error processing HTML document {item.get_name()}: {e}")
                    continue

            # FINAL VERIFICATION: Ensure directory and files still exist
            if not book_output_dir.exists():
                raise RuntimeError(f"Output directory disappeared after extraction: {book_output_dir}")

            # Count files, excluding macOS ._* metadata files
            actual_files = len([f for f in book_output_dir.glob("*") if not f.name.startswith('._')])
            if actual_files != len(self.diagrams):
                raise RuntimeError(
                    f"File count mismatch for {self.book_id}: "
                    f"Expected {len(self.diagrams)} files, found {actual_files}"
                )

            logger.info(f"  Extracted {len(self.diagrams)} diagrams to {book_output_dir}")
            return self.diagrams

        except Exception as e:
            logger.error(f"Failed to process {self.epub_path.name}: {e}")
            return []


def extract_all_diagrams(
    epub_dir: Path,
    output_dir: Path,
    metadata_file: Path,
    limit: Optional[int] = None
) -> Dict:
    """
    Extract diagrams from all EPUB files in a directory.

    Args:
        epub_dir: Directory containing EPUB files
        output_dir: Base directory for extracted images
        metadata_file: JSON file to store extraction metadata
        limit: Optional limit on number of books to process (for testing)

    Returns:
        Dictionary with extraction statistics
    """
    # Find all EPUB files
    epub_files = sorted(epub_dir.glob("*.epub"))

    # Filter out system files (._*)
    epub_files = [f for f in epub_files if not f.name.startswith('._')]

    if limit:
        epub_files = epub_files[:limit]
        logger.info(f"TEST MODE: Processing only {limit} books")

    logger.info(f"Found {len(epub_files)} EPUB files to process")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track all diagrams and statistics
    all_diagrams = []
    stats = {
        'total_books': len(epub_files),
        'books_processed': 0,
        'books_failed': 0,
        'total_diagrams': 0,
        'total_size_bytes': 0,
        'by_format': {},
        'books': []
    }

    # Process each EPUB
    for epub_path in tqdm(epub_files, desc="Extracting diagrams"):
        try:
            extractor = DiagramExtractor(epub_path, output_dir)
            diagrams = extractor.extract()

            if diagrams:
                all_diagrams.extend(diagrams)

                # Update statistics
                stats['books_processed'] += 1
                stats['total_diagrams'] += len(diagrams)

                for diagram in diagrams:
                    stats['total_size_bytes'] += diagram.size_bytes
                    fmt = diagram.format
                    stats['by_format'][fmt] = stats['by_format'].get(fmt, 0) + 1

                stats['books'].append({
                    'book_id': extractor.book_id,
                    'title': extractor.book_title,
                    'epub_file': epub_path.name,
                    'diagram_count': len(diagrams)
                })
            else:
                stats['books_failed'] += 1

        except Exception as e:
            logger.error(f"Error processing {epub_path.name}: {e}")
            stats['books_failed'] += 1

    # Save metadata to JSON
    metadata = {
        'stats': stats,
        'diagrams': [asdict(d) for d in all_diagrams]
    }

    logger.info(f"Saving metadata to {metadata_file}")
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Print summary
    print("\n" + "="*80)
    print("EXTRACTION COMPLETE")
    print("="*80)
    print(f"Books processed: {stats['books_processed']}/{stats['total_books']}")
    print(f"Books failed: {stats['books_failed']}")
    print(f"Total diagrams extracted: {stats['total_diagrams']:,}")
    print(f"Total size: {stats['total_size_bytes'] / (1024**3):.2f} GB")
    print(f"\nDiagrams by format:")
    for fmt, count in sorted(stats['by_format'].items()):
        print(f"  {fmt}: {count:,}")
    print(f"\nMetadata saved to: {metadata_file}")
    print(f"Images saved to: {output_dir}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Extract chess diagrams from EPUB files")
    parser.add_argument(
        '--epub-dir',
        type=Path,
        default=Path("/Volumes/T7 Shield/rag/books/epub"),
        help="Directory containing EPUB files"
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path("/Volumes/T7 Shield/rag/books/images"),
        help="Output directory for extracted images"
    )
    parser.add_argument(
        '--metadata-file',
        type=Path,
        default=Path("diagram_metadata.json"),
        help="JSON file to store extraction metadata"
    )
    parser.add_argument(
        '--limit',
        type=int,
        help="Limit number of books to process (for testing)"
    )
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help="Test mode: process only 3 books"
    )

    args = parser.parse_args()

    # Apply test mode
    if args.test_mode:
        args.limit = 3
        logger.info("TEST MODE: Processing 3 books only")

    # Validate directories
    if not args.epub_dir.exists():
        logger.error(f"EPUB directory not found: {args.epub_dir}")
        return 1

    # Run extraction
    stats = extract_all_diagrams(
        epub_dir=args.epub_dir,
        output_dir=args.output_dir,
        metadata_file=args.metadata_file,
        limit=args.limit
    )

    return 0


if __name__ == '__main__':
    exit(main())
