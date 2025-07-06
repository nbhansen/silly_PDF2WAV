# tests/conftest.py
"""Professional test fixtures for PDF to Audio Converter
Simple, reliable fixtures that real development teams use.
"""

from pathlib import Path
import tempfile
from typing import Any
from unittest.mock import MagicMock

import pytest

from application.config.system_config import SystemConfig, TTSEngine
from domain.errors import Result
from domain.models import PageRange, PDFInfo, ProcessingRequest, TextSegment, TimedAudioResult, TimingMetadata

# === Core Test Fixtures ===


@pytest.fixture
def temp_dir():
    """Isolated temporary directory for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_dir):
    """Standard test configuration with safe defaults."""
    return SystemConfig(
        tts_engine=TTSEngine.PIPER,
        llm_model_name="test-llm-model",
        gemini_model_name="test-gemini-model",
        upload_folder=str(temp_dir / "uploads"),
        audio_folder=str(temp_dir / "audio"),
        enable_text_cleaning=False,  # Fast tests
        enable_ssml=False,  # Fast tests
        enable_file_cleanup=False,  # Don't interfere with tests
        gemini_api_key=None,  # No external dependencies
    )


@pytest.fixture
def sample_pdf_file(temp_dir):
    """Create a fake PDF file for testing."""
    pdf_file = temp_dir / "sample.pdf"
    # Create minimal PDF-like content
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 0\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    pdf_file.write_bytes(pdf_content)
    return str(pdf_file)


# === Text Fixtures ===


@pytest.fixture
def simple_text():
    """Simple text for basic testing."""
    return "Hello world. This is a test sentence."


@pytest.fixture
def academic_text():
    """Academic text with typical research paper elements."""
    return """
    This study examined the effectiveness of automated text processing.
    Results showed a significant improvement (p < 0.001) in processing speed.
    According to Smith et al. (2020), similar approaches have been successful.
    Therefore, we recommend this method for future implementations.
    """.strip()


@pytest.fixture
def complex_text():
    """Text with challenging elements for robust testing."""
    return """
    Dr. Johnson's research at MIT (2023) found 85.7% improvement rates.
    The F(2,47) = 15.3 test results were statistically significant.
    However, further validation with larger datasets is needed.
    Key findings include: (1) faster processing, (2) better accuracy.
    """.strip()


# === Mock Service Fixtures ===


@pytest.fixture
def mock_tts_engine():
    """Professional mock TTS engine with realistic behavior."""
    mock = MagicMock()

    def generate_audio_side_effect(text: str):
        # Simulate realistic audio generation
        audio_size = len(text) * 10  # 10 bytes per character
        return Result.success(b"fake_audio_" + b"x" * audio_size)

    mock.generate_audio_data.side_effect = generate_audio_side_effect
    mock.get_output_format.return_value = "wav"
    mock.prefers_sync_processing.return_value = True
    mock.supports_ssml.return_value = True

    return mock


@pytest.fixture
def mock_llm_provider():
    """Professional mock LLM provider."""
    mock = MagicMock()

    def clean_text_side_effect(text: str):
        # Simulate realistic text cleaning
        cleaned = text.replace("\n", " ").strip()
        cleaned += "... *pause*"  # Add realistic LLM enhancements
        return Result.success(cleaned)

    mock.generate_content.side_effect = clean_text_side_effect
    mock.process_text.side_effect = clean_text_side_effect

    return mock


@pytest.fixture
def mock_file_manager(temp_dir):
    """Professional mock file manager with real file operations."""
    mock = MagicMock()

    # Track files for cleanup
    created_files = []

    def save_output_file(content: bytes, filename: str) -> str:
        filepath = temp_dir / filename
        filepath.write_bytes(content)
        created_files.append(str(filepath))
        return str(filepath)

    def save_temp_file(content: bytes, suffix: str = ".tmp") -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=temp_dir) as f:
            f.write(content)
            created_files.append(f.name)
            return f.name

    mock.save_output_file.side_effect = save_output_file
    mock.save_temp_file.side_effect = save_temp_file
    mock.get_output_dir.return_value = str(temp_dir)
    mock.created_files = created_files

    return mock


@pytest.fixture
def mock_ocr_provider():
    """Professional mock OCR provider."""
    mock = MagicMock()

    mock.extract_text.return_value = "This is extracted text from the PDF document."
    mock.get_pdf_info.return_value = PDFInfo(total_pages=3, title="Sample Document", author="Test Author")

    return mock


# === Domain Model Fixtures ===


@pytest.fixture
def sample_processing_request(sample_pdf_file):
    """Standard processing request for testing."""
    return ProcessingRequest(pdf_path=sample_pdf_file, output_name="test_output", page_range=PageRange())


@pytest.fixture
def sample_text_segments():
    """Sample text segments with realistic timing."""
    return [
        TextSegment(
            text="First sentence of the document.",
            start_time=0.0,
            duration=2.1,
            segment_type="sentence",
            chunk_index=0,
            sentence_index=0,
        ),
        TextSegment(
            text="Second sentence with more content to process.",
            start_time=2.1,
            duration=3.2,
            segment_type="sentence",
            chunk_index=0,
            sentence_index=1,
        ),
        TextSegment(
            text="Final sentence to complete the test.",
            start_time=5.3,
            duration=2.8,
            segment_type="sentence",
            chunk_index=0,
            sentence_index=2,
        ),
    ]


@pytest.fixture
def sample_timing_metadata(sample_text_segments):
    """Sample timing metadata for audio testing."""
    return TimingMetadata(
        total_duration=8.1, text_segments=sample_text_segments, audio_files=["test_output_combined.wav"]
    )


@pytest.fixture
def sample_timed_audio_result(sample_timing_metadata):
    """Complete timed audio result for integration testing."""
    return TimedAudioResult(
        audio_files=["test_output_combined.wav"],
        combined_mp3="test_output_combined.wav",
        timing_data=sample_timing_metadata,
    )


# === Professional Test Utilities ===


@pytest.fixture
def assert_audio_quality():
    """Utility for asserting audio output quality."""

    def _assert_audio_quality(audio_data: bytes, min_size: int = 100) -> None:
        assert audio_data is not None, "Audio data should not be None"
        assert len(audio_data) >= min_size, f"Audio data too small: {len(audio_data)} bytes"
        assert audio_data.startswith(b"fake_audio_") or b"RIFF" in audio_data[:20], "Invalid audio format"

    return _assert_audio_quality


@pytest.fixture
def assert_timing_accuracy():
    """Utility for asserting timing accuracy."""

    def _assert_timing_accuracy(segments: list[Any], tolerance: float = 0.1) -> None:
        for i, segment in enumerate(segments):
            assert segment.duration > 0, f"Segment {i} has invalid duration: {segment.duration}"
            assert segment.start_time >= 0, f"Segment {i} has negative start time: {segment.start_time}"

            if i > 0:
                prev_end = segments[i - 1].start_time + segments[i - 1].duration
                current_start = segment.start_time
                gap = abs(current_start - prev_end)
                assert gap <= tolerance, f"Timing gap too large between segments {i-1} and {i}: {gap}s"

    return _assert_timing_accuracy


# === pytest Configuration ===


def pytest_configure(config):
    """Configure pytest with professional markers."""
    config.addinivalue_line("markers", "unit: Fast unit tests with no external dependencies")
    config.addinivalue_line("markers", "integration: Integration tests with mocked external services")
    config.addinivalue_line("markers", "external: Tests requiring real external services (manual)")
    config.addinivalue_line("markers", "slow: Tests taking more than 5 seconds")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on location."""
    for item in items:
        # Auto-mark tests based on directory
        if "unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark external dependency tests
        if hasattr(item, "fixturenames") and any(
            "real_" in fixture or "external_" in fixture for fixture in item.fixturenames
        ):
            item.add_marker(pytest.mark.external)


# === Cleanup ===


@pytest.fixture(autouse=True)
def cleanup_test_files(temp_dir):
    """Automatically clean up test files after each test."""
    return
    # Cleanup happens automatically with temp_dir fixture
