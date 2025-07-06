# tests/benchmarks/test_mutable_vs_immutable.py
"""Comparison benchmarks: Mutable vs Immutable design patterns.
Measures the performance difference between old and new approaches.
"""

from dataclasses import dataclass
from dataclasses import replace as dataclasses_replace
import types
from typing import Any

import pytest


# Simulate old mutable patterns for comparison
class MutableChunker:
    """Simulates the old mutable list.append() patterns."""

    def chunk_text_mutable(self, text_chunks: list[str], max_chunk_size: int) -> list[str]:
        """Old pattern: using list.append() mutations."""
        processed_chunks = []

        for chunk in text_chunks:
            if len(chunk) <= max_chunk_size:
                processed_chunks.append(chunk)
                continue

            # Split by words (old mutable pattern)
            words = chunk.split()
            current_chunk = ""

            for word in words:
                if len(current_chunk) + len(word) + 1 > max_chunk_size and current_chunk:
                    processed_chunks.append(current_chunk.strip())
                    current_chunk = word
                else:
                    current_chunk += " " + word if current_chunk else word

            if current_chunk.strip():
                processed_chunks.append(current_chunk.strip())

        return processed_chunks


class ImmutableChunker:
    """New immutable pattern using comprehensions."""

    def chunk_text_immutable(self, text_chunks: list[str], max_chunk_size: int) -> list[str]:
        """New pattern: using immutable comprehensions."""
        return [result_chunk for chunk in text_chunks for result_chunk in self._process_chunk(chunk, max_chunk_size)]

    def _process_chunk(self, chunk: str, max_chunk_size: int) -> list[str]:
        """Process single chunk immutably."""
        if len(chunk) <= max_chunk_size:
            return [chunk]

        words = chunk.split()
        result_chunks = []
        current_chunk = ""

        for word in words:
            if len(current_chunk) + len(word) + 1 > max_chunk_size and current_chunk:
                result_chunks.append(current_chunk.strip())
                current_chunk = word
            else:
                current_chunk += " " + word if current_chunk else word

        if current_chunk.strip():
            result_chunks.append(current_chunk.strip())

        return result_chunks


# Simulate service container patterns
class MutableServiceContainer:
    """Simulates old mutable service container."""

    def __init__(self):
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: Any):
        """Mutable registration."""
        self._services[name] = service

    def get(self, name: str) -> Any:
        """Service retrieval."""
        return self._services.get(name)


class ImmutableServiceContainer:
    """New immutable service container pattern."""

    def __init__(self, services: dict[str, Any]):
        self._services: types.MappingProxyType[str, Any] = types.MappingProxyType(services)

    def get(self, name: str) -> Any:
        """Service retrieval from immutable container."""
        return self._services.get(name)


# Test data
@pytest.fixture
def chunking_test_data():
    """Test data for chunking benchmarks."""
    return [
        f"This is a test sentence number {i} with substantial content for chunking performance comparison. "
        + "It includes multiple clauses, punctuation marks, and sufficient length to trigger chunking logic. "
        + "The purpose is to measure the performance difference between mutable and immutable patterns." * 2
        for i in range(30)
    ]


@pytest.fixture
def service_test_data():
    """Test data for service container benchmarks."""
    return {f"service_{i}": f"instance_{i}" for i in range(100)}


class TestChunkingComparison:
    """Compare mutable vs immutable chunking performance."""

    def test_mutable_chunking_performance(self, benchmark, chunking_test_data):
        """Benchmark old mutable chunking pattern."""
        chunker = MutableChunker()

        def chunk_with_mutation():
            return chunker.chunk_text_mutable(chunking_test_data, max_chunk_size=1500)

        result = benchmark(chunk_with_mutation)
        assert len(result) >= len(chunking_test_data)

    def test_immutable_chunking_performance(self, benchmark, chunking_test_data):
        """Benchmark new immutable chunking pattern."""
        chunker = ImmutableChunker()

        def chunk_with_comprehension():
            return chunker.chunk_text_immutable(chunking_test_data, max_chunk_size=1500)

        result = benchmark(chunk_with_comprehension)
        assert len(result) >= len(chunking_test_data)


class TestServiceContainerComparison:
    """Compare mutable vs immutable service container performance."""

    def test_mutable_container_access(self, benchmark, service_test_data):
        """Benchmark mutable service container access."""
        container = MutableServiceContainer()  # type: ignore[no-untyped-call]
        for name, service in service_test_data.items():
            container.register(name, service)

        def access_services():
            results = []
            for i in range(0, 50, 2):  # Access every other service
                service = container.get(f"service_{i}")
                if service:
                    results.append(service)
            return results

        result = benchmark(access_services)
        assert len(result) == 25

    def test_immutable_container_access(self, benchmark, service_test_data):
        """Benchmark immutable service container access."""
        container = ImmutableServiceContainer(service_test_data)

        def access_services():
            results = []
            for i in range(0, 50, 2):  # Access every other service
                service = container.get(f"service_{i}")
                if service:
                    results.append(service)
            return results

        result = benchmark(access_services)
        assert len(result) == 25


class TestListOperationComparison:
    """Compare mutable list operations vs immutable comprehensions."""

    def test_mutable_list_building(self, benchmark):
        """Benchmark old mutable list.append() pattern."""

        def build_with_append():
            results = []
            for i in range(1000):
                if i % 2 == 0:
                    results.append(f"item_{i}")
                    if i % 4 == 0:
                        results.append(f"extra_{i}")
            return results

        result = benchmark(build_with_append)
        assert len(result) > 0

    def test_immutable_list_building(self, benchmark):
        """Benchmark new immutable comprehension pattern."""

        def build_with_comprehension():
            base_items = [f"item_{i}" for i in range(1000) if i % 2 == 0]
            extra_items = [f"extra_{i}" for i in range(1000) if i % 4 == 0]
            return base_items + extra_items

        result = benchmark(build_with_comprehension)
        assert len(result) > 0


class TestDataMutationComparison:
    """Compare data mutation vs immutable updates."""

    @dataclass
    class MutableData:
        """Simulate old mutable data pattern."""

        text: str
        start_time: float
        duration: float

        def update_timing(self, offset: float):
            """Mutable update."""
            self.start_time += offset

    @dataclass(frozen=True)
    class ImmutableData:
        """New frozen data pattern."""

        text: str
        start_time: float
        duration: float

    def test_mutable_data_updates(self, benchmark):
        """Benchmark mutable data updates."""

        def update_mutable_data():
            items = [self.MutableData(f"text_{i}", float(i), 1.0) for i in range(100)]
            # Mutate in place
            for item in items:
                item.update_timing(5.0)
            return items

        result = benchmark(update_mutable_data)
        assert len(result) == 100
        assert all(item.start_time >= 5.0 for item in result)

    def test_immutable_data_updates(self, benchmark):
        """Benchmark immutable data updates."""

        def update_immutable_data():
            items = [self.ImmutableData(f"text_{i}", float(i), 1.0) for i in range(100)]
            # Create new instances
            updated_items = [dataclasses_replace(item, start_time=item.start_time + 5.0) for item in items]
            return updated_items

        result = benchmark(update_immutable_data)
        assert len(result) == 100
        assert all(item.start_time >= 5.0 for item in result)


if __name__ == "__main__":
    # Allow running benchmarks directly
    pytest.main([__file__, "--benchmark-only", "--benchmark-sort=mean"])
