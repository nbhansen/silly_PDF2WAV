# tests/test_core_services.py
"""
Simple tests for core services using minimal mocking.
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from domain.services.audio_generation_service import AudioGenerationService
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.academic_ssml_service import AcademicSSMLService
from application.services.pdf_processing import PDFProcessingService
from domain.models import ProcessingRequest, PageRange, PDFInfo, TimedAudioResult
from tests.test_helpers import (
    FakeTimingStrategy, FakeTTSEngine, FakeLLMProvider, FakeTextExtractor,
    FakeFileManager, create_test_request
)


def test_audio_generation_service_creation():
    """Test AudioGenerationService can be created with current API"""
    timing_strategy = FakeTimingStrategy()
    service = AudioGenerationService(timing_strategy)
    
    assert service.timing_strategy == timing_strategy
    assert service.async_coordinator is None


def test_audio_generation_service_with_coordinator():
    """Test AudioGenerationService with async coordinator"""
    timing_strategy = FakeTimingStrategy()
    mock_coordinator = Mock()
    
    service = AudioGenerationService(timing_strategy, async_coordinator=mock_coordinator)
    
    assert service.timing_strategy == timing_strategy
    assert service.async_coordinator == mock_coordinator


def test_audio_generation_service_invalid_strategy():
    """Test AudioGenerationService rejects invalid timing strategy"""
    with pytest.raises(TypeError, match="timing_strategy must be an instance of ITimingStrategy"):
        AudioGenerationService("not_a_strategy")


def test_audio_generation_service_should_use_async():
    """Test should_use_async logic"""
    timing_strategy = FakeTimingStrategy()
    service = AudioGenerationService(timing_strategy)
    
    # Test with fake TTS engine (should default to sync)
    fake_tts = FakeTTSEngine()
    assert service.should_use_async(fake_tts) is False


def test_text_cleaning_service_creation():
    """Test TextCleaningService can be created"""
    # Without LLM provider
    service = TextCleaningService(llm_provider=None)
    assert service.llm_provider is None
    
    # With LLM provider
    llm_provider = FakeLLMProvider()
    service_with_llm = TextCleaningService(llm_provider=llm_provider)
    assert service_with_llm.llm_provider == llm_provider


def test_text_cleaning_service_with_config():
    """Test TextCleaningService with config object"""
    config = Mock()
    config.llm_max_chunk_size = 50000
    config.audio_target_chunk_size = 2000
    config.audio_max_chunk_size = 4000
    
    service = TextCleaningService(llm_provider=None, config=config)
    
    assert service.max_chunk_size == 50000
    assert service.audio_target_chunk_size == 2000
    assert service.audio_max_chunk_size == 4000


def test_text_cleaning_service_strip_ssml():
    """Test SSML stripping functionality"""
    service = TextCleaningService(llm_provider=None)
    
    ssml_text = '<speak>Hello <break time="1s"/> world!</speak>'
    clean_text = service.strip_ssml(ssml_text)
    
    assert clean_text == "Hello world!"


def test_academic_ssml_service_creation():
    """Test AcademicSSMLService can be created"""
    fake_tts = FakeTTSEngine()
    service = AcademicSSMLService(fake_tts)
    assert service is not None


def test_pdf_processing_service_creation():
    """Test PDFProcessingService can be created with all dependencies"""
    # Create all the dependencies
    fake_ocr = FakeTextExtractor()
    fake_timing_strategy = FakeTimingStrategy()
    audio_service = AudioGenerationService(fake_timing_strategy)
    file_manager = FakeFileManager()
    text_cleaner = TextCleaningService(llm_provider=None)
    fake_tts = FakeTTSEngine()
    ssml_service = AcademicSSMLService(fake_tts)
    llm_provider = FakeLLMProvider()
    
    # Create the main service
    pdf_service = PDFProcessingService(
        ocr_provider=fake_ocr,
        audio_generation_service=audio_service,
        file_manager=file_manager,
        text_cleaner=text_cleaner,
        ssml_service=ssml_service,
        llm_provider=llm_provider
    )
    
    assert pdf_service.ocr_provider == fake_ocr
    assert pdf_service.audio_generation_service == audio_service
    assert pdf_service.file_manager == file_manager
    assert pdf_service.text_cleaner == text_cleaner
    assert pdf_service.ssml_service == ssml_service
    assert pdf_service.llm_provider == llm_provider


def test_pdf_processing_service_get_pdf_info():
    """Test PDF info delegation works"""
    # Set up fake OCR with specific PDF info
    pdf_info = PDFInfo(total_pages=10, title="Test Doc", author="Test Author")
    fake_ocr = FakeTextExtractor(pdf_info=pdf_info)
    
    # Create minimal service
    fake_timing_strategy = FakeTimingStrategy()
    audio_service = AudioGenerationService(fake_timing_strategy)
    file_manager = FakeFileManager()
    text_cleaner = TextCleaningService(llm_provider=None)
    fake_tts = FakeTTSEngine()
    ssml_service = AcademicSSMLService(fake_tts)
    
    pdf_service = PDFProcessingService(
        ocr_provider=fake_ocr,
        audio_generation_service=audio_service,
        file_manager=file_manager,
        text_cleaner=text_cleaner,
        ssml_service=ssml_service
    )
    
    # Test delegation
    result = pdf_service.get_pdf_info("test.pdf")
    assert result.total_pages == 10
    assert result.title == "Test Doc"
    assert result.author == "Test Author"


def test_pdf_processing_service_validate_page_range():
    """Test page range validation delegation"""
    fake_ocr = FakeTextExtractor()
    
    # Create minimal service
    fake_timing_strategy = FakeTimingStrategy()
    audio_service = AudioGenerationService(fake_timing_strategy)
    file_manager = FakeFileManager()
    text_cleaner = TextCleaningService(llm_provider=None)
    fake_tts = FakeTTSEngine()
    ssml_service = AcademicSSMLService(fake_tts)
    
    pdf_service = PDFProcessingService(
        ocr_provider=fake_ocr,
        audio_generation_service=audio_service,
        file_manager=file_manager,
        text_cleaner=text_cleaner,
        ssml_service=ssml_service
    )
    
    # Test delegation
    page_range = PageRange(start_page=1, end_page=3)
    result = pdf_service.validate_page_range("test.pdf", page_range)
    
    assert result['valid'] is True
    assert 'total_pages' in result


def test_timing_strategy_generate_with_timing():
    """Test basic timing strategy functionality"""
    timing_strategy = FakeTimingStrategy()
    
    result = timing_strategy.generate_with_timing(
        text_chunks=["First chunk", "Second chunk"],
        output_filename="test_output"
    )
    
    assert isinstance(result, TimedAudioResult)
    assert len(result.audio_files) == 2
    assert result.combined_mp3 == "test_output_combined.mp3"
    assert result.timing_data is not None
    assert result.timing_data.total_duration == 4.0  # 2 chunks * 2 seconds


def test_timing_strategy_failure_mode():
    """Test timing strategy failure handling"""
    timing_strategy = FakeTimingStrategy(should_fail=True)
    
    result = timing_strategy.generate_with_timing(
        text_chunks=["Test chunk"],
        output_filename="test_output"
    )
    
    assert isinstance(result, TimedAudioResult)
    assert result.audio_files == []
    assert result.combined_mp3 is None
    assert result.timing_data is None