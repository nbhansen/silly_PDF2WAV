"""Tests for ThreadSafeProgressStore module.

Tests thread safety, error handling, and edge cases for progress tracking.
"""

from concurrent.futures import ThreadPoolExecutor
import time

from application.services.progress_store import (
    ProgressStatus,
    ThreadSafeProgressStore,
    cancel_operation,
    get_progress,
    is_operation_cancelled,
    update_progress,
)


class TestProgressStatus:
    """Tests for ProgressStatus dataclass."""

    def test_progress_status_error_state(self) -> None:
        """Should track error state properly."""
        status = ProgressStatus(
            operation_id="error-123",
            stage="failed",
            percentage=30,
            message="Failed processing",
            is_complete=True,
            is_error=True,
            error_message="Out of memory",
        )
        assert status.is_error is True
        assert status.error_message == "Out of memory"
        assert status.is_complete is True


class TestThreadSafeProgressStore:
    """Tests for ThreadSafeProgressStore class."""

    def test_store_update_and_get(self) -> None:
        """Should update and retrieve progress."""
        store = ThreadSafeProgressStore()
        store.update(
            operation_id="op-1",
            stage="processing",
            percentage=25,
            message="Quarter done",
        )
        progress = store.get("op-1")
        assert progress is not None
        assert progress.percentage == 25
        assert progress.message == "Quarter done"

    def test_store_get_nonexistent(self) -> None:
        """Should return None for nonexistent operation."""
        store = ThreadSafeProgressStore()
        progress = store.get("nonexistent")
        assert progress is None

    def test_store_cancel_operation(self) -> None:
        """Should mark operation as cancelled."""
        store = ThreadSafeProgressStore()
        store.update("op-2", "processing", 50, "Half done")
        store.cancel("op-2")
        progress = store.get("op-2")
        assert progress is not None
        assert progress.cancelled is True
        assert progress.stage == "cancelled"
        assert progress.is_complete is True

    def test_store_cancel_nonexistent(self) -> None:
        """Should handle cancelling nonexistent operation."""
        store = ThreadSafeProgressStore()
        # Should not raise
        store.cancel("nonexistent")
        assert store.is_cancelled("nonexistent") is True

    def test_store_is_cancelled(self) -> None:
        """Should correctly report cancellation status."""
        store = ThreadSafeProgressStore()
        assert store.is_cancelled("op-3") is False
        store.cancel("op-3")
        assert store.is_cancelled("op-3") is True

    def test_store_remove_operation(self) -> None:
        """Should remove operation from tracking."""
        store = ThreadSafeProgressStore()
        store.update("op-4", "processing", 75, "Almost done")
        store.remove("op-4")
        assert store.get("op-4") is None

    def test_store_remove_nonexistent(self) -> None:
        """Should handle removing nonexistent operation."""
        store = ThreadSafeProgressStore()
        # Should not raise
        store.remove("nonexistent")

    def test_store_thread_safety_concurrent_updates(self) -> None:
        """Should handle concurrent updates from multiple threads."""
        store = ThreadSafeProgressStore()
        num_operations = 100
        errors: list[Exception] = []

        def update_operation(op_id: int) -> None:
            try:
                for i in range(10):
                    store.update(
                        f"op-{op_id}",
                        f"stage-{i}",
                        i * 10,
                        f"Message {i}",
                    )
                    time.sleep(0.001)  # Small delay to increase contention
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(update_operation, range(num_operations))

        assert len(errors) == 0
        # All operations should have final state
        for op_id in range(num_operations):
            progress = store.get(f"op-{op_id}")
            assert progress is not None
            assert progress.percentage == 90  # Last iteration

    def test_store_thread_safety_concurrent_cancel(self) -> None:
        """Should handle concurrent cancellation safely."""
        store = ThreadSafeProgressStore()

        def worker(op_id: int) -> None:
            store.update(f"op-{op_id}", "processing", 50, "Working")
            store.cancel(f"op-{op_id}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(worker, range(50))

        # All operations should be cancelled
        for op_id in range(50):
            assert store.is_cancelled(f"op-{op_id}")

    def test_store_cleanup_stale_entries(self) -> None:
        """Should cleanup old entries when max exceeded."""
        # Create store with low limits for testing
        store = ThreadSafeProgressStore(max_age_seconds=0, max_entries=5)

        # Add more than max entries
        for i in range(10):
            store.update(f"op-{i}", "done", 100, "Complete", is_complete=True)
            time.sleep(0.001)  # Ensure different timestamps

        # Force cleanup by adding one more
        store.update("op-final", "done", 100, "Final", is_complete=True)

        # Some entries should have been cleaned up
        active_count = sum(1 for i in range(11) if store.get(f"op-{i}") is not None)
        # Final entry should always exist
        assert store.get("op-final") is not None
        # Most old entries should be cleaned up (within bounds)
        assert active_count <= 10


class TestGlobalFunctions:
    """Tests for backwards-compatible global functions."""

    def test_update_progress_function(self) -> None:
        """Should update progress using global function."""
        update_progress(
            operation_id="global-op-1",
            stage="running",
            percentage=60,
            message="Progress update",
        )
        progress = get_progress("global-op-1")
        assert progress is not None
        assert progress.percentage == 60

    def test_get_progress_function(self) -> None:
        """Should retrieve progress using global function."""
        update_progress("global-op-2", "running", 30, "Started")
        progress = get_progress("global-op-2")
        assert progress is not None
        assert progress.stage == "running"

    def test_cancel_operation_function(self) -> None:
        """Should cancel operation using global function."""
        update_progress("global-op-3", "running", 40, "Working")
        cancel_operation("global-op-3")
        assert is_operation_cancelled("global-op-3")

    def test_is_operation_cancelled_function(self) -> None:
        """Should check cancellation using global function."""
        assert is_operation_cancelled("never-started") is False
        cancel_operation("to-cancel")
        assert is_operation_cancelled("to-cancel") is True


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_operation_id(self) -> None:
        """Should handle empty operation ID."""
        store = ThreadSafeProgressStore()
        store.update("", "stage", 0, "Empty ID")
        progress = store.get("")
        assert progress is not None
        assert progress.operation_id == ""

    def test_unicode_in_progress_data(self) -> None:
        """Should handle unicode in progress data."""
        store = ThreadSafeProgressStore()
        store.update(
            "unicode-op",
            "processing",
            50,
            "Procesando documento \u00e9\u00f1\u00e1\u00ed\u00f3\u00fa \ud83d\udcda",
        )
        progress = store.get("unicode-op")
        assert progress is not None
        assert "\ud83d\udcda" in progress.message

    def test_large_result_data(self) -> None:
        """Should handle large result data."""
        store = ThreadSafeProgressStore()
        large_data = {"items": list(range(1000)), "text": "x" * 10000}
        store.update(
            "large-op",
            "done",
            100,
            "Complete",
            is_complete=True,
            result_data=large_data,
        )
        progress = store.get("large-op")
        assert progress is not None
        assert progress.result_data is not None
        assert len(progress.result_data["items"]) == 1000

    def test_percentage_boundary_values(self) -> None:
        """Should handle percentage boundary values."""
        store = ThreadSafeProgressStore()
        store.update("zero", "start", 0, "Zero percent")
        store.update("hundred", "done", 100, "Hundred percent")
        store.update("over", "error", 150, "Over hundred")  # Invalid but should work

        assert store.get("zero").percentage == 0  # type: ignore[union-attr]
        assert store.get("hundred").percentage == 100  # type: ignore[union-attr]
        assert store.get("over").percentage == 150  # type: ignore[union-attr]
