"""
RAG Fitness Evaluator - Determines suitability for RAG system inclusion.

This module evaluates chess content for its fitness as RAG (Retrieval-Augmented Generation)
training material. It analyzes factors like chunkability, answerability, factual density,
and retrieval friendliness to determine if content should be included in the RAG system.
"""

import logging
from typing import Dict, List, Optional, Any

from ..core.models import SemanticAnalysisResult, RAGFitnessResult, PGNAnalysisResult
from ..core.constants import EVSThresholds


class RAGFitnessEvaluator:
    """
    Evaluates chess content for RAG system suitability.

    The RAG fitness score determines whether content is suitable for inclusion
    in a Retrieval-Augmented Generation system. High-quality instructional content
    with good structure and clear explanations should score highly.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def evaluate_rag_fitness(self, text: str, title: str = "",
                             semantic_result: Optional[SemanticAnalysisResult] = None) -> RAGFitnessResult:
        """
        Comprehensive RAG fitness evaluation with v5 PGN integration.

        Args:
            text: Content text to evaluate
            title: Optional title/filename for context
            semantic_result: Pre-computed semantic analysis results

        Returns:
            RAGFitnessResult with detailed fitness metrics
        """
        if not text:
            return self._empty_fitness_result()

        try:
            # Use provided semantic result or create placeholder
            if semantic_result is None:
                # Create minimal semantic result for standalone evaluation
                semantic_result = self._create_minimal_semantic_result(text)

            # Core fitness evaluations
            chunkability = self._evaluate_chunkability(text)
            answerability = self._evaluate_answerability(text, title)
            factual_density = self._evaluate_factual_density(text, semantic_result)
            retrieval_friendliness = self._evaluate_retrieval_friendliness(text)

            # PGN Integration Bonus
            pgn_bonus = self._calculate_pgn_rag_bonus(semantic_result.pgn_analysis)

            # Apply PGN bonus to factual density (games are inherently factual)
            factual_density = min(factual_density + pgn_bonus, 1.0)

            # Calculate overall fitness score
            overall_score = self._calculate_overall_fitness(
                chunkability, answerability, factual_density, retrieval_friendliness
            )

            # Generate reasoning
            fitness_reasoning = self._generate_fitness_reasoning(
                chunkability, answerability, factual_density, retrieval_friendliness,
                pgn_bonus, semantic_result.pgn_analysis
            )

            return RAGFitnessResult(
                overall_rag_fitness=overall_score,
                chunkability_score=chunkability,
                answerability_score=answerability,
                factual_density_score=factual_density,
                retrieval_friendliness_score=retrieval_friendliness,
                pgn_detection_bonus=pgn_bonus,
                evs_score=semantic_result.pgn_analysis.evs_score,
                pgn_game_type=semantic_result.pgn_analysis.game_type,
                fitness_reasoning=fitness_reasoning
            )

        except Exception as e:
            self.logger.error(f"RAG fitness evaluation failed: {e}")
            return self._empty_fitness_result()

    def _evaluate_chunkability(self, text: str) -> float:
        """
        Evaluate how well the text can be chunked for RAG processing.

        Good chunkability means:
        - Well-structured paragraphs
        - Appropriate sentence length
        - Clear section breaks
        - Chess-specific structure (games, positions, analysis)
        """
        paragraphs = text.split('\n\n')
        sentences = text.split('.')

        # Count structural elements
        headers = len([line for line in text.split('\n') if line.isupper() or
                       any(word in line.lower() for word in
                           ['chapter', 'section', 'part', 'lesson', 'game', 'position', 'analysis'])])

        # Calculate average lengths
        avg_paragraph_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0

        # Score paragraph structure (ideal range: 40-200 words)
        if 40 <= avg_paragraph_length <= 200:
            paragraph_score = 1.0
        elif 20 <= avg_paragraph_length <= 300:
            paragraph_score = 0.8
        else:
            paragraph_score = 0.6

        # Score sentence structure (ideal range: 12-35 words)
        if 12 <= avg_sentence_length <= 35:
            sentence_score = 1.0
        elif 8 <= avg_sentence_length <= 50:
            sentence_score = 0.8
        else:
            sentence_score = 0.7

        # Score structural organization
        structure_score = min(headers / 8, 1.0)

        # Chess-specific structure bonus
        chess_structure_bonus = 0.0
        chess_structure_indicators = ['position', 'variation', 'move', 'analysis', 'game', 'diagram']
        chess_structure_count = sum(text.lower().count(indicator) for indicator in chess_structure_indicators)

        if chess_structure_count > 5:
            chess_structure_bonus = 0.1

        # PGN structure bonus (games have natural chunk boundaries)
        pgn_bonus = 0.0
        if any(pattern in text for pattern in ['[Event', '[White', '[Black', '1.e4', '1.d4', '1.']):
            pgn_bonus = 0.05

        final_score = (paragraph_score + sentence_score + structure_score) / 3
        final_score += chess_structure_bonus + pgn_bonus

        return min(final_score, 1.0)

    def _evaluate_answerability(self, text: str, title: str = "") -> float:
        """
        Evaluate how well the text can answer chess-related questions.

        Good answerability means the text contains information that can
        directly answer questions a chess student might ask.
        """
        synthetic_questions = self._generate_chess_questions(text, title)

        if not synthetic_questions:
            return 0.0

        answerable_count = 0
        for question in synthetic_questions:
            if self._can_answer_question(question, text):
                answerable_count += 1

        return answerable_count / len(synthetic_questions)

    def _generate_chess_questions(self, text: str, title: str = "") -> List[str]:
        """
        Generate synthetic questions that chess students might ask about this content.
        """
        questions = []
        text_lower = text.lower()

        # Title-based questions
        if title:
            questions.extend([
                f"What is {title} about?",
                f"What are the main concepts in {title}?",
                f"How does {title} work?"
            ])

        # Definition and concept questions
        if any(term in text_lower for term in ['is defined as', 'means', 'definition', 'concept']):
            questions.append("What does this term mean?")

        # How-to questions (high value for instruction)
        if any(word in text_lower for word in ['step', 'method', 'technique', 'approach', 'strategy']):
            questions.extend([
                "How do you perform this technique?",
                "What are the steps involved?",
                "When should you use this approach?"
            ])

        # Example-based questions
        if any(term in text_lower for term in ['example', 'for instance', 'such as', 'consider']):
            questions.extend([
                "What are examples of this concept?",
                "Can you show me how this works?"
            ])

        # Position-specific questions (chess domain)
        if 'position' in text_lower:
            questions.extend([
                "What should you do in this position?",
                "How do you evaluate this position?",
                "What are the key features of this position?"
            ])

        # Opening questions
        if any(word in text_lower for word in ['opening', 'defense', 'gambit']):
            questions.extend([
                "How do you play this opening?",
                "What are the main ideas in this opening?",
                "What are the typical plans for both sides?"
            ])

        # Tactical questions
        if any(word in text_lower for word in ['tactic', 'combination', 'sacrifice', 'pin', 'fork']):
            questions.extend([
                "How does this tactical motif work?",
                "When can you use this tactic?",
                "How do you recognize this pattern?"
            ])

        # Endgame questions
        if any(word in text_lower for word in ['endgame', 'ending', 'technique']):
            questions.extend([
                "What is the correct technique in this endgame?",
                "How do you win this ending?",
                "What are the key principles?"
            ])

        # Game analysis questions (PGN content)
        if any(pattern in text for pattern in ['1.', '2.', '[White', '[Black']):
            questions.extend([
                "What happened in this game?",
                "Why was this move played?",
                "What was the outcome of this game?",
                "What can we learn from this game?"
            ])

        # Strategy and planning questions
        if any(word in text_lower for word in ['plan', 'strategy', 'idea']):
            questions.extend([
                "What is the strategic idea here?",
                "How should you plan in this situation?",
                "What are the long-term goals?"
            ])

        return questions[:20]  # Limit for performance

    def _can_answer_question(self, question: str, text: str) -> bool:
        """
        Determine if the text can reasonably answer the given question.
        """
        question_lower = question.lower()
        text_lower = text.lower()

        # Extract meaningful words from question (remove stop words)
        stop_words = {
            'what', 'how', 'why', 'when', 'where', 'is', 'are', 'do', 'does',
            'the', 'a', 'an', 'this', 'that', 'in', 'on', 'at', 'for', 'with',
            'can', 'you', 'should', 'would', 'could'
        }

        question_words = set(question_lower.split()) - stop_words

        # Count matching words in text
        matching_words = sum(1 for word in question_words if word in text_lower)

        # Chess domain boost - lower threshold for chess-specific content
        chess_boost = 0.0
        if any(word in text_lower for word in ['chess', 'move', 'position', 'piece', 'game']):
            chess_boost = 0.1

        # Instructional content boost - lower threshold for teaching material
        instructional_boost = 0.0
        if any(word in text_lower for word in ['explain', 'because', 'therefore', 'technique', 'method']):
            instructional_boost = 0.1

        # Calculate match ratio with boosts
        base_threshold = 0.4
        adjusted_threshold = base_threshold - chess_boost - instructional_boost

        if not question_words:
            return False

        match_ratio = matching_words / len(question_words)
        return match_ratio >= adjusted_threshold

    def _evaluate_factual_density(self, text: str, semantic_result: SemanticAnalysisResult) -> float:
        """
        Evaluate the density of factual chess information.

        High factual density means the content contains concrete chess facts,
        techniques, and information rather than opinions or speculation.
        """
        # Base score from semantic analysis
        factual_score = (
                semantic_result.concept_density * 0.4 +
                semantic_result.chess_domain_relevance * 0.3 +
                semantic_result.comprehensive_concept_score * 0.3
        )

        # Opinion indicators (reduce factual density)
        opinion_indicators = [
            'i think', 'in my opinion', 'i believe', 'personally', 'i feel',
            'seems to me', 'my view', 'i suspect', 'probably', 'maybe'
        ]
        opinion_count = sum(text.lower().count(indicator) for indicator in opinion_indicators)
        opinion_penalty = min(opinion_count * 0.05, 0.2)  # Cap penalty at 20%

        # Factual indicators (increase factual density)
        factual_indicators = [
            'research shows', 'studies indicate', 'proven', 'demonstrated',
            'analysis reveals', 'according to', 'statistics show', 'data indicates',
            'masters play', 'theory recommends', 'established principle'
        ]
        factual_count = sum(text.lower().count(indicator) for indicator in factual_indicators)
        factual_bonus = min(factual_count * 0.08, 0.15)  # Cap bonus at 15%

        # Chess facts bonus (moves, positions, rules are inherently factual)
        chess_facts_bonus = 0.0
        chess_fact_indicators = [
            'move', 'position', 'rule', 'principle', 'technique',
            'pattern', 'structure', 'development', 'calculation'
        ]
        chess_facts_count = sum(text.lower().count(indicator) for indicator in chess_fact_indicators)
        if chess_facts_count > 10:
            chess_facts_bonus = 0.1

        # PGN factual bonus (games are factual by nature) - this will be added separately
        # as pgn_bonus in the calling method

        final_score = factual_score - opinion_penalty + factual_bonus + chess_facts_bonus
        return max(0.0, min(final_score, 1.0))

    def _evaluate_retrieval_friendliness(self, text: str) -> float:
        """
        Evaluate how retrieval-friendly the content is for RAG systems.

        Retrieval-friendly content has:
        - Clear topic boundaries
        - Good cross-references
        - Definitions and examples
        - Structured information
        """
        # Count retrieval-friendly features
        features = {
            'cross_references': (
                    text.lower().count('see also') +
                    text.lower().count('reference') +
                    text.lower().count('refer to') +
                    text.lower().count('related to')
            ),
            'definitions': (
                    text.lower().count('definition') +
                    text.lower().count('means') +
                    text.lower().count('is defined as') +
                    text.lower().count('refers to')
            ),
            'examples': (
                    text.lower().count('example') +
                    text.lower().count('for instance') +
                    text.lower().count('such as') +
                    text.lower().count('demonstrates')
            ),
            'clear_statements': (
                    text.lower().count('therefore') +
                    text.lower().count('because') +
                    text.lower().count('consequently') +
                    text.lower().count('this means')
            ),
            'structure': (
                    text.lower().count('first') +
                    text.lower().count('second') +
                    text.lower().count('finally') +
                    text.lower().count('next')
            ),
            'chess_specific': (
                    text.lower().count('position') +
                    text.lower().count('move') +
                    text.lower().count('variation') +
                    text.lower().count('analysis')
            ),
            'games': (
                    text.lower().count('game') +
                    text.lower().count('match') +
                    text.count('[Event') +  # PGN headers
                    text.count('[White')
            ),
            'pgn_structure': (
                    text.count('[') +
                    text.count('1.') +
                    text.count('2.') +
                    text.count('!')  # Chess annotations
            )
        }

        # Normalize features by text length
        text_length = len(text.split())
        normalized_features = {k: v / (text_length / 1000) for k, v in features.items()}

        # Weight different features
        weights = {
            'cross_references': 1.5,  # High value for RAG
            'definitions': 2.0,  # Very high value
            'examples': 1.8,  # High value
            'clear_statements': 1.2,  # Moderate value
            'structure': 1.0,  # Standard value
            'chess_specific': 1.4,  # Good for chess domain
            'games': 1.1,  # Moderate value
            'pgn_structure': 1.3  # Good for chess content
        }

        # Calculate weighted score
        weighted_score = sum(
            min(score * weights.get(feature, 1.0), 12)  # Cap individual contributions
            for feature, score in normalized_features.items()
        ) / 80  # Normalize to 0-1 range

        return min(weighted_score, 1.0)

    def _calculate_pgn_rag_bonus(self, pgn_analysis: PGNAnalysisResult) -> float:
        """
        Calculate PGN-specific RAG fitness bonus.

        PGN content can be very valuable for RAG if it contains good annotations
        and instructional context.
        """
        if pgn_analysis.evs_score == 0:
            return 0.0

        # Base bonus from EVS score
        base_bonus = min(pgn_analysis.evs_score / 500, 0.2)  # Max 20% bonus

        additional_bonus = 0.0

        # Annotation richness bonus
        if pgn_analysis.annotation_density > 0.2:
            additional_bonus += 0.05

        # Educational cues bonus
        if len(pgn_analysis.educational_cues) > 2:
            additional_bonus += 0.05

        # Famous game bonus (educational value)
        if pgn_analysis.famous_game_detected:
            additional_bonus += 0.05

        # Game type bonuses
        game_type_bonuses = {
            'annotated_game': 0.10,  # High value for RAG
            'position_study': 0.08,  # Good for specific topics
            'complete_game': 0.05,  # Moderate value
            'database_dump': 0.02  # Low value
        }
        additional_bonus += game_type_bonuses.get(pgn_analysis.game_type, 0.0)

        # Human analysis bonus (vs engine output)
        if pgn_analysis.humanness_score > EVSThresholds.HIGH_HUMANNESS_SCORE:
            additional_bonus += 0.06

        return min(base_bonus + additional_bonus, 0.25)  # Cap total bonus at 25%

    def _calculate_overall_fitness(self, chunkability: float, answerability: float,
                                   factual_density: float, retrieval_friendliness: float) -> float:
        """
        Calculate overall RAG fitness score with appropriate weighting.

        Answerability is most important for RAG, followed by factual density.
        """
        weights = {
            'chunkability': 0.20,  # Important for processing
            'answerability': 0.40,  # Most important for RAG
            'factual_density': 0.25,  # High importance for quality
            'retrieval_friendliness': 0.15  # Moderate importance
        }

        overall_score = (
                chunkability * weights['chunkability'] +
                answerability * weights['answerability'] +
                factual_density * weights['factual_density'] +
                retrieval_friendliness * weights['retrieval_friendliness']
        )

        return min(overall_score, 1.0)

    def _generate_fitness_reasoning(self, chunkability: float, answerability: float,
                                    factual_density: float, retrieval_friendliness: float,
                                    pgn_bonus: float = 0.0,
                                    pgn_analysis: Optional[PGNAnalysisResult] = None) -> str:
        """
        Generate human-readable reasoning for the fitness score.
        """
        reasons = []

        # Core metrics reasoning
        if chunkability > 0.75:
            reasons.append("Excellent chunking structure")
        elif chunkability > 0.6:
            reasons.append("Good chunking potential")
        elif chunkability < 0.4:
            reasons.append("Poor structure for chunking")

        if answerability > 0.7:
            reasons.append("High question answerability")
        elif answerability > 0.5:
            reasons.append("Moderate answerability")
        elif answerability < 0.3:
            reasons.append("Limited answerability")

        if factual_density > 0.7:
            reasons.append("Dense factual content")
        elif factual_density > 0.5:
            reasons.append("Good factual content")
        elif factual_density < 0.3:
            reasons.append("Low factual density")

        if retrieval_friendliness > 0.6:
            reasons.append("Retrieval-friendly format")
        elif retrieval_friendliness < 0.3:
            reasons.append("Poor retrieval structure")

        # PGN-specific reasoning
        if pgn_analysis and pgn_analysis.evs_score > 0:
            if pgn_analysis.evs_score >= 70:
                reasons.append(f"High-quality {pgn_analysis.game_type}")
            elif pgn_analysis.evs_score >= 50:
                reasons.append(f"Good {pgn_analysis.game_type}")
            else:
                reasons.append(f"Contains {pgn_analysis.game_type}")

        if pgn_bonus > 0.1:
            reasons.append("Strong PGN content bonus")
        elif pgn_bonus > 0.05:
            reasons.append("PGN content bonus")

        if pgn_analysis and pgn_analysis.famous_game_detected:
            reasons.append("Famous game context")

        # Educational context
        if pgn_analysis and pgn_analysis.educational_cues:
            if any(cue in pgn_analysis.educational_cues
                   for cue in ['elite_instruction', 'formal_education']):
                reasons.append("Elite instructional content")
            elif any(cue in pgn_analysis.educational_cues
                     for cue in ['instructional_content', 'analytical_content']):
                reasons.append("Instructional content detected")

        if not reasons:
            return "Basic RAG suitability"

        return "; ".join(reasons)

    def _create_minimal_semantic_result(self, text: str) -> SemanticAnalysisResult:
        """Create minimal semantic result for standalone RAG evaluation"""
        from ..core.models import create_empty_semantic_result

        # This would typically involve basic analysis, but for now return empty
        # In practice, you'd want to run at least basic semantic analysis
        return create_empty_semantic_result()

    def _empty_fitness_result(self) -> RAGFitnessResult:
        """Return empty fitness result for error cases"""
        return RAGFitnessResult(
            overall_rag_fitness=0.0,
            chunkability_score=0.0,
            answerability_score=0.0,
            factual_density_score=0.0,
            retrieval_friendliness_score=0.0,
            pgn_detection_bonus=0.0,
            evs_score=0.0,
            pgn_game_type='no_pgn_content',
            fitness_reasoning='Analysis failed'
        )

    def evaluate_content_for_rag_tiers(self, semantic_result: SemanticAnalysisResult,
                                       rag_fitness: RAGFitnessResult) -> Dict[str, Any]:
        """
        Evaluate content against RAG tier requirements.

        Returns recommendation for RAG inclusion based on EVS and fitness scores.
        """
        evs_score = semantic_result.pgn_analysis.evs_score
        fitness_score = rag_fitness.overall_rag_fitness

        # Tier recommendations based on both EVS and RAG fitness
        tier_recommendation = "REJECT"

        if evs_score >= EVSThresholds.TIER_1_THRESHOLD and fitness_score >= 0.7:
            tier_recommendation = "TIER_1"
        elif evs_score >= EVSThresholds.TIER_2_THRESHOLD and fitness_score >= 0.6:
            tier_recommendation = "TIER_2"
        elif evs_score >= EVSThresholds.TIER_3_THRESHOLD and fitness_score >= 0.5:
            tier_recommendation = "TIER_3"
        elif fitness_score >= 0.8:  # Exceptional RAG fitness can override lower EVS
            tier_recommendation = "TIER_3"

        # Additional quality checks
        quality_flags = []

        if semantic_result.instructional_value >= EVSThresholds.HIGH_INSTRUCTIONAL_VALUE:
            quality_flags.append("high_instructional_value")

        if rag_fitness.answerability_score >= 0.8:
            quality_flags.append("highly_answerable")

        if semantic_result.chess_domain_relevance >= EVSThresholds.HIGH_DOMAIN_RELEVANCE:
            quality_flags.append("strong_chess_domain")

        if semantic_result.pgn_analysis.famous_game_detected:
            quality_flags.append("famous_game")

        return {
            'tier_recommendation': tier_recommendation,
            'evs_score': evs_score,
            'rag_fitness_score': fitness_score,
            'quality_flags': quality_flags,
            'reasoning': rag_fitness.fitness_reasoning,
            'meets_rag_threshold': tier_recommendation != "REJECT"
        }