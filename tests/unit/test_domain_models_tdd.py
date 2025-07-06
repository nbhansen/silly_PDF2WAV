# tests/unit/test_domain_models_tdd.py
"""TDD tests for domain models - comprehensive coverage following red-green-refactor cycle.
Tests written first to drive implementation and ensure all edge cases are covered.
"""
from datetime import datetime, timedelta

import pytest

from domain.models import (
    CleanupResult,
    FileInfo,
    PageRange,
    PDFInfo,
    ProcessingRequest,
    ProcessingResult,
    TextSegment,
    TimedAudioResult,
    TimingMetadata,
)


class TestPageRange:
    """TDD tests for PageRange model - tests written first to drive behavior."""

    def test_default_page_range_is_full_document(self):
        """Should represent full document when no pages specified."""
        page_range = PageRange()
        assert page_range.is_full_document() is True
        assert page_range.start_page is None
        assert page_range.end_page is None

    def test_specific_page_range_is_not_full_document(self):
        """Should not be full document when specific pages are set."""
        page_range = PageRange(start_page=1, end_page=5)
        assert page_range.is_full_document() is False
        assert page_range.start_page == 1
        assert page_range.end_page == 5

    def test_partial_page_range_with_only_start_page(self):
        """Should not be full document when only start page is set."""
        page_range = PageRange(start_page=3)
        assert page_range.is_full_document() is False
        assert page_range.start_page == 3
        assert page_range.end_page is None

    def test_partial_page_range_with_only_end_page(self):
        """Should not be full document when only end page is set."""
        page_range = PageRange(end_page=10)
        assert page_range.is_full_document() is False
        assert page_range.start_page is None
        assert page_range.end_page == 10

    def test_page_range_equality(self):
        """Should support equality comparison."""
        range1 = PageRange(start_page=1, end_page=5)
        range2 = PageRange(start_page=1, end_page=5)
        range3 = PageRange(start_page=2, end_page=5)

        assert range1 == range2
        assert range1 != range3

    def test_page_range_validation_edge_cases(self):
        """Should handle edge cases in page ranges."""
        # Zero and negative pages should raise validation errors
        with pytest.raises(ValueError, match="start_page must be 1 or greater"):
            PageRange(start_page=0, end_page=0)

        with pytest.raises(ValueError, match="start_page must be 1 or greater"):
            PageRange(start_page=-1, end_page=5)


class TestProcessingRequest:
    """TDD tests for ProcessingRequest model."""

    def test_processing_request_creation_with_full_document(self):
        """Should create request for full document processing."""
        page_range = PageRange()
        request = ProcessingRequest(pdf_path="/path/to/document.pdf", output_name="audio_output", page_range=page_range)

        assert request.pdf_path == "/path/to/document.pdf"
        assert request.output_name == "audio_output"
        assert request.page_range.is_full_document() is True

    def test_processing_request_creation_with_specific_pages(self):
        """Should create request for specific page range."""
        page_range = PageRange(start_page=1, end_page=3)
        request = ProcessingRequest(pdf_path="/path/to/document.pdf", output_name="audio_output", page_range=page_range)

        assert request.pdf_path == "/path/to/document.pdf"
        assert request.output_name == "audio_output"
        assert request.page_range.start_page == 1
        assert request.page_range.end_page == 3

    def test_processing_request_with_empty_strings(self):
        """Should validate empty paths."""
        page_range = PageRange()

        # Empty pdf_path should raise validation error
        with pytest.raises(ValueError, match="pdf_path cannot be empty"):
            ProcessingRequest(pdf_path="", output_name="output", page_range=page_range)

    def test_processing_request_equality(self):
        """Should support equality comparison for requests."""
        page_range1 = PageRange(start_page=1, end_page=5)
        page_range2 = PageRange(start_page=1, end_page=5)

        request1 = ProcessingRequest("file.pdf", "output", page_range1)
        request2 = ProcessingRequest("file.pdf", "output", page_range2)
        request3 = ProcessingRequest("other.pdf", "output", page_range1)

        assert request1 == request2
        assert request1 != request3


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


class TestProcessingResult:
    """TDD tests for ProcessingResult model - comprehensive error handling tests."""

    def test_successful_processing_result_creation(self):
        """Should create successful result with audio files."""
        audio_files = ["file1.wav", "file2.wav"]
        result = ProcessingResult.success_result(audio_files=audio_files, combined_mp3="combined.mp3")

        assert result.success is True
        assert result.is_retryable is False
        assert result.audio_files == audio_files
        assert result.combined_mp3_file == "combined.mp3"
        assert result.error is None
        assert result.get_error_message() == "No error"
        assert result.get_error_code() is None

    def test_successful_result_with_timing_data(self):
        """Should create successful result with timing information."""
        from domain.models import TextSegment, TimingMetadata

        segments = [TextSegment("Hello world", 0.0, 1.0, "sentence", 0, 0)]
        timing_data = TimingMetadata(1.0, segments, ["audio.wav"])

        result = ProcessingResult.success_result(audio_files=["audio.wav"], timing_data=timing_data)

        assert result.success is True
        assert result.timing_data is not None
        assert result.timing_data.total_duration == 1.0

    def test_successful_result_with_debug_info(self):
        """Should create successful result with debug information."""
        debug_info = {"chunks_processed": 5, "total_duration": 120.5}
        result = ProcessingResult.success_result(audio_files=["output.wav"], debug_info=debug_info)

        assert result.success is True
        assert result.debug_info == debug_info

    def test_failed_processing_result_creation(self):
        """Should create failed result with error information."""
        from domain.errors import text_extraction_error

        error = text_extraction_error("Failed to extract text from PDF")
        result = ProcessingResult.failure_result(error)

        assert result.success is False
        assert result.is_retryable is True  # text extraction errors are typically retryable
        assert result.audio_files is None
        assert result.combined_mp3_file is None
        assert result.timing_data is None
        assert result.error == error
        assert "Failed to extract text from PDF" in result.get_error_message()
        assert result.get_error_code() is not None

    def test_processing_result_retryable_logic(self):
        """Should correctly determine if errors are retryable."""
        from domain.errors import audio_generation_error, configuration_error

        # Non-retryable error
        config_error = configuration_error("Invalid API key")
        non_retryable_result = ProcessingResult.failure_result(config_error)
        assert non_retryable_result.is_retryable is False

        # Retryable error
        audio_error = audio_generation_error("TTS service temporarily unavailable")
        retryable_result = ProcessingResult.failure_result(audio_error)
        assert retryable_result.is_retryable is True

    def test_processing_result_with_empty_audio_files(self):
        """Should handle empty audio files list."""
        result = ProcessingResult.success_result(audio_files=[])

        assert result.success is True
        assert result.audio_files == []

    def test_processing_result_immutability(self):
        """Should be immutable after creation."""
        audio_files = ["file1.wav"]
        result = ProcessingResult.success_result(audio_files=audio_files)

        # Modifying original list shouldn't affect result
        audio_files.append("file2.wav")
        assert result.audio_files is not None
        assert len(result.audio_files) == 1


class TestFileInfo:
    """TDD tests for FileInfo model - file management metadata."""

    def test_file_info_creation_with_recent_file(self):
        """Should create file info with proper metadata."""
        now = datetime.now()
        file_info = FileInfo(
            filename="test.wav", full_path="/audio/test.wav", size_bytes=1048576, created_at=now  # 1MB
        )

        assert file_info.filename == "test.wav"
        assert file_info.full_path == "/audio/test.wav"
        assert file_info.size_bytes == 1048576
        assert file_info.created_at == now
        assert file_info.last_accessed is None

    def test_file_info_size_conversion_to_mb(self):
        """Should correctly convert bytes to megabytes."""
        file_info = FileInfo(
            filename="large.wav", full_path="/audio/large.wav", size_bytes=5242880, created_at=datetime.now()  # 5MB
        )

        assert file_info.size_mb == 5.0

    def test_file_info_size_conversion_with_fractional_mb(self):
        """Should handle fractional megabytes correctly."""
        file_info = FileInfo(
            filename="small.wav", full_path="/audio/small.wav", size_bytes=1572864, created_at=datetime.now()  # 1.5MB
        )

        assert file_info.size_mb == 1.5

    def test_file_info_age_calculation(self):
        """Should calculate file age in hours correctly."""
        two_hours_ago = datetime.now() - timedelta(hours=2)
        file_info = FileInfo(filename="old.wav", full_path="/audio/old.wav", size_bytes=1024, created_at=two_hours_ago)

        age = file_info.age_hours
        assert 1.9 <= age <= 2.1  # Allow small tolerance for test execution time

    def test_file_info_with_zero_size(self):
        """Should handle zero-byte files."""
        file_info = FileInfo(filename="empty.txt", full_path="/tmp/empty.txt", size_bytes=0, created_at=datetime.now())

        assert file_info.size_mb == 0.0
        assert file_info.size_bytes == 0

    def test_file_info_with_last_accessed_time(self):
        """Should track last accessed time when provided."""
        created = datetime.now() - timedelta(hours=1)
        accessed = datetime.now() - timedelta(minutes=30)

        file_info = FileInfo(
            filename="accessed.wav",
            full_path="/audio/accessed.wav",
            size_bytes=2048,
            created_at=created,
            last_accessed=accessed,
        )

        assert file_info.last_accessed == accessed


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
