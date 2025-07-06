# tests/benchmarks/test_core_performance.py
"""Core performance benchmarks for immutable design patterns.
Focuses on the key refactored components.
"""

from dataclasses import replace as dataclasses_replace
import types

import pytest

from domain.models import TextSegment
from domain.text.chunking_strategy import SentenceBasedChunking, WordBasedChunking


# Test Data Setup
@pytest.fixture
def large_text_chunks():
    """Generate large text chunks for performance testing."""
    return [
        f"This is sentence {i} in a performance test. "
        + "It contains multiple words and punctuation marks for realistic chunking scenarios. "
        + "The goal is to measure the impact of immutable design patterns on text processing performance. "
        + "Each sentence should be long enough to trigger chunking logic appropriately." * 2
        for i in range(50)
    ]


@pytest.fixture
def sample_text_segments():
    """Generate sample text segments for timing engine benchmarks."""
    return [
        TextSegment(
            text=f"Sample text segment {i} for performance testing",
            start_time=float(i * 1.5),
            duration=1.2,
            segment_type="sentence",
            chunk_index=i // 10,
            sentence_index=i % 10,
        )
        for i in range(100)
    ]


class TestChunkingPerformance:
    """Benchmark immutable text chunking operations."""

    def test_sentence_chunking_immutable_pattern(self, benchmark, large_text_chunks):
        """Benchmark sentence-based chunking with immutable list comprehensions."""
        chunker = SentenceBasedChunking()

        def chunk_text():
            return chunker.chunk_text(large_text_chunks, max_chunk_size=1500)

        result = benchmark(chunk_text)
        assert len(result) >= len(large_text_chunks)  # Should create at least as many chunks

    def test_word_chunking_immutable_pattern(self, benchmark, large_text_chunks):
        """Benchmark word-based chunking with immutable patterns."""
        chunker = WordBasedChunking()

        def chunk_text():
            return chunker.chunk_text(large_text_chunks, max_chunk_size=1200)

        result = benchmark(chunk_text)
        assert len(result) >= len(large_text_chunks)


class TestDataStructurePerformance:
    """Benchmark frozen dataclass vs mutable alternatives."""

    def test_frozen_dataclass_creation_performance(self, benchmark):
        """Benchmark creation of frozen TextSegment dataclasses."""

        def create_frozen_segments():
            segments = [
                TextSegment(
                    text=f"Frozen segment {i}",
                    start_time=float(i),
                    duration=1.0,
                    segment_type="sentence",
                    chunk_index=i // 20,
                    sentence_index=i % 20,
                )
                for i in range(200)
            ]
            return segments

        result = benchmark(create_frozen_segments)
        assert len(result) == 200

    def test_dataclass_replace_vs_mutation_performance(self, benchmark, sample_text_segments):
        """Benchmark dataclasses.replace() for immutable updates."""

        def update_with_replace():
            updated_segments = [
                dataclasses_replace(segment, start_time=segment.start_time + 5.0) for segment in sample_text_segments
            ]
            return updated_segments

        result = benchmark(update_with_replace)
        assert len(result) == len(sample_text_segments)
        assert all(seg.start_time >= 5.0 for seg in result)


class TestMappingProxyPerformance:
    """Benchmark MappingProxyType vs regular dict performance."""

    def test_mapping_proxy_creation_performance(self, benchmark):
        """Benchmark creating MappingProxyType from large dict."""

        def create_proxy():
            base_dict = {f"service_{i}": f"factory_{i}" for i in range(500)}
            return types.MappingProxyType(base_dict)

        result = benchmark(create_proxy)
        assert len(result) == 500

    def test_mapping_proxy_lookup_performance(self, benchmark):
        """Benchmark lookups in MappingProxyType vs regular dict."""
        base_dict = {f"key_{i}": f"value_{i}" for i in range(1000)}
        proxy = types.MappingProxyType(base_dict)

        def lookup_from_proxy():
            results = []
            for i in range(0, 100, 2):  # Every other key
                key = f"key_{i}"
                if key in proxy:
                    results.append(proxy[key])
            return results

        result = benchmark(lookup_from_proxy)
        assert len(result) == 50


class TestListComprehensionPerformance:
    """Compare immutable list comprehensions vs append patterns."""

    def test_nested_comprehension_flattening(self, benchmark, large_text_chunks):
        """Benchmark nested comprehensions for text processing."""

        def flatten_words():
            # Pattern similar to our chunking strategy refactoring
            return [
                word.lower()
                for chunk in large_text_chunks
                for sentence in chunk.split(".")
                for word in sentence.split()
                if len(word) > 3
            ]

        result = benchmark(flatten_words)
        assert len(result) > 0

    def test_filter_comprehension_performance(self, benchmark):
        """Benchmark filtering with comprehensions."""
        data = list(range(5000))

        def filter_with_comprehension():
            return [x for x in data if x % 3 == 0 and x > 100]

        result = benchmark(filter_with_comprehension)
        assert len(result) > 0


class TestMemoryEfficiency:
    """Test memory efficiency of immutable patterns."""

    def test_large_frozen_dataclass_creation(self, benchmark):
        """Test creation of many frozen dataclasses."""

        def create_many_segments():
            return [
                TextSegment(
                    text=f"Memory test segment {i}",
                    start_time=float(i * 0.5),
                    duration=0.8,
                    segment_type="sentence",
                    chunk_index=i // 50,
                    sentence_index=i % 50,
                )
                for i in range(500)
            ]

        result = benchmark(create_many_segments)
        assert len(result) == 500

    def test_immutable_container_efficiency(self, benchmark):
        """Test efficiency of immutable containers."""

        def create_immutable_structures():
            # Create multiple immutable structures
            containers = []
            for batch in range(10):
                base_dict = {f"item_{i}": i * batch for i in range(100)}
                proxy = types.MappingProxyType(base_dict)
                containers.append(proxy)
            return containers

        result = benchmark(create_immutable_structures)
        assert len(result) == 10


if __name__ == "__main__":
    # Allow running benchmarks directly
    pytest.main([__file__, "--benchmark-only", "--benchmark-sort=mean"])
