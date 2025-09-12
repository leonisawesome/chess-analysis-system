"""
Quarantine Manager - Safe file deletion and recovery system.

This module provides a safe alternative to permanent file deletion by moving
low-quality files to quarantine locations with full recovery capabilities.
It maintains detailed manifests and provides automated cleanup options.

Key features:
- Safe file quarantine instead of permanent deletion
- Complete recovery manifests with metadata
- Automated old quarantine cleanup
- Progress tracking for large operations
- Cross-platform compatibility
"""

import logging
import json
import shutil
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from ..core.models import QuarantineManifest

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
            if desc:
                print(f"Starting: {desc}")

        def __iter__(self):
            for item in self.iterable:
                yield item
                self.update(1)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            if self.desc:
                print(f"Completed: {self.desc}")

        def update(self, n=1):
            self.n += n
            if self.total and self.n % max(1, self.total // 20) == 0:
                percent = (self.n / self.total) * 100
                print(f"Progress: {self.n}/{self.total} ({percent:.1f}%)")

        def set_description(self, desc):
            self.desc = desc

        def set_postfix(self, postfix_dict):
            pass


class QuarantineManager:
    """
    Manage quarantine operations for safe file deletion and recovery.

    The quarantine system provides a safe alternative to permanent file deletion.
    Files are moved to organized quarantine directories with detailed manifests
    that enable complete recovery of the original file structure.

    Features:
    - Preserves original directory structure in quarantine
    - Detailed manifest tracking for each quarantine session
    - Automated cleanup of old quarantines
    - Progress tracking for large operations
    - Complete recovery with original paths restored
    """

    def __init__(self, base_quarantine_dir: str = "chess_quarantine"):
        self.base_quarantine_dir = Path(base_quarantine_dir)
        self.logger = logging.getLogger(__name__)

        # Ensure base quarantine directory exists
        self.base_quarantine_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Quarantine manager initialized: {self.base_quarantine_dir}")

    def create_quarantine_session(self, deletion_threshold: int) -> str:
        """
        Create new quarantine session directory.

        Args:
            deletion_threshold: EVS threshold that triggered this quarantine

        Returns:
            Quarantine session ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_id = f"evs_below_{deletion_threshold}_{timestamp}"

        quarantine_path = self.base_quarantine_dir / quarantine_id
        quarantine_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (quarantine_path / "files").mkdir(exist_ok=True)
        (quarantine_path / "metadata").mkdir(exist_ok=True)

        self.logger.info(f"Created quarantine session: {quarantine_id}")
        return quarantine_id

    def move_files_to_quarantine(self, files_to_quarantine: List[Dict[str, Any]],
                                 quarantine_id: str, deletion_threshold: int) -> QuarantineManifest:
        """
        Move files to quarantine with detailed progress tracking.

        Args:
            files_to_quarantine: List of file dictionaries with metadata
            quarantine_id: Quarantine session identifier
            deletion_threshold: EVS threshold used for quarantine decision

        Returns:
            QuarantineManifest with complete operation details
        """
        quarantine_path = self.base_quarantine_dir / quarantine_id
        manifest_files = []
        total_size = 0
        moved_count = 0
        failed_moves = []

        self.logger.info(f"Moving {len(files_to_quarantine)} files to quarantine: {quarantine_id}")

        with tqdm(total=len(files_to_quarantine), desc="🗂️ Moving files to quarantine",
                  unit="files", disable=not TQDM_AVAILABLE) as pbar:

            for i, file_info in enumerate(files_to_quarantine):
                try:
                    source_path = Path(file_info['original_path'])
                    if not source_path.exists():
                        self.logger.warning(f"Source file not found: {source_path}")
                        failed_moves.append({
                            'path': str(source_path),
                            'error': 'File not found'
                        })
                        pbar.update(1)
                        continue

                    # Update progress description with current file
                    file_name = source_path.name
                    display_name = file_name[:30] + "..." if len(file_name) > 30 else file_name
                    pbar.set_description(f"🗂️ Moving: {display_name}")

                    # Preserve directory structure in quarantine
                    relative_path = self._get_relative_quarantine_path(source_path)
                    dest_path = quarantine_path / "files" / relative_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    # Get file size before moving
                    file_size = source_path.stat().st_size

                    # Move file to quarantine
                    shutil.move(str(source_path), str(dest_path))

                    # Record in manifest
                    manifest_entry = {
                        'original_path': str(source_path),
                        'quarantine_path': str(dest_path),
                        'relative_path': str(relative_path),
                        'evs_score': file_info.get('evs_score', 0),
                        'content_quality': file_info.get('content_quality', 0.0),
                        'game_type': file_info.get('game_type', 'unknown'),
                        'file_size': file_size,
                        'moved_date': datetime.now().isoformat(),
                        'file_hash': file_info.get('content_hash', ''),
                        'analysis_summary': self._extract_analysis_summary(file_info)
                    }
                    manifest_files.append(manifest_entry)

                    total_size += file_size
                    moved_count += 1

                    # Update progress stats
                    if moved_count % 10 == 0:
                        size_mb = total_size / 1024 / 1024
                        pbar.set_postfix({
                            'Moved': moved_count,
                            'Size': f"{size_mb:.1f}MB",
                            'Failed': len(failed_moves)
                        })

                    pbar.update(1)

                except Exception as e:
                    error_msg = str(e)
                    self.logger.error(f"Failed to quarantine {file_info.get('original_path', 'unknown')}: {error_msg}")
                    failed_moves.append({
                        'path': file_info.get('original_path', 'unknown'),
                        'error': error_msg
                    })
                    pbar.update(1)
                    continue

        # Create comprehensive manifest
        manifest = QuarantineManifest(
            quarantine_id=quarantine_id,
            creation_date=datetime.now().isoformat(),
            deletion_threshold=deletion_threshold,
            total_files=moved_count,
            total_size_bytes=total_size,
            files=manifest_files,
            recovery_instructions=self._generate_recovery_instructions(quarantine_id)
        )

        # Save manifest and metadata
        self._save_quarantine_manifest(quarantine_path, manifest)
        self._save_quarantine_metadata(quarantine_path, {
            'failed_moves': failed_moves,
            'operation_summary': {
                'total_attempted': len(files_to_quarantine),
                'successfully_moved': moved_count,
                'failed_moves': len(failed_moves),
                'total_size_mb': total_size / 1024 / 1024
            }
        })

        self.logger.info(f"Quarantine complete: {moved_count} files moved, {len(failed_moves)} failed "
                         f"({total_size / 1024 / 1024:.1f} MB total)")

        return manifest

    def restore_from_quarantine(self, quarantine_id: str) -> bool:
        """
        Restore files from quarantine back to original locations.

        Args:
            quarantine_id: Quarantine session to restore

        Returns:
            True if restoration was successful
        """
        quarantine_path = self.base_quarantine_dir / quarantine_id
        manifest_path = quarantine_path / "manifest.json"

        if not manifest_path.exists():
            self.logger.error(f"Quarantine manifest not found: {manifest_path}")
            return False

        try:
            # Load manifest
            manifest = self._load_quarantine_manifest(manifest_path)
            if not manifest:
                return False

            files_to_restore = manifest['files']
            files_restored = 0
            failed_restores = []

            self.logger.info(f"Restoring {len(files_to_restore)} files from quarantine: {quarantine_id}")

            with tqdm(total=len(files_to_restore), desc="📤 Restoring from quarantine",
                      unit="files", disable=not TQDM_AVAILABLE) as pbar:

                for file_info in files_to_restore:
                    try:
                        quarantine_file = Path(file_info['quarantine_path'])
                        original_path = Path(file_info['original_path'])

                        # Update progress description
                        display_name = original_path.name
                        if len(display_name) > 30:
                            display_name = display_name[:30] + "..."
                        pbar.set_description(f"📤 Restoring: {display_name}")

                        if not quarantine_file.exists():
                            failed_restores.append({
                                'path': str(original_path),
                                'error': 'Quarantine file not found'
                            })
                            pbar.update(1)
                            continue

                        # Ensure destination directory exists
                        original_path.parent.mkdir(parents=True, exist_ok=True)

                        # Check if destination already exists
                        if original_path.exists():
                            self.logger.warning(f"Destination already exists, creating backup: {original_path}")
                            backup_path = original_path.with_suffix(
                                f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{original_path.suffix}")
                            shutil.move(str(original_path), str(backup_path))

                        # Move back to original location
                        shutil.move(str(quarantine_file), str(original_path))
                        files_restored += 1

                        pbar.set_postfix({'Restored': files_restored, 'Failed': len(failed_restores)})
                        pbar.update(1)

                    except Exception as e:
                        error_msg = str(e)
                        self.logger.error(f"Failed to restore {file_info['original_path']}: {error_msg}")
                        failed_restores.append({
                            'path': file_info['original_path'],
                            'error': error_msg
                        })
                        pbar.update(1)

            # Save restoration report
            self._save_restoration_report(quarantine_path, {
                'restoration_date': datetime.now().isoformat(),
                'files_restored': files_restored,
                'failed_restores': failed_restores,
                'success_rate': files_restored / len(files_to_restore) if files_to_restore else 0
            })

            # Clean up quarantine directory if restoration was successful
            if files_restored > 0 and len(failed_restores) == 0:
                try:
                    shutil.rmtree(quarantine_path)
                    self.logger.info(f"Quarantine directory cleaned up: {quarantine_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up quarantine directory: {e}")

            self.logger.info(f"Restoration complete: {files_restored} files restored, {len(failed_restores)} failed")
            return files_restored > 0

        except Exception as e:
            self.logger.error(f"Failed to restore quarantine {quarantine_id}: {e}")
            return False

    def list_quarantines(self) -> List[Dict[str, Any]]:
        """
        List all available quarantine sessions.

        Returns:
            List of quarantine session information
        """
        if not self.base_quarantine_dir.exists():
            return []

        quarantines = []

        for quarantine_dir in self.base_quarantine_dir.iterdir():
            if quarantine_dir.is_dir():
                manifest_path = quarantine_dir / "manifest.json"

                if manifest_path.exists():
                    try:
                        manifest = self._load_quarantine_manifest(manifest_path)
                        if manifest:
                            # Calculate quarantine age
                            creation_date = datetime.fromisoformat(manifest['creation_date'])
                            age_days = (datetime.now() - creation_date).days

                            quarantine_info = {
                                'id': quarantine_dir.name,
                                'creation_date': manifest['creation_date'],
                                'age_days': age_days,
                                'total_files': manifest['total_files'],
                                'total_size_mb': manifest['total_size_bytes'] / 1024 / 1024,
                                'deletion_threshold': manifest['deletion_threshold'],
                                'recovery_available': True
                            }
                            quarantines.append(quarantine_info)

                    except Exception as e:
                        self.logger.warning(f"Failed to read quarantine manifest {quarantine_dir}: {e}")
                        # Add basic info even if manifest is corrupted
                        stat = quarantine_dir.stat()
                        quarantines.append({
                            'id': quarantine_dir.name,
                            'creation_date': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            'total_files': 0,
                            'total_size_mb': 0,
                            'deletion_threshold': 0,
                            'recovery_available': False,
                            'error': 'Corrupted manifest'
                        })

        # Sort by creation date (newest first)
        return sorted(quarantines, key=lambda x: x['creation_date'], reverse=True)

    def auto_purge_old_quarantines(self, max_age_days: int = 30):
        """
        Automatically purge quarantines older than specified days.

        Args:
            max_age_days: Maximum age in days before purging
        """
        if not self.base_quarantine_dir.exists():
            return

        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        purged_count = 0
        purged_size = 0

        quarantines_to_check = list(self.base_quarantine_dir.iterdir())

        if quarantines_to_check:
            with tqdm(quarantines_to_check, desc="🧹 Checking quarantines for purge",
                      unit="sessions", disable=not TQDM_AVAILABLE) as pbar:

                for quarantine_dir in quarantines_to_check:
                    if quarantine_dir.is_dir():
                        display_name = quarantine_dir.name
                        if len(display_name) > 30:
                            display_name = display_name[:30] + "..."
                        pbar.set_description(f"🧹 Checking: {display_name}")

                        try:
                            manifest_path = quarantine_dir / "manifest.json"

                            if manifest_path.exists():
                                manifest = self._load_quarantine_manifest(manifest_path)
                                if manifest:
                                    creation_date = datetime.fromisoformat(manifest['creation_date'])

                                    if creation_date < cutoff_date:
                                        # Calculate size before deletion
                                        dir_size = self._calculate_directory_size(quarantine_dir)

                                        # Remove quarantine directory
                                        shutil.rmtree(quarantine_dir)

                                        purged_count += 1
                                        purged_size += dir_size

                                        self.logger.info(f"Purged old quarantine: {quarantine_dir.name} "
                                                         f"(age: {(datetime.now() - creation_date).days} days)")
                            else:
                                # Check file system date if no manifest
                                stat = quarantine_dir.stat()
                                creation_date = datetime.fromtimestamp(stat.st_ctime)

                                if creation_date < cutoff_date:
                                    dir_size = self._calculate_directory_size(quarantine_dir)
                                    shutil.rmtree(quarantine_dir)
                                    purged_count += 1
                                    purged_size += dir_size

                                    self.logger.info(f"Purged old quarantine (no manifest): {quarantine_dir.name}")

                        except Exception as e:
                            self.logger.warning(f"Failed to process quarantine {quarantine_dir}: {e}")
                            continue

                    pbar.set_postfix({'Purged': purged_count, 'Size': f"{purged_size / 1024 / 1024:.1f}MB"})
                    pbar.update(1)

        if purged_count > 0:
            self.logger.info(f"Auto-purged {purged_count} old quarantine sessions "
                             f"({purged_size / 1024 / 1024:.1f} MB freed)")
        else:
            self.logger.info("No old quarantines found for purging")

    def get_quarantine_details(self, quarantine_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific quarantine session.

        Args:
            quarantine_id: Quarantine session identifier

        Returns:
            Detailed quarantine information or None if not found
        """
        quarantine_path = self.base_quarantine_dir / quarantine_id

        if not quarantine_path.exists():
            return None

        try:
            manifest_path = quarantine_path / "manifest.json"
            metadata_path = quarantine_path / "metadata" / "operation_metadata.json"

            details = {
                'quarantine_id': quarantine_id,
                'quarantine_path': str(quarantine_path),
                'exists': True
            }

            # Load manifest
            if manifest_path.exists():
                manifest = self._load_quarantine_manifest(manifest_path)
                if manifest:
                    details.update(manifest)

            # Load additional metadata
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    details['operation_metadata'] = metadata

            # Calculate current size
            current_size = self._calculate_directory_size(quarantine_path)
            details['current_size_bytes'] = current_size
            details['current_size_mb'] = current_size / 1024 / 1024

            # Check file integrity
            details['file_integrity'] = self._check_quarantine_integrity(quarantine_path, details.get('files', []))

            return details

        except Exception as e:
            self.logger.error(f"Failed to get quarantine details for {quarantine_id}: {e}")
            return None

    def _get_relative_quarantine_path(self, source_path: Path) -> Path:
        """
        Generate relative path for quarantine that preserves directory structure.

        Args:
            source_path: Original file path

        Returns:
            Relative path for quarantine storage
        """
        try:
            # Try to make relative to some common chess directory structures
            common_base_names = ['chess', 'Chess', 'games', 'Games', 'pgn', 'PGN']

            for part in source_path.parts:
                if part in common_base_names:
                    # Use everything from this point forward
                    base_index = source_path.parts.index(part)
                    relative_parts = source_path.parts[base_index:]
                    return Path(*relative_parts)

            # If no common base found, use the filename with a hash of the parent path
            parent_hash = hashlib.md5(str(source_path.parent).encode()).hexdigest()[:8]
            return Path(f"path_{parent_hash}") / source_path.name

        except Exception:
            # Fallback: just use the filename
            return Path(source_path.name)

    def _extract_analysis_summary(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key analysis information for manifest"""
        return {
            'instructional_value': file_info.get('instructional_value', 0.0),
            'domain_relevance': file_info.get('domain_relevance', 0.0),
            'detected_openings': file_info.get('detected_openings', [])[:3],
            'detected_players': file_info.get('detected_players', [])[:3],
            'top_concepts': file_info.get('top_concepts', [])[:5]
        }

    def _generate_recovery_instructions(self, quarantine_id: str) -> str:
        """Generate recovery instructions for the manifest"""
        return f"""QUARANTINE RECOVERY INSTRUCTIONS

Quarantine ID: {quarantine_id}
Creation Date: {datetime.now().isoformat()}

TO RESTORE ALL FILES:
python chess_system.py --restore-quarantine {quarantine_id}

TO LIST QUARANTINE DETAILS:
python chess_system.py --list-quarantines

SAFETY NOTES:
- Files are safely stored in quarantine, not permanently deleted
- Original directory structure is preserved
- Recovery restores files to exact original locations
- Manifest contains complete file metadata for verification

MANUAL RECOVERY:
If automated recovery fails, files are located in:
{self.base_quarantine_dir / quarantine_id / "files"}

See manifest.json for original file paths and metadata.
"""

    def _save_quarantine_manifest(self, quarantine_path: Path, manifest: QuarantineManifest):
        """Save quarantine manifest to file"""
        manifest_path = quarantine_path / "manifest.json"

        try:
            with open(manifest_path, 'w') as f:
                json.dump(asdict(manifest), f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save quarantine manifest: {e}")

    def _save_quarantine_metadata(self, quarantine_path: Path, metadata: Dict[str, Any]):
        """Save additional quarantine metadata"""
        metadata_path = quarantine_path / "metadata" / "operation_metadata.json"

        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save quarantine metadata: {e}")

    def _save_restoration_report(self, quarantine_path: Path, report: Dict[str, Any]):
        """Save restoration report"""
        report_path = quarantine_path / "metadata" / "restoration_report.json"

        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save restoration report: {e}")

    def _load_quarantine_manifest(self, manifest_path: Path) -> Optional[Dict[str, Any]]:
        """Load quarantine manifest from file"""
        try:
            with open(manifest_path, 'r') as f:
                return json.load(f)

        except Exception as e:
            self.logger.error(f"Failed to load quarantine manifest {manifest_path}: {e}")
            return None

    def _calculate_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes"""
        total_size = 0

        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size

        except Exception as e:
            self.logger.warning(f"Failed to calculate size for {directory}: {e}")

        return total_size

    def _check_quarantine_integrity(self, quarantine_path: Path, manifest_files: List[Dict]) -> Dict[str, Any]:
        """Check integrity of quarantined files against manifest"""
        integrity_report = {
            'total_manifest_files': len(manifest_files),
            'existing_files': 0,
            'missing_files': 0,
            'size_mismatches': 0,
            'missing_file_list': []
        }

        try:
            for file_info in manifest_files:
                quarantine_file_path = Path(file_info['quarantine_path'])

                if quarantine_file_path.exists():
                    integrity_report['existing_files'] += 1

                    # Check file size
                    actual_size = quarantine_file_path.stat().st_size
                    expected_size = file_info.get('file_size', 0)

                    if actual_size != expected_size:
                        integrity_report['size_mismatches'] += 1

                else:
                    integrity_report['missing_files'] += 1
                    integrity_report['missing_file_list'].append(file_info['original_path'])

        except Exception as e:
            self.logger.error(f"Quarantine integrity check failed: {e}")
            integrity_report['error'] = str(e)

        return integrity_report