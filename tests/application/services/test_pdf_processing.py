# tests/application/services/test_pdf_processing.py
import pytest
import os
from unittest.mock import patch
from application.services.pdf_processing import PDFProcessingService
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.audio_generation_service import AudioGenerationService
from tests.test_helpers import FakeTextExtractor, FakeLLMProvider, FakeTTSEngine, create_test_request

def create_test_service(**overrides):
    """Factory to create test service with fake dependencies"""
    fake_extractor = overrides.get('text_extractor', FakeTextExtractor())
    fake_llm = overrides.get('llm_provider', FakeLLMProvider())
    fake_tts = overrides.get('tts_engine', FakeTTSEngine())
    
    # Create real services but with fake providers
    text_cleaner = TextCleaningService(llm_provider=fake_llm)
    audio_generator = AudioGenerationService(tts_engine=fake_tts)
    
    return PDFProcessingService(
        text_extractor=fake_extractor,
        text_cleaner=text_cleaner,
        audio_generator=audio_generator,
        page_validator=fake_extractor,
        llm_provider=fake_llm,
        tts_engine=fake_tts
    )

def test_successful_processing(tmp_path):
    # Create a fake PDF file for path validation
    fake_pdf = tmp_path / "test.pdf"
    fake_pdf.write_text("fake pdf content")
    
    service = create_test_service()
    request = create_test_request(pdf_path=str(fake_pdf))
    
    # Mock file operations for audio generation
    with patch('os.makedirs'), \
         patch('builtins.open'), \
         patch('os.path.exists', return_value=True), \
         patch('os.path.getsize', return_value=1000):
        
        result = service.process_pdf(request)
    
    assert result.success == True
    assert result.audio_files is not None
    assert len(result.audio_files) > 0

def test_file_not_found():
    service = create_test_service()
    request = create_test_request(pdf_path="nonexistent.pdf")
    
    result = service.process_pdf(request)
    
    assert result.success == False
    assert "File not found" in result.error

def test_extraction_failure(tmp_path):
    fake_pdf = tmp_path / "test.pdf"
    fake_pdf.write_text("fake pdf content")
    
    failed_extractor = FakeTextExtractor(text_to_return="Error: OCR failed")
    service = create_test_service(text_extractor=failed_extractor)
    request = create_test_request(pdf_path=str(fake_pdf))
    
    result = service.process_pdf(request)
    
    assert result.success == False
    assert "Text extraction failed" in result.error

def test_tts_failure(tmp_path):
    fake_pdf = tmp_path / "test.pdf"
    fake_pdf.write_text("fake pdf content")
    
    failed_tts = FakeTTSEngine(should_fail=True)
    service = create_test_service(tts_engine=failed_tts)
    request = create_test_request(pdf_path=str(fake_pdf))
    
    with patch('os.makedirs'), \
         patch('builtins.open'), \
         patch('os.path.exists', return_value=True):
        
        result = service.process_pdf(request)
    
    assert result.success == False
    assert "Audio generation failed" in result.error

def test_get_pdf_info():
    service = create_test_service()
    pdf_info = service.get_pdf_info("test.pdf")
    
    assert pdf_info.total_pages == 1
    assert pdf_info.title == "Test PDF"
    assert pdf_info.author == "Test Author"

def test_validate_page_range():
    service = create_test_service()
    from domain.models import PageRange
    
    page_range = PageRange(start_page=1, end_page=1)
    result = service.validate_page_range("test.pdf", page_range)
    
    assert result['valid'] == True
    assert result['total_pages'] == 1