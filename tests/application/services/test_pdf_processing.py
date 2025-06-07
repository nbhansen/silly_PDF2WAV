# tests/application/services/test_pdf_processing.py - FIXED VERSION

import pytest
import os
from unittest.mock import MagicMock, patch, mock_open

from application.services.pdf_processing import PDFProcessingService
from domain.models import ProcessingRequest, PageRange, PDFInfo
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.audio_generation_service import AudioGenerationService
from domain.models import ILLMProvider, ITTSEngine

# Fixture for a dummy PDF file
@pytest.fixture
def dummy_pdf_path(tmp_path):
    pdf_file = tmp_path / "dummy.pdf"
    # Create a minimal dummy PDF file for path existence checks
    # For actual content extraction, pdfplumber will be mocked
    pdf_file.write_text("%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000054 00000 n\n0000000107 00000 n\ntrailer<</Size 4/Root 1 0 R>>startxref\n176\n%%EOF")
    return str(pdf_file)

# Fixtures for mocked external dependencies
@pytest.fixture
def mock_llm_provider():
    mock = MagicMock(spec=ILLMProvider)
    mock.generate_content.return_value = "Cleaned text summary."
    return mock

@pytest.fixture
def mock_tts_engine():
    mock = MagicMock(spec=ITTSEngine)
    mock.generate_audio_data.return_value = b"dummy_audio_bytes"
    mock.get_output_format.return_value = "wav"
    return mock

# Fixtures for core service dependencies (minimally mocked where external calls occur)
@pytest.fixture
def mock_tesseract_ocr_provider():
    with patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open') as mock_pdfplumber_open:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Extracted text from PDF."
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {"Author": "Test Author", "Title": "Test Title"}
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf
        
        # Mock get_pdf_info to return a consistent PDFInfo object
        mock_ocr = TesseractOCRProvider()
        mock_ocr.get_pdf_info = MagicMock(return_value=PDFInfo(total_pages=1, title="Test Title", author="Test Author"))
        mock_ocr.validate_range = MagicMock(return_value={'valid': True, 'total_pages': 1})
        return mock_ocr

@pytest.fixture
def mock_text_cleaning_service():
    # TextCleaningService uses LLM, so we'll mock the LLM interaction within it
    service = TextCleaningService()
    service.clean_text = MagicMock(return_value=["Cleaned chunk 1.", "Cleaned chunk 2."])
    return service

@pytest.fixture
def mock_audio_generation_service(mock_tts_engine):  # FIXED: Added required dependency
    # AudioGenerationService uses TTS engine and file system operations
    service = AudioGenerationService(tts_engine=mock_tts_engine)  # FIXED: Pass tts_engine
    service.generate_audio = MagicMock(return_value=(["audio_outputs/chunk1.mp3", "audio_outputs/chunk2.mp3"], "audio_outputs/combined.mp3"))
    return service

# Fixture for PDFProcessingService with its dependencies
@pytest.fixture
def pdf_processing_service(
    mock_tesseract_ocr_provider,
    mock_text_cleaning_service,
    mock_audio_generation_service,
    mock_llm_provider,
    mock_tts_engine
):
    service = PDFProcessingService(
        text_extractor=mock_tesseract_ocr_provider,
        text_cleaner=mock_text_cleaning_service,
        audio_generator=mock_audio_generation_service,
        page_validator=mock_tesseract_ocr_provider, # TesseractOCRProvider now handles page validation
        llm_provider=mock_llm_provider,
        tts_engine=mock_tts_engine
    )
    return service

# Integration Tests
class TestPDFProcessingService:

    def test_successful_end_to_end_processing(self, pdf_processing_service, dummy_pdf_path, mocker):
        mock_extract_text = mocker.patch.object(pdf_processing_service.text_extractor, 'extract_text', return_value="Some extracted text")
        mock_clean_text = mocker.patch.object(pdf_processing_service.text_cleaner, 'clean_text', return_value=["Cleaned chunk 1.", "Cleaned chunk 2."])
        mock_generate_audio = mocker.patch.object(pdf_processing_service.audio_generator, 'generate_audio', return_value=(['audio_outputs/chunk1.mp3', 'audio_outputs/chunk2.mp3'], 'audio_outputs/combined.mp3'))

        request = ProcessingRequest(
            pdf_path=dummy_pdf_path,
            output_name="test_output",
            page_range=PageRange(start_page=1, end_page=1)
        )
        
        result = pdf_processing_service.process_pdf(request)
        
        assert result.success is True
        assert "audio_outputs/chunk1.mp3" in result.audio_files
        assert "audio_outputs/chunk2.mp3" in result.audio_files
        assert result.combined_mp3_file == "audio_outputs/combined.mp3"
        assert result.debug_info["raw_text_length"] > 0
        assert result.debug_info["text_chunks_count"] == 2
        assert result.debug_info["audio_files_count"] == 2
        assert result.debug_info["combined_mp3_created"] is True
        
        # Verify interactions with dependencies
        mock_extract_text.assert_called_once_with(
            dummy_pdf_path, PageRange(start_page=1, end_page=1)
        )
        mock_clean_text.assert_called_once()
        mock_generate_audio.assert_called_once()

    def test_file_not_found_error(self, pdf_processing_service):
        request = ProcessingRequest(
            pdf_path="/non/existent/path/file.pdf",
            output_name="test_output",
            page_range=PageRange()
        )
        
        result = pdf_processing_service.process_pdf(request)
        
        assert result.success is False
        assert "File not found" in result.error

    def test_text_extraction_failure(self, pdf_processing_service, dummy_pdf_path, mocker):
        mock_extract_text = mocker.patch.object(pdf_processing_service.text_extractor, 'extract_text', return_value="Error: OCR failed")
        mock_clean_text = mocker.patch.object(pdf_processing_service.text_cleaner, 'clean_text')
        mock_generate_audio = mocker.patch.object(pdf_processing_service.audio_generator, 'generate_audio')
        
        request = ProcessingRequest(
            pdf_path=dummy_pdf_path,
            output_name="test_output",
            page_range=PageRange()
        )
        
        result = pdf_processing_service.process_pdf(request)
        
        assert result.success is False
        assert "Text extraction failed" in result.error
        mock_extract_text.assert_called_once()
        mock_clean_text.assert_not_called()
        mock_generate_audio.assert_not_called()

    def test_text_cleaning_failure_empty_chunks(self, pdf_processing_service, dummy_pdf_path, mocker):
        mock_extract_text = mocker.patch.object(pdf_processing_service.text_extractor, 'extract_text', return_value="Some extracted text")
        mock_clean_text = mocker.patch.object(pdf_processing_service.text_cleaner, 'clean_text', return_value=[])
        mock_generate_audio = mocker.patch.object(pdf_processing_service.audio_generator, 'generate_audio')
        
        request = ProcessingRequest(
            pdf_path=dummy_pdf_path,
            output_name="test_output",
            page_range=PageRange()
        )
        
        result = pdf_processing_service.process_pdf(request)
        
        assert result.success is False
        assert "Text cleaning failed - no output from cleaner" in result.error
        mock_extract_text.assert_called_once()
        mock_clean_text.assert_called_once()
        mock_generate_audio.assert_not_called()

    def test_audio_generation_failure_no_files(self, pdf_processing_service, dummy_pdf_path, mocker):
        mock_extract_text = mocker.patch.object(pdf_processing_service.text_extractor, 'extract_text', return_value="Some extracted text")
        mock_clean_text = mocker.patch.object(pdf_processing_service.text_cleaner, 'clean_text', return_value=["Cleaned chunk 1."])
        mock_generate_audio = mocker.patch.object(pdf_processing_service.audio_generator, 'generate_audio', return_value=([], None))
        
        request = ProcessingRequest(
            pdf_path=dummy_pdf_path,
            output_name="test_output",
            page_range=PageRange()
        )
        
        result = pdf_processing_service.process_pdf(request)
        
        assert result.success is False
        assert "Audio generation failed - no audio files produced" in result.error
        mock_extract_text.assert_called_once()
        mock_clean_text.assert_called_once()
        mock_generate_audio.assert_called_once()

    def test_processing_with_specific_page_range(self, pdf_processing_service, dummy_pdf_path, mocker):
        mock_extract_text = mocker.patch.object(pdf_processing_service.text_extractor, 'extract_text', return_value="Some extracted text")
        mock_clean_text = mocker.patch.object(pdf_processing_service.text_cleaner, 'clean_text', return_value=["Cleaned chunk 1."])
        mock_generate_audio = mocker.patch.object(pdf_processing_service.audio_generator, 'generate_audio', return_value=(['audio_outputs/chunk1.mp3'], 'audio_outputs/combined.mp3'))
        
        request = ProcessingRequest(
            pdf_path=dummy_pdf_path,
            output_name="test_output_pages",
            page_range=PageRange(start_page=1, end_page=1)
        )
        
        result = pdf_processing_service.process_pdf(request)
        
        assert result.success is True
        assert result.debug_info["page_range"]["start_page"] == 1
        assert result.debug_info["page_range"]["end_page"] == 1
        assert result.debug_info["page_range"]["range_description"] == "1-1"
        mock_extract_text.assert_called_once_with(
            dummy_pdf_path, PageRange(start_page=1, end_page=1)
        )
        mock_clean_text.assert_called_once()
        mock_generate_audio.assert_called_once()

    def test_processing_with_full_document_page_range(self, pdf_processing_service, dummy_pdf_path, mocker):
        mock_extract_text = mocker.patch.object(pdf_processing_service.text_extractor, 'extract_text', return_value="Some extracted text")
        mock_clean_text = mocker.patch.object(pdf_processing_service.text_cleaner, 'clean_text', return_value=["Cleaned chunk 1."])
        mock_generate_audio = mocker.patch.object(pdf_processing_service.audio_generator, 'generate_audio', return_value=(['audio_outputs/chunk1.mp3'], 'audio_outputs/combined.mp3'))
        
        request = ProcessingRequest(
            pdf_path=dummy_pdf_path,
            output_name="test_output_full",
            page_range=PageRange() # Default is full document
        )
        
        result = pdf_processing_service.process_pdf(request)
        
        assert result.success is True
        assert result.debug_info["page_range"] == "full_document"
        mock_extract_text.assert_called_once_with(
            dummy_pdf_path, PageRange()
        )
        mock_clean_text.assert_called_once()
        mock_generate_audio.assert_called_once()

    def test_get_pdf_info_delegation(self, pdf_processing_service, dummy_pdf_path, mocker):
        mock_get_pdf_info = mocker.patch.object(pdf_processing_service.text_extractor, 'get_pdf_info', return_value=PDFInfo(total_pages=1, title="Test Title", author="Test Author"))
        pdf_info = pdf_processing_service.get_pdf_info(dummy_pdf_path)
        
        assert pdf_info.total_pages == 1
        assert pdf_info.title == "Test Title"
        assert pdf_info.author == "Test Author"
        mock_get_pdf_info.assert_called_once_with(dummy_pdf_path)

    def test_validate_page_range_delegation(self, pdf_processing_service, dummy_pdf_path, mocker):
        mock_validate_range = mocker.patch.object(pdf_processing_service.page_validator, 'validate_range', return_value={'valid': True, 'total_pages': 1})
        page_range = PageRange(start_page=1, end_page=1)
        validation_result = pdf_processing_service.validate_page_range(dummy_pdf_path, page_range)
        
        assert validation_result['valid'] is True
        assert validation_result['total_pages'] == 1
        mock_validate_range.assert_called_once_with(dummy_pdf_path, page_range)

    def test_unexpected_exception_handling(self, pdf_processing_service, dummy_pdf_path, mocker):
        mock_extract_text = mocker.patch.object(pdf_processing_service.text_extractor, 'extract_text', return_value="Some extracted text")
        mock_clean_text = mocker.patch.object(pdf_processing_service.text_cleaner, 'clean_text', side_effect=Exception("Simulated unexpected error"))
        mock_generate_audio = mocker.patch.object(pdf_processing_service.audio_generator, 'generate_audio')
        
        request = ProcessingRequest(
            pdf_path=dummy_pdf_path,
            output_name="test_output",
            page_range=PageRange()
        )
        
        result = pdf_processing_service.process_pdf(request)
        
        assert result.success is False
        assert "Processing failed: Simulated unexpected error" in result.error
        mock_extract_text.assert_called_once()
        mock_clean_text.assert_called_once()
        mock_generate_audio.assert_not_called()