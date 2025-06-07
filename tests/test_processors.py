# tests/test_processors.py
import pytest
from application.services.pdf_processing import PDFProcessingService
from domain.models import ProcessingResult, TTSConfig, PageRange
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.audio_generation_service import AudioGenerationService
from domain.models import ProcessingRequest, PDFInfo

def test_pdf_processing_service_initialization(mocker):
    """Test PDFProcessingService initializes components"""
    mock_ocr_extractor = mocker.Mock(spec=TesseractOCRProvider)
    mock_text_cleaner = mocker.Mock(spec=TextCleaningService)
    mock_audio_generator = mocker.Mock(spec=AudioGenerationService)
    
    service = PDFProcessingService(
        ocr_extractor=mock_ocr_extractor,
        text_cleaner=mock_text_cleaner,
        audio_generator=mock_audio_generator
    )
    
    assert service.ocr_extractor == mock_ocr_extractor
    assert service.text_cleaner == mock_text_cleaner
    assert service.audio_generator == mock_audio_generator

def test_process_pdf_file_not_found(mocker):
    """Test processing non-existent file"""
    mock_ocr_extractor = mocker.Mock(spec=TesseractOCRProvider)
    mock_text_cleaner = mocker.Mock(spec=TextCleaningService)
    mock_audio_generator = mocker.Mock(spec=AudioGenerationService)
    
    service = PDFProcessingService(
        ocr_extractor=mock_ocr_extractor,
        text_cleaner=mock_text_cleaner,
        audio_generator=mock_audio_generator
    )
    
    mocker.patch('os.path.exists', return_value=False)
    
    request = ProcessingRequest(pdf_path="nonexistent.pdf", output_name="output", page_range=PageRange())
    result = service.process_pdf(request)
    
    assert result.success == False
    assert "File not found" in result.error

def test_process_pdf_success(mocker):
    """Test successful PDF processing pipeline"""
    mocker.patch('os.path.exists', return_value=True)
    
    mock_ocr_extractor = mocker.Mock(spec=TesseractOCRProvider)
    mock_ocr_extractor.extract_text.return_value = "Extracted text from PDF"
    mock_ocr_extractor.get_pdf_info.return_value = PDFInfo(total_pages=10, title="Test", author="Test")
    
    mock_text_cleaner = mocker.Mock(spec=TextCleaningService)
    mock_text_cleaner.clean_text.return_value = ["Cleaned text chunk 1", "Cleaned text chunk 2"]
    
    mock_audio_generator = mocker.Mock(spec=AudioGenerationService)
    mock_audio_generator.generate_audio.return_value = (["audio1.wav", "audio2.wav"], "combined.mp3")
    
    service = PDFProcessingService(
        ocr_extractor=mock_ocr_extractor,
        text_cleaner=mock_text_cleaner,
        audio_generator=mock_audio_generator
    )
    
    request = ProcessingRequest(pdf_path="test.pdf", output_name="output", page_range=PageRange())
    result = service.process_pdf(request)
    
    assert result.success == True
    assert len(result.audio_files) == 2
    assert result.combined_mp3_file == "combined.mp3"
    mock_ocr_extractor.extract_text.assert_called_once()
    mock_text_cleaner.clean_text.assert_called_once()
    mock_audio_generator.generate_audio.assert_called_once()

def test_process_pdf_extraction_failure(mocker):
    """Test handling of text extraction failure"""
    mocker.patch('os.path.exists', return_value=True)
    
    mock_ocr_extractor = mocker.Mock(spec=TesseractOCRProvider)
    mock_ocr_extractor.extract_text.side_effect = Exception("OCR failed")
    mock_ocr_extractor.get_pdf_info.return_value = PDFInfo(total_pages=10, title="Test", author="Test")
    
    mock_text_cleaner = mocker.Mock(spec=TextCleaningService)
    mock_audio_generator = mocker.Mock(spec=AudioGenerationService)
    
    service = PDFProcessingService(
        ocr_extractor=mock_ocr_extractor,
        text_cleaner=mock_text_cleaner,
        audio_generator=mock_audio_generator
    )
    
    request = ProcessingRequest(pdf_path="test.pdf", output_name="output", page_range=PageRange())
    result = service.process_pdf(request)
    
    assert result.success == False
    assert "Text extraction failed" in result.error

def test_process_pdf_with_page_range(mocker):
    """Test PDF processing with page range"""
    mocker.patch('os.path.exists', return_value=True)
    
    mock_ocr_extractor = mocker.Mock(spec=TesseractOCRProvider)
    mock_ocr_extractor.extract_text.return_value = "Extracted text from pages 5-10"
    mock_ocr_extractor.get_pdf_info.return_value = PDFInfo(total_pages=10, title="Test", author="Test")
    
    mock_text_cleaner = mocker.Mock(spec=TextCleaningService)
    mock_text_cleaner.clean_text.return_value = ["Cleaned page range text"]
    
    mock_audio_generator = mocker.Mock(spec=AudioGenerationService)
    mock_audio_generator.generate_audio.return_value = (["audio.wav"], None)
    
    service = PDFProcessingService(
        ocr_extractor=mock_ocr_extractor,
        text_cleaner=mock_text_cleaner,
        audio_generator=mock_audio_generator
    )
    
    request = ProcessingRequest(pdf_path="test.pdf", output_name="output", page_range=PageRange(start_page=5, end_page=10))
    result = service.process_pdf(request)
    
    assert result.success == True
    assert result.debug_info["page_range"]["start_page"] == 5
    assert result.debug_info["page_range"]["end_page"] == 10
    mock_ocr_extractor.extract_text.assert_called_once_with("test.pdf", PageRange(start_page=5, end_page=10))

def test_process_pdf_cleaning_failure(mocker):
    """Test handling of text cleaning failure"""
    mocker.patch('os.path.exists', return_value=True)
    
    mock_ocr_extractor = mocker.Mock(spec=TesseractOCRProvider)
    mock_ocr_extractor.extract_text.return_value = "Valid extracted text"
    mock_ocr_extractor.get_pdf_info.return_value = PDFInfo(total_pages=10, title="Test", author="Test")
    
    mock_text_cleaner = mocker.Mock(spec=TextCleaningService)
    mock_text_cleaner.clean_text.return_value = []  # Empty result
    
    mock_audio_generator = mocker.Mock(spec=AudioGenerationService)
    
    service = PDFProcessingService(
        ocr_extractor=mock_ocr_extractor,
        text_cleaner=mock_text_cleaner,
        audio_generator=mock_audio_generator
    )
    
    request = ProcessingRequest(pdf_path="test.pdf", output_name="output", page_range=PageRange())
    result = service.process_pdf(request)
    
    assert result.success == False
    assert "Text cleaning failed" in result.error

def test_get_pdf_info_success(mocker):
    """Test getting PDF information"""
    mock_ocr_extractor = mocker.Mock(spec=TesseractOCRProvider)
    mock_ocr_extractor.get_pdf_info.return_value = PDFInfo(
        total_pages=15,
        title='Test Document',
        author='Test Author'
    )
    
    mock_text_cleaner = mocker.Mock(spec=TextCleaningService)
    mock_audio_generator = mocker.Mock(spec=AudioGenerationService)
    
    service = PDFProcessingService(
        ocr_extractor=mock_ocr_extractor,
        text_cleaner=mock_text_cleaner,
        audio_generator=mock_audio_generator
    )
    
    info = service.get_pdf_info("test.pdf")
    
    assert info.total_pages == 15
    assert info.title == 'Test Document'
    mock_ocr_extractor.get_pdf_info.assert_called_once_with("test.pdf")

def test_validate_page_range_success(mocker):
    """Test successful page range validation"""
    mock_ocr_extractor = mocker.Mock(spec=TesseractOCRProvider)
    mock_ocr_extractor.validate_range.return_value = {
        'valid': True,
        'actual_start': 5,
        'actual_end': 15,
        'pages_to_process': 11
    }
    
    mock_text_cleaner = mocker.Mock(spec=TextCleaningService)
    mock_audio_generator = mocker.Mock(spec=AudioGenerationService)
    
    service = PDFProcessingService(
        ocr_extractor=mock_ocr_extractor,
        text_cleaner=mock_text_cleaner,
        audio_generator=mock_audio_generator
    )
    
    page_range = PageRange(start_page=5, end_page=15)
    result = service.validate_page_range("test.pdf", page_range)
    
    assert result['valid'] == True
    assert result['actual_start'] == 5
    assert result['actual_end'] == 15
    assert result['pages_to_process'] == 11
    mock_ocr_extractor.validate_range.assert_called_once_with("test.pdf", page_range)