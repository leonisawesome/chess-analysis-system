"""
Semantic analyzer integration for instructional language enhancement
Modification to existing ChessSemanticAnalyzer class
"""

# Add these imports to existing semantic_analyzer.py
from .instructional_detector import InstructionalLanguageDetector

# Optional embedding support
try:
    from sentence_transformers import SentenceTransformer

    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False


class ChessSemanticAnalyzer:
    """
    Modified ChessSemanticAnalyzer with instructional language integration
    Implements 4-AI partner consensus: 0.6 * generic + 0.35 * instructional + 0.05 * plan_chain
    """

    def __init__(self, idf_weights: Dict[str, float] = None, use_embedding_confirmation: bool = False):
        # Existing initialization code...
        self.idf_weights = idf_weights or {}

        # Initialize instructional language detector per AI partner recommendations
        embedding_model = None
        if EMBEDDING_AVAILABLE and use_embedding_confirmation:
            try:
                embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Loaded MiniLM embedding model for instructional confirmation")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")

        self.instructional_detector = InstructionalLanguageDetector(
            embedding_model=embedding_model,
            use_embedding_confirmation=use_embedding_confirmation
        )

        logger.info("ChessSemanticAnalyzer initialized with instructional language enhancement")

    def _analyze_explanation_clarity(self, chunks: List[str]) -> float:
        """
        Enhanced explanation clarity analysis implementing 4-AI partner consensus formula:
        explanation_clarity = 0.6 * generic + 0.35 * instructional + 0.05 * plan_chain

        Target improvement: 0.163 → 0.60+ for GM content
        """
        if not chunks:
            return 0.0

        # Phase 1: Generic clarity analysis (existing logic)
        generic_clarity = self._analyze_generic_clarity(chunks)

        # Phase 2: Instructional language analysis (new)
        instructional_score = self.instructional_detector.analyze_instructional_language(chunks)

        # Phase 3: Plan chain detection (lightweight implementation)
        plan_chain_bonus = self._detect_plan_chains(chunks)

        # Apply AI partner consensus formula
        explanation_clarity = min(
            0.6 * generic_clarity + 0.35 * instructional_score + 0.05 * plan_chain_bonus,
            1.0
        )

        # Log detailed breakdown for validation
        logger.debug(f"EXPLANATION CLARITY BREAKDOWN:")
        logger.debug(f"  Generic clarity: {generic_clarity:.3f} (weight: 0.6)")
        logger.debug(f"  Instructional score: {instructional_score:.3f} (weight: 0.35)")
        logger.debug(f"  Plan chain bonus: {plan_chain_bonus:.3f} (weight: 0.05)")
        logger.debug(f"  Final explanation clarity: {explanation_clarity:.3f}")

        return explanation_clarity

    def _analyze_generic_clarity(self, chunks: List[str]) -> float:
        """
        Existing generic clarity analysis logic
        (Preserve existing implementation - this is placeholder)
        """
        # This should contain the existing logic from the original semantic analyzer
        # Key metrics: word complexity, sentence structure, readability scores

        text = ' '.join(chunks)
        words = text.split()

        if not words:
            return 0.0

        # Simplified clarity metrics (replace with existing implementation)
        # Average word length (shorter = clearer)
        avg_word_length = sum(len(word) for word in words) / len(words)
        word_clarity = max(0.0, 1.0 - (avg_word_length - 4.0) / 8.0)

        # Sentence complexity (shorter sentences = clearer)
        sentences = text.split('.')
        avg_sentence_length = len(words) / max(len(sentences), 1)
        sentence_clarity = max(0.0, 1.0 - (avg_sentence_length - 15.0) / 25.0)

        # Chess terminology density (moderate = clearer)
        chess_terms = self._count_chess_terms(text)
        term_density = chess_terms / len(words)
        term_clarity = max(0.0, 1.0 - abs(term_density - 0.1) / 0.1)

        generic_clarity = (word_clarity + sentence_clarity + term_clarity) / 3.0
        return min(generic_clarity, 1.0)

    def _detect_plan_chains(self, chunks: List[str]) -> float:
        """
        Detect sequential planning language that indicates structured thinking
        Lightweight implementation for 0.05 weight component
        """
        text = ' '.join(chunks).lower()

        # Plan sequence indicators
        plan_indicators = [
            r'\bfirst\b.*\bthen\b',
            r'\binitially\b.*\bnext\b',
            r'\bstep \d+\b',
            r'\bafter\b.*\bwe can\b',
            r'\bonce\b.*\bfollowed by\b',
            r'\bthe sequence\b',
            r'\bin order to\b.*\bwe must\b'
        ]

        plan_chain_count = 0
        for pattern in plan_indicators:
            matches = re.findall(pattern, text)
            plan_chain_count += len(matches)

        # Normalize by text length
        words = text.split()
        if len(words) < 100:
            return 0.0

        plan_density = plan_chain_count / (len(words) / 100.0)  # Per 100 words
        return min(plan_density, 1.0)

    def _count_chess_terms(self, text: str) -> int:
        """Count chess-specific terminology for clarity assessment"""
        # Basic chess terms (integrate with existing vocabulary if available)
        chess_terms = [
            'opening', 'middlegame', 'endgame', 'tactics', 'strategy',
            'pawn', 'knight', 'bishop', 'rook', 'queen', 'king',
            'castle', 'castling', 'en passant', 'promotion',
            'check', 'checkmate', 'stalemate', 'draw',
            'sacrifice', 'pin', 'fork', 'skewer', 'discovery',
            'advantage', 'initiative', 'tempo', 'space', 'material'
        ]

        text_lower = text.lower()
        count = 0
        for term in chess_terms:
            count += len(re.findall(r'\b' + re.escape(term) + r'\b', text_lower))

        return count


# Integration instructions for existing semantic_analyzer.py:
"""
INTEGRATION STEPS:

1. Add imports at top of semantic_analyzer.py:
   from .instructional_detector import InstructionalLanguageDetector

2. Add to __init__ method:
   self.instructional_detector = InstructionalLanguageDetector()

3. Replace existing _analyze_explanation_clarity method with the enhanced version above

4. Add the new helper methods: _detect_plan_chains, _count_chess_terms (if not present)

5. Preserve all existing functionality in _analyze_generic_clarity

The enhanced formula will improve EVS scores for GM instructional content while
maintaining existing functionality for other content types.

Target metrics per AI partner consensus:
- Raw hits: 0 → 10+ on Shankland content  
- Explanation clarity: 0.098 → 0.45+
- Final EVS: 79.7 → 85+ (TIER_1)
"""