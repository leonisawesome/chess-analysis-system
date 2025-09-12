"""
Database Manager for Chess File Operations Tracking.

This module manages SQLite database operations for tracking file analysis,
renaming operations, and quality statistics. It provides persistence for
the complete analysis pipeline and enables resumable operations.
"""

import logging
import sqlite3
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from ..core.models import FileRecord, ProcessingStatus


class DatabaseManager:
    """
    Manage SQLite database for tracking file operations and analysis results.

    The database stores complete analysis results, processing status, and metadata
    to enable resumable operations, conflict resolution, and quality reporting.

    Key features:
    - Complete file operation tracking
    - Analysis result persistence
    - Quality distribution statistics
    - Resumable processing support
    - Conflict detection and resolution
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()

    def _init_database(self):
        """Initialize database schema with complete tracking capabilities"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Main file operations table
                conn.execute('''
                             CREATE TABLE IF NOT EXISTS file_operations
                             (
                                 id
                                 INTEGER
                                 PRIMARY
                                 KEY
                                 AUTOINCREMENT,
                                 original_path
                                 TEXT
                                 UNIQUE
                                 NOT
                                 NULL,
                                 new_filename
                                 TEXT,
                                 new_directory
                                 TEXT,
                                 content_hash
                                 TEXT,
                                 file_size
                                 INTEGER,
                                 modification_time
                                 REAL,
                                 analysis_data
                                 TEXT, -- JSON stored analysis results
                                 evs_score
                                 INTEGER,
                                 content_quality
                                 REAL,
                                 game_type
                                 TEXT,
                                 status
                                 TEXT,
                                 error_message
                                 TEXT,
                                 processing_time
                                 REAL,
                                 timestamp
                                 TEXT,
                                 -- Additional metadata
                                 instructional_value
                                 REAL,
                                 domain_relevance
                                 REAL,
                                 rag_fitness
                                 REAL,
                                 quality_tier
                                 TEXT,
                                 -- Constraints
                                 UNIQUE
                             (
                                 content_hash,
                                 new_filename
                             )
                                 )
                             ''')

                # Quality statistics table for reporting
                conn.execute('''
                             CREATE TABLE IF NOT EXISTS quality_statistics
                             (
                                 id
                                 INTEGER
                                 PRIMARY
                                 KEY
                                 AUTOINCREMENT,
                                 calculation_date
                                 TEXT,
                                 total_files
                                 INTEGER,
                                 tier_1_count
                                 INTEGER,
                                 tier_2_count
                                 INTEGER,
                                 tier_3_count
                                 INTEGER,
                                 below_threshold_count
                                 INTEGER,
                                 avg_evs_score
                                 REAL,
                                 avg_instructional_value
                                 REAL,
                                 avg_content_quality
                                 REAL,
                                 top_content_types
                                 TEXT, -- JSON
                                 processing_summary
                                 TEXT  -- JSON
                             )
                             ''')

                # Processing sessions table for resumable operations
                conn.execute('''
                             CREATE TABLE IF NOT EXISTS processing_sessions
                             (
                                 session_id
                                 TEXT
                                 PRIMARY
                                 KEY,
                                 start_time
                                 TEXT,
                                 end_time
                                 TEXT,
                                 total_files
                                 INTEGER,
                                 processed_files
                                 INTEGER,
                                 failed_files
                                 INTEGER,
                                 config_data
                                 TEXT, -- JSON
                                 status
                                 TEXT  -- running, completed, failed, interrupted
                             )
                             ''')

                # Performance indexes
                conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON file_operations(status)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_hash ON file_operations(content_hash)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_evs ON file_operations(evs_score)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_quality_tier ON file_operations(quality_tier)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_instructional ON file_operations(instructional_value)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON file_operations(timestamp)')

            self.logger.info(f"Database initialized at {self.db_path}")

        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    def insert_file_record(self, record: FileRecord):
        """
        Insert or update file record with complete analysis data.

        Args:
            record: FileRecord with complete analysis results
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Extract additional fields for easier querying
                instructional_value = record.analysis_data.get('instructional_value', 0.0)
                domain_relevance = record.analysis_data.get('domain_relevance', 0.0)
                rag_fitness = record.analysis_data.get('rag_overall_fitness', 0.0)

                # Determine quality tier
                from ..core.models import QualityTier
                quality_tier = QualityTier.classify_evs(record.evs_score)

                conn.execute('''
                    INSERT OR REPLACE INTO file_operations 
                    (original_path, new_filename, new_directory, content_hash, file_size,
                     modification_time, analysis_data, evs_score, content_quality, 
                     game_type, status, error_message, processing_time, timestamp,
                     instructional_value, domain_relevance, rag_fitness, quality_tier)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.original_path, record.new_filename, record.new_directory,
                    record.content_hash, record.file_size, record.modification_time,
                    json.dumps(record.analysis_data), record.evs_score, record.content_quality,
                    record.game_type, record.status, record.error_message,
                    record.processing_time, record.timestamp,
                    instructional_value, domain_relevance, rag_fitness, quality_tier
                ))

        except sqlite3.Error as e:
            self.logger.error(f"Database insert failed for {record.original_path}: {e}")
            raise

    def get_file_records(self, status: Optional[str] = None,
                         quality_tier: Optional[str] = None,
                         limit: Optional[int] = None,
                         order_by: str = "evs_score DESC") -> List[FileRecord]:
        """
        Retrieve file records with flexible filtering.

        Args:
            status: Filter by processing status
            quality_tier: Filter by quality tier (TIER_1, TIER_2, etc.)
            limit: Maximum number of records to return
            order_by: SQL ORDER BY clause

        Returns:
            List of FileRecord objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                query = "SELECT * FROM file_operations WHERE 1=1"
                params = []

                if status:
                    query += " AND status = ?"
                    params.append(status)

                if quality_tier:
                    query += " AND quality_tier = ?"
                    params.append(quality_tier)

                query += f" ORDER BY {order_by}"

                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                cursor = conn.execute(query, params)
                records = []

                for row in cursor:
                    analysis_data = json.loads(row['analysis_data']) if row['analysis_data'] else {}

                    record = FileRecord(
                        id=row['id'],
                        original_path=row['original_path'],
                        new_filename=row['new_filename'] or "",
                        new_directory=row['new_directory'] or "",
                        content_hash=row['content_hash'] or "",
                        file_size=row['file_size'] or 0,
                        modification_time=row['modification_time'] or 0.0,
                        analysis_data=analysis_data,
                        evs_score=row['evs_score'] or 0,
                        content_quality=row['content_quality'] or 0.0,
                        game_type=row['game_type'] or "",
                        status=row['status'] or "",
                        error_message=row['error_message'] or "",
                        processing_time=row['processing_time'] or 0.0,
                        timestamp=row['timestamp'] or ""
                    )
                    records.append(record)

                return records

        except Exception as e:
            self.logger.error(f"Failed to retrieve file records: {e}")
            return []

    def update_status(self, file_path: str, status: str, error_message: str = ""):
        """
        Update file processing status.

        Args:
            file_path: Path to the file
            status: New processing status
            error_message: Optional error message
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                             UPDATE file_operations
                             SET status        = ?,
                                 error_message = ?,
                                 timestamp     = ?
                             WHERE original_path = ?
                             ''', (status, error_message, datetime.now().isoformat(), file_path))

        except Exception as e:
            self.logger.error(f"Failed to update status for {file_path}: {e}")

    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive processing statistics.

        Returns:
            Dictionary with detailed statistics about processed files
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}

                # Basic counts by status
                cursor = conn.execute('''
                                      SELECT status, COUNT(*) as count
                                      FROM file_operations
                                      GROUP BY status
                                      ''')
                stats['status_distribution'] = dict(cursor.fetchall())

                # Quality tier distribution
                cursor = conn.execute('''
                                      SELECT quality_tier, COUNT(*) as count
                                      FROM file_operations
                                      WHERE status = 'analyzed'
                                      GROUP BY quality_tier
                                      ''')
                stats['quality_distribution'] = dict(cursor.fetchall())

                # EVS score statistics
                cursor = conn.execute('''
                                      SELECT COUNT(*)                 as total_analyzed,
                                             AVG(evs_score)           as avg_evs,
                                             MIN(evs_score)           as min_evs,
                                             MAX(evs_score)           as max_evs,
                                             AVG(content_quality)     as avg_quality,
                                             AVG(instructional_value) as avg_instructional,
                                             AVG(rag_fitness)         as avg_rag_fitness
                                      FROM file_operations
                                      WHERE status = 'analyzed'
                                      ''')
                evs_stats = cursor.fetchone()
                if evs_stats:
                    stats['score_statistics'] = {
                        'total_analyzed': evs_stats[0],
                        'avg_evs_score': evs_stats[1] or 0,
                        'min_evs_score': evs_stats[2] or 0,
                        'max_evs_score': evs_stats[3] or 0,
                        'avg_content_quality': evs_stats[4] or 0,
                        'avg_instructional_value': evs_stats[5] or 0,
                        'avg_rag_fitness': evs_stats[6] or 0
                    }

                # Content type distribution
                cursor = conn.execute('''
                                      SELECT game_type, COUNT(*) as count
                                      FROM file_operations
                                      WHERE status = 'analyzed'
                                      GROUP BY game_type
                                      ORDER BY count DESC
                                      ''')
                stats['content_type_distribution'] = dict(cursor.fetchall())

                # High-quality content analysis (EVS >= 70)
                cursor = conn.execute('''
                                      SELECT COUNT(*) as high_quality_count
                                      FROM file_operations
                                      WHERE status = 'analyzed'
                                        AND evs_score >= 70
                                      ''')
                high_quality_count = cursor.fetchone()[0]

                cursor = conn.execute('''
                                      SELECT COUNT(*) as total_count
                                      FROM file_operations
                                      WHERE status = 'analyzed'
                                      ''')
                total_count = cursor.fetchone()[0]

                if total_count > 0:
                    stats['rag_suitability'] = {
                        'high_quality_count': high_quality_count,
                        'total_analyzed': total_count,
                        'rag_inclusion_rate': high_quality_count / total_count
                    }

                # Processing performance
                cursor = conn.execute('''
                                      SELECT AVG(processing_time) as avg_processing_time,
                                             SUM(processing_time) as total_processing_time
                                      FROM file_operations
                                      WHERE processing_time > 0
                                      ''')
                perf_stats = cursor.fetchone()
                if perf_stats:
                    stats['performance'] = {
                        'avg_processing_time': perf_stats[0] or 0,
                        'total_processing_time': perf_stats[1] or 0
                    }

                return stats

        except Exception as e:
            self.logger.error(f"Failed to get processing statistics: {e}")
            return {}

    def get_top_quality_files(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get top quality files by EVS score for reporting.

        Args:
            limit: Maximum number of files to return

        Returns:
            List of file information dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                cursor = conn.execute('''
                                      SELECT original_path,
                                             new_filename,
                                             evs_score,
                                             content_quality,
                                             instructional_value,
                                             game_type,
                                             quality_tier,
                                             analysis_data
                                      FROM file_operations
                                      WHERE status = 'analyzed'
                                      ORDER BY evs_score DESC, content_quality DESC LIMIT ?
                                      ''', (limit,))

                results = []
                for row in cursor:
                    analysis_data = json.loads(row['analysis_data']) if row['analysis_data'] else {}

                    # Extract key information for reporting
                    file_info = {
                        'file_name': Path(row['original_path']).name,
                        'new_filename': row['new_filename'],
                        'evs_score': row['evs_score'],
                        'content_quality': row['content_quality'],
                        'instructional_value': row['instructional_value'],
                        'game_type': row['game_type'],
                        'quality_tier': row['quality_tier'],
                        'detected_openings': analysis_data.get('detected_openings', [])[:3],
                        'detected_players': analysis_data.get('detected_players', [])[:3],
                        'detected_books': analysis_data.get('detected_books', [])[:3],
                        'top_concepts': analysis_data.get('top_concepts', [])[:5]
                    }
                    results.append(file_info)

                return results

        except Exception as e:
            self.logger.error(f"Failed to get top quality files: {e}")
            return []

    def find_duplicate_content(self) -> List[Dict[str, Any]]:
        """
        Find files with identical content hashes (duplicates).

        Returns:
            List of duplicate groups with file information
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Find content hashes that appear multiple times
                cursor = conn.execute('''
                                      SELECT content_hash, COUNT(*) as count
                                      FROM file_operations
                                      WHERE content_hash != ''
                                      GROUP BY content_hash
                                      HAVING count > 1
                                      ORDER BY count DESC
                                      ''')

                duplicate_groups = []

                for hash_row in cursor:
                    content_hash = hash_row['content_hash']

                    # Get all files with this hash
                    file_cursor = conn.execute('''
                                               SELECT original_path, evs_score, content_quality, file_size, game_type
                                               FROM file_operations
                                               WHERE content_hash = ?
                                               ORDER BY evs_score DESC
                                               ''', (content_hash,))

                    files = []
                    for file_row in file_cursor:
                        files.append({
                            'path': file_row['original_path'],
                            'name': Path(file_row['original_path']).name,
                            'evs_score': file_row['evs_score'],
                            'content_quality': file_row['content_quality'],
                            'file_size': file_row['file_size'],
                            'game_type': file_row['game_type']
                        })

                    duplicate_groups.append({
                        'content_hash': content_hash,
                        'file_count': len(files),
                        'files': files,
                        'best_quality': max(files, key=lambda x: x['evs_score']) if files else None
                    })

                return duplicate_groups

        except Exception as e:
            self.logger.error(f"Failed to find duplicate content: {e}")
            return []

    def resolve_filename_conflicts(self) -> int:
        """
        Resolve filename conflicts by modifying duplicate names.

        Returns:
            Number of conflicts resolved
        """
        try:
            conflicts_resolved = 0

            with sqlite3.connect(self.db_path) as conn:
                # Find filename conflicts
                cursor = conn.execute('''
                                      SELECT new_filename, COUNT(*) as count
                                      FROM file_operations
                                      WHERE new_filename != '' AND new_filename IS NOT NULL
                                      GROUP BY new_filename
                                      HAVING count > 1
                                      ''')

                for row in cursor:
                    conflicting_filename = row['new_filename']

                    # Get all records with this filename, ordered by quality
                    conflict_cursor = conn.execute('''
                                                   SELECT id, original_path, evs_score, content_quality, content_hash
                                                   FROM file_operations
                                                   WHERE new_filename = ?
                                                   ORDER BY evs_score DESC, content_quality DESC
                                                   ''', (conflicting_filename,))

                    conflicting_records = conflict_cursor.fetchall()

                    # Keep the best one as-is, modify others
                    for i, record in enumerate(conflicting_records[1:], 1):
                        # Generate new filename with differentiator
                        name_parts = Path(conflicting_filename)
                        stem = name_parts.stem
                        suffix = name_parts.suffix

                        if record[2] > 0:  # Has EVS score
                            new_name = f"{stem}_alt{i}_EVS{record[2]}{suffix}"
                        else:
                            new_name = f"{stem}_alt{i}_{record[4][:8]}{suffix}"

                        # Update the record
                        conn.execute('''
                                     UPDATE file_operations
                                     SET new_filename = ?
                                     WHERE id = ?
                                     ''', (new_name, record[0]))

                        conflicts_resolved += 1

            self.logger.info(f"Resolved {conflicts_resolved} filename conflicts")
            return conflicts_resolved

        except Exception as e:
            self.logger.error(f"Failed to resolve filename conflicts: {e}")
            return 0

    def create_processing_session(self, session_id: str, total_files: int, config_data: Dict) -> bool:
        """
        Create a new processing session for resumable operations.

        Args:
            session_id: Unique session identifier
            total_files: Total number of files to process
            config_data: Configuration dictionary

        Returns:
            True if session created successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                             INSERT INTO processing_sessions
                             (session_id, start_time, total_files, processed_files, failed_files, config_data, status)
                             VALUES (?, ?, ?, 0, 0, ?, 'running')
                             ''', (session_id, datetime.now().isoformat(), total_files, json.dumps(config_data)))

            self.logger.info(f"Created processing session: {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create processing session {session_id}: {e}")
            return False

    def update_processing_session(self, session_id: str, processed_files: int, failed_files: int):
        """Update processing session progress"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                             UPDATE processing_sessions
                             SET processed_files = ?,
                                 failed_files    = ?
                             WHERE session_id = ?
                             ''', (processed_files, failed_files, session_id))

        except Exception as e:
            self.logger.error(f"Failed to update processing session {session_id}: {e}")

    def complete_processing_session(self, session_id: str, status: str = "completed"):
        """Mark processing session as completed"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                             UPDATE processing_sessions
                             SET end_time = ?,
                                 status   = ?
                             WHERE session_id = ?
                             ''', (datetime.now().isoformat(), status, session_id))

        except Exception as e:
            self.logger.error(f"Failed to complete processing session {session_id}: {e}")

    def export_results(self, output_path: str, format: str = "csv") -> bool:
        """
        Export analysis results to external format.

        Args:
            output_path: Path for export file
            format: Export format ('csv', 'json')

        Returns:
            True if export successful
        """
        try:
            records = self.get_file_records(status="analyzed")

            if format.lower() == "csv":
                return self._export_csv(records, output_path)
            elif format.lower() == "json":
                return self._export_json(records, output_path)
            else:
                self.logger.error(f"Unsupported export format: {format}")
                return False

        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return False

    def _export_csv(self, records: List[FileRecord], output_path: str) -> bool:
        """Export records to CSV format"""
        import csv

        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'original_path', 'new_filename', 'evs_score', 'content_quality',
                    'instructional_value', 'domain_relevance', 'game_type', 'quality_tier',
                    'file_size', 'processing_time'
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for record in records:
                    from ..core.models import QualityTier

                    writer.writerow({
                        'original_path': record.original_path,
                        'new_filename': record.new_filename,
                        'evs_score': record.evs_score,
                        'content_quality': record.content_quality,
                        'instructional_value': record.analysis_data.get('instructional_value', 0),
                        'domain_relevance': record.analysis_data.get('domain_relevance', 0),
                        'game_type': record.game_type,
                        'quality_tier': QualityTier.classify_evs(record.evs_score),
                        'file_size': record.file_size,
                        'processing_time': record.processing_time
                    })

            self.logger.info(f"CSV export completed: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"CSV export failed: {e}")
            return False

    def _export_json(self, records: List[FileRecord], output_path: str) -> bool:
        """Export records to JSON format"""
        try:
            export_data = {
                'export_date': datetime.now().isoformat(),
                'total_records': len(records),
                'records': []
            }

            for record in records:
                from ..core.models import QualityTier

                record_data = {
                    'original_path': record.original_path,
                    'new_filename': record.new_filename,
                    'evs_score': record.evs_score,
                    'content_quality': record.content_quality,
                    'game_type': record.game_type,
                    'quality_tier': QualityTier.classify_evs(record.evs_score),
                    'file_size': record.file_size,
                    'processing_time': record.processing_time,
                    'analysis_summary': {
                        'instructional_value': record.analysis_data.get('instructional_value', 0),
                        'domain_relevance': record.analysis_data.get('domain_relevance', 0),
                        'detected_openings': record.analysis_data.get('detected_openings', [])[:5],
                        'detected_players': record.analysis_data.get('detected_players', [])[:5],
                        'top_concepts': record.analysis_data.get('top_concepts', [])[:10]
                    }
                }
                export_data['records'].append(record_data)

            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)

            self.logger.info(f"JSON export completed: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"JSON export failed: {e}")
            return False

    def cleanup_database(self, keep_days: int = 30):
        """
        Clean up old database entries and optimize storage.

        Args:
            keep_days: Number of days of records to keep
        """
        try:
            cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 3600)

            with sqlite3.connect(self.db_path) as conn:
                # Remove old failed records
                cursor = conn.execute('''
                                      DELETE
                                      FROM file_operations
                                      WHERE status = 'failed' AND timestamp < ?
                                      ''', (cutoff_date,))

                deleted_count = cursor.rowcount

                # Vacuum database to reclaim space
                conn.execute('VACUUM')

            self.logger.info(f"Database cleanup completed: {deleted_count} old records removed")

        except Exception as e:
            self.logger.error(f"Database cleanup failed: {e}")