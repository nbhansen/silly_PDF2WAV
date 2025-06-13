# infrastructure/file/cleanup_scheduler.py
import threading
import time
from typing import Optional

from domain.interfaces import FileManager
from application.config.system_config import SystemConfig

class FileCleanupScheduler:
    """Infrastructure service for background file cleanup automation"""
    
    def __init__(self, file_manager: FileManager, config: SystemConfig):
        self.file_manager = file_manager
        self.config = config
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        print(f"FileCleanupScheduler: Cleanup every {config.auto_cleanup_interval_hours}h, max age {config.max_file_age_hours}h")
    
    def start(self):
        """Start the background cleanup scheduler"""
        if self.running:
            print("FileCleanupScheduler: Already running")
            return
        
        if not self.config.enable_file_cleanup:
            print("FileCleanupScheduler: File cleanup disabled, not starting")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_cleanup_loop, daemon=True)
        self.thread.start()
        
        print("FileCleanupScheduler: Background cleanup started")
    
    def stop(self):
        """Stop the background cleanup scheduler"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        
        print("FileCleanupScheduler: Background cleanup stopped")
    
    def _run_cleanup_loop(self):
        """Main cleanup loop running in background thread"""
        interval_seconds = self.config.auto_cleanup_interval_hours * 3600
        
        while self.running:
            try:
                # Sleep in small chunks so we can respond to stop requests
                for _ in range(int(interval_seconds)):
                    if not self.running:
                        break
                    time.sleep(1)
                
                if not self.running:
                    break
                
                # Run scheduled deletions first
                self._process_scheduled_deletions()
                
                # Run age-based cleanup
                self._run_age_based_cleanup()
                
                # Check disk usage and force cleanup if needed
                self._check_disk_usage()
                
            except Exception as e:
                print(f"FileCleanupScheduler: Error in cleanup loop: {e}")
                # Continue running even if one iteration fails
                time.sleep(60)  # Wait a minute before retrying
    
    def _process_scheduled_deletions(self):
        """Process files scheduled for deletion"""
        try:
            if hasattr(self.file_manager, 'process_scheduled_deletions'):
                result = self.file_manager.process_scheduled_deletions()
                if result.files_removed > 0:
                    print(f"FileCleanupScheduler: Processed scheduled deletions - {result.files_removed} files, {result.mb_freed:.1f} MB")
        except Exception as e:
            print(f"FileCleanupScheduler: Error processing scheduled deletions: {e}")
    
    def _run_age_based_cleanup(self):
        """Run cleanup based on file age"""
        try:
            result = self.file_manager.cleanup_old_files(self.config.max_file_age_hours)
            if result.files_removed > 0:
                print(f"FileCleanupScheduler: Age-based cleanup - {result.files_removed} files, {result.mb_freed:.1f} MB")
            
            if result.errors:
                print(f"FileCleanupScheduler: {len(result.errors)} cleanup errors occurred")
                
        except Exception as e:
            print(f"FileCleanupScheduler: Error in age-based cleanup: {e}")
    
    def _check_disk_usage(self):
        """Check disk usage and force cleanup if needed"""
        try:
            total_bytes = self.file_manager.get_total_disk_usage()
            total_mb = total_bytes / (1024 * 1024)
            
            if total_mb > self.config.max_disk_usage_mb:
                print(f"FileCleanupScheduler: Disk usage ({total_mb:.1f} MB) exceeds limit ({self.config.max_disk_usage_mb} MB)")
                
                # Force cleanup with shorter age limit
                forced_max_age = min(self.config.max_file_age_hours, 1.0)  # At most 1 hour for emergency cleanup
                result = self.file_manager.cleanup_old_files(forced_max_age)
                
                print(f"FileCleanupScheduler: Emergency cleanup - {result.files_removed} files, {result.mb_freed:.1f} MB")
                
        except Exception as e:
            print(f"FileCleanupScheduler: Error checking disk usage: {e}")
    
    def run_manual_cleanup(self) -> dict:
        """Run a manual cleanup and return results"""
        try:
            # Process scheduled deletions
            scheduled_result = None
            if hasattr(self.file_manager, 'process_scheduled_deletions'):
                scheduled_result = self.file_manager.process_scheduled_deletions()
            
            # Run age-based cleanup
            age_result = self.file_manager.cleanup_old_files(self.config.max_file_age_hours)
            
            total_files = age_result.files_removed
            total_mb = age_result.mb_freed
            
            if scheduled_result:
                total_files += scheduled_result.files_removed
                total_mb += scheduled_result.mb_freed
            
            return {
                'success': True,
                'files_removed': total_files,
                'mb_freed': total_mb,
                'errors': age_result.errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }