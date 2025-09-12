"""
Intelligent Filename Generator for Chess Files.

This module generates meaningful filenames from chess content analysis results.
It uses the EVS scores, semantic analysis, and detected entities to create
descriptive filenames that reflect the quality and content of chess files.

High-quality instructional content (EVS 85+) gets detailed, descriptive names,
while lower-quality content gets simpler naming schemes.
"""

import logging
import re
import unicodedata
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Any

from ..core.models import SemanticAnalysisResult, RenameConfig
from ..core.constants import EVSThresholds
from ..core.models import QualityTier


class FilenameGenerator:
    """
    Generate meaningful filenames from chess analysis results.

    The naming strategy adapts based on content quality:
    - High EVS scores (85+): Detailed names with players, openings, context
    - Medium EVS scores (70-84): Moderate detail with key information
    - Lower EVS scores: Basic classification with quality indicators

    All names include quality indicators and content hashes for uniqueness.
    """

    def __init__(self, config: RenameConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Directory organization structure
        self.directory_structure = {
            'annotated_game': 'Annotated_Games',
            'complete_game': 'Game_Collections',
            'position_study': 'Position_Studies',
            'database_dump': 'Database_Dumps',
            'book': 'Books_and_Manuals',
            'opening_study': 'Opening_Theory',
            'endgame_study': 'Endgame_Studies',
            'article': 'Articles_and_Papers',
            'unknown': 'Unclassified'
        }

        # Quality tier subdirectories
        self.quality_subdirs = {
            'TIER_1': 'Elite_Content',
            'TIER_2': 'Premium_Content',
            'TIER_3': 'Quality_Content',
            'BELOW_THRESHOLD': 'Basic_Content'
        }

        # Forbidden characters for cross-platform compatibility
        self.forbidden_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\x00']
        self.replacement_char = '_'

    def generate_filename(self, analysis_result: SemanticAnalysisResult,
                          file_path: str, content_hash: str) -> Tuple[str, str]:
        """
        Generate filename from analysis result.

        Args:
            analysis_result: Complete semantic analysis results
            file_path: Original file path
            content_hash: Content hash for uniqueness

        Returns:
            Tuple of (filename, target_directory)
        """
        try:
            # Extract file extension
            original_ext = Path(file_path).suffix.lower()

            # Determine content type and quality
            content_type = self._determine_content_type(analysis_result, original_ext)
            evs_score = int(analysis_result.pgn_analysis.evs_score)
            quality_tier = QualityTier.classify_evs(evs_score)

            # Extract key entities and metadata
            entities = self._extract_entities(analysis_result)
            year = self._extract_year(analysis_result, file_path)
            hash_short = content_hash[:8]

            # Generate filename based on quality tier
            if quality_tier == 'TIER_1':
                filename = self._generate_tier1_filename(
                    content_type, entities, evs_score, year, hash_short
                )
            elif quality_tier == 'TIER_2':
                filename = self._generate_tier2_filename(
                    content_type, entities, evs_score, year, hash_short
                )
            elif quality_tier == 'TIER_3':
                filename = self._generate_tier3_filename(
                    content_type, entities, analysis_result, year, hash_short
                )
            else:
                filename = self._generate_basic_filename(
                    content_type, analysis_result, hash_short
                )

            # Add extension
            final_filename = filename + original_ext

            # Ensure reasonable length
            if len(final_filename) > self.config.max_filename_length:
                final_filename = self._truncate_filename(final_filename, original_ext)

            # Determine target directory
            target_directory = self._determine_target_directory(content_type, quality_tier)

            self.logger.debug(f"Generated filename: {final_filename} -> {target_directory}")

            return final_filename, target_directory

        except Exception as e:
            self.logger.error(f"Filename generation failed for {file_path}: {e}")
            # Fallback filename
            timestamp = self._get_timestamp()
            fallback_name = f"Chess_File_{timestamp}_{content_hash[:8]}{Path(file_path).suffix}"
            return fallback_name, self.directory_structure.get('unknown', '')

    def _generate_tier1_filename(self, content_type: str, entities: Dict[str, str],
                                 evs_score: int, year: str, hash_short: str) -> str:
        """
        Generate detailed filename for Tier 1 content (EVS 85+).

        Tier 1 content gets the most descriptive names with full context.
        """
        parts = []

        # Content type (elite content marker)
        parts.append(f"Elite_{self._sanitize_text(content_type.title().replace('_', ''), 15)}")

        # Player information (detailed for elite content)
        if entities.get('players'):
            parts.append(entities['players'])
        elif entities.get('famous_players'):
            parts.append(self._sanitize_text(entities['famous_players'], 20))

        # Opening or main topic
        if entities.get('opening'):
            parts.append(self._sanitize_text(entities['opening'], 25))
        elif entities.get('book'):
            parts.append(self._sanitize_text(entities['book'], 25))
        elif entities.get('main_topic'):
            parts.append(self._sanitize_text(entities['main_topic'], 20))

        # EVS indicator for elite content
        parts.append(f"EVS{evs_score}")

        # Educational context markers
        if entities.get('instructional_level'):
            parts.append(self._sanitize_text(entities['instructional_level'], 10))

        # Year if available
        if year and year != "UnknownYear":
            parts.append(year)

        # Hash for uniqueness
        parts.append(hash_short)

        return "_".join(parts)

    def _generate_tier2_filename(self, content_type: str, entities: Dict[str, str],
                                 evs_score: int, year: str, hash_short: str) -> str:
        """
        Generate filename for Tier 2 content (EVS 80-84).

        Tier 2 content gets good descriptive names with key information.
        """
        parts = []

        # Content type (premium marker)
        parts.append(f"Premium_{self._sanitize_text(content_type.title().replace('_', ''), 15)}")

        # Primary entity (player, opening, or book)
        if entities.get('players'):
            parts.append(entities['players'])
        elif entities.get('opening'):
            parts.append(self._sanitize_text(entities['opening'], 20))
        elif entities.get('book'):
            parts.append(self._sanitize_text(entities['book'], 20))

        # EVS score
        parts.append(f"EVS{evs_score}")

        # Additional context if space allows
        if entities.get('secondary_topic'):
            parts.append(self._sanitize_text(entities['secondary_topic'], 15))

        # Year
        if year and year != "UnknownYear":
            parts.append(year)

        # Hash
        parts.append(hash_short)

        return "_".join(parts)

    def _generate_tier3_filename(self, content_type: str, entities: Dict[str, str],
                                 analysis_result: SemanticAnalysisResult, year: str,
                                 hash_short: str) -> str:
        """
        Generate filename for Tier 3 content (EVS 70-79).

        Tier 3 content gets moderate detail focusing on key aspects.
        """
        parts = []

        # Content type
        parts.append(self._sanitize_text(content_type.title().replace('_', ''), 15))

        # Primary entity
        if entities.get('players'):
            # Use only first player for tier 3
            first_player = entities['players'].split('_vs_')[0] if '_vs_' in entities['players'] else entities[
                'players']
            parts.append(first_player)
        elif entities.get('opening'):
            parts.append(self._sanitize_text(entities['opening'], 18))
        elif entities.get('book'):
            parts.append(self._sanitize_text(entities['book'], 18))

        # Quality indicator (use content quality instead of EVS for variety)
        quality_pct = int(analysis_result.content_quality_score * 100)
        parts.append(f"Q{quality_pct}")

        # Educational marker if high instructional value
        if analysis_result.instructional_value >= EVSThresholds.HIGH_INSTRUCTIONAL_VALUE:
            parts.append("Educational")

        # Hash
        parts.append(hash_short)

        return "_".join(parts)

    def _generate_basic_filename(self, content_type: str, analysis_result: SemanticAnalysisResult,
                                 hash_short: str) -> str:
        """
        Generate basic filename for below-threshold content.

        Basic content gets simple classification with minimal detail.
        """
        parts = []

        # Simple content type
        parts.append(self._sanitize_text(content_type.title().replace('_', ''), 12))

        # Basic quality indicator
        if analysis_result.content_quality_score > 0.3:
            quality_pct = int(analysis_result.content_quality_score * 100)
            parts.append(f"Q{quality_pct}")
        elif analysis_result.pgn_analysis.evs_score > 0:
            evs = int(analysis_result.pgn_analysis.evs_score)
            parts.append(f"EVS{evs}")
        else:
            parts.append("Basic")

        # Hash for uniqueness
        parts.append(hash_short)

        return "_".join(parts)

    def _extract_entities(self, analysis_result: SemanticAnalysisResult) -> Dict[str, str]:
        """Extract and format key entities from analysis results"""
        entities = {}

        # Player extraction (enhanced for different scenarios)
        if analysis_result.detected_players:
            players = analysis_result.detected_players[:2]  # Top 2 players
            if len(players) == 2:
                player1 = self._sanitize_text(players[0], 12)
                player2 = self._sanitize_text(players[1], 12)
                entities['players'] = f"{player1}_vs_{player2}"
            else:
                entities['players'] = self._sanitize_text(players[0], 20)

            # Also store for fallback
            entities['famous_players'] = players[0]

        # Opening extraction
        if analysis_result.detected_openings:
            primary_opening = analysis_result.detected_openings[0]
            entities['opening'] = primary_opening

            # Secondary opening if available
            if len(analysis_result.detected_openings) > 1:
                entities['secondary_opening'] = analysis_result.detected_openings[1]

        # Book extraction
        if analysis_result.detected_books:
            entities['book'] = analysis_result.detected_books[0]

        # Main topic from top concepts
        if analysis_result.top_concepts:
            # Find the most sophisticated concept as main topic
            sophisticated_concepts = [
                concept for concept in analysis_result.top_concepts[:5]
                if len(concept.split()) > 1  # Multi-word concepts are usually more specific
            ]
            if sophisticated_concepts:
                entities['main_topic'] = sophisticated_concepts[0]
            else:
                entities['main_topic'] = analysis_result.top_concepts[0]

        # Instructional level detection
        if analysis_result.instructional_value >= 0.9:
            entities['instructional_level'] = "Master"
        elif analysis_result.instructional_value >= EVSThresholds.HIGH_INSTRUCTIONAL_VALUE:
            entities['instructional_level'] = "Advanced"
        elif analysis_result.instructional_value >= 0.6:
            entities['instructional_level'] = "Intermediate"

        # Game type context
        entities['game_type'] = analysis_result.pgn_analysis.game_type

        return entities

    def _determine_content_type(self, analysis_result: SemanticAnalysisResult, file_ext: str) -> str:
        """Determine primary content type for naming"""
        pgn_analysis = analysis_result.pgn_analysis

        # Use PGN analysis if available
        if pgn_analysis.evs_score > 0:
            return pgn_analysis.game_type

        # Use semantic analysis for non-PGN content
        if analysis_result.detected_books:
            return "book"
        elif file_ext.lower() == '.pdf' and analysis_result.chess_domain_relevance > 0.7:
            if analysis_result.detected_openings:
                return "opening_study"
            elif any('endgame' in concept.lower() for concept in analysis_result.top_concepts[:5]):
                return "endgame_study"
            else:
                return "article"
        else:
            return "unknown"

    def _extract_year(self, analysis_result: SemanticAnalysisResult, file_path: str) -> str:
        """Extract or estimate year from various sources"""
        # Try publication year from semantic analysis
        if hasattr(analysis_result, 'publication_year') and analysis_result.publication_year:
            return str(analysis_result.publication_year)

        # Try to extract from top concepts
        year_patterns = re.compile(r'\b(19\d{2}|20\d{2})\b')
        text_to_search = " ".join(analysis_result.top_concepts[:10])

        matches = year_patterns.findall(text_to_search)
        if matches:
            # Return most recent year
            years = [int(year) for year in matches]
            return str(max(years))

        # Try filename
        filename_matches = year_patterns.findall(Path(file_path).name)
        if filename_matches:
            years = [int(year) for year in filename_matches]
            return str(max(years))

        return "UnknownYear"

    def _determine_target_directory(self, content_type: str, quality_tier: str) -> str:
        """Determine target directory structure"""
        if not self.config.enable_directory_organization:
            return ""

        # Base directory by content type
        base_dir = self.directory_structure.get(content_type, self.directory_structure['unknown'])

        # Add quality tier subdirectory
        quality_subdir = self.quality_subdirs.get(quality_tier, 'Basic_Content')

        return f"{base_dir}/{quality_subdir}"

    def _sanitize_text(self, text: str, max_length: int = 50) -> str:
        """Clean text for use in filenames"""
        if not text:
            return "Unknown"

        # Handle macOS colon issue specifically
        text = text.replace(':', '-')

        # Unicode normalization
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')

        # Remove/replace forbidden characters
        for char in self.forbidden_chars:
            text = text.replace(char, self.replacement_char)

        # Clean up multiple separators and whitespace
        text = re.sub(r'[_\-\s]+', '_', text)
        text = re.sub(r'^[_\-]+|[_\-]+$', '', text)

        # Truncate to max length
        if len(text) > max_length:
            text = text[:max_length].rstrip('_-')

        return text if text else "Unknown"

    def _truncate_filename(self, filename: str, extension: str) -> str:
        """Truncate filename while preserving important parts"""
        max_length = self.config.max_filename_length

        if len(filename) <= max_length:
            return filename

        # Split into parts
        name_without_ext = filename.replace(extension, '')
        parts = name_without_ext.split('_')

        if len(parts) < 3:
            # Simple truncation if not enough parts
            return name_without_ext[:max_length - len(extension)] + extension

        # Keep first part (content type), last part (hash), and truncate middle
        first_part = parts[0]
        last_part = parts[-1]
        middle_parts = parts[1:-1]

        # Calculate available space for middle parts
        fixed_length = len(first_part) + len(last_part) + len(extension) + 2  # 2 for underscores
        available_space = max_length - fixed_length

        # Truncate middle parts to fit
        truncated_middle = []
        current_length = 0

        for part in middle_parts:
            if current_length + len(part) + 1 <= available_space:  # +1 for underscore
                truncated_middle.append(part)
                current_length += len(part) + 1
            else:
                # Partial truncation of this part if space allows
                remaining_space = available_space - current_length - 1
                if remaining_space > 3:  # Only if meaningful space left
                    truncated_middle.append(part[:remaining_space])
                break

        # Reconstruct filename
        if truncated_middle:
            final_parts = [first_part] + truncated_middle + [last_part]
        else:
            final_parts = [first_part, last_part]

        return "_".join(final_parts) + extension

    def _get_timestamp(self) -> str:
        """Get timestamp for fallback filenames"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def generate_batch_naming_preview(self, analysis_results: List[Tuple[SemanticAnalysisResult, str, str]],
                                      max_preview: int = 20) -> Dict[str, Any]:
        """
        Generate naming preview for a batch of files.

        Useful for reviewing naming strategy before applying changes.

        Args:
            analysis_results: List of (semantic_result, file_path, content_hash) tuples
            max_preview: Maximum number of files to preview

        Returns:
            Dictionary with preview information and statistics
        """
        previews = []
        tier_counts = {'TIER_1': 0, 'TIER_2': 0, 'TIER_3': 0, 'BELOW_THRESHOLD': 0}
        content_type_counts = {}

        for i, (analysis_result, file_path, content_hash) in enumerate(analysis_results[:max_preview]):
            try:
                filename, target_dir = self.generate_filename(analysis_result, file_path, content_hash)

                evs_score = analysis_result.pgn_analysis.evs_score
                tier = QualityTier.classify_evs(evs_score)
                content_type = self._determine_content_type(analysis_result, Path(file_path).suffix)

                tier_counts[tier] += 1
                content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1

                previews.append({
                    'original_name': Path(file_path).name,
                    'new_name': filename,
                    'target_directory': target_dir,
                    'evs_score': evs_score,
                    'quality_tier': tier,
                    'content_type': content_type,
                    'instructional_value': analysis_result.instructional_value
                })

            except Exception as e:
                previews.append({
                    'original_name': Path(file_path).name,
                    'error': str(e)
                })

        return {
            'preview_count': len(previews),
            'total_files': len(analysis_results),
            'tier_distribution': tier_counts,
            'content_type_distribution': content_type_counts,
            'naming_previews': previews,
            'config': {
                'max_filename_length': self.config.max_filename_length,
                'directory_organization': self.config.enable_directory_organization,
                'quality_thresholds': {
                    'tier_1': self.config.quality_threshold_high,
                    'tier_2': self.config.quality_threshold_medium
                }
            }
        }

    def validate_filename_uniqueness(self, generated_filenames: List[str]) -> Dict[str, Any]:
        """
        Validate that generated filenames are unique.

        Returns conflict information and suggestions for resolution.
        """
        filename_counts = {}
        conflicts = []

        for filename in generated_filenames:
            if filename in filename_counts:
                filename_counts[filename] += 1
                if filename_counts[filename] == 2:  # First conflict
                    conflicts.append(filename)
            else:
                filename_counts[filename] = 1

        return {
            'total_filenames': len(generated_filenames),
            'unique_filenames': len(filename_counts),
            'conflicts': len(conflicts),
            'conflict_filenames': conflicts,
            'uniqueness_rate': len(filename_counts) / len(generated_filenames) if generated_filenames else 0
        }