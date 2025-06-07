# tests/test_processors.py - FIXED VERSION
import pytest
from application.services.pdf_processing import PDFProcessingService
from domain.models import ProcessingResult, TTSConfig, PageRange
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.audio_generation_service import AudioGenerationService
from domain.models import ProcessingRequest, PDFInfo

def test_pdf_processing_service_initialization(mocker):
    """Test PDFProcessingService initializes components"""
    mock_text_extractor = mocker.Mock(spec=TesseractOCRProvider)
    mock_text_cleaner = mocker.Mock(spec=TextCleaningService)
    mock_audio_generator = mocker.Mock(spec=AudioGenerationService)
    
    service = PDFProcessingService(
        text_extractor=mock_text_extractor,  # FIXED: was ocr_extractor
        text_cleaner=mock_text_cleaner,
        audio_generator=mock_audio_generator,
        page_validator=mock_text_extractor,  # ADDED: missing parameter
        llm_provider=None,  # ADDED: missing parameter
        tts_engine=None    # ADDED: missing parameter
    )
    
    assert service.text_extractor == mock_text_extractor
    assert service.text_cleaner == mock_text_cleaner
    assert service.audio_generator == mock_audio_generator

def test_process_pdf_file_not_found(mocker):
    """Test processing non-existent file"""
    mock_text_extractor = mocker.Mock(spec=TesseractOCRProvider)
    mock_text_cleaner = mocker.Mock(spec=TextCleaningService)
    mock_audio_generator = mocker.Mock(spec=AudioGenerationService)
    
    service = PDFProcessingService(
        text_extractor=mock_text_extractor,  # FIXED
        text_cleaner=mock_text_cleaner,
        audio_generator=mock_audio_generator,
        page_validator=mock_text_extractor,  # ADDED
        llm_provider=None,  # ADDED
        tts_engine=None    # ADDED
    )
    
    mocker.patch('os.path.exists', return_value=False)
    
    request = ProcessingRequest(pdf_path="nonexistent.pdf", output_name="output", page_range=PageRange())
    result = service.process_pdf(request)
    
    assert result.success == False
    assert "File not found" in result.error