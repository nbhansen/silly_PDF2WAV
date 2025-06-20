# tests/test_domain_models.py
"""
Simple tests for domain models - basic object creation and properties.
"""
import pytest
from datetime import datetime, timedelta
from domain.models import (
    PageRange, ProcessingRequest, PDFInfo, ProcessingResult, FileInfo, CleanupResult,
    TextSegment, TimingMetadata, TimedAudioResult
)
from domain.errors import configuration_error


def test_page_range_creation():
    """Test PageRange object creation and methods"""
    # Full document range
    full_range = PageRange()
    assert full_range.is_full_document() is True
    assert full_range.start_page is None
    assert full_range.end_page is None
    
    # Specific page range
    specific_range = PageRange(start_page=1, end_page=5)
    assert specific_range.is_full_document() is False
    assert specific_range.start_page == 1
    assert specific_range.end_page == 5


def test_processing_request_creation():
    """Test ProcessingRequest object creation"""
    page_range = PageRange(start_page=1, end_page=3)
    request = ProcessingRequest(
        pdf_path="/path/to/test.pdf",
        output_name="test_output",
        page_range=page_range
    )
    
    assert request.pdf_path == "/path/to/test.pdf"
    assert request.output_name == "test_output"
    assert request.page_range.start_page == 1
    assert request.page_range.end_page == 3


def test_pdf_info_creation():
    """Test PDFInfo object creation"""
    pdf_info = PDFInfo(total_pages=10, title="Test Document", author="Test Author")
    
    assert pdf_info.total_pages == 10
    assert pdf_info.title == "Test Document"
    assert pdf_info.author == "Test Author"


def test_processing_result_success():
    """Test successful ProcessingResult"""
    result = ProcessingResult.success_result(
        audio_files=["file1.wav", "file2.wav"],
        combined_mp3="combined.mp3",
        debug_info={"chunks": 2}
    )
    
    assert result.success is True
    assert result.is_retryable is False
    assert result.audio_files == ["file1.wav", "file2.wav"]
    assert result.combined_mp3_file == "combined.mp3"
    assert result.debug_info == {"chunks": 2}
    assert result.error is None
    assert result.get_error_code() is None


def test_processing_result_failure():
    """Test failed ProcessingResult"""
    error = configuration_error("Config invalid")
    result = ProcessingResult.failure_result(error)
    
    assert result.success is False
    assert result.is_retryable is False  # Config errors are not retryable
    assert result.audio_files is None
    assert result.combined_mp3_file is None
    assert result.error == error
    assert "Configuration error" in result.get_error_message()
    assert result.get_error_code() == "configuration_error"


def test_file_info_properties():
    """Test FileInfo object and its properties"""
    created_time = datetime.now() - timedelta(hours=2)
    file_info = FileInfo(
        filename="test.mp3",
        full_path="/tmp/test.mp3",
        size_bytes=2097152,  # 2 MB
        created_at=created_time
    )
    
    assert file_info.filename == "test.mp3"
    assert file_info.full_path == "/tmp/test.mp3"
    assert file_info.size_bytes == 2097152
    assert file_info.size_mb == 2.0
    assert abs(file_info.age_hours - 2.0) < 0.1  # Close to 2 hours


def test_cleanup_result():
    """Test CleanupResult object"""
    cleanup = CleanupResult(
        files_removed=3,
        bytes_freed=5242880,  # 5 MB
        errors=["Failed to delete file1.txt"]
    )
    
    assert cleanup.files_removed == 3
    assert cleanup.bytes_freed == 5242880
    assert cleanup.mb_freed == 5.0
    assert cleanup.errors == ["Failed to delete file1.txt"]


def test_text_segment():
    """Test TextSegment object and properties"""
    segment = TextSegment(
        text="This is a test sentence.",
        start_time=1.5,
        duration=3.0,
        segment_type="sentence",
        chunk_index=0,
        sentence_index=1
    )
    
    assert segment.text == "This is a test sentence."
    assert segment.start_time == 1.5
    assert segment.duration == 3.0
    assert segment.end_time == 4.5
    assert segment.segment_type == "sentence"
    assert segment.chunk_index == 0
    assert segment.sentence_index == 1


def test_timing_metadata():
    """Test TimingMetadata and segment lookup"""
    segments = [
        TextSegment("First sentence.", 0.0, 2.0, "sentence", 0, 0),
        TextSegment("Second sentence.", 2.0, 1.5, "sentence", 0, 1),
        TextSegment("Third sentence.", 3.5, 2.2, "sentence", 0, 2)
    ]
    
    metadata = TimingMetadata(
        total_duration=5.7,
        text_segments=segments,
        audio_files=["audio_part01.wav"]
    )
    
    assert metadata.total_duration == 5.7
    assert len(metadata.text_segments) == 3
    assert metadata.audio_files == ["audio_part01.wav"]
    
    # Test segment lookup
    assert metadata.get_segment_at_time(1.0).text == "First sentence."
    assert metadata.get_segment_at_time(2.5).text == "Second sentence."
    assert metadata.get_segment_at_time(4.0).text == "Third sentence."
    assert metadata.get_segment_at_time(10.0) is None  # Beyond end


def test_timed_audio_result():
    """Test TimedAudioResult with and without timing data"""
    # Without timing data
    result_no_timing = TimedAudioResult(
        audio_files=["test.wav"],
        combined_mp3="test.mp3"
    )
    
    assert result_no_timing.audio_files == ["test.wav"]
    assert result_no_timing.combined_mp3 == "test.mp3"
    assert result_no_timing.has_timing_data is False
    assert result_no_timing.timing_data is None
    
    # With timing data
    segments = [TextSegment("Test.", 0.0, 1.0, "sentence", 0, 0)]
    timing_data = TimingMetadata(1.0, segments, ["test.wav"])
    
    result_with_timing = TimedAudioResult(
        audio_files=["test.wav"],
        combined_mp3="test.mp3",
        timing_data=timing_data
    )
    
    assert result_with_timing.has_timing_data is True
    assert result_with_timing.timing_data.total_duration == 1.0