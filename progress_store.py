"""Thread-safe progress tracking for long-running operations.

This module provides a thread-safe implementation for tracking progress
of document processing operations. Designed for single-user home app
but with proper locking to prevent race conditions.
"""

from dataclasses import dataclass
import logging
import threading
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProgressStatus:
    """Progress tracking for long-running operations."""

    operation_id: str
    stage: str
    percentage: int
    message: str
    is_complete: bool = False
    is_error: bool = False
    error_message: Optional[str] = None
    result_data: Optional[dict[str, Any]] = None
    cancelled: bool = False


class ThreadSafeProgressStore:
    """Thread-safe storage for operation progress tracking.

    Uses a lock to ensure thread-safety for concurrent access.
    Includes automatic cleanup of stale entries.
    """

    def __init__(self, max_age_seconds: int = 3600, max_entries: int = 100):
        """Initialize the progress store.

        Args:
            max_age_seconds: Maximum age of entries before cleanup (default 1 hour)
            max_entries: Maximum number of entries before forced cleanup
        """
        self._lock = threading.Lock()
        self._progress: dict[str, ProgressStatus] = {}
        self._cancellation_flags: dict[str, bool] = {}
        self._timestamps: dict[str, float] = {}
        self._max_age_seconds = max_age_seconds
        self._max_entries = max_entries

    def update(
        self,
        operation_id: str,
        stage: str,
        percentage: int,
        message: str,
        is_complete: bool = False,
        is_error: bool = False,
        error_message: Optional[str] = None,
        result_data: Optional[dict[str, Any]] = None,
    ) -> None:
        """Update progress for an operation (thread-safe)."""
        with self._lock:
            self._progress[operation_id] = ProgressStatus(
                operation_id=operation_id,
                stage=stage,
                percentage=percentage,
                message=message,
                is_complete=is_complete,
                is_error=is_error,
                error_message=error_message,
                result_data=result_data,
                cancelled=self._cancellation_flags.get(operation_id, False),
            )
            self._timestamps[operation_id] = time.time()
            self._cleanup_if_needed()

    def get(self, operation_id: str) -> Optional[ProgressStatus]:
        """Get current progress for an operation (thread-safe)."""
        with self._lock:
            return self._progress.get(operation_id)

    def cancel(self, operation_id: str) -> None:
        """Mark an operation as cancelled (thread-safe)."""
        with self._lock:
            self._cancellation_flags[operation_id] = True
            if operation_id in self._progress:
                current = self._progress[operation_id]
                self._progress[operation_id] = ProgressStatus(
                    operation_id=current.operation_id,
                    stage="cancelled",
                    percentage=current.percentage,
                    message="Processing cancelled by user",
                    is_complete=True,
                    is_error=False,
                    cancelled=True,
                )

    def is_cancelled(self, operation_id: str) -> bool:
        """Check if an operation has been cancelled (thread-safe)."""
        with self._lock:
            return self._cancellation_flags.get(operation_id, False)

    def remove(self, operation_id: str) -> None:
        """Remove an operation from tracking (thread-safe)."""
        with self._lock:
            self._progress.pop(operation_id, None)
            self._cancellation_flags.pop(operation_id, None)
            self._timestamps.pop(operation_id, None)

    def _cleanup_if_needed(self) -> None:
        """Remove stale entries if needed (must be called with lock held)."""
        if len(self._progress) <= self._max_entries:
            return

        current_time = time.time()
        stale_ids = [
            op_id
            for op_id, timestamp in self._timestamps.items()
            if current_time - timestamp > self._max_age_seconds
        ]

        for op_id in stale_ids:
            self._progress.pop(op_id, None)
            self._cancellation_flags.pop(op_id, None)
            self._timestamps.pop(op_id, None)
            logger.debug("Cleaned up stale progress entry: %s", op_id)


# Global instance for backwards compatibility with existing route handlers
_progress_store = ThreadSafeProgressStore()


# Backwards-compatible functions that use the global store
def update_progress(
    operation_id: str,
    stage: str,
    percentage: int,
    message: str,
    is_complete: bool = False,
    is_error: bool = False,
    error_message: Optional[str] = None,
    result_data: Optional[dict[str, Any]] = None,
) -> None:
    """Update progress for an operation."""
    _progress_store.update(
        operation_id=operation_id,
        stage=stage,
        percentage=percentage,
        message=message,
        is_complete=is_complete,
        is_error=is_error,
        error_message=error_message,
        result_data=result_data,
    )


def get_progress(operation_id: str) -> Optional[ProgressStatus]:
    """Get current progress for an operation."""
    return _progress_store.get(operation_id)


def cancel_operation(operation_id: str) -> None:
    """Mark an operation as cancelled."""
    _progress_store.cancel(operation_id)


def is_operation_cancelled(operation_id: str) -> bool:
    """Check if an operation has been cancelled."""
    return _progress_store.is_cancelled(operation_id)
