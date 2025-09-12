"""
Main Chess File Renaming Orchestrator.

This module coordinates the complete chess file analysis and renaming workflow.
It manages the discovery, analysis, naming, and organization of chess files using
the sophisticated semantic analysis pipeline to identify high-quality content.

Key responsibilities:
- File discovery and filtering
- Batch processing with progress tracking
- Analysis pipeline orchestration
- Filename generation and conflict resolution
- Quality-based organization
- Progress reporting and statistics
"""

import logging
import os
import json
import shutil
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

from ..core.models import RenameConfig, FileRecord
from ..core.constants import FileTypes
from ..core.models import QualityTier
from ..storage.database_manager import DatabaseManager
from ..file_ops.file_processor import FileProcessor
from ..file_ops.filename_generator import FilenameGenerator
from ..scoring.idf_calculator import IDFCalculator

try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


    class tqdm:
        def __init__(self, iterable=None, total=None, desc=None, **kwargs):
            self.iterable = iterable or []
            self.total = total or len(self.iterable)
            self.desc = desc
            self.n = 0

        def __iter__(self):
            for item in self.iterable:
                yield item
                self.update(1)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def update(self, n=1):
            self.n += n
            if self.total and self.n % max(1, self.total // 20) == 0:
                percent = (self.n / self.total) * 100
                print(f"Progress: {self.n}/{self.total} ({percent:.1f}%)")

        def set_description(self, desc):
            pass

        def set_postfix(self, postfix_dict):
            pass


class ChessFileRenamer:
    """
    Main orchestrator for chess file analysis and renaming operations.

    This class coordinates the complete workflow:
    1. File discovery and validation
    2. Batch processing with the sophisticated analysis pipeline
    3. Quality-based filename generation
    4. Conflict resolution
    5. File organization and renaming
    6. Progress tracking and reporting

    The orchestrator ensures that GM-level instructional content achieves
    the target EVS scores of 85+ through proper integration of all analysis
    components without shortcuts or architectural violations.
    """

    def __init__(self, config: RenameConfig):
        self.config = config
        self.logger = self._setup_logging()

        # Initialize core components
        self.db = DatabaseManager(config.database_path)
        self.file_processor = FileProcessor(config)
        self.filename_generator = FilenameGenerator(config)

        # Statistics tracking
        self.stats = {
            'files_discovered': 0,
            'files_analyzed': 0,
            'files_renamed': 0,
            'files_failed': 0,
            'files_skipped': 0,
            'tier_1_count': 0,
            'tier_2_count': 0,
            'tier_3_count': 0,
            'processing_start_time': None,
            'processing_end_time': None
        }

        # Session management
        self.session_id = f"chess_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.logger.info(f"Chess file renamer initialized - Session: {self.session_id}")

    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logger
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, self.config.log_level))

        # Prevent duplicate handlers
        if logger.handlers:
            return logger

        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )

        # File handler
        log_file = Path('chess_renaming.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.config.log_level))
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        return logger

    def run(self):
        """
        Main execution method with comprehensive workflow orchestration.

        This implements the complete processing pipeline using the sophisticated
        analysis architecture to properly evaluate chess content and achieve
        target EVS scores for instructional material.
        """
        try:
            self.stats['processing_start_time'] = time.time()
            self.logger.info("Starting Chess File Processing System v5.1")

            # Create processing session
            self._create_processing_session()

            # Step 1: Create backup if enabled
            if self.config.backup_enabled:
                self._create_backup()

            # Step 2: Discover and validate files
            discovered_files = self._discover_files()
            if not discovered_files:
                self.logger.warning("No chess files discovered")
                return

            # Step 3: Calculate IDF weights if beneficial
            self._calculate_idf_weights_if_needed(discovered_files)

            # Step 4: Process files in batches using sophisticated analysis
            self._process_files_in_batches(discovered_files)

            # Step 5: Resolve conflicts and optimize naming
            self._resolve_conflicts_and_optimize()

            # Step 6: Execute renaming operations
            self._execute_renaming_operations()

            # Step 7: Validate results
            self._validate_results()

            # Step 8: Generate comprehensive report
            self._generate_final_report()

            self.stats['processing_end_time'] = time.time()
            self.logger.info("Chess file processing completed successfully")

        except KeyboardInterrupt:
            self.logger.info("Processing interrupted by user - saving progress")
            self._handle_interruption()

        except Exception as e:
            self.logger.error(f"Fatal error in processing pipeline: {e}")
            self.logger.error(traceback.format_exc())
            self._handle_processing_failure(e)
            raise

        finally:
            self._cleanup_and_finalize()

    def _discover_files(self) -> List[str]:
        """
        Discover chess files with comprehensive filtering and validation.

        Returns:
            List of validated chess file paths
        """
        self.logger.info(f"Discovering chess files in {self.config.source_directory}")

        source_path = Path(self.config.source_directory)
        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {self.config.source_directory}")

        discovered_files = []

        # First pass: count total files for progress tracking
        print("Scanning directory structure...")
        total_files = sum(len(files) for _, _, files in os.walk(source_path))

        # Second pass: filter and validate chess files
        with tqdm(total=total_files, desc="🔍 Discovering chess files",
                  unit="files", disable=not TQDM_AVAILABLE) as pbar:

            for root, dirs, files in os.walk(source_path):
                for file in files:
                    pbar.update(1)

                    file_path = Path(root) / file

                    # Check file extension
                    if file_path.suffix.lower() not in FileTypes.CHESS_EXTENSIONS:
                        continue

                    # Check minimum file size
                    try:
                        if file_path.stat().st_size < FileTypes.MIN_FILE_SIZE:
                            continue
                    except (OSError, IOError):
                        continue

                    # Validate file accessibility
                    if not os.access(file_path, os.R_OK):
                        self.logger.warning(f"File not readable: {file_path}")
                        continue

                    discovered_files.append(str(file_path))

                    # Update progress description periodically
                    if len(discovered_files) % 100 == 0:
                        pbar.set_description(f"🔍 Found {len(discovered_files)} chess files")

        self.stats['files_discovered'] = len(discovered_files)
        self.logger.info(f"Discovery complete: {len(discovered_files)} chess files found")

        return discovered_files

    def _calculate_idf_weights_if_needed(self, file_paths: List[str]):
        """
        Calculate IDF weights if beneficial for the corpus size.

        IDF weighting improves semantic analysis for larger collections
        by identifying rare vs common chess terms.
        """
        # Only calculate IDF for larger collections where it's beneficial
        if len(file_paths) < 100:
            self.logger.info("Skipping IDF calculation for small collection")
            return

        self.logger.info("Calculating IDF weights for enhanced semantic analysis")

        # Sample documents for IDF calculation (don't need all for good estimates)
        import random
        sample_size = min(500, len(file_paths))
        sample_files = random.sample(file_paths, sample_size)

        # Extract text from sample files
        documents = []

        with tqdm(sample_files, desc="📚 Reading sample files for IDF calculation",
                  unit="files", disable=not TQDM_AVAILABLE) as pbar:

            for file_path in sample_files:
                try:
                    text_content = self.file_processor.text_extractor.extract_text(file_path)
                    if text_content.strip():
                        documents.append(text_content)

                    pbar.set_postfix({'Documents': len(documents)})

                except Exception as e:
                    self.logger.debug(f"Failed to read sample file {file_path}: {e}")
                    continue

        if len(documents) >= 50:  # Minimum for meaningful IDF calculation
            # Calculate IDF weights
            idf_calculator = IDFCalculator()
            idf_weights = idf_calculator.calculate_corpus_idf(documents)

            # Save for future use
            idf_calculator.save_idf_weights(idf_weights, "chess_idf_weights.json")

            # Apply to file processor for enhanced analysis
            self.file_processor.set_idf_weights(idf_weights)

            self.logger.info(f"IDF weights calculated and applied: {idf_weights.vocabulary_size} terms")
        else:
            self.logger.warning("Insufficient documents for IDF calculation")

    def _process_files_in_batches(self, file_paths: List[str]):
        """
        Process files in batches using the sophisticated analysis pipeline.

        This method orchestrates the complete analysis workflow that should
        identify GM instructional content and assign appropriate EVS scores.
        """
        batch_size = self.config.batch_size
        total_batches = (len(file_paths) + batch_size - 1) // batch_size

        self.logger.info(f"Processing {len(file_paths)} files in {total_batches} batches")

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(file_paths))
            batch_files = file_paths[start_idx:end_idx]

            print(f"\n--- Processing Batch {batch_num + 1}/{total_batches} ---")
            self.logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_files)} files)")

            self._process_batch(batch_files, batch_num + 1, total_batches)

            # Update session progress
            self._update_session_progress()

    def _process_batch(self, file_paths: List[str], batch_num: int, total_batches: int):
        """
        Process a single batch of files with progress tracking.

        This uses either single-threaded or multi-threaded processing based
        on configuration, maintaining the sophisticated analysis pipeline.
        """
        if self.config.max_workers == 1:
            self._process_batch_single_threaded(file_paths, batch_num, total_batches)
        else:
            self._process_batch_multi_threaded(file_paths, batch_num, total_batches)

    def _process_batch_single_threaded(self, file_paths: List[str], batch_num: int, total_batches: int):
        """Single-threaded batch processing with detailed progress tracking"""
        with tqdm(total=len(file_paths), desc=f"🔬 Analyzing batch {batch_num}/{total_batches}",
                  unit="files", disable=not TQDM_AVAILABLE) as pbar:

            for i, file_path in enumerate(file_paths):
                try:
                    # Update progress description with current file
                    filename = Path(file_path).name
                    display_name = filename[:35] + "..." if len(filename) > 35 else filename
                    pbar.set_description(f"🔬 Analyzing: {display_name}")

                    # Perform complete analysis using sophisticated pipeline
                    record = self.file_processor.analyze_file(file_path)

                    # Store results in database
                    self.db.insert_file_record(record)

                    # Update statistics based on results
                    self._update_processing_stats(record)

                    # Update progress display
                    pbar.set_postfix({
                        'EVS': f"{record.evs_score}",
                        'Quality': f"{record.content_quality:.2f}",
                        'Tier': QualityTier.classify_evs(record.evs_score),
                        'Success': f"{self.stats['files_analyzed']}/{self.stats['files_analyzed'] + self.stats['files_failed']}"
                    })

                except Exception as e:
                    self.logger.error(f"Failed to process {file_path}: {e}")
                    self.stats['files_failed'] += 1

                    pbar.set_postfix({
                        'Status': 'Failed',
                        'Success': f"{self.stats['files_analyzed']}/{self.stats['files_analyzed'] + self.stats['files_failed']}"
                    })

                pbar.update(1)

    def _process_batch_multi_threaded(self, file_paths: List[str], batch_num: int, total_batches: int):
        """Multi-threaded batch processing with progress tracking"""
        print(f"Using {self.config.max_workers} workers for parallel processing...")

        successful = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.file_processor.analyze_file, file_path): file_path
                for file_path in file_paths
            }

            # Process results with progress tracking
            with tqdm(total=len(file_paths), desc=f"🔬 Parallel analysis batch {batch_num}/{total_batches}",
                      unit="files", disable=not TQDM_AVAILABLE) as pbar:

                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]

                    try:
                        record = future.result()

                        # Store results
                        self.db.insert_file_record(record)
                        self._update_processing_stats(record)

                        successful += 1

                        pbar.set_postfix({
                            'Success': successful,
                            'Failed': failed,
                            'Rate': f"{successful / (successful + failed) * 100:.1f}%" if (
                                                                                                      successful + failed) > 0 else "0%"
                        })

                    except Exception as e:
                        self.logger.error(f"Failed to process {file_path}: {e}")
                        failed += 1
                        self.stats['files_failed'] += 1

                        pbar.set_postfix({
                            'Success': successful,
                            'Failed': failed,
                            'Rate': f"{successful / (successful + failed) * 100:.1f}%" if (
                                                                                                      successful + failed) > 0 else "0%"
                        })

                    pbar.update(1)

        self.logger.info(f"Batch {batch_num} complete: {successful} analyzed, {failed} failed")

    def _update_processing_stats(self, record: FileRecord):
        """Update processing statistics based on analysis results"""
        if record.status == "analyzed":
            self.stats['files_analyzed'] += 1

            # Update tier counts
            tier = QualityTier.classify_evs(record.evs_score)
            if tier == "TIER_1":
                self.stats['tier_1_count'] += 1
            elif tier == "TIER_2":
                self.stats['tier_2_count'] += 1
            elif tier == "TIER_3":
                self.stats['tier_3_count'] += 1
        else:
            self.stats['files_failed'] += 1

    def _resolve_conflicts_and_optimize(self):
        """
        Resolve filename conflicts and optimize naming strategies.

        This step ensures unique filenames while preserving quality-based naming.
        """
        print("\n🔧 Resolving filename conflicts and optimizing names...")

        # Generate filenames for all analyzed files
        self._generate_filenames()

        # Resolve conflicts
        conflicts_resolved = self.db.resolve_filename_conflicts()

        if conflicts_resolved > 0:
            self.logger.info(f"Resolved {conflicts_resolved} filename conflicts")
        else:
            self.logger.info("No filename conflicts found")

    def _generate_filenames(self):
        """Generate filenames for all analyzed files"""
        analyzed_records = self.db.get_file_records(status="analyzed")

        if not analyzed_records:
            self.logger.warning("No analyzed files found for filename generation")
            return

        self.logger.info(f"Generating filenames for {len(analyzed_records)} files")

        with tqdm(analyzed_records, desc="🏷️ Generating filenames",
                  unit="files", disable=not TQDM_AVAILABLE) as pbar:

            for record in analyzed_records:
                try:
                    # Reconstruct semantic analysis result for filename generation
                    semantic_result = self._reconstruct_semantic_result(record)

                    # Generate filename using sophisticated analysis results
                    new_filename, target_directory = self.filename_generator.generate_filename(
                        semantic_result, record.original_path, record.content_hash
                    )

                    # Update record with generated filename
                    record.new_filename = new_filename
                    record.new_directory = target_directory
                    self.db.insert_file_record(record)

                    pbar.set_postfix({'Generated': pbar.n + 1})

                except Exception as e:
                    self.logger.error(f"Filename generation failed for {record.original_path}: {e}")
                    continue

    def _execute_renaming_operations(self):
        """Execute file renaming with progress tracking and validation"""
        if self.config.dry_run:
            self.logger.info("DRY RUN: Would rename files, but dry_run=True")
            self._preview_renaming_operations()
            return

        print("\n📁 Executing file renaming operations...")

        # Get files ready for renaming
        records = self.db.get_file_records(status="analyzed")

        if not records:
            self.logger.warning("No files available for renaming")
            return

        rollback_data = []
        successful_renames = 0

        with tqdm(total=len(records), desc="📁 Renaming files",
                  unit="files", disable=not TQDM_AVAILABLE) as pbar:

            for record in records:
                try:
                    if not record.new_filename:
                        self.logger.warning(f"No new filename for {record.original_path}")
                        pbar.update(1)
                        continue

                    original_path = Path(record.original_path)

                    # Update progress description
                    display_name = original_path.name[:30] + "..." if len(
                        original_path.name) > 30 else original_path.name
                    pbar.set_description(f"📁 Renaming: {display_name}")

                    # Determine target path
                    target_path = self._determine_target_path(record, original_path)

                    # Check for conflicts
                    if target_path.exists() and target_path != original_path:
                        self.logger.warning(f"Target file already exists: {target_path}")
                        self.db.update_status(record.original_path, "skipped", "Target file exists")
                        self.stats['files_skipped'] += 1
                        pbar.update(1)
                        continue

                    # Perform the rename
                    if original_path != target_path:
                        # Ensure target directory exists
                        target_path.parent.mkdir(parents=True, exist_ok=True)

                        # Execute rename
                        original_path.rename(target_path)

                        # Record for rollback
                        rollback_data.append({
                            'new_path': str(target_path),
                            'original_path': str(original_path)
                        })

                        successful_renames += 1
                        self.logger.debug(f"Renamed: {original_path.name} -> {record.new_filename}")

                    # Update database status
                    self.db.update_status(record.original_path, "renamed")
                    self.stats['files_renamed'] += 1

                    # Update progress
                    pbar.set_postfix({
                        'Renamed': successful_renames,
                        'Rate': f"{successful_renames / (pbar.n + 1) * 100:.1f}%"
                    })

                except Exception as e:
                    self.logger.error(f"Failed to rename {record.original_path}: {e}")
                    self.db.update_status(record.original_path, "failed", str(e))
                    self.stats['files_failed'] += 1

                pbar.update(1)

        # Save rollback data
        if rollback_data:
            with open(self.config.rollback_file, 'w') as f:
                json.dump(rollback_data, f, indent=2)
            self.logger.info(f"Rollback data saved to {self.config.rollback_file}")

        self.logger.info(f"Rename operation complete: {successful_renames} files renamed")

    def _preview_renaming_operations(self):
        """Preview renaming operations for dry run"""
        records = self.db.get_file_records(status="analyzed", limit=20)

        print("\n--- RENAMING PREVIEW (DRY RUN) ---")
        for record in records:
            if record.new_filename:
                original_name = Path(record.original_path).name
                target_dir = record.new_directory or "Same directory"
                evs_score = record.evs_score
                tier = QualityTier.classify_evs(evs_score)

                print(f"  {original_name}")
                print(f"    -> {record.new_filename}")
                print(f"    -> Directory: {target_dir}")
                print(f"    -> EVS: {evs_score} ({tier})")
                print()

        if len(records) == 20:
            print("  ... (showing first 20 files only)")

    def _validate_results(self):
        """Validate renamed files and analysis results"""
        if not self.config.validate_after_rename or self.config.dry_run:
            return

        print("\n✅ Validating results...")

        records = self.db.get_file_records(status="renamed")
        validation_errors = 0

        if records:
            with tqdm(records, desc="✅ Validating renamed files",
                      unit="files", disable=not TQDM_AVAILABLE) as pbar:

                for record in records:
                    try:
                        # Construct expected new path
                        target_path = self._determine_target_path(record, Path(record.original_path))

                        # Check if file exists and has correct size
                        if not target_path.exists():
                            self.logger.error(f"Renamed file missing: {target_path}")
                            validation_errors += 1
                        elif target_path.stat().st_size != record.file_size:
                            self.logger.error(f"File size mismatch: {target_path}")
                            validation_errors += 1

                        pbar.set_postfix({'Errors': validation_errors})

                    except Exception as e:
                        self.logger.error(f"Validation failed for {record.original_path}: {e}")
                        validation_errors += 1

        if validation_errors == 0:
            self.logger.info("All renamed files validated successfully")
        else:
            self.logger.warning(f"Validation found {validation_errors} errors")

    def _generate_final_report(self):
        """Generate comprehensive processing report"""
        print("\n📊 Generating final report...")

        # Get comprehensive statistics
        db_stats = self.db.get_processing_statistics()
        processing_time = self.stats.get('processing_end_time', time.time()) - self.stats['processing_start_time']

        # Generate report
        report = self._create_comprehensive_report(db_stats, processing_time)

        # Save report to file
        report_path = 'chess_processing_report.txt'
        with open(report_path, 'w') as f:
            f.write(report)

        # Display key statistics
        print("\n" + "=" * 60)
        print("CHESS FILE PROCESSING COMPLETE")
        print("=" * 60)
        print(f"Files Discovered: {self.stats['files_discovered']}")
        print(f"Files Analyzed: {self.stats['files_analyzed']}")
        print(f"Files Renamed: {self.stats['files_renamed']}")
        print(f"Processing Time: {processing_time / 60:.1f} minutes")
        print(f"Quality Distribution:")
        print(f"  TIER 1 (EVS 85+): {self.stats['tier_1_count']}")
        print(f"  TIER 2 (EVS 80-84): {self.stats['tier_2_count']}")
        print(f"  TIER 3 (EVS 70-79): {self.stats['tier_3_count']}")
        print(f"Report saved to: {report_path}")
        print("=" * 60)

        self.logger.info(f"Final report generated: {report_path}")

    def _create_comprehensive_report(self, db_stats: Dict, processing_time: float) -> str:
        """Create detailed processing report"""
        # Get top quality files for report
        top_files = self.db.get_top_quality_files(20)

        report = f"""
CHESS FILE PROCESSING REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Session ID: {self.session_id}

PROCESSING SUMMARY:
==================
Total Processing Time: {processing_time / 60:.1f} minutes
Files Discovered: {self.stats['files_discovered']}
Files Successfully Analyzed: {self.stats['files_analyzed']}
Files Renamed: {self.stats['files_renamed']}
Files Failed: {self.stats['files_failed']}
Files Skipped: {self.stats['files_skipped']}

QUALITY DISTRIBUTION:
====================
TIER 1 (EVS 85+): {self.stats['tier_1_count']} files
TIER 2 (EVS 80-84): {self.stats['tier_2_count']} files  
TIER 3 (EVS 70-79): {self.stats['tier_3_count']} files
Below Threshold: {self.stats['files_analyzed'] - self.stats['tier_1_count'] - self.stats['tier_2_count'] - self.stats['tier_3_count']} files

RAG SUITABILITY:
===============
Files meeting RAG threshold (EVS 70+): {self.stats['tier_1_count'] + self.stats['tier_2_count'] + self.stats['tier_3_count']}
RAG inclusion rate: {((self.stats['tier_1_count'] + self.stats['tier_2_count'] + self.stats['tier_3_count']) / max(self.stats['files_analyzed'], 1) * 100):.1f}%

TOP 20 HIGHEST QUALITY FILES:
=============================
"""

        for i, file_info in enumerate(top_files, 1):
            report += f"{i:2d}. {file_info['file_name']}\n"
            report += f"    EVS: {file_info['evs_score']}, Quality: {file_info['content_quality']:.3f}\n"
            report += f"    Type: {file_info['game_type']}, Tier: {file_info['quality_tier']}\n"
            if file_info['detected_openings']:
                report += f"    Openings: {', '.join(file_info['detected_openings'])}\n"
            report += "\n"

        report += f"""
CONFIGURATION:
=============
Source Directory: {self.config.source_directory}
Output Directory: {self.config.output_directory or 'In-place renaming'}
Dry Run: {self.config.dry_run}
Backup Enabled: {self.config.backup_enabled}
Directory Organization: {self.config.enable_directory_organization}
Max Workers: {self.config.max_workers}
Batch Size: {self.config.batch_size}

DATABASE STATISTICS:
===================
{json.dumps(db_stats, indent=2)}

PERFORMANCE METRICS:
===================
Average Processing Time per File: {processing_time / max(self.stats['files_analyzed'], 1):.2f} seconds
Files per Minute: {self.stats['files_analyzed'] / (processing_time / 60):.1f}
Success Rate: {(self.stats['files_analyzed'] / max(self.stats['files_discovered'], 1) * 100):.1f}%
"""

        return report

    # Additional helper methods
    def _create_processing_session(self):
        """Create processing session for tracking"""
        config_data = {
            'source_directory': self.config.source_directory,
            'batch_size': self.config.batch_size,
            'max_workers': self.config.max_workers,
            'dry_run': self.config.dry_run
        }

        self.db.create_processing_session(
            self.session_id,
            0,  # Will be updated after discovery
            config_data
        )

    def _update_session_progress(self):
        """Update processing session progress"""
        self.db.update_processing_session(
            self.session_id,
            self.stats['files_analyzed'],
            self.stats['files_failed']
        )

    def _create_backup(self):
        """Create backup of source directory if enabled"""
        if not self.config.backup_enabled:
            return

        backup_dir = self.config.backup_directory
        if not backup_dir:
            backup_dir = f"{self.config.source_directory}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.logger.info(f"Creating backup at {backup_dir}")

        try:
            print("Creating backup...")
            shutil.copytree(self.config.source_directory, backup_dir)
            self.logger.info(f"Backup created successfully at {backup_dir}")
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            if not self.config.dry_run:
                raise

    def _determine_target_path(self, record: FileRecord, original_path: Path) -> Path:
        """Determine target path for renamed file"""
        if self.config.output_directory:
            target_base = Path(self.config.output_directory)
        else:
            target_base = original_path.parent

        if record.new_directory:
            target_dir = target_base / record.new_directory
        else:
            target_dir = target_base

        return target_dir / record.new_filename

    def _reconstruct_semantic_result(self, record: FileRecord):
        """Reconstruct semantic analysis result from database record"""
        # This is a simplified reconstruction for filename generation
        # In practice, you might want to store more complete results
        from ..core.models import SemanticAnalysisResult, PGNAnalysisResult

        pgn_analysis = PGNAnalysisResult(
            evs_score=record.evs_score,
            structure_score=record.analysis_data.get('pgn_structure_score', 0),
            annotation_richness=record.analysis_data.get('pgn_annotation_richness', 0),
            humanness_score=record.analysis_data.get('pgn_humanness_score', 0),
            educational_context=record.analysis_data.get('pgn_educational_context', 0),
            game_type=record.game_type,
            total_moves=record.analysis_data.get('pgn_total_moves', 0),
            annotation_density=record.analysis_data.get('pgn_annotation_density', 0),
            has_headers=False,
            has_variations=False,
            famous_game_detected=record.analysis_data.get('famous_game_detected', False),
            educational_cues=record.analysis_data.get('pgn_educational_cues', [])
        )

        semantic_result = SemanticAnalysisResult(
            content_quality_score=record.content_quality,
            chess_domain_relevance=record.analysis_data.get('domain_relevance', 0),
            instructional_value=record.analysis_data.get('instructional_value', 0),
            concept_density=record.analysis_data.get('concept_density', 0),
            explanation_clarity=record.analysis_data.get('explanation_clarity', 0),
            top_concepts=record.analysis_data.get('top_concepts', []),
            semantic_categories={},
            publication_year_score=record.analysis_data.get('publication_year_score', 0),
            comprehensive_concept_score=record.analysis_data.get('comprehensive_concept_score', 0),
            detected_openings=record.analysis_data.get('detected_openings', []),
            detected_players=record.analysis_data.get('detected_players', []),
            detected_books=record.analysis_data.get('detected_books', []),
            pgn_analysis=pgn_analysis,
            pgn_integration_score=record.analysis_data.get('pgn_integration_score', 0)
        )

        return semantic_result

    def _handle_interruption(self):
        """Handle user interruption gracefully"""
        self.db.complete_processing_session(self.session_id, "interrupted")
        self.logger.info("Processing session marked as interrupted")

    def _handle_processing_failure(self, error: Exception):
        """Handle processing failure"""
        self.db.complete_processing_session(self.session_id, "failed")
        self.logger.error(f"Processing session marked as failed: {error}")

    def _cleanup_and_finalize(self):
        """Cleanup and finalize processing session"""
        if hasattr(self, 'session_id'):
            self.db.complete_processing_session(self.session_id, "completed")