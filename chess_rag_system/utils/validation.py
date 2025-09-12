"""
Validation Utilities for Chess RAG System.

Provides comprehensive validation for system configuration, file integrity,
analysis results, and EVS integration correctness.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from ..core.models import SemanticAnalysisResult, RenameConfig
from ..core.constants import EVSThresholds
from ..core.models import QualityTier


class SystemValidator:
    """Comprehensive system validation utilities"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_system_requirements(self) -> Dict[str, Any]:
        """
        Validate system requirements and dependencies.

        Returns:
            Validation report with status and recommendations
        """
        report = {
            'overall_status': 'PASS',
            'python_version': None,
            'dependencies': {},
            'warnings': [],
            'errors': [],
            'recommendations': []
        }

        # Check Python version
        python_version = sys.version_info
        report['python_version'] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"

        if python_version < (3, 8):
            report['errors'].append(f"Python 3.8+ required, found {report['python_version']}")
            report['overall_status'] = 'FAIL'
        elif python_version < (3, 9):
            report['warnings'].append(f"Python 3.9+ recommended for optimal performance")

        # Check critical dependencies
        critical_deps = [
            ('pathlib', 'Core file operations'),
            ('sqlite3', 'Database operations'),
            ('json', 'Data serialization'),
            ('logging', 'System logging')
        ]

        # Check optional but important dependencies
        optional_deps = [
            ('tqdm', 'Progress tracking', 'pip install tqdm'),
            ('torch', 'NLP features', 'pip install torch'),
            ('transformers', 'Semantic analysis', 'pip install transformers'),
            ('sentence_transformers', 'Sentence embeddings', 'pip install sentence-transformers'),
            ('sklearn', 'Machine learning', 'pip install scikit-learn'),
            ('PyPDF2', 'PDF processing', 'pip install PyPDF2'),
            ('docx', 'DOCX processing', 'pip install python-docx')
        ]

        # Test critical dependencies
        for dep_name, description in critical_deps:
            try:
                __import__(dep_name)
                report['dependencies'][dep_name] = {'status': 'AVAILABLE', 'description': description}
            except ImportError:
                report['dependencies'][dep_name] = {'status': 'MISSING', 'description': description}
                report['errors'].append(f"Critical dependency missing: {dep_name}")
                report['overall_status'] = 'FAIL'

        # Test optional dependencies
        for dep_name, description, install_cmd in optional_deps:
            try:
                __import__(dep_name)
                report['dependencies'][dep_name] = {
                    'status': 'AVAILABLE',
                    'description': description,
                    'install_command': install_cmd
                }
            except ImportError:
                report['dependencies'][dep_name] = {
                    'status': 'MISSING',
                    'description': description,
                    'install_command': install_cmd
                }
                report['warnings'].append(f"Optional dependency missing: {dep_name}")

        # Generate recommendations
        missing_optional = [name for name, info in report['dependencies'].items()
                            if info['status'] == 'MISSING' and 'install_command' in info]

        if missing_optional:
            report['recommendations'].append(
                f"Install optional dependencies for full functionality: "
                f"{' && '.join([report['dependencies'][dep]['install_command'] for dep in missing_optional])}"
            )

        if report['overall_status'] == 'PASS' and not report['warnings']:
            report['recommendations'].append("System is fully configured for optimal performance")

        return report

    def validate_configuration(self, config: RenameConfig) -> Dict[str, Any]:
        """
        Validate system configuration.

        Args:
            config: Configuration to validate

        Returns:
            Validation report
        """
        report = {
            'overall_status': 'PASS',
            'errors': [],
            'warnings': [],
            'configuration_issues': []
        }

        # Validate source directory
        if not Path(config.source_directory).exists():
            report['errors'].append(f"Source directory not found: {config.source_directory}")
            report['overall_status'] = 'FAIL'
        elif not os.access(config.source_directory, os.R_OK):
            report['errors'].append(f"Source directory not readable: {config.source_directory}")
            report['overall_status'] = 'FAIL'

        # Validate output directory if specified
        if config.output_directory:
            output_path = Path(config.output_directory)
            if output_path.exists():
                if not os.access(output_path, os.W_OK):
                    report['errors'].append(f"Output directory not writable: {config.output_directory}")
                    report['overall_status'] = 'FAIL'
            else:
                try:
                    output_path.mkdir(parents=True, exist_ok=True)
                    report['warnings'].append(f"Created output directory: {config.output_directory}")
                except Exception as e:
                    report['errors'].append(f"Cannot create output directory: {e}")
                    report['overall_status'] = 'FAIL'

        # Validate worker configuration
        if config.max_workers < 1:
            report['errors'].append("max_workers must be at least 1")
            report['overall_status'] = 'FAIL'
        elif config.max_workers > os.cpu_count() * 2:
            report['warnings'].append(f"max_workers ({config.max_workers}) is very high for {os.cpu_count()} CPU cores")

        # Validate batch size
        if config.batch_size < 1:
            report['errors'].append("batch_size must be at least 1")
            report['overall_status'] = 'FAIL'
        elif config.batch_size > 10000:
            report['warnings'].append("Very large batch_size may cause memory issues")

        # Validate quality thresholds
        if config.quality_threshold_high <= config.quality_threshold_medium:
            report['configuration_issues'].append(
                "quality_threshold_high should be greater than quality_threshold_medium")

        if config.quality_threshold_medium < 50 or config.quality_threshold_high < 50:
            report['warnings'].append("Quality thresholds seem low - consider values 70-90 for meaningful filtering")

        return report

    def validate_evs_integration(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that EVS integration is working correctly.

        This is critical for verifying that the architectural fix
        properly boosts EVS scores for instructional content.

        Args:
            test_results: Results from EVS integration test

        Returns:
            Validation report on EVS integration correctness
        """
        report = {
            'integration_status': 'UNKNOWN',
            'instructional_detection': 'UNKNOWN',
            'evs_boost_applied': 'UNKNOWN',
            'target_achievement': 'UNKNOWN',
            'issues': [],
            'recommendations': []
        }

        try:
            semantic = test_results.get('semantic_breakdown', {})
            integration = test_results.get('integration_analysis', {})
            final = test_results.get('final_scores', {})

            instructional_value = semantic.get('instructional_value', 0)
            instructional_boost = integration.get('instructional_boost', 0)
            final_evs = final.get('evs_score', 0)

            # Validate instructional content detection
            if instructional_value >= EVSThresholds.HIGH_INSTRUCTIONAL_VALUE:
                report['instructional_detection'] = 'PASS'
            elif instructional_value >= 0.6:
                report['instructional_detection'] = 'PARTIAL'
                report['issues'].append(
                    f"Instructional value {instructional_value:.3f} is moderate but below high threshold")
            else:
                report['instructional_detection'] = 'FAIL'
                report['issues'].append(
                    f"Low instructional value {instructional_value:.3f} - content may not be instructional")

            # Validate EVS boost application
            if instructional_value >= EVSThresholds.HIGH_INSTRUCTIONAL_VALUE:
                if instructional_boost >= 0.15:  # Expect significant boost for high instructional content
                    report['evs_boost_applied'] = 'PASS'
                elif instructional_boost >= 0.05:
                    report['evs_boost_applied'] = 'PARTIAL'
                    report['issues'].append(
                        f"EVS boost {instructional_boost:.3f} is lower than expected for high instructional content")
                else:
                    report['evs_boost_applied'] = 'FAIL'
                    report['issues'].append(f"No significant EVS boost applied despite high instructional value")
            else:
                report['evs_boost_applied'] = 'N/A'

            # Validate target achievement
            if final_evs >= EVSThresholds.TIER_1_THRESHOLD:  # 85+
                report['target_achievement'] = 'EXCELLENT'
            elif final_evs >= EVSThresholds.TIER_2_THRESHOLD:  # 80+
                report['target_achievement'] = 'GOOD'
            elif final_evs >= EVSThresholds.TIER_3_THRESHOLD:  # 70+
                report['target_achievement'] = 'ACCEPTABLE'
            else:
                report['target_achievement'] = 'INSUFFICIENT'
                report['issues'].append(f"Final EVS {final_evs:.1f} below RAG inclusion threshold")

            # Overall integration status
            if (report['instructional_detection'] == 'PASS' and
                    report['evs_boost_applied'] == 'PASS' and
                    report['target_achievement'] in ['EXCELLENT', 'GOOD']):
                report['integration_status'] = 'PASS'
            elif report['target_achievement'] in ['GOOD', 'ACCEPTABLE']:
                report['integration_status'] = 'PARTIAL'
            else:
                report['integration_status'] = 'FAIL'

            # Generate recommendations
            if report['integration_status'] == 'PASS':
                report['recommendations'].append(
                    "EVS integration is working correctly - GM content achieves target scores")
            elif report['integration_status'] == 'PARTIAL':
                report['recommendations'].append("EVS integration working but may benefit from boost tuning")
                if instructional_boost < 0.2:
                    report['recommendations'].append(
                        "Consider increasing instructional boost weights in IntegrationScorer")
            else:
                report['recommendations'].append(
                    "EVS integration needs attention - check semantic analysis and boost calculations")
                report['recommendations'].append("Debug the IntegrationScorer._calculate_instructional_boost() method")

        except Exception as e:
            report['integration_status'] = 'ERROR'
            report['issues'].append(f"Validation failed: {e}")

        return report

    def validate_file_integrity(self, original_path: str, new_path: str) -> bool:
        """
        Validate that file was renamed correctly without corruption.

        Args:
            original_path: Original file path (may not exist after rename)
            new_path: New file path

        Returns:
            True if file integrity is maintained
        """
        try:
            if not Path(new_path).exists():
                self.logger.error(f"Renamed file does not exist: {new_path}")
                return False

            # Additional integrity checks could be added here
            # (file size, content hash comparison, etc.)

            return True

        except Exception as e:
            self.logger.error(f"File integrity validation failed: {e}")
            return False

    def validate_analysis_results(self, results: SemanticAnalysisResult) -> Dict[str, Any]:
        """
        Validate analysis results for reasonableness and consistency.

        Args:
            results: Semantic analysis results to validate

        Returns:
            Validation report
        """
        report = {
            'overall_validity': 'PASS',
            'issues': [],
            'warnings': []
        }

        # Check for reasonable score ranges
        scores_to_check = [
            ('instructional_value', results.instructional_value, 0.0, 1.0),
            ('chess_domain_relevance', results.chess_domain_relevance, 0.0, 1.0),
            ('concept_density', results.concept_density, 0.0, 1.0),
            ('explanation_clarity', results.explanation_clarity, 0.0, 1.0),
            ('content_quality_score', results.content_quality_score, 0.0, 1.0)
        ]

        for name, value, min_val, max_val in scores_to_check:
            if not (min_val <= value <= max_val):
                report['issues'].append(f"{name} out of range: {value} (expected {min_val}-{max_val})")
                report['overall_validity'] = 'FAIL'

        # Check EVS score range
        evs_score = results.pgn_analysis.evs_score
        if not (0 <= evs_score <= 100):
            report['issues'].append(f"EVS score out of range: {evs_score} (expected 0-100)")
            report['overall_validity'] = 'FAIL'

        # Check for consistency between scores
        if (results.instructional_value > 0.8 and
                results.chess_domain_relevance > 0.7 and
                evs_score < 60):
            report['warnings'].append("High instructional value and domain relevance but low EVS - check integration")

        # Check for reasonable concept extraction
        if not results.top_concepts:
            report['warnings'].append("No concepts extracted - may indicate analysis issue")
        elif len(results.top_concepts) > 50:
            report['warnings'].append("Very many concepts extracted - may indicate noisy analysis")

        return report


def run_comprehensive_validation(config: RenameConfig = None) -> Dict[str, Any]:
    """
    Run comprehensive system validation.

    Args:
        config: Optional configuration to validate

    Returns:
        Complete validation report
    """
    validator = SystemValidator()

    full_report = {
        'validation_timestamp': None,
        'system_requirements': None,
        'configuration': None,
        'overall_status': 'UNKNOWN',
        'summary': []
    }

    from datetime import datetime
    full_report['validation_timestamp'] = datetime.now().isoformat()

    # System requirements validation
    full_report['system_requirements'] = validator.validate_system_requirements()

    # Configuration validation if provided
    if config:
        full_report['configuration'] = validator.validate_configuration(config)

    # Determine overall status
    req_status = full_report['system_requirements']['overall_status']
    config_status = full_report.get('configuration', {}).get('overall_status', 'PASS')

    if req_status == 'FAIL' or config_status == 'FAIL':
        full_report['overall_status'] = 'FAIL'
    elif req_status == 'PASS' and config_status == 'PASS':
        full_report['overall_status'] = 'PASS'
    else:
        full_report['overall_status'] = 'PARTIAL'

    # Generate summary
    if full_report['overall_status'] == 'PASS':
        full_report['summary'].append("✅ System validation passed - ready for operation")
    elif full_report['overall_status'] == 'PARTIAL':
        full_report['summary'].append("⚠️ System validation passed with warnings - check recommendations")
    else:
        full_report['summary'].append("❌ System validation failed - resolve errors before proceeding")

    return full_report