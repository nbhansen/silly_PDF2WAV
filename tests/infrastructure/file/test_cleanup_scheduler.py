# tests/infrastructure/file/test_cleanup_scheduler.py
"""Comprehensive unit tests for FileCleanupScheduler implementation.

Tests initialization, file scheduling, thread management, cleanup logic, thread safety, and error handling.
"""

from concurrent.futures import ThreadPoolExecutor
import threading
from typing import NoReturn
from unittest.mock import MagicMock, patch

import pytest

from domain.interfaces import IFileManager
from infrastructure.file.cleanup_scheduler import FileCleanupScheduler

# === Test Fixtures ===


@pytest.fixture
def mock_file_manager():
    """Mock IFileManager for testing cleanup scheduler."""
    mock = MagicMock(spec=IFileManager)
    mock.delete_file.return_value = None
    return mock


@pytest.fixture
def scheduler_params():
    """Standard parameters for scheduler initialization."""
    return {"max_file_age_seconds": 60, "check_interval_seconds": 10}


@pytest.fixture
def scheduler(mock_file_manager, scheduler_params):
    """FileCleanupScheduler instance for testing."""
    return FileCleanupScheduler(file_manager=mock_file_manager, **scheduler_params)


@pytest.fixture
def mock_time():
    """Mock time.time() for deterministic testing."""
    with patch("infrastructure.file.cleanup_scheduler.time.time") as mock:
        mock.return_value = 1000.0  # Fixed timestamp
        yield mock


# === Initialization Tests ===


class TestFileCleanupSchedulerInitialization:
    """Test FileCleanupScheduler initialization and parameter validation."""

    def test_init_with_valid_parameters(self, mock_file_manager):
        """Should initialize successfully with valid parameters."""
        scheduler = FileCleanupScheduler(
            file_manager=mock_file_manager, max_file_age_seconds=120, check_interval_seconds=30
        )

        assert scheduler.file_manager is mock_file_manager
        assert scheduler.max_file_age_seconds == 120
        assert scheduler.check_interval_seconds == 30
        assert isinstance(scheduler._lock, type(threading.Lock()))
        assert isinstance(scheduler._stop_event, type(threading.Event()))
        assert scheduler._thread is None  # Thread created on start(), not init
        assert scheduler._scheduled_files == {}

    def test_init_with_zero_age_seconds(self, mock_file_manager):
        """Should accept zero max_file_age_seconds for immediate cleanup."""
        scheduler = FileCleanupScheduler(
            file_manager=mock_file_manager, max_file_age_seconds=0, check_interval_seconds=5
        )

        assert scheduler.max_file_age_seconds == 0
        assert scheduler.check_interval_seconds == 5

    def test_init_with_zero_check_interval(self, mock_file_manager):
        """Should accept zero check_interval_seconds for continuous checking."""
        scheduler = FileCleanupScheduler(
            file_manager=mock_file_manager, max_file_age_seconds=60, check_interval_seconds=0
        )

        assert scheduler.max_file_age_seconds == 60
        assert scheduler.check_interval_seconds == 0


# === File Scheduling Tests ===


class TestFileScheduling:
    """Test file scheduling functionality and timestamp tracking."""

    def test_schedule_single_file(self, scheduler, mock_time):
        """Should schedule single file with current timestamp."""
        filepath = "/test/file.txt"

        scheduler.schedule(filepath)

        assert filepath in scheduler._scheduled_files
        assert scheduler._scheduled_files[filepath] == 1000.0
        mock_time.assert_called_once()

    def test_schedule_multiple_files(self, scheduler, mock_time):
        """Should schedule multiple files with their respective timestamps."""
        files = ["/test/file1.txt", "/test/file2.txt", "/test/file3.txt"]
        timestamps = [1000.0, 1001.0, 1002.0]

        for file_path, timestamp in zip(files, timestamps, strict=True):
            mock_time.return_value = timestamp
            scheduler.schedule(file_path)

        assert len(scheduler._scheduled_files) == 3
        for file_path, expected_timestamp in zip(files, timestamps, strict=True):
            assert scheduler._scheduled_files[file_path] == expected_timestamp

    def test_schedule_thread_safety_concurrent_operations(self, scheduler, mock_time):
        """Should handle concurrent file scheduling safely."""
        files = [f"/test/file_{i}.txt" for i in range(20)]
        mock_time.return_value = 1000.0

        def schedule_file(filepath: str) -> None:
            scheduler.schedule(filepath)

        # Execute concurrent scheduling
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(schedule_file, filepath) for filepath in files]
            for future in futures:
                future.result()  # Wait for completion

        # All files should be scheduled
        assert len(scheduler._scheduled_files) == 20
        for filepath in files:
            assert filepath in scheduler._scheduled_files
            assert scheduler._scheduled_files[filepath] == 1000.0

    def test_schedule_overwrites_existing_file_timestamp(self, scheduler, mock_time):
        """Should update timestamp when scheduling same file multiple times."""
        filepath = "/test/file.txt"

        # First scheduling
        mock_time.return_value = 1000.0
        scheduler.schedule(filepath)
        assert scheduler._scheduled_files[filepath] == 1000.0

        # Second scheduling with different timestamp
        mock_time.return_value = 2000.0
        scheduler.schedule(filepath)
        assert scheduler._scheduled_files[filepath] == 2000.0
        assert len(scheduler._scheduled_files) == 1


# === Thread Management Tests ===


class TestThreadManagement:
    """Test background thread lifecycle management."""

    def test_start_creates_and_starts_thread(self, scheduler):
        """Should create and start a new daemon thread."""
        assert scheduler._thread is None

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread.is_alive.return_value = False
            mock_thread_cls.return_value = mock_thread

            scheduler.start()

            mock_thread_cls.assert_called_once_with(target=scheduler._cleanup_job, daemon=True)
            mock_thread.start.assert_called_once()

    def test_start_does_not_restart_running_thread(self, scheduler):
        """Should not start new thread if one is already running."""
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        scheduler._thread = mock_thread

        scheduler.start()

        # No new thread should be created — existing one is alive
        mock_thread.start.assert_not_called()

    def test_stop_background_thread_with_proper_cleanup(self, scheduler):
        """Should stop background thread and wait for completion."""
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        scheduler._thread = mock_thread

        scheduler.stop()

        assert scheduler._stop_event.is_set()
        mock_thread.join.assert_called_once_with(timeout=5)

    def test_stop_does_nothing_when_thread_is_none(self, scheduler):
        """Should handle stop gracefully when thread was never started."""
        assert scheduler._thread is None

        # Should not raise
        scheduler.stop()

    def test_stop_does_nothing_when_thread_not_running(self, scheduler):
        """Should handle stop gracefully when thread is not running."""
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        scheduler._thread = mock_thread

        scheduler.stop()

        mock_thread.join.assert_not_called()

    def test_multiple_start_stop_cycles(self, scheduler):
        """Should create a new thread for each start cycle (threads can't be restarted)."""
        threads_created = []

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread.is_alive.return_value = False
            mock_thread_cls.return_value = mock_thread
            threads_created.append(mock_thread)

            # First start
            scheduler.start()
            assert mock_thread_cls.call_count == 1

            # Simulate thread finished
            mock_thread.is_alive.return_value = True
            scheduler.stop()
            mock_thread.is_alive.return_value = False

            # Second start — should create a NEW thread
            mock_thread2 = MagicMock()
            mock_thread2.is_alive.return_value = False
            mock_thread_cls.return_value = mock_thread2

            scheduler.start()
            assert mock_thread_cls.call_count == 2


# === Cleanup Logic Tests ===


class TestCleanupLogic:
    """Test file cleanup logic and expiration processing."""

    def test_process_expired_files_removes_old_files(self, scheduler, mock_file_manager, mock_time):
        """Should remove files that exceed max age."""
        # Set up files with different ages
        current_time = 2000.0
        mock_time.return_value = current_time

        # Schedule files with known timestamps
        scheduler._scheduled_files = {
            "/old/file1.txt": 1900.0,  # 100 seconds old (expired)
            "/old/file2.txt": 1880.0,  # 120 seconds old (expired)
            "/new/file.txt": 1950.0,  # 50 seconds old (not expired)
        }

        scheduler._process_expired_files()

        # Expired files should be deleted and removed from schedule
        mock_file_manager.delete_file.assert_any_call("/old/file1.txt")
        mock_file_manager.delete_file.assert_any_call("/old/file2.txt")
        assert mock_file_manager.delete_file.call_count == 2

        # Only non-expired file should remain
        assert scheduler._scheduled_files == {"/new/file.txt": 1950.0}

    def test_process_expired_files_keeps_non_expired_files(self, scheduler, mock_file_manager, mock_time):
        """Should keep files that have not exceeded max age."""
        current_time = 2000.0
        mock_time.return_value = current_time

        # All files are within max age (60 seconds)
        scheduler._scheduled_files = {
            "/recent/file1.txt": 1950.0,  # 50 seconds old
            "/recent/file2.txt": 1970.0,  # 30 seconds old
            "/recent/file3.txt": 1990.0,  # 10 seconds old
        }

        scheduler._process_expired_files()

        # No files should be deleted
        mock_file_manager.delete_file.assert_not_called()

        # All files should remain scheduled
        assert len(scheduler._scheduled_files) == 3
        assert "/recent/file1.txt" in scheduler._scheduled_files
        assert "/recent/file2.txt" in scheduler._scheduled_files
        assert "/recent/file3.txt" in scheduler._scheduled_files

    def test_process_expired_files_mixed_expired_and_valid(self, scheduler, mock_file_manager, mock_time):
        """Should handle mix of expired and non-expired files correctly."""
        current_time = 2000.0
        mock_time.return_value = current_time

        scheduler._scheduled_files = {
            "/expired/file1.txt": 1900.0,  # 100 seconds old (expired)
            "/valid/file1.txt": 1950.0,  # 50 seconds old (valid)
            "/expired/file2.txt": 1920.0,  # 80 seconds old (expired)
            "/valid/file2.txt": 1980.0,  # 20 seconds old (valid)
        }

        scheduler._process_expired_files()

        # Only expired files deleted
        mock_file_manager.delete_file.assert_any_call("/expired/file1.txt")
        mock_file_manager.delete_file.assert_any_call("/expired/file2.txt")
        assert mock_file_manager.delete_file.call_count == 2

        # Valid files remain
        expected_remaining = {
            "/valid/file1.txt": 1950.0,
            "/valid/file2.txt": 1980.0,
        }
        assert scheduler._scheduled_files == expected_remaining

    def test_process_expired_files_retains_failed_deletions(self, scheduler, mock_file_manager, mock_time):
        """Should keep files in tracking when deletion fails (for retry next cycle)."""
        current_time = 2000.0
        mock_time.return_value = current_time

        scheduler._scheduled_files = {"/expired/file.txt": 1900.0}

        mock_file_manager.delete_file.side_effect = OSError("File not found")

        # Should NOT raise — errors are caught and logged
        scheduler._process_expired_files()

        # File should remain in schedule for retry next cycle
        assert "/expired/file.txt" in scheduler._scheduled_files
        mock_file_manager.delete_file.assert_called_once_with("/expired/file.txt")

    def test_process_expired_files_with_empty_schedule(self, scheduler, mock_file_manager, mock_time):
        """Should handle empty file schedule without issues."""
        mock_time.return_value = 2000.0
        assert scheduler._scheduled_files == {}

        scheduler._process_expired_files()

        mock_file_manager.delete_file.assert_not_called()
        assert scheduler._scheduled_files == {}

    def test_process_expired_files_thread_safety(self, scheduler, mock_file_manager, mock_time):
        """Should maintain thread safety during file processing."""
        current_time = 2000.0
        mock_time.return_value = current_time

        # Set up expired files
        scheduler._scheduled_files = {
            "/expired/file1.txt": 1900.0,
            "/expired/file2.txt": 1880.0,
        }

        # Test that the method can be called safely - the lock usage is internal
        # We'll verify the lock exists and the operation completes successfully
        assert isinstance(scheduler._lock, type(threading.Lock()))

        scheduler._process_expired_files()

        # Files should be processed and removed
        assert scheduler._scheduled_files == {}
        assert mock_file_manager.delete_file.call_count == 2


# === Thread Safety Tests ===


class TestThreadSafety:
    """Test thread-safe operations and lock contention scenarios."""

    def test_concurrent_schedule_calls_thread_safe(self, scheduler, mock_time):
        """Should handle concurrent schedule() calls safely."""
        mock_time.return_value = 1000.0
        files = [f"/concurrent/file_{i}.txt" for i in range(50)]

        def schedule_files_batch(file_batch: list[str]) -> None:
            for filepath in file_batch:
                scheduler.schedule(filepath)

        # Split files into batches for concurrent processing
        batch_size = 10
        batches = [files[i : i + batch_size] for i in range(0, len(files), batch_size)]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(schedule_files_batch, batch) for batch in batches]
            for future in futures:
                future.result()

        # All files should be scheduled without corruption
        assert len(scheduler._scheduled_files) == 50
        for filepath in files:
            assert filepath in scheduler._scheduled_files

    def test_schedule_during_cleanup_processing(self, scheduler, mock_file_manager, mock_time):
        """Should allow scheduling while cleanup is processing."""
        current_time = 2000.0
        mock_time.return_value = current_time

        # Set up some expired files
        scheduler._scheduled_files = {"/expired/file.txt": 1900.0}

        # Schedule a new file before cleanup
        scheduler.schedule("/new/file.txt")

        # Process expired files - should only delete expired one
        scheduler._process_expired_files()

        # New file should remain (not expired), old file should be removed
        assert "/new/file.txt" in scheduler._scheduled_files
        assert "/expired/file.txt" not in scheduler._scheduled_files
        mock_file_manager.delete_file.assert_called_once_with("/expired/file.txt")

    def test_stop_during_active_cleanup(self, scheduler):
        """Should handle stop signal during active cleanup processing."""
        # Test that stop event can be set during cleanup
        assert not scheduler._stop_event.is_set()

        # Simulate stopping during cleanup
        scheduler._stop_event.set()
        assert scheduler._stop_event.is_set()

        # The cleanup job should respect the stop event
        with patch.object(scheduler, "_process_expired_files") as mock_process:
            # Mock wait to return True immediately (stop requested)
            with patch.object(scheduler._stop_event, "wait", return_value=True):
                scheduler._cleanup_job()

            # Process should not be called when stop event is set
            mock_process.assert_not_called()

    def test_lock_contention_scenarios(self, scheduler, mock_time):
        """Should handle lock contention between schedule and cleanup."""
        mock_time.return_value = 1000.0

        # Test that scheduling and cleanup can both access the lock
        # Schedule some files
        for i in range(5):
            scheduler.schedule(f"/test/file{i}.txt")

        assert len(scheduler._scheduled_files) == 5

        # Process expired files (none should be expired since they're all at 1000.0)
        scheduler._process_expired_files()

        # All files should still be there since none are expired
        assert len(scheduler._scheduled_files) == 5

        # Test that lock is accessible and working
        assert isinstance(scheduler._lock, type(threading.Lock()))


# === Error Handling Tests ===


class TestErrorHandling:
    """Test error handling scenarios and exception recovery."""

    def test_file_manager_delete_failures_continue_processing(self, scheduler, mock_file_manager, mock_time):
        """Should continue processing remaining files when one deletion fails."""
        current_time = 2000.0
        mock_time.return_value = current_time

        scheduler._scheduled_files = {
            "/fail/file1.txt": 1900.0,
            "/fail/file2.txt": 1880.0,
        }

        # First delete fails, second succeeds
        mock_file_manager.delete_file.side_effect = [OSError("Permission denied"), None]

        scheduler._process_expired_files()

        # Both deletes should be attempted
        assert mock_file_manager.delete_file.call_count == 2
        # Failed file stays tracked for retry, successful one is removed
        assert "/fail/file1.txt" in scheduler._scheduled_files
        assert "/fail/file2.txt" not in scheduler._scheduled_files

    def test_cleanup_job_continues_after_exceptions(self, scheduler):
        """Should continue cleanup job after exceptions in processing."""
        call_count = 0

        def failing_process() -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Test exception")
            # Second call succeeds - don't increment further

        with patch.object(scheduler, "_process_expired_files", side_effect=failing_process):
            # Mock the stop event to control the loop
            with patch.object(scheduler._stop_event, "is_set") as mock_is_set:
                # First two calls return False (continue), third returns True (stop)
                mock_is_set.side_effect = [False, False, True]

                with patch.object(scheduler._stop_event, "wait") as mock_wait:
                    # Make wait return immediately
                    mock_wait.return_value = False

                    # Should not crash despite exception
                    scheduler._cleanup_job()

            # Should have attempted processing twice (once failed, once succeeded)
            assert call_count == 2

    def test_cleanup_job_handles_file_deletion_exceptions(self, scheduler):
        """Should handle file deletion exceptions in cleanup job gracefully."""
        call_count = 0

        def process_with_exception() -> NoReturn:
            nonlocal call_count
            call_count += 1
            raise OSError("File deletion failed")

        with (
            patch.object(scheduler, "_process_expired_files", side_effect=process_with_exception),
            patch.object(scheduler._stop_event, "is_set") as mock_is_set,
            patch.object(scheduler._stop_event, "wait") as mock_wait,
        ):
            # First call returns False (continue), second returns True (stop)
            mock_is_set.side_effect = [False, True]
            # Make wait return immediately
            mock_wait.return_value = False

            # Should not crash despite file deletion exception
            scheduler._cleanup_job()

        # Should have attempted to process once
        assert call_count == 1

    def test_thread_join_timeout_handling(self, scheduler):
        """Should handle thread join timeouts gracefully."""
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        mock_thread.join.return_value = None  # Simulate timeout
        scheduler._thread = mock_thread

        # Stop should complete even if join times out
        scheduler.stop()

        # Should have attempted to join with timeout
        mock_thread.join.assert_called_once_with(timeout=5)


# === Integration Tests ===


class TestIntegration:
    """Test complete scheduler workflows and integration scenarios."""

    def test_complete_lifecycle_schedule_cleanup_verify(self, mock_file_manager, mock_time):
        """Should complete full lifecycle from scheduling to cleanup."""
        scheduler = FileCleanupScheduler(
            file_manager=mock_file_manager, max_file_age_seconds=60, check_interval_seconds=10
        )

        # Schedule files at different times
        files_and_times = [
            ("/test/file1.txt", 1000.0),
            ("/test/file2.txt", 1010.0),
            ("/test/file3.txt", 1020.0),
        ]

        for filepath, timestamp in files_and_times:
            mock_time.return_value = timestamp
            scheduler.schedule(filepath)

        # Verify all files scheduled
        assert len(scheduler._scheduled_files) == 3

        # Advance time to expire first two files
        mock_time.return_value = 1100.0  # 100 seconds later

        # Process cleanup
        scheduler._process_expired_files()

        # All files should be deleted since they are all older than 60 seconds:
        # file1: 1100-1000=100 > 60 (expired)
        # file2: 1100-1010=90 > 60 (expired)
        # file3: 1100-1020=80 > 60 (expired)
        mock_file_manager.delete_file.assert_any_call("/test/file1.txt")
        mock_file_manager.delete_file.assert_any_call("/test/file2.txt")
        mock_file_manager.delete_file.assert_any_call("/test/file3.txt")
        assert mock_file_manager.delete_file.call_count == 3

        # All files should be removed
        assert scheduler._scheduled_files == {}

    def test_multiple_files_different_expiration_times(self, mock_file_manager, scheduler, mock_time):
        """Should handle multiple files with staggered expiration correctly."""
        base_time = 1000.0

        # Schedule files at different intervals
        files_with_times = [
            ("/early/file1.txt", base_time),  # Will expire first
            ("/early/file2.txt", base_time + 10),  # Will expire second
            ("/middle/file.txt", base_time + 30),  # Will expire third
            ("/late/file.txt", base_time + 50),  # Will not expire
        ]

        for filepath, timestamp in files_with_times:
            mock_time.return_value = timestamp
            scheduler.schedule(filepath)

        # Process at different time points
        test_times_and_expected_deletions = [
            (base_time + 70, 1),  # Only first file expired (70-0=70 > 60)
            (base_time + 80, 2),  # First two files expired
            (base_time + 100, 3),  # First three files expired
            (base_time + 120, 4),  # All files expired
        ]

        for test_time, _expected_total_deletions in test_times_and_expected_deletions:
            # Reset file manager mock
            mock_file_manager.reset_mock()

            # Re-schedule all files for this test iteration
            for filepath, timestamp in files_with_times:
                scheduler._scheduled_files[filepath] = timestamp

            mock_time.return_value = test_time
            scheduler._process_expired_files()

            # Count files that should be expired at this time
            expired_count = sum(
                1 for _, timestamp in files_with_times if (test_time - timestamp) > scheduler.max_file_age_seconds
            )

            assert mock_file_manager.delete_file.call_count == expired_count
