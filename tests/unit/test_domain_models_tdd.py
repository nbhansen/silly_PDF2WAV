# tests/unit/test_domain_models_tdd.py
"""TDD tests for domain models - comprehensive coverage following red-green-refactor cycle.

Tests written first to drive implementation and ensure all edge cases are covered.
"""

from domain.models import (
    CleanupResult,
    PDFInfo,
    TextSegment,
    TimedAudioResult,
    TimingMetadata,
)


class TestPDFInfo:
    """TDD tests for PDFInfo model."""

    def test_pdf_info_creation_with_valid_data(self):
        """Should create PDF info with all required fields."""
        pdf_info = PDFInfo(total_pages=25, title="Research Paper Title", author="Dr. Jane Smith")

        assert pdf_info.total_pages == 25
        assert pdf_info.title == "Research Paper Title"
        assert pdf_info.author == "Dr. Jane Smith"

    def test_pdf_info_with_empty_metadata(self):
        """Should handle empty title and author."""
        pdf_info = PDFInfo(total_pages=10, title="", author="")

        assert pdf_info.total_pages == 10
        assert pdf_info.title == ""
        assert pdf_info.author == ""

    def test_pdf_info_with_zero_pages(self):
        """Should handle edge case of zero pages."""
        pdf_info = PDFInfo(total_pages=0, title="Empty Document", author="Unknown")

        assert pdf_info.total_pages == 0

    def test_pdf_info_with_unicode_content(self):
        """Should handle unicode characters in title and author."""
        pdf_info = PDFInfo(total_pages=5, title="Título en Español: José María", author="李小明")

        assert pdf_info.title == "Título en Español: José María"
        assert pdf_info.author == "李小明"


class TestCleanupResult:
    """TDD tests for CleanupResult model - file cleanup operations."""

    def test_cleanup_result_with_successful_cleanup(self):
        """Should create cleanup result with removal statistics."""
        result = CleanupResult(files_removed=5, bytes_freed=10485760, errors=[])  # 10MB

        assert result.files_removed == 5
        assert result.bytes_freed == 10485760
        assert result.mb_freed == 10.0
        assert result.errors == []

    def test_cleanup_result_with_errors(self):
        """Should track cleanup errors."""
        errors = ["Permission denied: /protected/file.wav", "File not found: /missing.mp3"]
        result = CleanupResult(files_removed=2, bytes_freed=5242880, errors=errors)

        assert result.files_removed == 2
        assert result.mb_freed == 5.0
        assert result.errors == errors
        assert len(result.errors) == 2

    def test_cleanup_result_with_no_files_removed(self):
        """Should handle case where no files were removed."""
        result = CleanupResult(files_removed=0, bytes_freed=0, errors=[])

        assert result.files_removed == 0
        assert result.bytes_freed == 0
        assert result.mb_freed == 0.0

    def test_cleanup_result_bytes_to_mb_conversion(self):
        """Should correctly convert bytes to megabytes."""
        result = CleanupResult(files_removed=1, bytes_freed=1572864, errors=[])  # 1.5MB

        assert result.mb_freed == 1.5


class TestTextSegment:
    """TDD tests for TextSegment model - timing and text segmentation."""

    def test_text_segment_creation(self):
        """Should create text segment with all timing information."""
        segment = TextSegment(
            text="This is a test sentence.",
            start_time=1.5,
            duration=2.3,
            segment_type="sentence",
            chunk_index=0,
            sentence_index=1,
        )

        assert segment.text == "This is a test sentence."
        assert segment.start_time == 1.5
        assert segment.duration == 2.3
        assert segment.segment_type == "sentence"
        assert segment.chunk_index == 0
        assert segment.sentence_index == 1
        assert segment.end_time == 3.8  # start_time + duration

    def test_text_segment_end_time_calculation(self):
        """Should calculate end time correctly."""
        segment = TextSegment(
            text="Short text.", start_time=0.0, duration=1.0, segment_type="sentence", chunk_index=0, sentence_index=0
        )

        assert segment.end_time == 1.0

    def test_text_segment_with_zero_duration(self):
        """Should handle very short duration segments."""
        segment = TextSegment(
            text="[pause]",  # Non-empty text for pause segments
            start_time=5.0,
            duration=0.001,  # Very small positive duration
            segment_type="sentence",  # Use valid segment type
            chunk_index=1,
            sentence_index=0,
        )

        assert segment.end_time == 5.001
        assert segment.duration == 0.001
        assert segment.text == "[pause]"

    def test_text_segment_types(self):
        """Should support different segment types."""
        sentence_segment = TextSegment("Sentence.", 0.0, 1.0, "sentence", 0, 0)
        paragraph_segment = TextSegment("Paragraph text.", 1.0, 3.0, "paragraph", 0, 1)
        heading_segment = TextSegment("Chapter 1", 4.0, 1.5, "heading", 1, 0)

        assert sentence_segment.segment_type == "sentence"
        assert paragraph_segment.segment_type == "paragraph"
        assert heading_segment.segment_type == "heading"

    def test_text_segment_with_unicode_text(self):
        """Should handle unicode text content."""
        segment = TextSegment(
            text="这是中文测试。Hello 世界!",
            start_time=0.0,
            duration=2.5,
            segment_type="sentence",
            chunk_index=0,
            sentence_index=0,
        )

        assert "中文" in segment.text
        assert "世界" in segment.text


class TestTimingMetadata:
    """TDD tests for TimingMetadata model - complete timing information."""

    def test_timing_metadata_creation(self):
        """Should create timing metadata with segments and duration."""
        segments = [
            TextSegment("First sentence.", 0.0, 1.5, "sentence", 0, 0),
            TextSegment("Second sentence.", 1.5, 2.0, "sentence", 0, 1),
        ]

        metadata = TimingMetadata(total_duration=3.5, text_segments=segments, audio_files=["output.wav"])

        assert metadata.total_duration == 3.5
        assert len(metadata.text_segments) == 2
        assert metadata.audio_files == ["output.wav"]

    def test_timing_metadata_get_segment_at_time_found(self):
        """Should find segment active at given time."""
        segments = [
            TextSegment("First.", 0.0, 2.0, "sentence", 0, 0),
            TextSegment("Second.", 2.0, 3.0, "sentence", 0, 1),
            TextSegment("Third.", 5.0, 2.0, "sentence", 0, 2),
        ]

        metadata = TimingMetadata(7.0, segments, ["audio.wav"])

        # Test finding segments at various times
        segment_1 = metadata.get_segment_at_time(1.0)
        assert segment_1 is not None
        assert segment_1.text == "First."

        segment_2 = metadata.get_segment_at_time(2.5)
        assert segment_2 is not None
        assert segment_2.text == "Second."

        segment_3 = metadata.get_segment_at_time(6.0)
        assert segment_3 is not None
        assert segment_3.text == "Third."

    def test_timing_metadata_get_segment_at_time_not_found(self):
        """Should return None when no segment is active at given time."""
        segments = [TextSegment("Only segment.", 1.0, 2.0, "sentence", 0, 0)]

        metadata = TimingMetadata(3.0, segments, ["audio.wav"])

        # Before segment starts
        assert metadata.get_segment_at_time(0.5) is None
        # After segment ends
        assert metadata.get_segment_at_time(3.5) is None

    def test_timing_metadata_get_segment_at_exact_boundaries(self):
        """Should handle exact boundary times correctly."""
        segments = [TextSegment("Test segment.", 1.0, 2.0, "sentence", 0, 0)]

        metadata = TimingMetadata(3.0, segments, ["audio.wav"])

        # At exact start time
        start_segment = metadata.get_segment_at_time(1.0)
        assert start_segment is not None
        assert start_segment.text == "Test segment."

        # At exact end time
        end_segment = metadata.get_segment_at_time(3.0)
        assert end_segment is not None
        assert end_segment.text == "Test segment."

    def test_timing_metadata_with_empty_segments(self):
        """Should handle empty segments list."""
        metadata = TimingMetadata(0.0, [], ["audio.wav"])

        assert len(metadata.text_segments) == 0
        assert metadata.get_segment_at_time(1.0) is None

    def test_timing_metadata_with_multiple_audio_files(self):
        """Should support multiple audio files."""
        segments = [TextSegment("Text.", 0.0, 1.0, "sentence", 0, 0)]
        audio_files = ["part1.wav", "part2.wav", "combined.mp3"]

        metadata = TimingMetadata(1.0, segments, audio_files)

        assert len(metadata.audio_files) == 3
        assert "part1.wav" in metadata.audio_files
        assert "combined.mp3" in metadata.audio_files


class TestTimedAudioResult:
    """TDD tests for TimedAudioResult model - audio with optional timing."""

    def test_timed_audio_result_without_timing_data(self):
        """Should create audio result without timing information."""
        result = TimedAudioResult(audio_files=["output.wav"], combined_mp3="output.mp3")

        assert result.audio_files == ["output.wav"]
        assert result.combined_mp3 == "output.mp3"
        assert result.timing_data is None
        assert result.has_timing_data is False

    def test_timed_audio_result_with_timing_data(self):
        """Should create audio result with timing information."""
        segments = [TextSegment("Hello.", 0.0, 1.0, "sentence", 0, 0)]
        timing_data = TimingMetadata(1.0, segments, ["output.wav"])

        result = TimedAudioResult(audio_files=["output.wav"], combined_mp3="output.mp3", timing_data=timing_data)

        assert result.has_timing_data is True
        assert result.timing_data is not None
        assert result.timing_data.total_duration == 1.0
        assert len(result.timing_data.text_segments) == 1

    def test_timed_audio_result_with_multiple_files(self):
        """Should handle multiple audio files."""
        audio_files = ["part1.wav", "part2.wav", "part3.wav"]
        result = TimedAudioResult(audio_files=audio_files, combined_mp3="combined.mp3")

        assert len(result.audio_files) == 3
        assert all(file in result.audio_files for file in audio_files)

    def test_timed_audio_result_without_combined_mp3(self):
        """Should handle case with no combined MP3 file."""
        result = TimedAudioResult(audio_files=["only.wav"], combined_mp3=None)

        assert result.audio_files == ["only.wav"]
        assert result.combined_mp3 is None

    def test_timed_audio_result_with_empty_audio_files(self):
        """Should handle empty audio files list."""
        result = TimedAudioResult(audio_files=[], combined_mp3=None)

        assert result.audio_files == []
        assert result.combined_mp3 is None
        assert result.has_timing_data is False
