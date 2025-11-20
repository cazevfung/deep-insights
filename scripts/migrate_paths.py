"""
Migration script to move existing files and update session JSON records.

This script migrates:
1. Batch directories from tests/results/run_{batch_id}/ to data/research/batches/run_{batch_id}/
2. Reports from tests/results/reports/ to data/research/reports/
3. Updates session JSON files to reference new paths

Usage:
    python scripts/migrate_paths.py [--dry-run] [--backup]
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from loguru import logger
import argparse
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import Config


class PathMigration:
    """Handle migration of files and session records."""
    
    def __init__(self, dry_run: bool = False, backup: bool = False):
        """
        Initialize migration.
        
        Args:
            dry_run: If True, only show what would be done without making changes
            backup: If True, create backup before migration
        """
        self.dry_run = dry_run
        self.backup = backup
        self.config = Config()
        
        # Get paths from config
        self.new_batches_dir = self.config.get_batches_dir()
        self.new_reports_dir = self.config.get_reports_dir()
        
        # Old paths
        self.old_batches_dir = project_root / "tests" / "results"
        self.old_reports_dir = project_root / "tests" / "results" / "reports"
        self.sessions_dir = project_root / "data" / "research" / "sessions"
        
        # Statistics
        self.stats = {
            "batches_moved": 0,
            "reports_moved": 0,
            "sessions_updated": 0,
            "errors": []
        }
    
    def migrate_batches(self) -> List[Tuple[Path, Path]]:
        """
        Migrate batch directories from old location to new location.
        
        Returns:
            List of (old_path, new_path) tuples for moved batches
        """
        logger.info("=" * 60)
        logger.info("Migrating Batch Directories")
        logger.info("=" * 60)
        
        if not self.old_batches_dir.exists():
            logger.warning(f"Old batches directory does not exist: {self.old_batches_dir}")
            return []
        
        # Find all batch directories (run_*)
        batch_dirs = [d for d in self.old_batches_dir.iterdir() 
                     if d.is_dir() and d.name.startswith("run_")]
        
        if not batch_dirs:
            logger.info("No batch directories found to migrate")
            return []
        
        logger.info(f"Found {len(batch_dirs)} batch directories to migrate")
        
        # Ensure new directory exists
        self.new_batches_dir.mkdir(parents=True, exist_ok=True)
        
        moved = []
        for batch_dir in sorted(batch_dirs):
            old_path = batch_dir
            new_path = self.new_batches_dir / batch_dir.name
            
            if new_path.exists():
                logger.warning(f"Target already exists, skipping: {new_path}")
                self.stats["errors"].append(f"Target exists: {new_path}")
                continue
            
            try:
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would move: {old_path} -> {new_path}")
                else:
                    logger.info(f"Moving: {old_path.name}")
                    shutil.move(str(old_path), str(new_path))
                    logger.success(f"  ✓ Moved to: {new_path}")
                
                moved.append((old_path, new_path))
                self.stats["batches_moved"] += 1
                
            except Exception as e:
                error_msg = f"Failed to move {old_path}: {e}"
                logger.error(error_msg)
                self.stats["errors"].append(error_msg)
        
        return moved
    
    def migrate_reports(self) -> List[Tuple[Path, Path]]:
        """
        Migrate report files from old location to new location.
        
        Returns:
            List of (old_path, new_path) tuples for moved reports
        """
        logger.info("=" * 60)
        logger.info("Migrating Report Files")
        logger.info("=" * 60)
        
        if not self.old_reports_dir.exists():
            logger.warning(f"Old reports directory does not exist: {self.old_reports_dir}")
            return []
        
        # Find all report files
        report_files = list(self.old_reports_dir.glob("report_*.md"))
        
        if not report_files:
            logger.info("No report files found to migrate")
            return []
        
        logger.info(f"Found {len(report_files)} report files to migrate")
        
        # Ensure new directory exists
        self.new_reports_dir.mkdir(parents=True, exist_ok=True)
        
        moved = []
        for report_file in sorted(report_files):
            old_path = report_file
            new_path = self.new_reports_dir / report_file.name
            
            if new_path.exists():
                logger.warning(f"Target already exists, skipping: {new_path}")
                self.stats["errors"].append(f"Target exists: {new_path}")
                continue
            
            try:
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would move: {old_path.name} -> {new_path}")
                else:
                    logger.info(f"Moving: {old_path.name}")
                    shutil.move(str(old_path), str(new_path))
                    logger.success(f"  ✓ Moved to: {new_path}")
                
                moved.append((old_path, new_path))
                self.stats["reports_moved"] += 1
                
            except Exception as e:
                error_msg = f"Failed to move {report_file}: {e}"
                logger.error(error_msg)
                self.stats["errors"].append(error_msg)
        
        return moved
    
    def update_session_paths(self, moved_reports: List[Tuple[Path, Path]]) -> int:
        """
        Update session JSON files to reference new report paths.
        
        Args:
            moved_reports: List of (old_path, new_path) tuples for moved reports
        
        Returns:
            Number of sessions updated
        """
        logger.info("=" * 60)
        logger.info("Updating Session JSON Files")
        logger.info("=" * 60)
        
        if not self.sessions_dir.exists():
            logger.warning(f"Sessions directory does not exist: {self.sessions_dir}")
            return 0
        
        # Create mapping of old paths to new paths
        path_mapping = {str(old): str(new) for old, new in moved_reports}
        
        # Also map old directory to new directory for relative paths
        old_reports_str = str(self.old_reports_dir)
        new_reports_str = str(self.new_reports_dir)
        
        # Find all session files
        session_files = list(self.sessions_dir.glob("session_*.json"))
        
        if not session_files:
            logger.info("No session files found")
            return 0
        
        logger.info(f"Found {len(session_files)} session files to check")
        
        updated_count = 0
        
        for session_file in sorted(session_files):
            try:
                # Load session file
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                updated = False
                
                # Update report_path in phase4 artifact
                if "phase_artifacts" in session_data:
                    phase4 = session_data["phase_artifacts"].get("phase4")
                    if phase4:
                        artifact = phase4.get("artifact", {})
                        
                        # Update report_path
                        if "report_path" in artifact:
                            old_path = artifact["report_path"]
                            new_path = self._map_path(old_path, path_mapping, old_reports_str, new_reports_str)
                            if new_path != old_path:
                                artifact["report_path"] = new_path
                                updated = True
                                logger.info(f"  Updated report_path: {session_file.name}")
                        
                        # Update additional_report_paths
                        if "additional_report_paths" in artifact:
                            old_paths = artifact["additional_report_paths"]
                            new_paths = [
                                self._map_path(p, path_mapping, old_reports_str, new_reports_str)
                                for p in old_paths
                            ]
                            if new_paths != old_paths:
                                artifact["additional_report_paths"] = new_paths
                                updated = True
                                logger.info(f"  Updated additional_report_paths: {session_file.name}")
                
                # Save if updated
                if updated:
                    if self.dry_run:
                        logger.info(f"[DRY RUN] Would update: {session_file.name}")
                    else:
                        # Create backup if requested
                        if self.backup:
                            backup_path = session_file.with_suffix(f".json.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                            shutil.copy2(session_file, backup_path)
                            logger.debug(f"  Created backup: {backup_path.name}")
                        
                        # Save updated session
                        with open(session_file, 'w', encoding='utf-8') as f:
                            json.dump(session_data, f, ensure_ascii=False, indent=2)
                        
                        logger.success(f"  ✓ Updated: {session_file.name}")
                        updated_count += 1
                        self.stats["sessions_updated"] += 1
                
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse JSON in {session_file}: {e}"
                logger.error(error_msg)
                self.stats["errors"].append(error_msg)
            except Exception as e:
                error_msg = f"Failed to update {session_file}: {e}"
                logger.error(error_msg)
                self.stats["errors"].append(error_msg)
        
        return updated_count
    
    def _map_path(self, path_str: str, path_mapping: Dict[str, str], 
                  old_dir: str, new_dir: str) -> str:
        """
        Map old path to new path.
        
        Args:
            path_str: Original path string
            path_mapping: Direct path mappings
            old_dir: Old directory path
            new_dir: New directory path
        
        Returns:
            New path string
        """
        # Try direct mapping first
        if path_str in path_mapping:
            return path_mapping[path_str]
        
        # Try directory replacement
        if old_dir in path_str:
            return path_str.replace(old_dir, new_dir)
        
        # No change needed
        return path_str
    
    def print_summary(self):
        """Print migration summary."""
        logger.info("=" * 60)
        logger.info("Migration Summary")
        logger.info("=" * 60)
        logger.info(f"Batches moved: {self.stats['batches_moved']}")
        logger.info(f"Reports moved: {self.stats['reports_moved']}")
        logger.info(f"Sessions updated: {self.stats['sessions_updated']}")
        
        if self.stats["errors"]:
            logger.warning(f"Errors encountered: {len(self.stats['errors'])}")
            for error in self.stats["errors"]:
                logger.error(f"  - {error}")
        else:
            logger.success("No errors encountered!")
        
        if self.dry_run:
            logger.info("\n[DRY RUN] No actual changes were made. Run without --dry-run to execute migration.")
    
    def run(self):
        """Run the complete migration process."""
        logger.info("Starting Path Migration")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info(f"Backup: {self.backup}")
        logger.info(f"New batches directory: {self.new_batches_dir}")
        logger.info(f"New reports directory: {self.new_reports_dir}")
        logger.info("")
        
        # Migrate batches
        moved_batches = self.migrate_batches()
        logger.info("")
        
        # Migrate reports
        moved_reports = self.migrate_reports()
        logger.info("")
        
        # Update session files
        self.update_session_paths(moved_reports)
        logger.info("")
        
        # Print summary
        self.print_summary()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate batch directories and reports to new paths, and update session JSON files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup copies of session files before updating"
    )
    
    args = parser.parse_args()
    
    migration = PathMigration(dry_run=args.dry_run, backup=args.backup)
    migration.run()


if __name__ == "__main__":
    main()


