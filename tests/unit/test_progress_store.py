"""Tests for ThreadSafeProgressStore module.

Tests thread safety, error handling, and edge cases for progress tracking.
"""

from concurrent.futures import ThreadPoolExecutor
import time
from unittest.mock import patch

from application.services.progress_store import ProgressStatus, ThreadSafeProgressStore


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

    def test_store_update_ignored_after_cancellation(self) -> None:
        """Regular updates should be ignored after cancellation to prevent TOCTOU race."""
        store = ThreadSafeProgressStore()
        store.update("op-cancel", "processing", 50, "Working")
        store.cancel("op-cancel")
        # Regular update should be ignored — cancellation status preserved
        store.update("op-cancel", "processing", 75, "Still working")
        progress = store.get("op-cancel")
        assert progress is not None
        assert progress.stage == "cancelled"
        assert progress.percentage == 50

    def test_store_error_update_allowed_after_cancellation(self) -> None:
        """Error/complete updates should pass through even after cancellation."""
        store = ThreadSafeProgressStore()
        store.update("op-err", "processing", 50, "Working")
        store.cancel("op-err")
        # Error update should pass through
        store.update("op-err", "error", 0, "Failed", is_error=True, error_message="boom")
        progress = store.get("op-err")
        assert progress is not None
        assert progress.is_error is True
        assert progress.cancelled is True  # cancelled flag preserved

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
        """Finished entries older than max_age_seconds should be purged on the next update."""
        store = ThreadSafeProgressStore(max_age_seconds=60, max_entries=100)
        store.update("op-old", "done", 100, "Complete", is_complete=True)

        two_minutes_later = time.time() + 120
        with patch("application.services.progress_store.time.time", return_value=two_minutes_later):
            store.update("op-new", "starting", 0, "Fresh")

        assert store.get("op-old") is None
        assert store.get("op-new") is not None

    def test_store_stale_cleanup_spares_in_flight_operations(self) -> None:
        """In-flight operations must never be age-evicted.

        A long processing phase emits no updates, and eviction would drop the
        cancellation flag while the background thread still runs.
        """
        store = ThreadSafeProgressStore(max_age_seconds=60, max_entries=100)
        store.update("op-running", "processing", 20, "Working")

        two_minutes_later = time.time() + 120
        with patch("application.services.progress_store.time.time", return_value=two_minutes_later):
            store.update("op-new", "starting", 0, "Fresh")

        progress = store.get("op-running")
        assert progress is not None
        assert progress.stage == "processing"

    def test_store_cancel_refreshes_entry_lifetime(self) -> None:
        """Cancelling must refresh the timestamp so the cancellation flag outlives the age window."""
        store = ThreadSafeProgressStore(max_age_seconds=60, max_entries=100)
        store.update("op-cancel", "processing", 50, "Working")

        two_minutes_later = time.time() + 120
        with patch("application.services.progress_store.time.time", return_value=two_minutes_later):
            store.cancel("op-cancel")
            store.update("op-other", "starting", 0, "Fresh")

        assert store.is_cancelled("op-cancel") is True
        progress = store.get("op-cancel")
        assert progress is not None
        assert progress.stage == "cancelled"

    def test_store_enforces_max_entries_with_fresh_entries(self) -> None:
        """Store must stay bounded even when no entry is stale — oldest evicted first."""
        store = ThreadSafeProgressStore(max_age_seconds=3600, max_entries=5)

        for i in range(10):
            store.update(f"op-{i}", "processing", 50, "Working")
            time.sleep(0.001)  # Ensure distinct timestamps for deterministic eviction order

        remaining = [f"op-{i}" for i in range(10) if store.get(f"op-{i}") is not None]
        assert len(remaining) == 5
        assert remaining == ["op-5", "op-6", "op-7", "op-8", "op-9"]

    def test_store_overflow_evicts_finished_before_in_flight(self) -> None:
        """When over the cap, finished entries go first even if an in-flight entry is older."""
        store = ThreadSafeProgressStore(max_age_seconds=3600, max_entries=3)
        store.update("op-oldest-running", "processing", 10, "Working")
        time.sleep(0.001)
        store.update("op-done", "complete", 100, "Done", is_complete=True)
        time.sleep(0.001)
        store.update("op-running-2", "processing", 20, "Working")
        time.sleep(0.001)
        store.update("op-running-3", "processing", 30, "Working")

        assert store.get("op-done") is None
        assert store.get("op-oldest-running") is not None
        assert store.get("op-running-2") is not None
        assert store.get("op-running-3") is not None


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
