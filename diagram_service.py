#!/usr/bin/env python3
"""
Static EPUB Diagram Service
Loads diagram metadata, ranks diagrams by relevance, and provides lookup utilities.

Phase 6.1a - Static Diagram Integration
"""

from collections import defaultdict
import json
import math
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Stopwords for text similarity (minimal set for chess content)
STOP_WORDS = set("""
    the a an and or of to in for on with from this that these those is are was were
    be as by after before during white black move moves plan plans strategy lines
    mainline variation position positions
""".split())

# Opening keyword pattern for relevance scoring
OPENING_KEYWORDS = re.compile(
    r'\b([A-E][0-9]{2}|najdorf|benko|hedgehog|caro-kann|sicilian|french|grunfeld|'
    r'king.?indian|...e5|...c5|ruy.?lopez|queens.?gambit|italian|spanish|scotch|'
    r'pirc|alekhine|dragon|sveshnikov|taimanov|kan|scheveningen|nimzo|queens.?indian|'
    r'slav|semi-slav|catalan|english|reti|kings.?gambit|vienna)\b',
    re.IGNORECASE
)


def tokenize(text: str) -> List[str]:
    """
    Extract meaningful tokens from text (no stopwords).

    Args:
        text: Input text

    Returns:
        List of lowercase tokens
    """
    tokens = re.findall(r"[A-Za-z0-9+.#=/-]+", (text or "").lower())
    return [t for t in tokens if t not in STOP_WORDS]


def jaccard_similarity(text1: str, text2: str) -> float:
    """
    Compute Jaccard similarity between two texts.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score (0.0 to 1.0)
    """
    set1, set2 = set(tokenize(text1)), set(tokenize(text2))

    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    return intersection / union if union > 0 else 0.0


class DiagramIndex:
    """
    In-memory index of chess diagrams from EPUB files.

    Provides fast lookup by book_id, diagram_id, and book_name.
    Includes quality filtering and relevance ranking.
    """

    def __init__(self):
        self.by_book = defaultdict(list)  # book_id -> [diagram_info]
        self.by_id = {}                   # diagram_id -> diagram_info
        self.whitelist = set()            # Set of valid diagram_ids
        self.book_name_to_id = {}         # book_name -> book_id (reverse lookup)
        self.total_diagrams = 0
        self.filtered_count = 0

    def load(self, metadata_path: str, min_size_bytes: int = 12000) -> 'DiagramIndex':
        """
        Load diagram metadata from JSON file.

        Args:
            metadata_path: Path to diagram_metadata_full.json
            min_size_bytes: Minimum file size to include (filters icons/ribbons)

        Returns:
            self (for chaining)
        """
        logger.info(f"Loading diagram metadata from {metadata_path}...")

        with open(metadata_path, 'r') as f:
            data = json.load(f)

        self.total_diagrams = data['stats']['total_diagrams']

        for diagram in data['diagrams']:
            # Quality filter: Skip small images (likely icons/ribbons)
            if diagram.get('size_bytes', 0) < min_size_bytes:
                self.filtered_count += 1
                continue

            book_id = diagram['book_id']
            diagram_id = diagram['diagram_id']

            # Store diagram
            self.by_book[book_id].append(diagram)
            self.by_id[diagram_id] = diagram
            self.whitelist.add(diagram_id)

            # Build reverse lookup (book_name -> book_id)
            book_name = diagram['epub_filename']
            if book_name not in self.book_name_to_id:
                self.book_name_to_id[book_name] = book_id

        # Sort diagrams by position_in_document for sequential relevance
        for book_id in self.by_book:
            self.by_book[book_id].sort(key=lambda x: x.get('position_in_document', 1e9))

        logger.info(f"✅ Loaded {len(self.by_id):,} diagrams from {len(self.by_book)} books")
        logger.info(f"   Filtered {self.filtered_count:,} small images (< {min_size_bytes:,} bytes)")
        logger.info(f"   Indexed {len(self.book_name_to_id)} unique book names")

        return self

    def get_diagrams_for_book(self, book_id: str) -> List[Dict]:
        """Get all diagrams for a specific book."""
        return self.by_book.get(book_id, [])

    def get_diagram_by_id(self, diagram_id: str) -> Optional[Dict]:
        """Get a single diagram by ID."""
        return self.by_id.get(diagram_id)

    def is_valid_diagram_id(self, diagram_id: str) -> bool:
        """Check if diagram ID exists in whitelist."""
        return diagram_id in self.whitelist

    def get_book_id_from_name(self, book_name: str) -> Optional[str]:
        """Map book filename to book_id."""
        return self.book_name_to_id.get(book_name)

    def rank_diagrams_for_chunk(
        self,
        diagrams: List[Dict],
        chunk: Dict,
        max_k: int = 5
    ) -> List[Dict]:
        """
        Rank diagrams by relevance to a text chunk.

        Algorithm:
            score = 0.8 * text_similarity (Jaccard)
                  + 0.4 * opening_keywords (ECO, "Najdorf", etc.)
                  + 0.2 * sequential_proximity (position in book)
                  + 0.1 * size_quality (larger images prioritized)

        Args:
            diagrams: List of diagram metadata dicts
            chunk: Qdrant chunk payload dict
            max_k: Maximum diagrams to return

        Returns:
            Top k diagrams sorted by relevance score
        """
        if not diagrams:
            return []

        # Extract chunk information
        chunk_text = chunk.get('text', '')[:2000]  # First 2K chars
        chunk_index = chunk.get('chunk_index', 0)

        scores = []

        for diagram in diagrams:
            # 1. Text overlap (Jaccard similarity)
            diagram_context = f"{diagram.get('context_before', '')} {diagram.get('context_after', '')}"
            score_overlap = 0.8 * jaccard_similarity(chunk_text, diagram_context)

            # 2. Opening keyword match
            score_keyword = 0.0
            if OPENING_KEYWORDS.search(chunk_text) and OPENING_KEYWORDS.search(diagram_context):
                score_keyword = 0.4

            # 3. Sequential proximity (position in book)
            score_proximity = 0.0
            if 'position_in_document' in diagram:
                delta = abs((diagram['position_in_document'] or 0) - chunk_index)
                score_proximity = 0.2 * math.exp(-delta / 10.0)

            # 4. Quality boost (larger images prioritized)
            score_quality = 0.1 if diagram.get('size_bytes', 0) >= 25000 else 0.0

            # Total score
            total_score = score_overlap + score_keyword + score_proximity + score_quality
            scores.append((total_score, diagram))

        # Sort by score (descending)
        scores.sort(key=lambda x: x[0], reverse=True)

        # Return top k
        top_diagrams = [diagram for _, diagram in scores[:max_k]]

        # Fallback: Ensure at least 2 diagrams if available (even if low score)
        if len(top_diagrams) < min(2, len(diagrams)):
            remaining = [diagram for _, diagram in scores[len(top_diagrams):2]]
            top_diagrams = (top_diagrams + remaining)[:max_k]

        return top_diagrams


# Global instance (loaded on app startup)
diagram_index = DiagramIndex()
