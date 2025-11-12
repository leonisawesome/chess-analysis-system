#!/usr/bin/env python3
"""
Static EPUB Diagram Service
Loads diagram metadata, ranks diagrams by relevance, and provides lookup utilities.

Phase 6.1a - Static Diagram Integration
"""

from collections import defaultdict
import json
import math
import os
import re
import logging
from typing import List, Dict, Optional, Set

logger = logging.getLogger(__name__)

# Stopwords for text similarity (minimal set for chess content)
STOP_WORDS = set("""
    the a an and or of to in for on with from this that these those is are was were
    be as by after before during white black move moves plan plans strategy lines
    mainline variation position positions
""".split())

# ECO code pattern (A00-E99)
ECO_PATTERN = re.compile(r'\b([A-E][0-9]{2})\b', re.IGNORECASE)

# Opening lexicon for detection with ECO ranges
# Note: Uses both ASCII apostrophe (') and typographical apostrophe (') for Unicode compatibility
OPENING_LEXICON = {
    "queens_gambit_declined": [
        r"queen[''']?s gambit declined", r"\bqgd\b",
        r"\b(d3[0-9]|d4[0-9]|d5[0-9]|d6[0-9])\b"  # ECO D30–D69
    ],
    "sicilian": [
        r"\bsicilian\b", r"\bnajdorf\b", r"\bdragon\b", r"\bsveshnikov\b",
        r"\btaimanov\b", r"\bkan\b", r"\bscheveningen\b",
        r"\b(b2[0-9]|b3[0-9]|b4[0-9]|b5[0-9]|b6[0-9]|b7[0-9]|b8[0-9]|b9[0-9])\b"  # B20-B99
    ],
    "caro_kann": [r"caro-?kann", r"\bb1[0-9]\b"],  # B10-B19
    "kings_indian": [r"king[''']?s indian", r"\be9[0-9]\b"],  # E90-E99
    "french": [r"\bfrench\b", r"\bc0[0-9]|c1[0-9]\b"],  # C00-C19
    "ruy_lopez": [r"ruy.?lopez", r"\bspanish\b", r"\bc6[0-9]|c7[0-9]|c8[0-9]|c9[0-9]\b"],
    "nimzo_indian": [r"nimzo-?indian", r"\be2[0-9]|e3[0-9]|e4[0-9]\b"],
    "grunfeld": [r"gr[uü]nfeld", r"\bd7[0-9]|d8[0-9]|d9[0-9]\b"],
    "english": [r"\benglish opening\b", r"\benglish\b", r"\ba[12][0-9]\b"],
    "italian": [r"\bitalian\b", r"\bgiuoco\b", r"\bc5[0-9]\b"],
}

# Original keyword pattern kept for backward compatibility
OPENING_KEYWORDS = re.compile(
    r'\b([A-E][0-9]{2}|najdorf|benko|hedgehog|caro-kann|sicilian|french|grunfeld|'
    r'king.?indian|...e5|...c5|ruy.?lopez|queens.?gambit|italian|spanish|scotch|'
    r'pirc|alekhine|dragon|sveshnikov|taimanov|kan|scheveningen|nimzo|queens.?indian|'
    r'slav|semi-slav|catalan|english|reti|kings.?gambit|vienna)\b',
    re.IGNORECASE
)


def detect_opening_tags(text: str) -> tuple:
    """
    Detect opening tags and ECO codes from text.

    Args:
        text: Query or caption text

    Returns:
        Tuple of (opening_tags set, eco_codes set)
    """
    text_lower = (text or "").lower()
    tags = set()
    eco_codes = set()

    # Extract ECO codes
    for match in ECO_PATTERN.finditer(text):
        eco_codes.add(match.group(1).upper())

    # Match opening lexicon patterns
    for opening_key, patterns in OPENING_LEXICON.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                tags.add(opening_key)
                break

    return tags, eco_codes


def normalize_caption(text: str, max_len: int = 200) -> str:
    """
    Normalize EPUB caption text by fixing spacing issues.

    Handles common concatenation artifacts:
    - "TheNb6" -> "The Nb6"
    - "0-0-0Bd7" -> "0-0-0 Bd7"
    - "is10.Rc1" -> "is 10.Rc1"
    - "Bd713." -> "Bd7 13."

    Args:
        text: Raw caption text
        max_len: Maximum caption length

    Returns:
        Cleaned caption with proper spacing
    """
    if not text:
        return "Chess diagram"

    text = text.strip()

    # 1. Insert space between lowercase and piece letter (KQRBN)
    #    "theBc8" -> "the Bc8", "TheNb6" -> "The Nb6"
    text = re.sub(r'([a-z])([KQRBN])', r'\1 \2', text)

    # 2. Insert space after castling before next piece/move
    #    "0-0-0Bd7" -> "0-0-0 Bd7"
    text = re.sub(r'(0-0-0|0-0)(?=[KQRBNa-h0-9])', r'\1 ', text)

    # 3. Insert space before move numbers after letters
    #    "is10.Rc1" -> "is 10.Rc1"
    text = re.sub(r'([A-Za-z])(\d+\.)', r'\1 \2', text)

    # 4. Insert space between SAN notation and following move number
    #    "Bd713." -> "Bd7 13."
    text = re.sub(r'([KQRBN]?[a-h]?[1-8][\+#]?)(\d+\.)', r'\1 \2', text)

    # 5. Collapse multiple spaces
    text = re.sub(r'\s{2,}', ' ', text)

    # 6. Smart truncate at word boundary to avoid mid-word cutoff
    if len(text) > max_len:
        cutoff = text.rfind(' ', 0, max_len)
        if cutoff < max_len // 2:  # No space found in reasonable range
            cutoff = max_len
        text = text[:cutoff].rstrip() + '…'

    return text


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
        registered_books: Set[str] = set()

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
            if book_id not in registered_books:
                self._register_book_aliases(book_id, diagram)
                registered_books.add(book_id)

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

    def get_book_title(self, book_id: str) -> Optional[str]:
        diagrams = self.by_book.get(book_id)
        if not diagrams:
            return None
        return diagrams[0].get('book_title') or diagrams[0].get('source_file') or diagrams[0].get('epub_filename')

    def get_diagram_by_id(self, diagram_id: str) -> Optional[Dict]:
        """Get a single diagram by ID."""
        return self.by_id.get(diagram_id)

    def is_valid_diagram_id(self, diagram_id: str) -> bool:
        """Check if diagram ID exists in whitelist."""
        return diagram_id in self.whitelist

    def get_book_id_from_name(self, book_name: str) -> Optional[str]:
        """Map book filename to book_id."""
        return self.book_name_to_id.get(book_name)

    def _register_book_aliases(self, book_id: str, diagram: Dict) -> None:
        """
        Register multiple lookup aliases for a book so different naming
        conventions (slug, title, with/without extension) resolve correctly.
        """
        filename = (diagram.get('epub_filename')
                    or diagram.get('epub_file')
                    or diagram.get('source_file')
                    or '').strip()
        title = (diagram.get('book_title')
                 or diagram.get('title')
                 or '').strip()

        candidates = set()

        if filename:
            candidates.add(filename)
            base = os.path.splitext(os.path.basename(filename))[0]
            candidates.add(base)
            candidates.add(base.lower())
            candidates.add(base.replace('_', ' '))
            candidates.add(base.replace('_', ' ').lower())

        if title:
            candidates.add(title)
            candidates.add(title.lower())
            slug = self._slugify(title)
            if slug:
                candidates.add(slug)

        for alias in candidates:
            key = alias.strip()
            if key and key not in self.book_name_to_id:
                self.book_name_to_id[key] = book_id

    def search_books_by_query(self, query: str, max_matches: int = 3) -> List[str]:
        """Return book IDs whose titles share tokens with the user query."""
        if not query:
            return []

        tokens = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) >= 4]
        if not tokens:
            return []

        token_set = set(tokens)
        candidates = []

        for book_id, diagrams in self.by_book.items():
            title = (diagrams[0].get('book_title') or diagrams[0].get('source_file') or '').lower()
            if not title:
                continue
            title_tokens = set(re.findall(r"[a-z0-9]+", title))
            overlap = token_set & title_tokens
            if not overlap:
                continue
            score = len(overlap) / len(token_set)
            candidates.append((score, -len(title_tokens), book_id))

        if not candidates:
            return []

        candidates.sort(key=lambda x: (-x[0], x[1]))
        return [book_id for _, _, book_id in candidates[:max_matches]]

    @staticmethod
    def _slugify(value: str) -> str:
        value = value.lower()
        value = re.sub(r'[^a-z0-9]+', '_', value)
        return value.strip('_')

    @staticmethod
    def is_metadata_image(diagram: Dict) -> bool:
        """
        Detect if a diagram is likely book metadata/promotional content rather than a chess position.

        Returns True if diagram should be EXCLUDED.
        """
        context_before = (diagram.get('context_before') or '').lower()
        context_after = (diagram.get('context_after') or '').lower()
        combined_context = f"{context_before} {context_after}"

        # Metadata/promotional/illustrative keywords
        metadata_keywords = [
            'gambit publications',
            'app store',
            'google play',
            'apple store',
            'lichess.org',
            'click on the direct links',
            'search for',
            'to find chess studio',
            'cannot guarantee that this feature',
            'www.',
            'http://',
            'https://',
            '.com',
            '.org',
            # Metaphorical/illustrative language (not chess positions)
            'tag-team',
            'partner',
            'think of',
            'let\'s be',
            'we\'re all going',
            'close friends',
            'less formal',
            'arrows',
            'illustration',
            'metaphor',
            'icon',
            'symbol',
            'graphic',
            # Non-diagram artifacts (chapter banners, author bios, photos)
            'chapter guide',
            'chapter overview',
            'chapter summary',
            'preface',
            'introduction',
            'about the author',
            'coach',
            'nationally ranked',
            'national champion',
            'has taught over',
            'biography',
            'dedication',
            'photo credit'
        ]

        # If context contains promotional/metaphorical text, exclude it
        for keyword in metadata_keywords:
            if keyword in combined_context:
                return True

        filename = (diagram.get('original_filename') or diagram.get('image_file') or '').lower()
        diagram_id = diagram.get('diagram_id', '').lower()

        filename_metadata_tokens = [
            'cover',
            'chapter_',
            'chapter-',
            'preface',
            'introduction',
            'about_',
            'author',
            'coach',
            'portrait',
            'banner',
            'toc',
            'contents'
        ]
        if any(token in filename for token in filename_metadata_tokens):
            return True

        # Early diagrams (e.g., _0000) can still be valid boards, so keep them unless
        # other metadata rules trigger.

        # If caption doesn't contain chess-specific terms, likely not a chess diagram
        chess_keywords = [
            'position', 'move', 'square', 'piece', 'pawn', 'knight', 'bishop',
            'rook', 'queen', 'king', 'file', 'rank', 'diagram', 'after',
            'white', 'black', 'opening', 'defense', 'variation', 'attack'
        ]

        has_chess_term = any(keyword in combined_context for keyword in chess_keywords)
        if len(combined_context) > 50 and not has_chess_term:
            # Long caption with no chess terms - likely metaphorical/illustrative
            return True

        width = diagram.get('width') or diagram.get('image_width') or 0
        height = diagram.get('height') or diagram.get('image_height') or 0
        if width and height and (width < 400 or height < 400):
            return True
        if diagram.get('size_bytes', 0) < 20000:
            return True

        return False

    def rank_diagrams_for_chunk(
        self,
        diagrams: List[Dict],
        chunk: Dict,
        query: str = "",
        max_k: int = 5
    ) -> List[Dict]:
        """
        Rank diagrams by relevance to a text chunk and user query.

        Algorithm (query-aware):
            score = 3.5 * opening_match (query vs diagram)
                  + 2.0 * same_chapter
                  + 0.8 * text_similarity (Jaccard)
                  + 0.2 * sequential_proximity
                  + 0.1 * size_quality

        If query has opening intent (QGD, Sicilian, etc.), diagrams with matching
        openings receive a dominant boost (3.5x weight).

        Args:
            diagrams: List of diagram metadata dicts
            chunk: Qdrant chunk payload dict
            query: User's original query text (for opening detection)
            max_k: Maximum diagrams to return

        Returns:
            Top k diagrams sorted by relevance score
        """
        if not diagrams:
            return []

        # FILTER: Remove metadata/promotional images
        chess_diagrams = [d for d in diagrams if not self.is_metadata_image(d)]

        if not chess_diagrams:
            print("⚠️  All diagrams filtered out as metadata - no valid chess diagrams found")
            return []

        if len(chess_diagrams) < len(diagrams):
            print(f"🔍 Filtered {len(diagrams) - len(chess_diagrams)} metadata images, {len(chess_diagrams)} chess diagrams remaining")

        diagrams = chess_diagrams

        # Extract chunk information
        chunk_text = chunk.get('text', '')[:2000]  # First 2K chars
        chunk_index = chunk.get('chunk_index', 0)

        # Detect opening intent from query
        q_tags, q_eco = detect_opening_tags(query)
        opening_intent = bool(q_tags or q_eco)

        # Detect opening tags from chunk metadata
        chunk_metadata = " ".join([
            chunk.get('title', ''),
            chunk.get('book_title', ''),
            chunk.get('chapter_title', ''),
            chunk.get('section_path', '')
        ])
        r_tags, r_eco = detect_opening_tags(chunk_metadata)

        # Try to identify chunk's source document
        chunk_doc = chunk.get('chapter_file') or chunk.get('section_path') or ""

        scores = []

        for diagram in diagrams:
            # Diagram context and metadata
            diagram_context = f"{diagram.get('context_before', '')} {diagram.get('context_after', '')}"
            diagram_metadata = f"{diagram_context} {diagram.get('book_title', '')}"
            d_tags, d_eco = detect_opening_tags(diagram_metadata)

            # 1. OPENING MATCH (dominant signal for featured diagrams)
            opening_match = 0.0
            if opening_intent:
                # Check direct query-diagram match OR query-chunk-diagram chain
                if (q_tags & d_tags) or (q_eco & d_eco) or \
                   ((q_tags & r_tags) and (r_tags & d_tags)) or \
                   ((q_eco & r_eco) and (r_eco & d_eco)):
                    opening_match = 3.5

            # 2. SAME CHAPTER (strong signal for within-book relevance)
            same_chapter = 0.0
            diagram_doc = diagram.get('html_document', '')
            if chunk_doc and diagram_doc and diagram_doc in chunk_doc:
                same_chapter = 2.0

            # 3. TEXT OVERLAP (Jaccard similarity)
            raw_similarity = jaccard_similarity(chunk_text, diagram_context)
            text_similarity = 0.8 * raw_similarity

            # 4. SEQUENTIAL PROXIMITY (position in book)
            proximity = 0.0
            if 'position_in_document' in diagram:
                delta = abs((diagram['position_in_document'] or 0) - chunk_index)
                proximity = 0.2 * math.exp(-delta / 10.0)

            # 5. QUALITY BOOST (larger images prioritized)
            quality = 0.1 if diagram.get('size_bytes', 0) >= 25000 else 0.0

            # Total score
            total_score = opening_match + same_chapter + text_similarity + proximity + quality
            scores.append((total_score, diagram, raw_similarity, opening_match))

        # Sort by score (descending)
        scores.sort(key=lambda x: x[0], reverse=True)

        # If opening intent detected, prefer opening-matched diagrams
        if opening_intent:
            matched = [diagram for score, diagram, _, match in scores if match >= 3.5]
            if len(matched) >= 2:
                # Sufficient opening-matched diagrams found
                return matched[:max_k]

        # Drop diagrams with negligible textual overlap to avoid mismatched openings
        similarity_floor = 0.08 if opening_intent else 0.04
        score_floor = 0.6 if opening_intent else 0.25
        filtered = [
            (score, diagram)
            for score, diagram, raw_sim, _ in scores
            if score >= score_floor and raw_sim >= similarity_floor
        ]

        candidate_scores = filtered if filtered else [(score, diagram) for score, diagram, _, _ in scores]

        # Default: return top k by score
        top_diagrams = [diagram for _, diagram in candidate_scores[:max_k]]

        # Fallback: Ensure at least 2 diagrams if available (even if low score)
        if len(top_diagrams) < min(2, len(diagrams)):
            remaining = [diagram for _, diagram in scores[len(top_diagrams):2]]
            top_diagrams = (top_diagrams + remaining)[:max_k]

        return top_diagrams


# Global instance (loaded on app startup)
diagram_index = DiagramIndex()
