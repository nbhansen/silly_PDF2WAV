# infrastructure/file/file_manager.py
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set

from domain.interfaces import FileManager
from domain.models import FileInfo, CleanupResult

class LocalFileManager(FileManager):
    """Simple, robust file lifecycle management for local storage"""
    
    def __init__(self, managed_directory: str):
        self.managed_dir = Path(managed_directory)
        self.managed_dir.mkdir(parents=True, exist_ok=True)
        
        # Simple in-memory tracking for scheduled deletions
        self._scheduled_deletions: dict[str, datetime] = {}
        self._cleanup_lock = threading.Lock()
        
        print(f"FileManager: Managing directory {self.managed_dir}")
    
    def cleanup_old_files(self, max_age_hours: float) -> CleanupResult:
        """Remove files older than max_age_hours"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        files_removed = 0
        bytes_freed = 0
        errors = []
        
        with self._cleanup_lock:
            try:
                for file_path in self.managed_dir.iterdir():
                    if not file_path.is_file():
                        continue
                    
                    try:
                        # Get file creation time
                        created_at = datetime.fromtimestamp(file_path.stat().st_ctime)
                        
                        if created_at < cutoff_time:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            
                            files_removed += 1
                            bytes_freed += file_size
                            
                            print(f"FileManager: Removed old file {file_path.name} ({file_size} bytes)")
                            
                    except Exception as e:
                        error_msg = f"Failed to remove {file_path.name}: {e}"
                        errors.append(error_msg)
                        print(f"FileManager: {error_msg}")
                
                # Clean up scheduled deletions for removed files
                self._cleanup_scheduled_deletions()
                
            except Exception as e:
                errors.append(f"Cleanup scan failed: {e}")
                print(f"FileManager: Cleanup scan failed: {e}")
        
        result = CleanupResult(
            files_removed=files_removed,
            bytes_freed=bytes_freed,
            errors=errors
        )
        
        if files_removed > 0:
            print(f"FileManager: Cleanup complete - removed {files_removed} files, freed {result.mb_freed:.1f} MB")
        
        return result
    
    def get_file_info(self, filename: str) -> Optional[FileInfo]:
        """Get information about a specific file"""
        file_path = self.managed_dir / filename
        
        if not file_path.exists() or not file_path.is_file():
            return None
        
        try:
            stat = file_path.stat()
            return FileInfo(
                filename=filename,
                full_path=str(file_path),
                size_bytes=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_ctime),
                last_accessed=datetime.fromtimestamp(stat.st_atime)
            )
        except Exception as e:
            print(f"FileManager: Failed to get info for {filename}: {e}")
            return None
    
    def list_managed_files(self) -> List[FileInfo]:
        """List all files under management"""
        files = []
        
        try:
            for file_path in self.managed_dir.iterdir():
                if file_path.is_file():
                    info = self.get_file_info(file_path.name)
                    if info:
                        files.append(info)
        except Exception as e:
            print(f"FileManager: Failed to list files: {e}")
        
        return sorted(files, key=lambda f: f.created_at, reverse=True)
    
    def schedule_cleanup(self, filename: str, delay_hours: float) -> bool:
        """Schedule a file for deletion after delay_hours"""
        if delay_hours <= 0:
            print(f"FileManager: Invalid delay {delay_hours} hours for {filename}")
            return False
        
        file_path = self.managed_dir / filename
        if not file_path.exists():
            print(f"FileManager: Cannot schedule cleanup for non-existent file {filename}")
            return False
        
        deletion_time = datetime.now() + timedelta(hours=delay_hours)
        
        with self._cleanup_lock:
            self._scheduled_deletions[filename] = deletion_time
        
        print(f"FileManager: Scheduled {filename} for deletion at {deletion_time}")
        return True
    
    def get_total_disk_usage(self) -> int:
        """Get total bytes used by managed files"""
        total_bytes = 0
        
        try:
            for file_path in self.managed_dir.iterdir():
                if file_path.is_file():
                    total_bytes += file_path.stat().st_size
        except Exception as e:
            print(f"FileManager: Failed to calculate disk usage: {e}")
        
        return total_bytes
    
    def process_scheduled_deletions(self) -> CleanupResult:
        """Process any files scheduled for deletion (call periodically)"""
        now = datetime.now()
        files_to_delete = []
        
        with self._cleanup_lock:
            # Find files ready for deletion
            for filename, deletion_time in list(self._scheduled_deletions.items()):
                if now >= deletion_time:
                    files_to_delete.append(filename)
                    del self._scheduled_deletions[filename]
        
        # Delete the files
        files_removed = 0
        bytes_freed = 0
        errors = []
        
        for filename in files_to_delete:
            file_path = self.managed_dir / filename
            
            try:
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    
                    files_removed += 1
                    bytes_freed += file_size
                    
                    print(f"FileManager: Deleted scheduled file {filename} ({file_size} bytes)")
                else:
                    print(f"FileManager: Scheduled file {filename} already deleted")
                    
            except Exception as e:
                error_msg = f"Failed to delete scheduled file {filename}: {e}"
                errors.append(error_msg)
                print(f"FileManager: {error_msg}")
        
        return CleanupResult(
            files_removed=files_removed,
            bytes_freed=bytes_freed,
            errors=errors
        )
    
    def _cleanup_scheduled_deletions(self):
        """Remove scheduled deletions for files that no longer exist"""
        to_remove = []
        
        for filename in self._scheduled_deletions:
            file_path = self.managed_dir / filename
            if not file_path.exists():
                to_remove.append(filename)
        
        for filename in to_remove:
            del self._scheduled_deletions[filename]
    
    def get_stats(self) -> dict:
        """Get file management statistics"""
        files = self.list_managed_files()
        total_size = sum(f.size_bytes for f in files)
        
        return {
            'total_files': len(files),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'oldest_file_hours': max((f.age_hours for f in files), default=0),
            'scheduled_deletions': len(self._scheduled_deletions),
            'directory': str(self.managed_dir)
        }