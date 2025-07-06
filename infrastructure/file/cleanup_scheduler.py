"""Background service for managing cleanup of old files.
Runs in a separate thread to periodically remove expired files.
"""

import threading
import time

from domain.interfaces import IFileManager


class FileCleanupScheduler:
    """Background thread service for periodic cleanup of expired files.
    Monitors registered files and removes them when they exceed max age.
    """

    def __init__(self, file_manager: IFileManager, max_file_age_seconds: int, check_interval_seconds: int):
        """Initialize the cleanup scheduler (does not start automatically).

        Args:
            file_manager: IFileManager implementation for file operations
            max_file_age_seconds: Maximum file age before deletion
            check_interval_seconds: How often to check for expired files
        """
        self.file_manager = file_manager
        self.max_file_age_seconds = max_file_age_seconds
        self.check_interval_seconds = check_interval_seconds

        # Thread-safe file tracking
        self._lock = threading.Lock()
        self._scheduled_files: dict[str, float] = {}  # {filepath: creation_timestamp}

        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._cleanup_job, daemon=True)

    def schedule(self, filepath: str) -> None:
        """Schedule a file for cleanup monitoring."""
        with self._lock:
            self._scheduled_files[filepath] = time.time()

    def start(self) -> None:
        """Start the background cleanup thread."""
        if not self._thread.is_alive():
            self._stop_event.clear()
            self._thread.start()

    def stop(self) -> None:
        """Stop the background cleanup thread."""
        if self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=5)

    def _cleanup_job(self) -> None:
        """Main cleanup loop running in background thread."""
        while not self._stop_event.is_set():
            try:
                self._process_expired_files()
            except Exception:
                # Log error but continue running
                pass

            # Wait for next interval, checking stop event
            self._stop_event.wait(self.check_interval_seconds)

    def _process_expired_files(self) -> None:
        """Process and remove expired files."""
        current_time = time.time()
        files_to_delete = []

        with self._lock:
            # Find expired files
            for filepath, creation_time in list(self._scheduled_files.items()):
                if (current_time - creation_time) > self.max_file_age_seconds:
                    files_to_delete.append(filepath)

            # Remove expired files
            for filepath in files_to_delete:
                self.file_manager.delete_file(filepath)
                del self._scheduled_files[filepath]
