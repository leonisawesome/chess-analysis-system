"""
Chess Semantic Analyzer - Core instructional value detection engine.
This module handles the sophisticated semantic analysis that identifies high-quality
instructional chess content. It uses comprehensive vocabulary, IDF weighting,
and multiple analysis dimensions to calculate instructional value.
"""

import logging
import re
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ..core.models import SemanticAnalysisResult, IDFWeights, AnalysisRequest
from ..core.constants import (
    ChessVocabulary, CategoryWeights, InstructionalIndicators,
    EVSThresholds, FileTypes
)

# Optional imports for NLP features
try:
    import torch
    from transformers import AutoTokenizer, AutoModel
    from sentence_transformers import SentenceTransformer
    from sklearn.feature_extraction.text import TfidfVectorizer

    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False

# Import the new instructional detector
try:
    from .instructional_detector import InstructionalLanguageDetector
    INSTRUCTIONAL_DETECTOR_AVAILABLE = True
except ImportError:
    INSTRUCTIONAL_DETECTOR_AVAILABLE = False
    logging.warning("InstructionalLanguageDetector not available, using fallback")


class ChessSemanticAnalyzer:
    """
    Core semantic analysis engine for chess instructional content.

    This analyzer uses sophisticated multi-dimensional analysis:
    1. IDF-weighted domain relevance
    2. Instructional value detection via teaching patterns
    3. Concept density analysis with comprehensive vocabulary
    4. Explanation clarity assessment
    5. Publication year scoring with author reputation

    The goal is to identify high-quality instructional content that should
    score 85+ EVS for RAG inclusion.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "auto"):
        self.logger = logging.getLogger(__name__)
        self.device = self._setup_device(device)

        # Initialize models only if NLP libraries available
        if NLP_AVAILABLE:
            self.logger.info("Loading semantic models...")
            self.sentence_model = SentenceTransformer(model_name, device=self.device)
        else:
            self.sentence_model = None
            self.logger.warning("NLP libraries not available - using fallback analysis")

        # Load chess vocabulary
        self.chess_concepts = ChessVocabulary.get_chess_concepts()

        # IDF weights (will be loaded if available)
        self.idf_weights: Optional[IDFWeights] = None

        # Compile regex patterns for performance
        self._compile_patterns()

        # Count total terms for reporting
        total_terms = sum(len(terms) for terms in self.chess_concepts.values())
        self.logger.info(f"Semantic analyzer initialized with {total_terms} chess terms")

        # NEW: Initialize instructional language detector
        self.enable_instructional_detection = INSTRUCTIONAL_DETECTOR_AVAILABLE
        
        if self.enable_instructional_detection:
            try:
                self.instructional_detector = InstructionalLanguageDetector(
                    embedding_model=self.sentence_model
                )
                self.logger.info("Instructional language detector initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize instructional detector: {e}")
                self.enable_instructional_detection = False
                self.instructional_detector = None
        else:
            self.instructional_detector = None

    def _setup_device(self, device: str) -> str:
        """Setup computation device"""
        if not NLP_AVAILABLE:
            return "cpu"

        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon
            else:
                return "cpu"
        return device

    def _compile_patterns(self):
        """Compile regex patterns for performance"""
        # Instructional patterns
        self.teaching_pattern = re.compile(
            r'\b(?:' + '|'.join(InstructionalIndicators.TEACHING_PATTERNS) + r')\b',
            re.IGNORECASE
        )

        self.explanation_pattern = re.compile(
            r'\b(?:' + '|'.join(InstructionalIndicators.EXPLANATION_PATTERNS) + r')\b',
            re.IGNORECASE
        )

        self.educational_cues_pattern = re.compile(
            r'\b(?:' + '|'.join(InstructionalIndicators.EDUCATIONAL_CUES) + r')\b',
            re.IGNORECASE
        )

        self.beginner_penalty_pattern = re.compile(
            r'\b(?:' + '|'.join(InstructionalIndicators.BEGINNER_PENALTIES) + r')\b',
            re.IGNORECASE
        )

    def set_idf_weights(self, idf_weights: IDFWeights):
        """Set IDF weights for enhanced analysis"""
        self.idf_weights = idf_weights
        self.logger.info("IDF weights loaded for enhanced semantic analysis")

    def analyze_chess_content(self, request: AnalysisRequest) -> SemanticAnalysisResult:
        """
        Main entry point for chess content analysis.

        This method orchestrates the complete semantic analysis pipeline:
        1. Text preprocessing and chunking
        2. Domain relevance analysis (with optional IDF weighting)
        3. Instructional value detection (critical for EVS boost)
        4. Concept density analysis
        5. Explanation clarity assessment
        6. Publication year scoring

        Args:
            request: AnalysisRequest containing text and metadata

        Returns:
            SemanticAnalysisResult with all analysis dimensions
        """
        if not request.text or len(request.text.strip()) < 50:
            return self._create_empty_result()

        try:
            # Preprocess and chunk text
            chunks = self._chunk_text(request.text, max_length=FileTypes.MAX_CHUNK_SIZE)

            # Core semantic analysis dimensions
            domain_relevance = self._analyze_domain_relevance(chunks)
            instructional_value = self._analyze_instructional_value(chunks)  # CRITICAL for EVS
            concept_density = self._analyze_concept_density(chunks)
            explanation_clarity = self._analyze_explanation_clarity(chunks)

            # Metadata analysis
            publication_score = self._calculate_publication_year_score(request.year, request.author)
            comprehensive_score = self._comprehensive_concept_analysis(request.text)

            # Entity extraction
            detected_openings = self._detect_openings(request.text)
            detected_players = self._detect_players(request.text)
            detected_books = self._detect_books(request.text)
            top_concepts = self._extract_top_concepts(chunks)
            semantic_categories = self._categorize_semantic_content(chunks)

            # Calculate overall content quality (this feeds into EVS integration)
            content_quality = self._calculate_content_quality(
                domain_relevance, instructional_value, concept_density,
                explanation_clarity, comprehensive_score
            )

            # === PHASE 1: EVS COMPONENT BREAKDOWN LOGGING (AI PARTNER DIAGNOSTIC) ===
            self.logger.info("=== EVS COMPONENT BREAKDOWN (DIAGNOSTIC) ===")
            self.logger.info(f"Domain Relevance: {domain_relevance:.3f} (chess-specific)")
            self.logger.info(f"Instructional Value: {instructional_value:.3f} (pattern detection)")
            self.logger.info(f"Concept Density: {concept_density:.3f} (vocabulary)")
            self.logger.info(f"Explanation Clarity: {explanation_clarity:.3f} (α*generic + β*instructional + γ*plan)")
            self.logger.info(f"Comprehensive Score: {comprehensive_score:.3f} (overall)")
            self.logger.info(f"Content Quality (Weighted): {content_quality:.3f}")
            
            # Calculate what EVS should be if this maps 1:1
            expected_evs = content_quality * 100  # Simple 0-1 → 0-100 scaling
            self.logger.info(f"Expected EVS (if 1:1 mapping): {expected_evs:.1f}")
            
            # Component weights used in quality calculation  
            self.logger.info("Quality Component Weights:")
            self.logger.info("  - instructional_value: 0.30")
            self.logger.info("  - domain_relevance: 0.25") 
            self.logger.info("  - concept_density: 0.20")
            self.logger.info("  - explanation_clarity: 0.15")
            self.logger.info("  - comprehensive_score: 0.10")
            self.logger.info("=== END EVS COMPONENT BREAKDOWN ===")

            # Note: PGN analysis and integration will be handled by the integration layer
            from ..core.models import create_empty_pgn_result

            return SemanticAnalysisResult(
                content_quality_score=content_quality,
                chess_domain_relevance=domain_relevance,
                instructional_value=instructional_value,  # This should be 1.0 for GM content
                concept_density=concept_density,
                explanation_clarity=explanation_clarity,
                top_concepts=top_concepts,
                semantic_categories=semantic_categories,
                publication_year_score=publication_score,
                comprehensive_concept_score=comprehensive_score,
                detected_openings=detected_openings,
                detected_players=detected_players,
                detected_books=detected_books,
                pgn_analysis=create_empty_pgn_result(),  # Will be filled by integration layer
                pgn_integration_score=0.0  # Will be calculated by integration layer
            )

        except Exception as e:
            self.logger.error(f"Semantic analysis failed: {e}")
            return self._create_empty_result()

    def _analyze_instructional_value(self, chunks: List[str]) -> float:
        """
        CRITICAL METHOD: Analyze instructional value of content.

        This is the key method that should identify GM instructional content
        and return values close to 1.0 for high-quality teaching material.

        The algorithm looks for:
        - Teaching patterns (how to, explanation, demonstration)
        - Educational structure (lessons, exercises, examples)
        - Advanced concepts with explanations
        - Expert-level instruction markers
        """
        if not chunks:
            return 0.0

        total_instructional_score = 0.0

        for chunk in chunks:
            chunk_lower = chunk.lower()
            chunk_words = len(chunk.split())

            if chunk_words == 0:
                continue

            chunk_score = 0.0

            # 1. Teaching patterns (high weight for instructional content)
            teaching_matches = len(self.teaching_pattern.findall(chunk))
            chunk_score += teaching_matches * 3.0  # High weight

            # 2. Explanation patterns (shows teaching intent)
            explanation_matches = len(self.explanation_pattern.findall(chunk))
            chunk_score += explanation_matches * 2.5

            # 3. Educational cues (masterclass, lecture, etc.)
            educational_matches = len(self.educational_cues_pattern.findall(chunk))
            chunk_score += educational_matches * 4.0  # Very high weight

            # 4. Advanced instructional patterns
            advanced_patterns = [
                'advanced technique', 'master class', 'grandmaster explains',
                'theoretical foundation', 'deep analysis', 'comprehensive study',
                'professional approach', 'expert level', 'sophisticated understanding',
                'strategic principle', 'positional understanding', 'tactical awareness'
            ]

            for pattern in advanced_patterns:
                if pattern in chunk_lower:
                    chunk_score += 5.0  # Very high for advanced instruction

            # 5. Question-based teaching
            question_patterns = ['how to', 'what is', 'why does', 'when should', 'which move']
            for pattern in question_patterns:
                if pattern in chunk_lower:
                    chunk_score += 2.0

            # 6. Structured instruction indicators
            structure_indicators = [
                'step by step', 'first', 'second', 'third', 'finally',
                'lesson', 'chapter', 'section', 'part', 'exercise',
                'example', 'demonstration', 'practice', 'drill'
            ]

            structure_score = sum(2.0 for indicator in structure_indicators
                                  if indicator in chunk_lower)
            chunk_score += structure_score

            # 7. Expert authority markers
            authority_markers = [
                'grandmaster', 'international master', 'world champion',
                'chess expert', 'professional player', 'titled player',
                'chess coach', 'chess trainer', 'chess instructor'
            ]

            authority_score = sum(3.0 for marker in authority_markers
                                  if marker in chunk_lower)
            chunk_score += authority_score

            # 8. PENALTY for beginner content (reduces instructional value)
            beginner_penalties = len(self.beginner_penalty_pattern.findall(chunk))
            chunk_score -= beginner_penalties * 3.0

            # 9. Bonus for chess-specific instructional content
            chess_instruction_bonus = 0.0
            chess_teaching_patterns = [
                'position analysis', 'move analysis', 'game analysis',
                'opening principles', 'middlegame planning', 'endgame technique',
                'tactical pattern', 'strategic concept', 'positional understanding'
            ]

            for pattern in chess_teaching_patterns:
                if pattern in chunk_lower:
                    chess_instruction_bonus += 2.0

            chunk_score += chess_instruction_bonus

            # Normalize by chunk length and add to total
            normalized_chunk_score = min(chunk_score / max(chunk_words / 50, 1), 0.4)
            total_instructional_score += max(normalized_chunk_score, 0.0)

        # Calculate final instructional value
        final_score = total_instructional_score / len(chunks) if chunks else 0.0

        # Apply IDF boost if available and high instructional content detected
        if self.idf_weights and final_score > 0.5:
            idf_boost = self._calculate_idf_instructional_boost(chunks)
            final_score = min(final_score + idf_boost, 1.0)

        return min(final_score, 1.0)

    def _calculate_idf_instructional_boost(self, chunks: List[str]) -> float:
        """Calculate IDF-based boost for instructional content"""
        if not self.idf_weights:
            return 0.0

        text = " ".join(chunks).lower()
        boost = 0.0

        # Look for high-value instructional terms with their IDF weights
        high_value_terms = [
            'masterclass', 'grandmaster preparation', 'chess course',
            'instructional', 'educational', 'advanced technique',
            'strategic principle', 'tactical pattern'
        ]

        for term in high_value_terms:
            if term in text:
                idf_weight = self.idf_weights.term_weights.get(term, 1.0)
                boost += min(idf_weight / 10, 0.1)  # Cap individual boosts

        return min(boost, 0.2)  # Cap total boost at 0.2

    def _analyze_domain_relevance(self, chunks: List[str]) -> float:
        """Enhanced domain relevance analysis with optional IDF weighting"""
        if not chunks:
            return 0.0

        if self.idf_weights and NLP_AVAILABLE and self.sentence_model:
            return self._idf_weighted_domain_relevance(chunks)
        else:
            return self._keyword_domain_relevance_fallback(chunks)

    def _idf_weighted_domain_relevance(self, chunks: List[str]) -> float:
        """IDF-weighted domain relevance analysis"""
        text = " ".join(chunks).lower()
        total_weighted_score = 0.0
        total_possible_weight = 0.0

        # Calculate IDF-weighted matches
        for category, terms in self.chess_concepts.items():
            category_weight = CategoryWeights.DOMAIN_RELEVANCE_WEIGHTS.get(category, 1.0)

            for term in terms:
                term_lower = term.lower()
                idf_weight = self.idf_weights.term_weights.get(term_lower, 1.0)

                # Combined weight: category importance * IDF weight
                combined_weight = category_weight * idf_weight
                total_possible_weight += combined_weight

                if term_lower in text:
                    total_weighted_score += combined_weight

        # Normalize by total possible weight
        if total_possible_weight > 0:
            relevance = total_weighted_score / total_possible_weight
        else:
            relevance = 0.0

        return min(relevance, 1.0)

    def _keyword_domain_relevance_fallback(self, chunks: List[str]) -> float:
        """Enhanced fallback with comprehensive vocabulary when IDF not available"""
        if not chunks:
            return 0.0

        text = " ".join(chunks).lower()
        total_words = len(text.split())

        if total_words == 0:
            return 0.0

        # Count matches across all categories with enhanced weighting
        total_weighted_matches = 0

        for category, terms in self.chess_concepts.items():
            weight = CategoryWeights.DOMAIN_RELEVANCE_WEIGHTS.get(category, 1.0)
            for term in terms:
                if term.lower() in text:
                    total_weighted_matches += weight

        # Normalize by text length
        relevance_score = min(total_weighted_matches / max(total_words / 50, 1), 1.0)
        return relevance_score

    def _analyze_concept_density(self, chunks: List[str]) -> float:
        """Enhanced concept density with comprehensive vocabulary"""
        if not chunks:
            return 0.0

        text = " ".join(chunks).lower()
        total_words = len(text.split())

        if total_words == 0:
            return 0.0

        weighted_concepts = 0

        for category, concepts in self.chess_concepts.items():
            weight = CategoryWeights.DOMAIN_RELEVANCE_WEIGHTS.get(category, 1.0)
            for concept in concepts:
                if concept.lower() in text:
                    weighted_concepts += weight

        density = weighted_concepts / (total_words / 100)
        return min(density / 30, 1.0)

    def _analyze_explanation_clarity(self, chunks: List[str]) -> float:
        """
        Enhanced explanation clarity analysis with chess-specific instructional patterns
        
        Implements the 3-component approach from AI partner consultation:
        - Generic clarity (existing logic)
        - Instructional language score (new component)  
        - Plan chain bonus (new component)
        """
        # Calculate generic clarity using existing logic
        generic_clarity = self._analyze_generic_clarity(chunks)
        
        # Calculate instructional language score if detector available
        instructional_score = 0.0
        plan_chain_bonus = 0.0
        
        if hasattr(self, 'enable_instructional_detection') and self.enable_instructional_detection and self.instructional_detector:
            try:
                # Get instructional language score
                
                # Debug logging per AI partner consensus
                if chunks:
                    self.logger.info(f"DETECTOR INPUT: {len(chunks)} chunks, first={chunks[0][:100] if chunks else 'EMPTY'}")
                else:
                    self.logger.info("DETECTOR INPUT: EMPTY chunks list")
                
                # === OBJECT STATE DIAGNOSTIC (5-AI PARTNER CONSENSUS) ===
                import hashlib, os, sys
                self.logger.info('=== DETECTOR STATE ANALYSIS ===')
                
                # 1. Object identity and provenance (ChatGPT + Perplexity)
                detector_module = self.instructional_detector.__class__.__module__
                detector_file = getattr(__import__(detector_module), '__file__', 'UNKNOWN')
                object_id = id(self.instructional_detector)
                self.logger.info(f'DETECTOR: module={detector_module}, file={detector_file}, id={object_id}')
                
                # 2. Vocabulary loading verification (All partners priority)
                if hasattr(self.instructional_detector, 'fixed_phrases'):
                    phrase_count = sum(len(phrases) for phrases in self.instructional_detector.fixed_phrases.values())
                    categories = list(self.instructional_detector.fixed_phrases.keys())
                    self.logger.info(f'VOCABULARY: loaded={phrase_count} phrases, categories={categories}')
                    
                    if phrase_count == 0:
                        self.logger.error('CRITICAL: EMPTY VOCABULARY IN INTEGRATION CONTEXT')
                    else:
                        # Sample first few phrases for verification
                        sample = list(self.instructional_detector.fixed_phrases.values())[0][:3] if categories else []
                        self.logger.info(f'VOCABULARY_SAMPLE: {sample}')
                else:
                    self.logger.error('CRITICAL: NO fixed_phrases ATTRIBUTE FOUND')
                
                # 3. Compiled patterns verification (Grok recommendation)
                if hasattr(self.instructional_detector, 'compiled_patterns'):
                    pattern_count = len(self.instructional_detector.compiled_patterns)
                    self.logger.info(f'PATTERNS: compiled={pattern_count}')
                else:
                    self.logger.error('CRITICAL: NO compiled_patterns FOUND')
                
                # 4. Payload verification (ChatGPT)
                payload = ' '.join(chunks) if chunks else 'EMPTY'
                payload_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]
                self.logger.info(f'PAYLOAD: hash={payload_hash}, len={len(payload)}, preview={payload[:100]}')
                
                self.logger.info('=== END DETECTOR ANALYSIS ===')

                instructional_score = self.instructional_detector.analyze_instructional_language(chunks)
                
                # Get plan chain bonus
                plan_chain_bonus = self.instructional_detector.detect_plan_chains(chunks)
                
            except Exception as e:
                self.logger.warning(f"Instructional detection failed, using fallback: {e}")
                instructional_score = 0.0
                plan_chain_bonus = 0.0
        
        # Integrate scores using AI partner recommended formula
        # α=0.6 * generic + β=0.35 * instructional + γ=0.05 * plan_chain
        final_clarity = min(
            0.6 * generic_clarity + 
            0.35 * instructional_score + 
            0.05 * plan_chain_bonus,
            1.0
        )
        
        # === EXPLANATION CLARITY BREAKDOWN LOGGING ===
        self.logger.info(f"=== EXPLANATION CLARITY BREAKDOWN ===")
        self.logger.info(f"Generic Clarity: {generic_clarity:.3f}")
        self.logger.info(f"Instructional Score: {instructional_score:.3f} (from pattern detection)")
        self.logger.info(f"Plan Chain Bonus: {plan_chain_bonus:.3f}")
        self.logger.info(f"Formula: 0.6*{generic_clarity:.3f} + 0.35*{instructional_score:.3f} + 0.05*{plan_chain_bonus:.3f}")
        self.logger.info(f"Final Explanation Clarity: {final_clarity:.3f}")
        self.logger.info(f"=== END EXPLANATION CLARITY ===")
        
        # Log detailed breakdown for debugging  
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                f"Explanation clarity breakdown: "
                f"generic={generic_clarity:.3f}, "
                f"instructional={instructional_score:.3f}, "
                f"plan_chain={plan_chain_bonus:.3f}, "
                f"final={final_clarity:.3f}"
            )
        
        return final_clarity
    
    def _analyze_generic_clarity(self, chunks: List[str]) -> float:
        """
        Original explanation clarity logic preserved as separate method
        This maintains backwards compatibility while allowing new component integration
        """
        clarity_indicators = {
            'structure': ['first', 'second', 'third', 'finally', 'then', 'next', 'subsequently'],
            'clarity': ['clear', 'obvious', 'straightforward', 'evident', 'apparent'],
            'examples': ['for example', 'such as', 'like', 'consider', 'imagine', 'instance'],
            'transitions': ['however', 'therefore', 'meanwhile', 'consequently', 'furthermore'],
            'emphasis': ['important', 'crucial', 'key', 'essential', 'critical', 'vital'],
            'explanation': ['because', 'since', 'due to', 'as a result', 'this means']
        }

        total_score = 0.0
        for chunk in chunks:
            chunk_lower = chunk.lower()
            chunk_score = 0.0

            for category, indicators in clarity_indicators.items():
                category_score = sum(1 for indicator in indicators if indicator in chunk_lower)
                weight = 0.15 if category in ['examples', 'explanation'] else 0.1
                chunk_score += category_score * weight

            # Penalty for overly complex sentences
            avg_sentence_length = len(chunk.split()) / max(chunk.count('.'), 1)
            if avg_sentence_length > 30:
                chunk_score *= 0.7
            elif avg_sentence_length > 25:
                chunk_score *= 0.85

            # Bonus for intermediate complexity
            if 15 <= avg_sentence_length <= 25:
                chunk_score *= 1.1

            total_score += min(chunk_score, 0.4)

        return min(total_score / len(chunks), 1.0) if chunks else 0.0


    def _calculate_publication_year_score(self, year: str, author: str = "") -> float:
        """Enhanced publication year score with sliding scale"""
        if year == "UnknownYear" or not year:
            return 0.0

        try:
            year_int = int(year)
        except (ValueError, TypeError):
            return 0.0

        # Enhanced sliding scale - rewards both classics and modern works
        if year_int <= 1960:  # Chess classics
            base_score = 12 + min(3, (1960 - year_int) / 20)  # Up to 15
        elif year_int >= 2020:  # Latest modern works
            base_score = 15
        elif year_int >= 2015:  # Recent modern works
            base_score = 14
        elif year_int >= 2010:
            base_score = 13
        elif year_int >= 2005:
            base_score = 12
        elif year_int >= 2000:
            base_score = 11
        elif year_int >= 1995:
            base_score = 10
        elif year_int >= 1985:
            base_score = 9
        else:  # 1961-1984
            base_score = 7

        # Enhanced author reputation bonus
        author_lower = author.lower() if author else ""

        # Trusted authors (get bonus points)
        famous_authors = [
            'kasparov', 'fischer', 'karpov', 'carlsen', 'anand', 'kramnik', 'shirov',
            'dvoretsky', 'aagaard', 'silman', 'watson', 'alburt', 'pachman', 'euwe',
            'fine', 'tal', 'petrosian', 'spassky', 'botvinnik', 'lasker', 'capablanca',
            'alekhine', 'bronstein', 'kotov', 'averbach', 'smyslov', 'reshevsky'
        ]

        # Excluded authors (explicitly no bonus)
        excluded_authors = [
            'cyrus lakdawala', 'lakdawala',
            'eric schiller', 'schiller',
            'raymond keene', 'keene',
            'fred reinfeld', 'reinfeld',
            'i.a. horowitz', 'horowitz'
        ]

        author_bonus = 0

        # Check exclusion list first
        is_excluded = any(excluded in author_lower for excluded in excluded_authors)

        if not is_excluded:
            for famous in famous_authors:
                if famous in author_lower:
                    author_bonus = 2
                    break

        return min(base_score + author_bonus, 15.0)

    def _comprehensive_concept_analysis(self, text: str) -> float:
        """Enhanced comprehensive analysis"""
        text_lower = text.lower()

        coverage_scores = {}
        importance_weights = CategoryWeights.DOMAIN_RELEVANCE_WEIGHTS

        for category, terms in self.chess_concepts.items():
            matches = sum(1 for term in terms if term.lower() in text_lower)
            category_size = len(terms)
            coverage = min(matches / max(category_size * 0.08, 1), 1.0)
            coverage_scores[category] = coverage

        weighted_score = 0
        total_weight = 0
        for category, score in coverage_scores.items():
            weight = importance_weights.get(category, 1.0)
            weighted_score += score * weight
            total_weight += weight

        return weighted_score / total_weight if total_weight > 0 else 0.0

    def _calculate_content_quality(self, domain_relevance: float, instructional_value: float,
                                   concept_density: float, explanation_clarity: float,
                                   comprehensive_score: float) -> float:
        """
        Calculate overall content quality score.

        This score feeds into the EVS integration layer. High instructional value
        should significantly boost the content quality score.
        """
        # Enhanced weighting that prioritizes instructional value
        weights = {
            'instructional_value': 0.30,  # Increased weight for instructional content
            'domain_relevance': 0.25,
            'concept_density': 0.20,
            'explanation_clarity': 0.15,
            'comprehensive_score': 0.10
        }

        quality_score = (
                domain_relevance * weights['domain_relevance'] +
                instructional_value * weights['instructional_value'] +
                concept_density * weights['concept_density'] +
                explanation_clarity * weights['explanation_clarity'] +
                comprehensive_score * weights['comprehensive_score']
        )

        # Bonus for high instructional value (should help EVS integration)
        if instructional_value >= EVSThresholds.HIGH_INSTRUCTIONAL_VALUE:
            quality_boost = min(instructional_value * 0.2, 0.15)  # Up to 15% boost
            quality_score = min(quality_score + quality_boost, 1.0)

        return min(quality_score, 1.0)

    # Entity detection methods
    def _detect_openings(self, text: str) -> List[str]:
        """Enhanced opening detection with curated list"""
        text_lower = text.lower()
        detected = []

        for opening in self.chess_concepts.get('curated_openings', []):
            if opening.lower() in text_lower:
                detected.append(opening)

        return detected[:20]

    def _detect_players(self, text: str) -> List[str]:
        """Enhanced player detection"""
        text_lower = text.lower()
        detected = []

        # This would need to be expanded with comprehensive player lists
        famous_players = [
            'kasparov', 'karpov', 'fischer', 'carlsen', 'anand', 'kramnik',
            'tal', 'petrosian', 'spassky', 'botvinnik', 'capablanca', 'alekhine'
        ]

        for player in famous_players:
            if player in text_lower:
                detected.append(player)

        return detected[:20]

    def _detect_books(self, text: str) -> List[str]:
        """Detect famous chess books mentioned in text"""
        text_lower = text.lower()
        detected = []

        for book in self.chess_concepts.get('famous_chess_books', []):
            if book.lower() in text_lower:
                detected.append(book)

        return detected[:15]

    def _extract_top_concepts(self, chunks: List[str]) -> List[str]:
        """Enhanced concept extraction with comprehensive vocabulary"""
        text = " ".join(chunks).lower()
        concept_counts = {}

        for category, concepts in self.chess_concepts.items():
            weight = CategoryWeights.DOMAIN_RELEVANCE_WEIGHTS.get(category, 1.0)
            for concept in concepts:
                if concept.lower() in text:
                    weighted_count = (concept_counts.get(concept, 0) + 1) * weight
                    concept_counts[concept] = weighted_count

        sorted_concepts = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)
        return [concept for concept, count in sorted_concepts[:25]]

    def _categorize_semantic_content(self, chunks: List[str]) -> Dict[str, float]:
        """Enhanced semantic categorization"""
        if not chunks:
            return {}

        text = " ".join(chunks)
        total_words = len(text.split())

        category_scores = {}
        for category, concepts in self.chess_concepts.items():
            matches = sum(1 for concept in concepts if concept.lower() in text.lower())
            score = matches / max(total_words / 200, 1) if total_words > 0 else 0
            category_scores[category] = min(score, 1.0)

        return category_scores

    def _chunk_text(self, text: str, max_length: int = 512) -> List[str]:
        """Break text into manageable chunks"""
        sentences = text.split('.')
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_length:
                current_chunk += sentence + "."
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + "."

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks[:20]  # Limit to first 20 chunks for performance

    def _create_empty_result(self) -> SemanticAnalysisResult:
        """Return empty result for failed analysis"""
        from ..core.models import create_empty_semantic_result
        return create_empty_semantic_result()