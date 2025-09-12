"""
Chess domain vocabulary and constants for semantic analysis.
This comprehensive vocabulary powers the instructional value detection.
"""

from typing import Dict, List


class ChessVocabulary:
    """Comprehensive chess vocabulary for semantic analysis"""

    @staticmethod
    def get_chess_concepts() -> Dict[str, List[str]]:
        """Load ultimate comprehensive chess concept dictionary with curated books and openings"""
        return {
            'basic_pieces_moves': [
                'pawn', 'rook', 'bishop', 'knight', 'queen', 'king', 'pieces',
                'move', 'moves', 'square', 'squares', 'board', 'position',
                'capture', 'captures', 'attack', 'attacks', 'defend', 'defense',
                'check', 'checkmate', 'stalemate', 'draw', 'resign',
                'white', 'black', 'player', 'opponent', 'game', 'chess',
                'material', 'advantage', 'winning', 'losing', 'equal'
            ],

            'chess_notation': [
                'algebraic notation', 'descriptive notation', 'pgn', 'fen',
                'san notation', 'long algebraic', 'coordinate notation',
                'figurine notation', 'move notation', 'score notation',
                'annotation', 'commentary', 'analysis', 'variation'
            ],

            'advanced_positional_concepts': [
                'pawn structure', 'space advantage', 'advanced pawn', 'bind', 'maroczy bind',
                'blockade', 'centralization', 'closed game', 'control of the center',
                'cramped position', 'doubled pawns', 'good bishop', 'bad bishop',
                'isolated pawn', 'backward pawn', 'passed pawn', 'connected passed pawns',
                'open file', 'pawn break', 'pawn chain', 'positional play', 'squeeze',
                'outpost', 'open files and ranks', 'weak squares', 'prophylaxis',
                'two weaknesses', 'restriction', 'neutralization', 'over-protection',
                'simplification', 'pawn breaks', 'coordination', 'development',
                'king safety', 'material gain', 'least active piece', 'maximum activity',
                'stability', 'trade', 'flexibility', 'attack principle', 'minimum force',
                'maximum force', 'sustained fighting', 'zugzwang', 'favorable pawn-structure',
                'initiative', 'piece activity', 'tension', 'exchanging pieces',
                'defending pieces', 'knight outposts', 'bishop pair advantage',
                'rook on open files', 'pawn majority', 'outside passed pawn',
                'hanging pawns', 'pawn islands', 'prophylactic thinking',
                'piece harmony', 'strategic breakthrough', 'central pawn duo'
            ],

            'instructional_vocabulary': [
                'dark-square bishop', 'dark squares', 'dead draw', 'dead position',
                'decoy', 'defense', 'deflection', 'demonstration board', 'descriptive notation',
                'desperado', 'development', 'diagonal', 'discovered attack', 'discovered check',
                'diversionary sacrifice', 'domination', 'double attack', 'double check',
                'doubled pawns', 'doubled rooks', 'double fianchetto', 'draw',
                'draw by insufficient material', 'draw by repetition', 'draw by stalemate',
                'drawish', 'duffer', 'dynamic play', 'eco', 'elo rating', 'en passant',
                'en prise', 'endgame', 'endgame study', 'engine', 'equalize', 'exchange',
                'exchange sacrifice', 'fianchetto', 'fifty-move rule', 'file',
                'fischerandom', 'fish', 'flag', 'flank', 'flank opening', 'fool\'s mate',
                'forced move', 'fork', 'fortress', 'gambit', 'grandmaster', 'half-open file',
                'hanging', 'hole', 'hypermodern', 'imbalance', 'initiative',
                'insufficient material', 'intermezzo', 'international master', 'isolated pawn',
                'kingside', 'knight', 'light-square bishop', 'light squares', 'liquidation',
                'long diagonal', 'loose', 'lost position', 'luft', 'major piece',
                'majority', 'mate', 'material', 'mating net', 'middlegame', 'minor piece',
                'minority attack', 'mobility', 'norm', 'notation', 'novelty', 'open file',
                'open game', 'opening', 'opposite-colored bishops', 'opposition', 'outpost',
                'outside passed pawn', 'overloading', 'passed pawn', 'passive', 'patzer',
                'pawn', 'pawn chain', 'pawn island', 'pawn storm', 'pawn structure',
                'perpetual check', 'piece', 'pin', 'poisoned pawn', 'positional play',
                'promotion', 'prophylaxis', 'protected passed pawn', 'queenside',
                'quiet move', 'rank', 'rapid chess', 'resign', 'rook', 'rook lift',
                'sacrifice', 'scholar\'s mate', 'sealed move', 'semi-open file',
                'skewer', 'smothered mate', 'space', 'stalemate', 'swindle', 'tabiya',
                'tactics', 'tempo', 'threefold repetition', 'time control', 'time pressure',
                'touch-move rule', 'transposition', 'triangulation', 'underpromotion',
                'weak square', 'windmill', 'wrong rook pawn', 'x-ray', 'zugzwang', 'zwickmuhle',
                'absolute seventh rank', 'adjournment', 'artificial castling', 'breakthrough',
                'central break', 'endgame transition', 'favorable imbalance', 'hanging pawns',
                'hypermodernism', 'key square', 'pawn duo', 'piece sacrifice for initiative',
                'prophylactic move', 'rule of the square', 'strategic plan', 'tempo gain',
                'weak color complex'
            ],

            'tactical_concepts': [
                'pin', 'fork', 'skewer', 'discovered attack', 'double attack',
                'deflection', 'decoy', 'clearance', 'interference', 'removing defender',
                'sacrifice', 'combination', 'tactical motif', 'tactical pattern',
                'knight fork', 'family fork', 'royal fork', 'bishop pin', 'rook pin',
                'absolute pin', 'relative pin', 'cross pin', 'counter pin',
                'back rank mate', 'smothered mate', 'epaulette mate', 'corridor mate',
                'discovered check', 'double check', 'windmill', 'zwischenzug',
                'in-between move', 'intermediate move', 'greek gift', 'sacrifice on h7',
                'clearance sacrifice', 'deflection sacrifice', 'attraction',
                'magnet', 'x-ray attack', 'battery', 'desperado', 'zugzwang',
                'remove the guard', 'destroy the defender', 'overload',
                'diversion', 'lure', 'mating net', 'mating attack', 'knight sacrifice',
                'bishop sacrifice', 'rook sacrifice', 'queen sacrifice', 'exchange sacrifice',
                'positional sacrifice', 'temporary sacrifice', 'sound sacrifice',
                'speculative sacrifice', 'intuitive sacrifice'
            ],

            'strategic_concepts': [
                'planning', 'strategy', 'evaluation', 'assessment', 'imbalance',
                'prophylaxis', 'prevention', 'weak point', 'strong point',
                'long-term advantage', 'positional sacrifice', 'strategic theme',
                'maneuvering', 'regrouping', 'piece coordination', 'harmony',
                'blockade', 'restriction', 'restraint', 'bind', 'squeeze',
                'breakthrough', 'pawn breakthrough', 'piece breakthrough',
                'tempo', 'tempi', 'time', 'development advantage',
                'piece development', 'rapid development', 'lagging development',
                'dynamic', 'static', 'permanent weakness', 'temporary weakness',
                'strategic planning', 'long-term thinking', 'positional understanding'
            ],

            'instructional_concepts': [
                'chess principle', 'chess rule', 'chess law', 'learning method',
                'training exercise', 'improvement technique', 'study plan',
                'chess understanding', 'pattern recognition', 'calculation',
                'visualization', 'analysis', 'annotation', 'commentary',
                'explanation', 'instruction', 'teaching', 'coaching',
                'chess lesson', 'chess course', 'chess tutorial',
                'blunder', 'mistake', 'inaccuracy', 'good move', 'excellent move',
                'brilliant move', 'best move', 'forced move', 'only move',
                'puzzle', 'exercise', 'drill', 'practice', 'study',
                'masterclass', 'lecture', 'demonstration', 'intermediate level',
                'advanced level', 'master level', 'expert level', 'professional level'
            ],

            'famous_chess_books': [
                # Classical Foundations
                'chess fundamentals', 'lasker\'s manual of chess', 'my system', 'chess praxis',
                'modern ideas in chess', 'judgment and planning in chess', 'pawn power in chess',
                'think like a grandmaster', 'the art of the middle game', 'the soviet chess primer',

                # Modern Positional/Strategic
                'secrets of modern chess strategy', 'modern chess strategy', 'simple chess',
                'chess strategy for club players', 'chess structures a grandmaster guide',
                'positional decision making in chess', 'dynamic decision making in chess',
                'technical decision making in chess', 'the seven deadly chess sins', 'chess for zebras',
                'techniques of positional play', 'evaluate like a grandmaster',
                'the road to chess improvement', 'pump up your rating', 'under the surface',
                'the complete manual of positional chess', 'how to play dynamic chess',
                'the method in chess',

                # Aagaard Series (High-value instructional content)
                'grandmaster preparation calculation', 'grandmaster preparation positional play',
                'grandmaster preparation strategic play', 'grandmaster preparation attack defence',
                'grandmaster preparation endgame play', 'thinking inside the box',
                'excelling at chess', 'excelling at positional chess', 'excelling at technical chess',
                'excelling at combinational play', 'practical chess defence', 'applying logic in chess'
            ],

            'curated_openings': [
                # 1.e4 Openings - High instructional value
                'ruy lopez closed', 'ruy lopez marshall attack', 'ruy lopez berlin defense',
                'sicilian najdorf', 'sicilian dragon', 'sicilian sveshnikov', 'sicilian scheveningen',
                'french winawer', 'french classical', 'french tarrasch', 'french advance',
                'caro-kann classical', 'caro-kann advance', 'caro-kann panov-botvinnik attack',
                'italian game classical', 'two knights defense', 'alekhine defense',
                'pirc defense', 'king\'s gambit', 'scotch game',

                # 1.d4 Openings - High instructional value
                'queen\'s gambit declined', 'queen\'s gambit accepted', 'slav defense', 'semi-slav',
                'nimzo-indian', 'queen\'s indian', 'king\'s indian', 'grunfeld defense',
                'modern benoni', 'catalan opening', 'dutch defense', 'london system'
            ]
        }


class CategoryWeights:
    """Importance weights for different concept categories"""

    INSTRUCTIONAL_ANALYSIS_WEIGHTS = {
        'instructional_vocabulary': 4.0,  # Highest weight for instructional content
        'instructional_concepts': 3.5,  # High weight for learning concepts
        'advanced_positional_concepts': 3.0,  # Advanced concepts are valuable
        'tactical_concepts': 3.0,  # Tactical instruction is valuable
        'strategic_concepts': 3.0,  # Strategic instruction is valuable
        'famous_chess_books': 2.5,  # Known good instructional sources
        'curated_openings': 2.0,  # Opening instruction is valuable
        'chess_notation': 1.5,  # Technical content
        'basic_pieces_moves': 1.0  # Basic content, lower weight
    }

    DOMAIN_RELEVANCE_WEIGHTS = {
        'advanced_positional_concepts': 4.0,
        'instructional_vocabulary': 3.5,
        'tactical_concepts': 3.5,
        'strategic_concepts': 3.5,
        'instructional_concepts': 3.0,
        'curated_openings': 2.5,
        'famous_chess_books': 2.0,
        'chess_notation': 1.5,
        'basic_pieces_moves': 0.8
    }


class EVSThresholds:
    """Thresholds for Educational Value Score classification"""

    # RAG Tier Requirements (the target thresholds)
    TIER_1_THRESHOLD = 85  # Elite instructional content
    TIER_2_THRESHOLD = 80  # Premium educational material
    TIER_3_THRESHOLD = 70  # Quality supplementary content

    # Component score thresholds for high-quality content
    HIGH_INSTRUCTIONAL_VALUE = 0.8  # Should trigger EVS boost
    HIGH_DOMAIN_RELEVANCE = 0.7  # Strong chess content
    HIGH_EXPLANATION_CLARITY = 0.6  # Well-explained content

    # PGN Analysis thresholds
    HIGH_ANNOTATION_RICHNESS = 15  # Rich annotations
    HIGH_HUMANNESS_SCORE = 12  # Human commentary vs engine
    HIGH_EDUCATIONAL_CONTEXT = 8  # Educational setting


class InstructionalIndicators:
    """Patterns that indicate high instructional value"""

    TEACHING_PATTERNS = [
        'understand', 'explain', 'demonstrate', 'analyze', 'evaluate',
        'example', 'exercise', 'practice', 'study', 'improve', 'master',
        'technique', 'method', 'approach', 'principle', 'strategy', 'concept',
        'how to', 'what is', 'why does', 'when should', 'remember',
        'important', 'key', 'essential', 'fundamental', 'critical',
        'lesson', 'tutorial', 'guide', 'instruction', 'advanced', 'intermediate'
    ]

    EXPLANATION_PATTERNS = [
        'because', 'since', 'therefore', 'thus', 'consequently',
        'this means', 'the reason', 'as a result', 'leads to',
        'causes', 'due to', 'resulting in', 'this shows',
        'we can see', 'notice that', 'observe that'
    ]

    EDUCATIONAL_CUES = [
        'masterclass', 'lecture', 'demonstration', 'deep analysis',
        'comprehensive', 'detailed explanation', 'step by step',
        'learning objective', 'key takeaway', 'summary',
        'practice exercise', 'homework', 'assignment'
    ]

    # Penalty patterns (reduce instructional value)
    BEGINNER_PENALTIES = [
        'beginner', 'basic', 'simple', 'easy', 'elementary', 'first steps',
        'learn to play', 'how pieces move', 'chess for kids'
    ]


# File processing constants
class FileTypes:
    """Supported file types and their characteristics"""

    CHESS_EXTENSIONS = {'.pgn', '.pdf', '.txt', '.doc', '.docx', '.epub', '.djvu'}

    TEXT_EXTENSIONS = {'.txt', '.pgn'}
    PDF_EXTENSIONS = {'.pdf'}
    DOCUMENT_EXTENSIONS = {'.doc', '.docx', '.epub', '.djvu'}

    MIN_FILE_SIZE = 100  # Minimum file size in bytes
    MAX_CHUNK_SIZE = 512  # Maximum chunk size for analysis