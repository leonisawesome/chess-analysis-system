"""
PGN Analysis Engine and EVS (Educational Value Score) Calculator.

This module analyzes chess game notation (PGN) content and calculates Educational Value Scores.
The EVS should identify high-quality instructional content that merits inclusion in the RAG system.

CRITICAL: This is where the EVS calculation issue needs to be fixed.
GM instructional content should score 85+ EVS, not 60-65.
"""

import logging
import re
import unicodedata
from typing import List, Tuple, Optional

from ..core.models import PGNAnalysisResult, create_empty_pgn_result
from ..core.constants import EVSThresholds


class AdvancedPGNDetector:
    """
    Hybrid PGN detection and analysis engine.

    This class combines simple pattern matching with sophisticated analysis
    to evaluate the educational value of chess content. The goal is to identify
    high-quality instructional material that should score 85+ EVS.

    ARCHITECTURAL NOTE: This class calculates the base EVS score which then
    gets integrated with semantic analysis via the integration layer.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Compile regex patterns for performance
        self._compile_patterns()

        # Educational cue patterns for detecting instructional content
        self.educational_patterns = [
            r'(?i)\b(?:because|since|therefore|thus|consequently)\b',
            r'(?i)\b(?:idea|plan|strategy|concept|principle)\b',
            r'(?i)\b(?:better|stronger|weaker|good|bad|excellent|poor)\s+(?:move|position|choice)\b',
            r'(?i)\b(?:white|black)\s+(?:should|must|needs to|has to|wants to|aims to)\b',
            r'(?i)\b(?:typical|common|standard|usual|normal)\s+(?:position|move|structure)\b',
            r'(?i)\b(?:advantage|disadvantage|edge|initiative|pressure)\b',
            r'(?i)\b(?:attacking|defending|controlling|improving|developing)\b'
        ]

        # Famous game detection patterns (high educational value)
        self.famous_contexts = [
            r'(?i)\b(?:world championship|candidates|olympiad)\b',
            r'(?i)\b(?:kasparov|karpov|fischer|carlsen|anand|kramnik|tal|petrosian|spassky|botvinnik)\b',
            r'(?i)\b(?:immortal game|evergreen game|opera game|game of the century)\b'
        ]

        # High-value instructional content patterns
        self.instructional_context_patterns = [
            r'(?i)\b(?:masterclass|master class|grandmaster course|chess course)\b',
            r'(?i)\b(?:lesson|tutorial|example|demonstration|analysis)\b',
            r'(?i)\b(?:opening theory|middlegame planning|endgame technique)\b',
            r'(?i)\b(?:positional understanding|strategic concept|tactical pattern)\b',
            r'(?i)\b(?:training|education|instruction|teaching|coaching)\b'
        ]

    def _compile_patterns(self):
        """Compile regex patterns for performance"""
        self.move_pattern = re.compile(r'\b(?:[KQRBN]?[a-h]?[1-8]?[x]?[a-h][1-8](?:=[QRBN])?[+#]?|O-O(?:-O)?[+#]?)\b')
        self.move_number_pattern = re.compile(r'\b\d+\.(?:\.\.)?\s*')
        self.annotation_pattern = re.compile(r'[!?]{1,2}')
        self.nag_pattern = re.compile(r'\$\d+')
        self.comment_pattern = re.compile(r'\{([^}]*)\}')
        self.variation_pattern = re.compile(r'\(([^)]*)\)')
        self.header_pattern = re.compile(r'\[(\w+)\s+"([^"]*)"\]')
        self.result_pattern = re.compile(r'\b(?:1-0|0-1|1/2-1/2|\*)\b')

    def preprocess_text(self, text: str) -> str:
        """Enhanced text preprocessing for PDF artifacts and unicode"""
        if not text:
            return ""

        # Handle unicode and smart quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        # Fix PDF artifacts
        text = re.sub(r'([a-zA-Z])\s+([a-zA-Z])', r'\1\2', text)  # Fix broken words
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace

        # Fix broken move notation
        text = re.sub(r'(\d+)\s*\.\s*([KQRBN]?[a-h][1-8])', r'\1.\2', text)

        return text.strip()

    def detect_pgn_regions(self, text: str, window_size: int = 200) -> List[Tuple[str, int, int]]:
        """Detect PGN regions using sliding window approach"""
        text = self.preprocess_text(text)
        regions = []

        # Sliding window to find PGN-dense areas
        words = text.split()
        for i in range(0, len(words) - window_size + 1, window_size // 2):
            window_text = ' '.join(words[i:i + window_size])

            # Count chess indicators
            moves = len(self.move_pattern.findall(window_text))
            move_numbers = len(self.move_number_pattern.findall(window_text))

            # Threshold for PGN content
            if moves >= 10 and move_numbers >= 5:
                start_pos = len(' '.join(words[:i]))
                end_pos = len(' '.join(words[:i + window_size]))
                regions.append((window_text, start_pos, end_pos))

        return regions

    def analyze_structure(self, text: str) -> float:
        """
        Analyze PGN structure (0-20 points).

        ISSUE: This method may be undervaluing instructional content that
        doesn't have perfect PGN structure but has high educational value.
        """
        score = 0.0

        # Check for headers (0-8 points)
        headers = self.header_pattern.findall(text)
        header_score = min(len(headers) * 1.5, 8.0)
        score += header_score

        # Check for proper move notation (0-6 points)
        moves = self.move_pattern.findall(text)
        move_numbers = self.move_number_pattern.findall(text)

        if moves and move_numbers:
            move_ratio = len(move_numbers) / len(moves) if moves else 0
            move_score = min(move_ratio * 6, 6.0)
            score += move_score

        # Check for game result (0-3 points)
        if self.result_pattern.search(text):
            score += 3.0

        # Check for complete game structure (0-3 bonus)
        if headers and moves and self.result_pattern.search(text):
            score += 3.0

        # ENHANCEMENT: Bonus for instructional content even without perfect structure
        instructional_bonus = 0.0
        for pattern in self.instructional_context_patterns:
            if re.search(pattern, text):
                instructional_bonus += 2.0  # Bonus for instructional context

        score += min(instructional_bonus, 6.0)  # Cap instructional bonus

        return min(score, 20.0)

    def analyze_annotation_richness(self, text: str) -> Tuple[float, float]:
        """
        Analyze annotation richness (0-20 points).

        CRITICAL: This method should heavily reward instructional annotations
        and commentary that indicate teaching intent.
        """
        moves = self.move_pattern.findall(text)
        annotations = self.annotation_pattern.findall(text)

        annotation_density = 0.0
        if moves:
            annotation_density = len(annotations) / len(moves)

        score = 0.0

        # Base score from annotation density
        if annotation_density >= 0.2:
            score += min(annotation_density * 15, 10.0)

        # Comments and variations analysis
        comments = self.comment_pattern.findall(text)
        variations = self.variation_pattern.findall(text)
        nags = self.nag_pattern.findall(text)

        # ENHANCED: Comment quality scoring with instructional bias
        comment_score = 0.0
        for comment in comments:
            comment_length = len(comment)

            # Base scoring by length
            if comment_length > 50:  # Substantial comments
                base_points = 2.0
            elif comment_length > 20:
                base_points = 1.5
            elif comment_length > 5:
                base_points = 0.5
            else:
                base_points = 0.1

            # INSTRUCTIONAL BONUS: Look for teaching patterns in comments
            instructional_multiplier = 1.0
            comment_lower = comment.lower()

            # High-value instructional indicators
            if any(pattern in comment_lower for pattern in ['because', 'since', 'therefore', 'this shows']):
                instructional_multiplier = 2.0
            elif any(pattern in comment_lower for pattern in ['idea', 'plan', 'principle', 'concept']):
                instructional_multiplier = 1.8
            elif any(pattern in comment_lower for pattern in ['better', 'stronger', 'good move', 'bad move']):
                instructional_multiplier = 1.6
            elif any(pattern in comment_lower for pattern in ['should', 'must', 'needs to', 'wants to']):
                instructional_multiplier = 1.5

            comment_score += base_points * instructional_multiplier

        # Variation scoring with instructional bias
        variation_score = 0.0
        for variation in variations:
            depth = variation.count('(') + 1
            base_variation_score = min(1 + depth * 0.5, 3.0)

            # Bonus for instructional variations
            if any(pattern in variation.lower() for pattern in ['better', 'alternative', 'if']):
                base_variation_score *= 1.3

            variation_score += base_variation_score

        # Add component scores
        score += min(comment_score, 8.0)  # Increased cap for comments
        score += min(variation_score, 4.0)
        score += min(len(nags) * 0.5, 2.0)

        return min(score, 20.0), annotation_density

    def analyze_humanness(self, text: str) -> float:
        """
        Detect human vs engine analysis (0-20 points).

        CRITICAL: This should heavily reward instructional content over
        raw engine analysis. Educational explanations should score high.
        """
        score = 0.0

        # Educational language patterns (positive indicators)
        educational_matches = 0
        for pattern in self.educational_patterns:
            educational_matches += len(re.findall(pattern, text))

        # ENHANCED: Higher weight for educational patterns
        base_educational_score = min(educational_matches * 1.2, 15.0)  # Increased from 0.8
        score += base_educational_score

        # INSTRUCTIONAL CONTENT BONUS
        instructional_bonus = 0.0
        for pattern in self.instructional_context_patterns:
            if re.search(pattern, text):
                instructional_bonus += 3.0  # High bonus for instructional context

        score += min(instructional_bonus, 8.0)

        # Engine noise detection (penalties) - but reduced for instructional content
        engine_indicators = [
            r'\b\d+\.\d{2}\b',  # Numerical evaluations
            r'\bcp\s*[-+]?\d+\b',  # Centipawn notation
            r'\b(?:depth|nodes|nps|time)\s*\d+\b'  # Engine statistics
        ]

        engine_noise = 0
        for pattern in engine_indicators:
            engine_noise += len(re.findall(pattern, text, re.IGNORECASE))

        # Reduced penalty if instructional content is present
        penalty_multiplier = 0.5 if instructional_bonus > 0 else 1.0
        penalty = min(engine_noise * 1.0 * penalty_multiplier, 6.0)  # Reduced max penalty
        score = max(score - penalty, 0.0)

        # Bonus for natural language flow
        sentence_count = text.count('.') + text.count('!') + text.count('?')
        if sentence_count > 0:
            avg_sentence_length = len(text.split()) / sentence_count
            if 8 <= avg_sentence_length <= 25:  # Natural range
                score += 3.0

        return min(score, 20.0)

    def analyze_educational_context(self, text: str, surrounding_text: str = "") -> Tuple[float, List[str]]:
        """
        Analyze educational context from surrounding text (0-15 points).

        CRITICAL: This should identify instructional content and boost scores
        significantly for educational material.
        """
        score = 0.0
        educational_cues = []

        # Combine text sources
        full_text = text + " " + surrounding_text
        full_text_lower = full_text.lower()

        # INSTRUCTIONAL CONTENT DETECTION (highest priority)
        instructional_indicators = [
            (r'(?i)\b(?:masterclass|master class|chess course|grandmaster course)\b', "elite_instruction", 5.0),
            (r'(?i)\b(?:lesson|tutorial|example|demonstration|training)\b', "instructional_content", 3.0),
            (r'(?i)\b(?:analysis|annotation|commentary|explanation)\b', "analytical_content", 2.5),
            (r'(?i)\b(?:opening|middlegame|endgame)\s+(?:study|theory|guide|course)\b', "phase_specific_study", 3.5),
            (r'(?i)\b(?:master|grandmaster|world champion|expert)\s+(?:explains|teaches|analyzes)\b',
             "expert_instruction", 4.0),
            (r'(?i)\b(?:chess education|chess training|chess coaching)\b', "formal_education", 4.5),
            (r'(?i)\b(?:position|move|strategy)\s+(?:explained|analyzed|discussed)\b', "detailed_analysis", 2.0)
        ]

        for pattern, cue_type, points in instructional_indicators:
            if re.search(pattern, full_text):
                score += points
                educational_cues.append(cue_type)

        # Famous game detection (educational value)
        famous_detected = False
        for pattern in self.famous_contexts:
            if re.search(pattern, full_text):
                famous_detected = True
                score += 2.0  # Reduced from 3.0 to make room for instructional bonuses
                educational_cues.append("famous_game_context")
                break

        # Book/article context (instructional value)
        if any(indicator in full_text_lower for indicator in
               ['chapter', 'page', 'author', 'published', 'edition', 'book', 'manual']):
            score += 2.5  # Increased for book context
            educational_cues.append("published_content")

        # Author expertise context
        expert_patterns = [
            r'(?i)\b(?:by|from|according to)\s+(?:gm|grandmaster|im|international master)\b',
            r'(?i)\b(?:world champion|chess expert|master level)\b'
        ]

        for pattern in expert_patterns:
            if re.search(pattern, full_text):
                score += 2.0
                educational_cues.append("expert_author")
                break

        return min(score, 15.0), educational_cues

    def classify_game_type(self, structure_score: float, annotation_richness: float,
                           humanness_score: float, educational_context: float) -> str:
        """
        Classify the type of PGN content.

        ENHANCEMENT: Bias towards instructional classifications for educational content.
        """
        # Enhanced classification that favors instructional content
        if educational_context >= 8 and humanness_score >= 12:
            return "annotated_game"  # High educational value
        elif annotation_richness >= 12 and humanness_score >= 10:
            return "annotated_game"  # Rich annotations with human commentary
        elif structure_score >= 15 and educational_context >= 5:
            return "complete_game"  # Well-structured with some educational context
        elif humanness_score >= 12 or educational_context >= 6:
            return "position_study"  # Human analysis or educational content
        else:
            return "database_dump"  # Raw data

    def analyze_pgn_content(self, text: str, surrounding_text: str = "") -> PGNAnalysisResult:
        """
        Complete hybrid PGN analysis with EVS scoring.

        CRITICAL METHOD: This is where EVS is calculated. The issue is likely here -
        the method may not be properly weighting instructional content.

        TARGET: GM instructional content should score 85+ EVS, not 60-65.
        """
        if not text:
            return create_empty_pgn_result()

        try:
            # Preprocess text
            processed_text = self.preprocess_text(text)

            # Core analysis components
            structure_score = self.analyze_structure(processed_text)
            annotation_richness, annotation_density = self.analyze_annotation_richness(processed_text)
            humanness_score = self.analyze_humanness(processed_text)
            educational_context, educational_cues = self.analyze_educational_context(
                processed_text, surrounding_text
            )

            # CRITICAL EVS CALCULATION
            # Base EVS: sum of all components + base score
            base_evs = structure_score + annotation_richness + humanness_score + educational_context

            # INSTRUCTIONAL CONTENT BOOST (THIS IS THE KEY FIX)
            instructional_boost = 0.0

            # Check for high-value instructional indicators
            if any(cue in educational_cues for cue in ['elite_instruction', 'expert_instruction', 'formal_education']):
                instructional_boost += 20.0  # Major boost for elite instruction
            elif any(cue in educational_cues for cue in ['instructional_content', 'phase_specific_study']):
                instructional_boost += 15.0  # Significant boost for instructional content
            elif any(cue in educational_cues for cue in ['analytical_content', 'expert_author']):
                instructional_boost += 10.0  # Moderate boost for analytical content

            # Additional boosts for quality indicators
            if humanness_score >= EVSThresholds.HIGH_HUMANNESS_SCORE:
                instructional_boost += 5.0  # Human analysis bonus

            if annotation_richness >= EVSThresholds.HIGH_ANNOTATION_RICHNESS:
                instructional_boost += 5.0  # Rich annotation bonus

            if educational_context >= EVSThresholds.HIGH_EDUCATIONAL_CONTEXT:
                instructional_boost += 8.0  # Educational context bonus

            # Calculate final EVS with instructional boost
            evs_score = base_evs + instructional_boost + 15  # Base 15 for valid content
            evs_score = min(evs_score, 100.0)  # Cap at 100

            # Additional metrics
            moves = self.move_pattern.findall(processed_text)
            total_moves = len(moves)
            has_headers = bool(self.header_pattern.search(processed_text))
            has_variations = bool(self.variation_pattern.search(processed_text))

            # Famous game detection
            famous_game_detected = any(re.search(pattern, text + " " + surrounding_text)
                                       for pattern in self.famous_contexts)

            # Game type classification
            game_type = self.classify_game_type(
                structure_score, annotation_richness, humanness_score, educational_context
            )

            result = PGNAnalysisResult(
                evs_score=evs_score,
                structure_score=structure_score,
                annotation_richness=annotation_richness,
                humanness_score=humanness_score,
                educational_context=educational_context,
                game_type=game_type,
                total_moves=total_moves,
                annotation_density=annotation_density,
                has_headers=has_headers,
                has_variations=has_variations,
                famous_game_detected=famous_game_detected,
                educational_cues=educational_cues
            )

            # Log details for debugging
            self.logger.debug(
                f"EVS Analysis: base={base_evs:.1f}, boost={instructional_boost:.1f}, final={evs_score:.1f}")
            self.logger.debug(f"Educational cues: {educational_cues}")

            return result

        except Exception as e:
            self.logger.error(f"PGN analysis failed: {e}")
            return create_empty_pgn_result()