# tests/conftest.py
"""
Simple, working test fixtures for PDF to Audio Converter.
No complex dependencies - just the basics that work.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def fake_pdf_file(temp_dir):
    """Create a fake PDF file for testing"""
    pdf_file = temp_dir / "test.pdf"
    pdf_file.write_text("This is fake PDF content for testing")
    return pdf_file


@pytest.fixture
def sample_text():
    """Sample text for testing"""
    return "This is sample text for testing text processing."


@pytest.fixture
def academic_text():
    """Sample academic text with typical research paper content"""
    return """
    This study examined 1,247 research articles published between 2020 and 2024.
    The analysis revealed a 73.2 percent improvement in processing efficiency.
    Statistical tests showed F(2, 47) = 15.3, p < 0.001, indicating significant results.
    However, further validation is needed to confirm these findings.
    Therefore, we recommend additional research in this area.
    """


@pytest.fixture
def mock_tts_engine():
    """Create a simple mock TTS engine"""
    mock_tts = MagicMock()
    mock_tts.generate_audio_data.return_value = b"fake_audio_data"
    mock_tts.get_output_format.return_value = "wav"
    mock_tts.prefers_sync_processing.return_value = True
    mock_tts.supports_ssml.return_value = True
    return mock_tts


@pytest.fixture
def mock_text_extractor():
    """Create a simple mock text extractor"""
    from domain.models import PDFInfo
    
    mock_extractor = MagicMock()
    mock_extractor.extract_text.return_value = "This is extracted text from a PDF document."
    mock_extractor.get_pdf_info.return_value = PDFInfo(
        total_pages=5, 
        title="Test Document", 
        author="Test Author"
    )
    return mock_extractor


@pytest.fixture
def mock_llm_provider():
    """Create a simple mock LLM provider"""
    mock_llm = MagicMock()
    mock_llm.generate_content.return_value = "This is cleaned and enhanced text with... natural pauses."
    return mock_llm


@pytest.fixture
def processing_request(fake_pdf_file):
    """Create a basic processing request"""
    from domain.models import ProcessingRequest, PageRange
    
    return ProcessingRequest(
        pdf_path=str(fake_pdf_file),
        output_name="test_output",
        page_range=PageRange()
    )


# Test markers for easy filtering
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "unit: Unit tests") 
    config.addinivalue_line("markers", "slow: Slow tests")