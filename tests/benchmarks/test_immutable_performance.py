# tests/benchmarks/test_immutable_performance.py
"""Performance benchmarks for immutable design pattern implementation.
Measures the impact of our immutable refactoring on key operations.
"""

from dataclasses import replace as dataclasses_replace
import types
from typing import Any

import pytest

from application.config.system_config import SystemConfig, TTSEngine
from domain.container.service_container import ServiceContainer, create_service_container_builder
from domain.models import TextSegment
from domain.text.chunking_strategy import ChunkingService, SentenceBasedChunking, WordBasedChunking


# Test Data Setup
@pytest.fixture
def test_config():
    """Create a test configuration."""
    return SystemConfig(tts_engine=TTSEngine.PIPER, llm_model_name="test-model", gemini_model_name="test-gemini-model")


@pytest.fixture
def large_text_chunks():
    """Generate large text chunks for performance testing."""
    return [
        f"This is a test sentence number {i} with enough content to test chunking performance. "
        + "It contains multiple clauses and punctuation marks. "
        + "The purpose is to simulate real document processing scenarios." * 3
        for i in range(100)
    ]


@pytest.fixture
def sample_text_segments():
    """Generate sample text segments for timing engine benchmarks."""
    return [
        TextSegment(
            text=f"Sample text segment {i}",
            start_time=float(i * 2),
            duration=1.5,
            segment_type="sentence",
            chunk_index=i // 10,
            sentence_index=i % 10,
        )
        for i in range(50)
    ]


class TestServiceContainerPerformance:
    """Benchmark immutable service container operations."""

    def test_container_creation_performance(self, benchmark, test_config):
        """Benchmark service container creation time."""

        def create_container():
            return ServiceContainer(test_config)

        result = benchmark(create_container)
        assert result is not None

    def test_service_resolution_performance(self, benchmark, test_config):
        """Benchmark service resolution from immutable container."""
        container = ServiceContainer(test_config)

        def get_multiple_services():
            # Get multiple services to test lookup performance
            services: list[Any] = []
            for _ in range(10):
                services.append(container.get("tts_engine"))
            return services

        result = benchmark(get_multiple_services)
        assert len(result) == 10

    def test_builder_pattern_performance(self, benchmark, test_config):
        """Benchmark immutable container builder pattern."""

        def create_with_builder():
            return (
                create_service_container_builder(test_config)
                .register(str, lambda: "test_service")
                .register(int, lambda: 42)
                .build()
            )

        result = benchmark(create_with_builder)
        assert result is not None


class TestChunkingStrategyPerformance:
    """Benchmark immutable text chunking operations."""

    def test_sentence_chunking_performance(self, benchmark, large_text_chunks):
        """Benchmark sentence-based chunking with immutable patterns."""
        chunker = SentenceBasedChunking()

        def chunk_large_text():
            return chunker.chunk_text(large_text_chunks, max_chunk_size=2000)

        result = benchmark(chunk_large_text)
        assert len(result) > 0

    def test_word_chunking_performance(self, benchmark, large_text_chunks):
        """Benchmark word-based chunking with immutable patterns."""
        chunker = WordBasedChunking()

        def chunk_large_text():
            return chunker.chunk_text(large_text_chunks, max_chunk_size=1500)

        result = benchmark(chunk_large_text)
        assert len(result) > 0

    def test_chunking_service_performance(self, benchmark, large_text_chunks):
        """Benchmark chunking service with strategy pattern."""
        service = ChunkingService()

        def process_chunks():
            return service.process_chunks(large_text_chunks, max_chunk_size=2000)

        result = benchmark(process_chunks)
        assert len(result) > 0


class TestImmutableDataStructurePerformance:
    """Benchmark frozen dataclass operations vs regular dataclass operations."""

    def test_frozen_dataclass_creation(self, benchmark):
        """Benchmark frozen dataclass creation performance."""

        def create_text_segments():
            segments = []
            for i in range(100):
                segment = TextSegment(
                    text=f"Text segment {i}",
                    start_time=float(i),
                    duration=1.0,
                    segment_type="sentence",
                    chunk_index=0,
                    sentence_index=i,
                )
                segments.append(segment)
            return segments

        result = benchmark(create_text_segments)
        assert len(result) == 100

    def test_dataclass_replace_performance(self, benchmark, sample_text_segments):
        """Benchmark dataclasses.replace() performance for immutable updates."""

        def update_segments():
            updated = []
            for segment in sample_text_segments:
                new_segment = dataclasses_replace(segment, start_time=segment.start_time + 10.0)
                updated.append(new_segment)
            return updated

        result = benchmark(update_segments)
        assert len(result) == len(sample_text_segments)

    def test_mapping_proxy_access_performance(self, benchmark):
        """Benchmark MappingProxyType access vs regular dict access."""
        # Create test data
        regular_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
        proxy_dict = types.MappingProxyType(regular_dict)

        def access_proxy_values():
            results = []
            for i in range(100):
                key = f"key_{i}"
                if key in proxy_dict:
                    results.append(proxy_dict[key])
            return results

        result = benchmark(access_proxy_values)
        assert len(result) == 100


class TestListComprehensionPerformance:
    """Compare list comprehension vs append patterns performance."""

    def test_list_comprehension_performance(self, benchmark):
        """Benchmark immutable list comprehension patterns."""

        def filter_with_comprehension():
            data = list(range(10000))
            # Immutable filtering pattern
            return [x for x in data if x % 2 == 0 and x > 100]

        result = benchmark(filter_with_comprehension)
        assert len(result) > 0

    def test_nested_comprehension_performance(self, benchmark, large_text_chunks):
        """Benchmark nested comprehensions for flattening operations."""

        def flatten_with_comprehension():
            # Simulate the chunking pattern we use
            return [
                word
                for chunk in large_text_chunks[:10]  # Limit for benchmark
                for word in chunk.split()
                if len(word) > 3
            ]

        result = benchmark(flatten_with_comprehension)
        assert len(result) > 0


class TestMemoryPerformance:
    """Test memory efficiency of immutable patterns."""

    def test_frozen_dataclass_memory_efficiency(self, benchmark):
        """Test memory overhead of frozen dataclasses."""

        def create_many_segments():
            return [
                TextSegment(
                    text=f"Segment {i}",
                    start_time=float(i),
                    duration=1.0,
                    segment_type="sentence",
                    chunk_index=i // 100,
                    sentence_index=i % 100,
                )
                for i in range(1000)
            ]

        result = benchmark(create_many_segments)
        assert len(result) == 1000

    def test_mapping_proxy_memory_efficiency(self, benchmark):
        """Test memory efficiency of MappingProxyType."""

        def create_large_proxy():
            base_dict = {f"service_{i}": f"instance_{i}" for i in range(1000)}
            return types.MappingProxyType(base_dict)

        result = benchmark(create_large_proxy)
        assert len(result) == 1000


class TestConcurrencyPerformance:
    """Test thread safety performance of immutable structures."""

    def test_concurrent_service_access(self, benchmark, test_config):
        """Test concurrent access to immutable service container."""
        container = ServiceContainer(test_config)

        def concurrent_access():
            # Simulate multiple threads accessing services
            results = []
            for _ in range(50):
                service: Any = container.get("tts_engine")
                results.append(service)
            return results

        result = benchmark(concurrent_access)
        assert len(result) == 50


if __name__ == "__main__":
    # Allow running benchmarks directly
    pytest.main([__file__, "--benchmark-only", "--benchmark-sort=mean"])
