"""
Chess-specific instructional language detector - Hotfix implementation
Based on 4-AI partner consultation consensus
Implements: empirical vocabulary, context gates, diminishing returns, slot patterns
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict, Counter

# Import vocabulary from hotfix file
from .instructional_vocabulary_hotfix import (
    INSTRUCTIONAL_LEXICON,
    SLOT_PATTERNS,
    CATEGORY_WEIGHTS,
    CATEGORY_CAPS
)

# Optional embedding support
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np

    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class InstructionalHit:
    """Represents a detected instructional phrase with context validation"""
    phrase: str
    category: str
    position: int
    context_valid: bool = False
    embedding_score: float = 0.0
    weight: float = 1.0


class ChessEntityDetector:
    """
    Detects chess context for gate validation
    Implements OR logic across chess cues per AI partner recommendations
    """

    def __init__(self):
        # SAN notation patterns
        self.san_pattern = re.compile(
            r'\b(?:O-O(?:-O)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?)\b'
        )

        # Square notation
        self.square_pattern = re.compile(r'\b[a-h][1-8]\b')

        # ECO codes
        self.eco_pattern = re.compile(r'\b[A-E][0-9]{2}\b')

        # Evaluation symbols and words
        self.eval_pattern = re.compile(
            r'\b(?:only move|equalize|equalizes|advantage|edge|keeps?|consolidates?|press|hold|winning|losing|equal|better|worse|±|∓|==|\+=|\+−)\b',
            re.IGNORECASE
        )

        # Chess terminology from existing system
        self.chess_terms_pattern = re.compile(
            r'\b(?:pawn|knight|bishop|rook|queen|king|castle|castling|endgame|opening|middlegame|tactics|strategy|sacrifice|pin|fork|skewer|discovered|deflection|clearance|zwischenzug)\b',
            re.IGNORECASE
        )

    def has_chess_context(self, text: str, window_sentences: int = 1) -> bool:
        """
        Check if text has sufficient chess context for instructional phrases
        Uses OR logic across multiple chess indicators per AI partner consensus
        """
        # Check current sentence
        if self._has_chess_indicators(text):
            return True

        # Check ±window_sentences if window > 0
        if window_sentences > 0:
            sentences = text.split('.')
            for i, sentence in enumerate(sentences):
                if i > 0 and self._has_chess_indicators(sentences[i - 1]):
                    return True
                if i < len(sentences) - 1 and self._has_chess_indicators(sentences[i + 1]):
                    return True

        return False

    def _has_chess_indicators(self, sentence: str) -> bool:
        """Check single sentence for chess indicators"""
        return (
                bool(self.san_pattern.search(sentence)) or
                bool(self.square_pattern.search(sentence)) or
                bool(self.eco_pattern.search(sentence)) or
                bool(self.eval_pattern.search(sentence)) or
                bool(self.chess_terms_pattern.search(sentence))
        )


class InstructionalLanguageDetector:
    """
    Chess-specific instructional language detector implementing 4-AI partner consensus:
    - Empirical vocabulary from GM content analysis
    - Context gates with OR logic and ±1 sentence window
    - Embedding confirmation (optional)
    - Diminishing returns with category caps
    - Slot template support for dynamic patterns
    """

    def __init__(self, embedding_model: Optional[SentenceTransformer] = None,
                 use_embedding_confirmation: bool = False):
        self.entity_detector = ChessEntityDetector()
        self.embedding_model = embedding_model
        self.use_embedding_confirmation = use_embedding_confirmation

        # Load vocabulary and compile patterns
        self._load_instructional_vocabulary()
        self._compile_patterns()

        # Precompute didactic exemplar embeddings if available
        if self.embedding_model and EMBEDDING_AVAILABLE and use_embedding_confirmation:
            self._precompute_didactic_exemplars()

        logger.info(f"InstructionalLanguageDetector initialized:")
        logger.info(f"  - Fixed phrases: {sum(len(phrases) for phrases in self.fixed_phrases.values())}")
        logger.info(f"  - Slot patterns: {len(self.slot_patterns)}")
        logger.info(f"  - Embedding confirmation: {self.use_embedding_confirmation}")

    def _load_instructional_vocabulary(self):
        """Load empirical vocabulary from AI partner consultation"""
        self.fixed_phrases = INSTRUCTIONAL_LEXICON
        self.slot_patterns = SLOT_PATTERNS
        self.category_weights = CATEGORY_WEIGHTS
        self.category_caps = CATEGORY_CAPS

        # Log vocabulary statistics per AI partner recommendations
        for category, phrases in self.fixed_phrases.items():
            logger.debug(f"Loaded {len(phrases)} phrases for category '{category}': {phrases[:3]}...")

    def _compile_patterns(self):
        """Compile regex patterns for efficient matching"""
        self.compiled_patterns = {}

        # Compile fixed phrase patterns by category
        for category, phrases in self.fixed_phrases.items():
            patterns = []
            for phrase in phrases:
                # Escape special regex characters, make case-insensitive
                escaped = re.escape(phrase.lower())
                patterns.append(escaped)

            if patterns:
                combined_pattern = r'\b(?:' + '|'.join(patterns) + r')\b'
                self.compiled_patterns[category] = re.compile(combined_pattern, re.IGNORECASE)

        # Compile slot patterns
        self.compiled_slot_patterns = []
        for pattern_spec in self.slot_patterns:
            compiled = re.compile(pattern_spec['pattern'], re.IGNORECASE)
            self.compiled_slot_patterns.append({
                'category': pattern_spec['category'],
                'pattern': compiled,
                'weight': pattern_spec['weight'],
                'slots': pattern_spec.get('slots', [])
            })

    def _precompute_didactic_exemplars(self):
        """Precompute embeddings for didactic exemplars (optional feature)"""
        exemplars = [
            "The key idea behind this move is to improve piece coordination",
            "This typical plan aims to dominate the center",
            "The fundamental principle here is king safety",
            "This textbook example shows proper technique"
        ]

        try:
            self.didactic_embeddings = self.embedding_model.encode(exemplars)
            self.embedding_threshold_full = 0.55
            self.embedding_threshold_half = 0.48
            logger.info("Didactic exemplar embeddings precomputed")
        except Exception as e:
            logger.warning(f"Failed to precompute embeddings: {e}")
            self.use_embedding_confirmation = False

    def analyze_instructional_language(self, chunks: List[str]) -> float:
        """
        Main analysis method implementing 4-AI partner consensus approach
        Returns normalized instructional language score [0.0, 1.0]
        """
        if not chunks:
            return 0.0

        # Combine all chunks for analysis
        text = ' '.join(chunks)

        # Initialize tracking
        all_hits = []
        category_counts = defaultdict(int)
        total_hits_raw = 0
        total_hits_gated = 0

        # Phase 1: Fixed phrase detection
        for category, pattern in self.compiled_patterns.items():
            matches = pattern.finditer(text.lower())

            for match in matches:
                total_hits_raw += 1

                # Extract context window for gate validation
                start_pos = max(0, match.start() - 200)
                end_pos = min(len(text), match.end() + 200)
                context = text[start_pos:end_pos]

                # Create hit object
                hit = InstructionalHit(
                    phrase=match.group(),
                    category=category,
                    position=match.start(),
                    weight=self.category_weights.get(category, 1.0)
                )

                # Gate validation (OR logic, ±1 sentence window)
                hit.context_valid = self.entity_detector.has_chess_context(context, window_sentences=1)

                if hit.context_valid:
                    total_hits_gated += 1

                    # Apply diminishing returns
                    if category_counts[category] < self.category_caps[category]:
                        diminishing_factor = 0.8 ** category_counts[category]
                        hit.weight *= diminishing_factor
                        all_hits.append(hit)
                        category_counts[category] += 1

        # Phase 2: Slot pattern detection
        for pattern_spec in self.compiled_slot_patterns:
            matches = pattern_spec['pattern'].finditer(text)

            for match in matches:
                total_hits_raw += 1

                # Extract context for gate validation
                start_pos = max(0, match.start() - 200)
                end_pos = min(len(text), match.end() + 200)
                context = text[start_pos:end_pos]

                hit = InstructionalHit(
                    phrase=match.group(),
                    category=pattern_spec['category'],
                    position=match.start(),
                    weight=pattern_spec['weight']
                )

                hit.context_valid = self.entity_detector.has_chess_context(context, window_sentences=1)

                if hit.context_valid:
                    total_hits_gated += 1
                    category = pattern_spec['category']

                    if category_counts[category] < self.category_caps[category]:
                        diminishing_factor = 0.8 ** category_counts[category]
                        hit.weight *= diminishing_factor
                        all_hits.append(hit)
                        category_counts[category] += 1

        # Phase 3: Optional embedding confirmation
        if self.use_embedding_confirmation and all_hits and EMBEDDING_AVAILABLE:
            self._apply_embedding_confirmation(all_hits, text)

        # Calculate final score
        total_weighted_score = sum(hit.weight for hit in all_hits)

        # Normalize by text length (rough approximation)
        text_length_factor = len(text.split()) / 1000.0  # Per 1000 words
        normalized_score = min(total_weighted_score / max(text_length_factor, 0.5), 1.0)

        # Log diagnostics per AI partner requirements
        gate_pass_rate = total_hits_gated / max(total_hits_raw, 1)
        logger.info(
            f"INSTRUCTIONAL ANALYSIS - Raw hits: {total_hits_raw}, Gated: {total_hits_gated}, Pass rate: {gate_pass_rate:.3f}")
        logger.info(f"INSTRUCTIONAL ANALYSIS - Categories: {dict(category_counts)}")
        logger.info(f"INSTRUCTIONAL ANALYSIS - Final score: {normalized_score:.3f}")

        return normalized_score

    def _apply_embedding_confirmation(self, hits: List[InstructionalHit], text: str):
        """Apply optional embedding confirmation to reduce false positives"""
        if not self.embedding_model:
            return

        try:
            # Extract contexts around hits
            contexts = []
            for hit in hits:
                start = max(0, hit.position - 100)
                end = min(len(text), hit.position + 100)
                contexts.append(text[start:end])

            # Compute similarities with didactic exemplars
            context_embeddings = self.embedding_model.encode(contexts)

            for i, hit in enumerate(hits):
                similarities = [
                    np.dot(context_embeddings[i], exemplar) /
                    (np.linalg.norm(context_embeddings[i]) * np.linalg.norm(exemplar))
                    for exemplar in self.didactic_embeddings
                ]
                max_similarity = max(similarities)

                # Apply embedding-based weighting
                if max_similarity >= self.embedding_threshold_full:
                    hit.embedding_score = 1.0
                elif max_similarity >= self.embedding_threshold_half:
                    hit.embedding_score = 0.5
                    hit.weight *= 0.5
                else:
                    hit.embedding_score = 0.0
                    hit.weight *= 0.1  # Heavily penalize low similarity

        except Exception as e:
            logger.warning(f"Embedding confirmation failed: {e}")