"""
Core data models for the Chess RAG System.
All dataclasses and result objects used throughout the system.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime


@dataclass
class IDFWeights:
    """Container for IDF weights calculated from corpus analysis"""
    term_weights: Dict[str, float]
    total_documents: int
    vocabulary_size: int
    calculation_date: str
    corpus_hash: str


@dataclass
class PGNAnalysisResult:
    """Results from hybrid PGN analysis with EVS scoring"""
    evs_score: float  # Educational Value Score 0-100
    structure_score: float  # 0-20
    annotation_richness: float  # 0-20
    humanness_score: float  # 0-20
    educational_context: float  # 0-15
    game_type: str  # annotated_game, complete_game, position_study, database_dump
    total_moves: int
    annotation_density: float
    has_headers: bool
    has_variations: bool
    famous_game_detected: bool
    educational_cues: List[str]


@dataclass
class SemanticAnalysisResult:
    """Results from semantic analysis with v5 PGN integration and IDF weighting"""
    content_quality_score: float
    chess_domain_relevance: float
    instructional_value: float
    concept_density: float
    explanation_clarity: float
    top_concepts: List[str]
    semantic_categories: Dict[str, float]
    # Enhanced fields from v4
    publication_year_score: float
    comprehensive_concept_score: float
    detected_openings: List[str]
    detected_players: List[str]
    detected_books: List[str]
    # v5 PGN Integration
    pgn_analysis: PGNAnalysisResult
    pgn_integration_score: float


@dataclass
class RAGFitnessResult:
    """Results from RAG fitness evaluation"""
    overall_rag_fitness: float
    chunkability_score: float
    answerability_score: float
    factual_density_score: float
    retrieval_friendliness_score: float
    pgn_detection_bonus: float
    evs_score: float
    pgn_game_type: str
    fitness_reasoning: str


@dataclass
class RenameConfig:
    """Configuration for the renaming process"""
    source_directory: str
    output_directory: str = ""  # If empty, rename in place
    database_path: str = "chess_renaming.db"
    dry_run: bool = True
    batch_size: int = 1000
    max_workers: int = 4
    backup_enabled: bool = True
    backup_directory: str = ""
    max_filename_length: int = 120
    quality_threshold_high: int = 80  # EVS for A-tier naming
    quality_threshold_medium: int = 60  # EVS for B-tier naming
    enable_directory_organization: bool = False
    preserve_extensions: bool = True
    log_level: str = "INFO"
    resume_on_failure: bool = True
    validate_after_rename: bool = True
    rollback_file: str = "rename_rollback.json"


@dataclass
class FileRecord:
    """Record for tracking file operations"""
    id: int
    original_path: str
    new_filename: str
    new_directory: str
    content_hash: str
    file_size: int
    modification_time: float
    analysis_data: Dict[str, Any]
    evs_score: int
    content_quality: float
    game_type: str
    status: str  # discovered, analyzed, named, staged, renamed, failed, skipped
    error_message: str = ""
    processing_time: float = 0.0
    timestamp: str = ""


@dataclass
class QuarantineManifest:
    """Manifest for files moved to quarantine"""
    quarantine_id: str
    creation_date: str
    deletion_threshold: int
    total_files: int
    total_size_bytes: int
    files: List[Dict[str, Any]]
    recovery_instructions: str


@dataclass
class AnalysisRequest:
    """Request object for content analysis"""
    text: str
    file_path: str = ""
    title: str = ""
    author: str = ""
    year: str = "UnknownYear"
    surrounding_text: str = ""
    use_idf_weighting: bool = True


@dataclass
class AnalysisResponse:
    """Response object containing all analysis results"""
    semantic_result: SemanticAnalysisResult
    rag_fitness: RAGFitnessResult
    processing_time: float
    status: str
    error_message: str = ""


# Quality tier classifications
class QualityTier:
    """Constants for quality tier classification"""
    TIER_1_MIN = 85  # Elite instructional content
    TIER_2_MIN = 80  # Premium educational material
    TIER_3_MIN = 70  # Quality supplementary content

    @staticmethod
    def classify_evs(evs_score: float) -> str:
        """Classify EVS score into quality tier"""
        if evs_score >= QualityTier.TIER_1_MIN:
            return "TIER_1"
        elif evs_score >= QualityTier.TIER_2_MIN:
            return "TIER_2"
        elif evs_score >= QualityTier.TIER_3_MIN:
            return "TIER_3"
        else:
            return "BELOW_THRESHOLD"


# Processing status constants
class ProcessingStatus:
    """Constants for file processing status"""
    DISCOVERED = "discovered"
    ANALYZED = "analyzed"
    NAMED = "named"
    STAGED = "staged"
    RENAMED = "renamed"
    FAILED = "failed"
    SKIPPED = "skipped"
    QUARANTINED = "quarantined"


# Game type constants
class GameType:
    """Constants for PGN game types"""
    ANNOTATED_GAME = "annotated_game"
    COMPLETE_GAME = "complete_game"
    POSITION_STUDY = "position_study"
    DATABASE_DUMP = "database_dump"
    NO_PGN_CONTENT = "no_pgn_content"
    ERROR = "error"


def create_empty_pgn_result() -> PGNAnalysisResult:
    """Create empty PGN analysis result for error cases"""
    return PGNAnalysisResult(
        evs_score=0.0,
        structure_score=0.0,
        annotation_richness=0.0,
        humanness_score=0.0,
        educational_context=0.0,
        game_type=GameType.NO_PGN_CONTENT,
        total_moves=0,
        annotation_density=0.0,
        has_headers=False,
        has_variations=False,
        famous_game_detected=False,
        educational_cues=[]
    )


def create_empty_semantic_result() -> SemanticAnalysisResult:
    """Create empty semantic analysis result for error cases"""
    return SemanticAnalysisResult(
        content_quality_score=0.0,
        chess_domain_relevance=0.0,
        instructional_value=0.0,
        concept_density=0.0,
        explanation_clarity=0.0,
        top_concepts=[],
        semantic_categories={},
        publication_year_score=0.0,
        comprehensive_concept_score=0.0,
        detected_openings=[],
        detected_players=[],
        detected_books=[],
        pgn_analysis=create_empty_pgn_result(),
        pgn_integration_score=0.0
    )