"""
A dedicated service for managing the cleanup of old files in a background thread.
"""
import os
import time
import threading
from typing import Dict

from domain.interfaces import IFileManager

class FileCleanupScheduler:
    """
    Manages a background thread to periodically clean up registered files
    that have exceeded their maximum age.
    """

    def __init__(
        self,
        file_manager: IFileManager,
        max_file_age_seconds: int,
        check_interval_seconds: int
    ):
        """
        Initializes the scheduler. Does NOT start it.

        Args:
            file_manager: An object that implements the IFileManager interface.
            max_file_age_seconds: The maximum age for a file in seconds before deletion.
            check_interval_seconds: How often the cleanup thread should wake up to check for old files.
        """
        if not isinstance(file_manager, IFileManager):
            raise TypeError("file_manager must implement IFileManager")

        self.file_manager = file_manager
        self.max_file_age_seconds = max_file_age_seconds
        self.check_interval_seconds = check_interval_seconds

        # Thread-safe structures for managing files
        self._lock = threading.Lock()
        self._scheduled_files: Dict[str, float] = {} # {filepath: creation_timestamp}
        
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._cleanup_job, daemon=True)

        print(
            f"FileCleanupScheduler initialized. "
            f"Max Age: {self.max_file_age_seconds}s, "
            f"Check Interval: {self.check_interval_seconds}s."
        )

    def schedule(self, filepath: str) -> None:
        """Schedules a file for future cleanup monitoring."""
        with self._lock:
            self._scheduled_files[filepath] = time.time()
        print(f"Scheduled for cleanup: {os.path.basename(filepath)}")

    def start(self) -> None:
        """Starts the background cleanup thread."""
        if not self._thread.is_alive():
            print("Starting background file cleanup thread.")
            self._stop_event.clear()
            self._thread.start()

    def stop(self) -> None:
        """Signals the background cleanup thread to stop."""
        if self._thread.is_alive():
            print("Stopping background file cleanup thread.")
            self._stop_event.set()
            self._thread.join(timeout=5) # Wait for thread to finish

    def _cleanup_job(self) -> None:
        """The main loop for the background thread."""
        while not self._stop_event.is_set():
            try:
                files_to_delete = []
                current_time = time.time()

                with self._lock:
                    # Find files that are older than the max age
                    # Create a copy of items to avoid runtime error for changing dict size
                    for filepath, creation_time in list(self._scheduled_files.items()):
                        if (current_time - creation_time) > self.max_file_age_seconds:
                            files_to_delete.append(filepath)

                    # Delete the files and remove them from the tracking dictionary
                    for filepath in files_to_delete:
                        print(f"File expired: {os.path.basename(filepath)}. Deleting.")
                        self.file_manager.delete_file(filepath)
                        del self._scheduled_files[filepath]
            
            except Exception as e:
                print(f"Error in cleanup thread: {e}")

            # Wait for the next interval, but check for stop event more frequently
            self._stop_event.wait(self.check_interval_seconds)

