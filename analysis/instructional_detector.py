"""
Instructional Language Detector for Chess RAG System
Implements chess-specific instructional pattern recognition with context gates,
embedding confirmation, and category-based weighting.

Based on comprehensive AI partner consultation and technical validation.
"""

import re
import logging
from typing import List, Dict, Set, Tuple, Optional, NamedTuple
from dataclasses import dataclass
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class InstructionalHit:
    """Represents a detected instructional phrase with context"""
    phrase: str
    category: str
    sentence_idx: int
    span: Tuple[int, int]
    weight: float
    slots: Dict[str, str] = None
    context_valid: bool = False
    embedding_bonus: float = 0.0


class ChessEntityDetector:
    """Lightweight detectors for chess entities used in context gating"""

    def __init__(self):
        # SAN move pattern (loose but effective)
        self.san_pattern = re.compile(
            r'\b(O-O(?:-O)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?|[a-h]x[a-h][1-8](?:=[QRBN])?[+#]?)\b'
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

        # Phase indicators
        self.opening_indicators = re.compile(
            r'\b(?:theory|novelty|tabiya|ECO|opening|development|castling|center)\b',
            re.IGNORECASE
        )

        self.endgame_indicators = re.compile(
            r'\b(?:rook ending|opposition|zugzwang|tablebase|endgame|king activity|passed pawn)\b',
            re.IGNORECASE
        )

    def has_chess_context(self, sentence: str) -> bool:
        """Check if sentence has sufficient chess context for instructional phrases"""
        return (
                bool(self.san_pattern.search(sentence)) or
                bool(self.square_pattern.search(sentence)) or
                bool(self.eco_pattern.search(sentence)) or
                bool(self.eval_pattern.search(sentence))
        )

    def get_phase_hint(self, sentence: str) -> str:
        """Determine chess phase context"""
        if self.opening_indicators.search(sentence):
            return "opening"
        elif self.endgame_indicators.search(sentence):
            return "endgame"
        else:
            return "any"


class InstructionalLanguageDetector:
    """
    Chess-specific instructional language detector implementing:
    - Category-based weighting from AI partner recommendations
    - Context gates for false positive reduction
    - Embedding confirmation using MiniLM
    - Slot template support for dynamic patterns
    - Diminishing returns to prevent verbosity abuse
    """

    def __init__(self, embedding_model: Optional[SentenceTransformer] = None):
        self.entity_detector = ChessEntityDetector()
        self.embedding_model = embedding_model

        # Category weights from ChatGPT's recommendations
        self.category_weights = {
            'teaching_intent': 1.0,
            'template': 1.0,  # Slot-filled patterns
            'methodology': 0.9,
            'endgame_technique': 0.9,
            'tactical_explanation': 0.8,
            'middlegame_plan': 0.8,
            'evaluation_shift': 0.8,
            'opening_principle': 0.7,
            'practical_prep': 0.6
        }

        # Load vocabulary and compile patterns
        self._load_instructional_vocabulary()
        self._compile_patterns()

        # Precompute didactic exemplar embeddings for confirmation
        if self.embedding_model:
            self._precompute_didactic_exemplars()

    def _load_instructional_vocabulary(self):
        """Load instructional phrases from chess vocabulary"""
        from ..core.constants import ChessVocabulary

        chess_concepts = ChessVocabulary.get_chess_concepts()

        # Priority phrases from ChatGPT's 40 fixed phrases + 10 slot templates
        self.fixed_phrases = {
            'teaching_intent': [
                'the idea is', 'the key idea here', 'this move aims to',
                'with the idea of', 'the plan is simple', 'important concept',
                'fundamental principle', 'rule of thumb', 'model game', 'textbook example'
            ],
            'middlegame_plan': [
                'improve the worst piece', 'overprotect', 'create luft',
                'accumulate small advantages', 'probe weaknesses',
                'attack the base of the pawn chain', 'minority attack',
                'seize the open file', 'dominate the file'
            ],
            'endgame_technique': [
                'don\'t hurry', 'rook behind the passed pawn', 'build the bridge',
                'shouldering the king', 'opposition', 'triangulation',
                'outside passed pawn', 'corresponding squares'
            ],
            'tactical_explanation': [
                'removal of the defender', 'deflection theme', 'clearance idea',
                'zwischenzug resource', 'only resource', 'quiet move that wins'
            ],
            'evaluation_shift': [
                'only move', 'keeps the advantage', 'keeps the edge', 'equalizes',
                'move order nuance', 'imprecise move order', 'press without risk',
                'hard to hold', 'consolidates the advantage'
            ],
            'opening_principle': [
                'fights for the center', 'controls the center', 'develops with tempo',
                'violates a basic principle', 'keeps options flexible'
            ],
            'practical_prep': [
                'anti system setup', 'tabiya position', 'human-friendly plan',
                'practical choice over theoretical best'
            ]
        }

        # Slot templates from ChatGPT's recommendations
        self.slot_templates = [
            ('{MOVE} aims to', 'template'),
            ('{MOVE} prepares', 'template'),
            ('{MOVE} prevents', 'template'),
            ('re-route the {PIECE} to {SQUARE}', 'template'),
            ('overprotect {SQUARE}', 'template'),
            ('double rooks on {FILE}', 'template'),
            ('the idea behind {MOVE}', 'template'),
            ('fight for {SQUARE}', 'template'),
            ('control {SQUARE}', 'template'),
            ('activate the {PIECE}', 'template')
        ]

    def _compile_patterns(self):
        """Compile regex patterns for efficient matching"""
        import ahocorasick  # For efficient multi-pattern matching

        # Build Aho-Corasick automaton for fixed phrases
        self.ac_automaton = ahocorasick.Automaton()

        phrase_id = 0
        for category, phrases in self.fixed_phrases.items():
            for phrase in phrases:
                self.ac_automaton.add_word(phrase.lower(), (phrase_id, phrase, category))
                phrase_id += 1

        self.ac_automaton.make_automaton()

        # Compile slot template regexes
        self.slot_regexes = []
        san_pattern = r'(?:[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?|O-O(?:-O)?)'
        piece_pattern = r'(?:king|queen|rook|bishop|knight|pawn)'
        square_pattern = r'[a-h][1-8]'
        file_pattern = r'[a-h]-file'

        slot_patterns = {
            'MOVE': san_pattern,
            'PIECE': piece_pattern,
            'SQUARE': square_pattern,
            'FILE': file_pattern
        }

        for template, category in self.slot_templates:
            # Replace slot placeholders with regex patterns
            regex_pattern = template
            slots_in_template = []

            for slot, pattern in slot_patterns.items():
                if f'{{{slot}}}' in template:
                    regex_pattern = regex_pattern.replace(f'{{{slot}}}', f'(?P<{slot}>{pattern})')
                    slots_in_template.append(slot)

            compiled_regex = re.compile(regex_pattern, re.IGNORECASE)
            self.slot_regexes.append((compiled_regex, template, category, slots_in_template))

    def _precompute_didactic_exemplars(self):
        """Precompute embeddings for didactic exemplar sentences"""
        didactic_exemplars = [
            "The key idea behind this move is to control the center",
            "This plan aims to improve piece coordination",
            "The typical pattern involves a minority attack",
            "A fundamental principle is king safety before attack",
            "This endgame technique requires precise calculation"
        ]

        self.didactic_embeddings = self.embedding_model.encode(didactic_exemplars)
        # Compute prototype embedding (mean)
        self.didactic_prototype = np.mean(self.didactic_embeddings, axis=0)

    def analyze_instructional_language(self, chunks: List[str]) -> float:
        """
        Main analysis method implementing AI partner recommendations:
        - Context gating for false positive reduction
        - Category-based weighting with diminishing returns
        - Embedding confirmation when available
        - Plan chain bonus detection
        """
        all_hits = []

        # Process each chunk (sentence)
        for chunk_idx, chunk in enumerate(chunks):
            chunk_lower = chunk.lower()

            # Find fixed phrase matches using Aho-Corasick
            for end_idx, (phrase_id, phrase, category) in self.ac_automaton.iter(chunk_lower):
                start_idx = end_idx - len(phrase) + 1

                hit = InstructionalHit(
                    phrase=phrase,
                    category=category,
                    sentence_idx=chunk_idx,
                    span=(start_idx, end_idx + 1),
                    weight=self.category_weights.get(category, 0.5)
                )

                # Apply context gate
                hit.context_valid = self.entity_detector.has_chess_context(chunk)
                if hit.context_valid:
                    # Add embedding confirmation bonus if available
                    if self.embedding_model:
                        hit.embedding_bonus = self._compute_embedding_bonus(chunk)

                    all_hits.append(hit)

            # Find slot template matches
            for regex, template, category, slots in self.slot_regexes:
                for match in regex.finditer(chunk):
                    # Extract slot values
                    slot_values = {}
                    for slot in slots:
                        if match.group(slot):
                            slot_values[slot] = match.group(slot)

                    hit = InstructionalHit(
                        phrase=template,
                        category=category,
                        sentence_idx=chunk_idx,
                        span=match.span(),
                        weight=self.category_weights.get(category, 0.5),
                        slots=slot_values
                    )

                    # Apply context gate (should pass since slots require chess entities)
                    hit.context_valid = True  # Slot patterns inherently have chess context

                    if self.embedding_model:
                        hit.embedding_bonus = self._compute_embedding_bonus(chunk)

                    all_hits.append(hit)

        # Compute category scores with diminishing returns
        category_scores = {}
        for category in self.category_weights.keys():
            category_hits = [h for h in all_hits if h.category == category and h.context_valid]
            if category_hits:
                # Sort by weight + embedding bonus, apply diminishing returns
                scores = [h.weight + h.embedding_bonus for h in category_hits]
                scores.sort(reverse=True)
                category_scores[category] = self._apply_diminishing_returns(scores[:6])  # Cap at 6

        # Compute final instructional language score
        total_score = sum(category_scores.values())

        # Normalize by maximum possible score (rough estimate)
        max_possible = len(self.category_weights) * 1.5  # Account for embedding bonuses
        normalized_score = min(total_score / max_possible, 1.0)

        return normalized_score

    def _compute_embedding_bonus(self, sentence: str) -> float:
        """Compute embedding similarity bonus with didactic exemplars"""
        if not hasattr(self, 'didactic_prototype'):
            return 0.0

        try:
            sentence_embedding = self.embedding_model.encode([sentence])[0]
            cosine_sim = np.dot(sentence_embedding, self.didactic_prototype) / (
                    np.linalg.norm(sentence_embedding) * np.linalg.norm(self.didactic_prototype)
            )

            # ChatGPT's threshold recommendations
            if cosine_sim >= 0.55:
                return 0.15  # Full bonus
            elif cosine_sim >= 0.48:
                return 0.07  # Half bonus
            else:
                return 0.0

        except Exception as e:
            logger.warning(f"Embedding bonus calculation failed: {e}")
            return 0.0

    def _apply_diminishing_returns(self, scores: List[float], decay_factor: float = 0.8) -> float:
        """Apply diminishing returns to prevent verbosity abuse"""
        total_score = 0.0
        multiplier = 1.0

        for score in scores:
            total_score += score * multiplier
            multiplier *= decay_factor

        return total_score

    def detect_plan_chains(self, chunks: List[str]) -> float:
        """
        Detect plan chain patterns: aims/prepares/prevents + improve/consolidate
        From ChatGPT's recommendations for plan chain bonus
        """
        intent_patterns = re.compile(
            r'\b(?:aims to|prepares|prevents|with the idea|in order to)\b',
            re.IGNORECASE
        )
        action_patterns = re.compile(
            r'\b(?:improve|re-route|consolidate|activate|control|dominate)\b',
            re.IGNORECASE
        )

        chain_detected = False

        # Look for intent + action within 2 sentences
        for i, chunk in enumerate(chunks):
            if intent_patterns.search(chunk):
                # Check current sentence and next sentence for action
                search_chunks = chunks[i:i + 2] if i < len(chunks) - 1 else [chunk]
                for search_chunk in search_chunks:
                    if action_patterns.search(search_chunk):
                        chain_detected = True
                        break
                if chain_detected:
                    break

        return 0.05 if chain_detected else 0.0  # ChatGPT's recommended bonus