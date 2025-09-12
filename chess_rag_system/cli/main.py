"""
Command Line Interface for Chess RAG System.

This module provides the main CLI entry point for the modular chess file analysis
and renaming system. It handles argument parsing, command routing, and provides
a clean interface for all system operations.
"""

import argparse
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from chess_rag_system.cli.commands import CommandHandler
from chess_rag_system.utils.logging_config import setup_logging


def create_argument_parser():
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(
        description='Chess RAG System v5.1 - Modular Architecture with EVS Integration Fix',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Time estimation before processing
  python -m chess_rag_system "/path/to/chess/files" --estimate-time

  # Calculate IDF weights for enhanced analysis  
  python -m chess_rag_system "/path/to/chess/files" --calculate-idf

  # Execute analysis and renaming with EVS integration
  python -m chess_rag_system "/path/to/chess/files" --execute --backup

  # Test EVS integration on single file
  python -m chess_rag_system --test-evs-integration "/path/to/test/file.pgn"

  # Generate quarantine scripts for low-quality files
  python -m chess_rag_system --generate-deletion-scripts --deletion-threshold 70

  # Restore quarantined files
  python -m chess_rag_system --restore-quarantine evs_below_70_20241201_143022

For more examples: python -m chess_rag_system --help-examples
""")

    # Main operation arguments
    parser.add_argument('source_directory', nargs='?',
                        help='Source directory containing chess files')

    parser.add_argument('--output-directory',
                        help='Output directory (default: rename in place)')

    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Perform dry run without actual renaming (default)')

    parser.add_argument('--execute', action='store_true',
                        help='Execute actual operations (overrides --dry-run)')

    # Analysis and processing options
    parser.add_argument('--workers', type=int, default=4,
                        help='Number of worker processes (default: 4)')

    parser.add_argument('--batch-size', type=int, default=1000,
                        help='Batch size for processing (default: 1000)')

    parser.add_argument('--max-runtime', type=int, metavar='MINUTES',
                        help='Maximum runtime in minutes (graceful shutdown)')

    # EVS Integration Testing - NEW FEATURE
    parser.add_argument('--test-evs-integration', metavar='FILE_PATH',
                        help='Test EVS integration on a single file and show detailed breakdown')

    parser.add_argument('--debug-evs', action='store_true',
                        help='Enable detailed EVS calculation debugging')

    # IDF Enhancement
    parser.add_argument('--calculate-idf', action='store_true',
                        help='Calculate IDF weights from corpus for enhanced analysis')

    parser.add_argument('--idf-weights-path', default='chess_idf_weights.json',
                        help='Path to IDF weights file (default: chess_idf_weights.json)')

    # Quality analysis and reporting
    parser.add_argument('--quality-breakdown', metavar='FILE_PATH',
                        help='Show detailed quality breakdown for a specific file')

    parser.add_argument('--sample-analysis', type=int, metavar='COUNT',
                        help='Analyze a sample of files for quality estimation')

    parser.add_argument('--export-results', choices=['csv', 'json'],
                        help='Export analysis results to specified format')

    # Quarantine operations
    parser.add_argument('--generate-deletion-scripts', action='store_true',
                        help='Generate safe quarantine scripts for low-quality files')

    parser.add_argument('--deletion-threshold', type=int, default=70,
                        help='EVS threshold for quarantine (default: 70)')

    parser.add_argument('--deletion-analysis-only', action='store_true',
                        help='Show quarantine analysis without generating scripts')

    parser.add_argument('--execute-quarantine', type=int, metavar='EVS_THRESHOLD',
                        help='Execute immediate quarantine for files below EVS threshold')

    parser.add_argument('--restore-quarantine', metavar='QUARANTINE_ID',
                        help='Restore files from quarantine session')

    parser.add_argument('--list-quarantines', action='store_true',
                        help='List available quarantine sessions')

    # File organization
    parser.add_argument('--organize', action='store_true',
                        help='Organize files into quality-based directory structure')

    parser.add_argument('--quality-threshold-high', type=int, default=85,
                        help='EVS threshold for high quality (TIER_1) (default: 85)')

    parser.add_argument('--quality-threshold-medium', type=int, default=80,
                        help='EVS threshold for medium quality (TIER_2) (default: 80)')

    # Backup and safety
    parser.add_argument('--backup', action='store_true', default=True,
                        help='Create backup before operations (default)')

    parser.add_argument('--no-backup', action='store_true',
                        help='Disable backup creation')

    parser.add_argument('--rollback', metavar='ROLLBACK_FILE',
                        help='Rollback previous operations using rollback file')

    # Database and persistence
    parser.add_argument('--database', default='chess_analysis.db',
                        help='Database file path (default: chess_analysis.db)')

    parser.add_argument('--resume-session', metavar='SESSION_ID',
                        help='Resume interrupted processing session')

    # Utility operations
    parser.add_argument('--estimate-time', action='store_true',
                        help='Estimate processing time based on sample analysis')

    parser.add_argument('--validate-config', action='store_true',
                        help='Validate configuration and system requirements')

    parser.add_argument('--system-info', action='store_true',
                        help='Show system information and available features')

    # Logging and debugging
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        default='INFO', help='Logging level (default: INFO)')

    parser.add_argument('--quiet', action='store_true',
                        help='Suppress non-essential output')

    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output with detailed progress')

    # Help and examples
    parser.add_argument('--help-examples', action='store_true',
                        help='Show detailed usage examples')

    parser.add_argument('--version', action='version', version='Chess RAG System v5.1')

    return parser


def main():
    """Main CLI entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Handle special help commands
    if args.help_examples:
        from chess_rag_system.cli.commands import show_usage_examples
        show_usage_examples()
        return

    # Setup logging
    log_level = 'WARNING' if args.quiet else args.log_level
    if args.verbose:
        log_level = 'DEBUG'

    setup_logging(log_level)

    # Create command handler
    command_handler = CommandHandler()

    try:
        # Route to appropriate command
        if args.test_evs_integration:
            command_handler.test_evs_integration(args)
        elif args.quality_breakdown:
            command_handler.quality_breakdown(args)
        elif args.sample_analysis:
            command_handler.sample_analysis(args)
        elif args.calculate_idf:
            command_handler.calculate_idf(args)
        elif args.generate_deletion_scripts or args.deletion_analysis_only:
            command_handler.handle_quarantine_operations(args)
        elif args.execute_quarantine:
            command_handler.execute_quarantine(args)
        elif args.restore_quarantine:
            command_handler.restore_quarantine(args)
        elif args.list_quarantines:
            command_handler.list_quarantines(args)
        elif args.rollback:
            command_handler.rollback_operations(args)
        elif args.estimate_time:
            command_handler.estimate_processing_time(args)
        elif args.validate_config:
            command_handler.validate_configuration(args)
        elif args.system_info:
            command_handler.show_system_info(args)
        elif args.export_results:
            command_handler.export_results(args)
        elif args.resume_session:
            command_handler.resume_session(args)
        elif args.source_directory:
            command_handler.process_files(args)
        else:
            print("Error: No operation specified. Use --help for usage information.")
            print("\nQuick start:")
            print("  python -m chess_rag_system --help-examples")
            print("  python -m chess_rag_system \"/path/to/chess/files\" --estimate-time")
            return 1

    except KeyboardInterrupt:
        print("\nOperation interrupted by user.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose or args.log_level == 'DEBUG':
            import traceback
            traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())