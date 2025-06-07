# tests/test_text_processing.py
import pytest
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from domain.services.text_cleaning_service import TextCleaningService
from domain.models import PDFInfo, ILLMProvider
import os

def test_tesseract_ocr_provider_get_pdf_info(mocker):
    """Test PDF info extraction using TesseractOCRProvider"""
    extractor = TesseractOCRProvider()
    
    # Mock pdfplumber to return known data
    mock_open = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open')
    # Create mock PDF object
    mock_pdf = mocker.Mock()
    mock_pdf.pages = [mocker.Mock(), mocker.Mock(), mocker.Mock()]  # 3 pages
    mock_pdf.metadata = {'Title': 'Test Paper', 'Author': 'Test Author'}
    mock_open.return_value.__enter__.return_value = mock_pdf
    
    result = extractor.get_pdf_info("test.pdf")
    
    assert result.total_pages == 3
    assert result.title == 'Test Paper'
    assert result.author == 'Test Author'

def test_tesseract_ocr_provider_error_handling(mocker):
    """Test TesseractOCRProvider handles errors gracefully"""
    extractor = TesseractOCRProvider()
    
    # Mock pdfplumber to raise an exception
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', side_effect=Exception("File not found"))
    result = extractor.get_pdf_info("nonexistent.pdf")
    
    assert result.total_pages == 0
    assert result.title == 'Unknown'
    assert result.author == 'Unknown'

def test_text_cleaning_service_no_llm_provider():
    """Test TextCleaningService fallback when no LLM provider provided"""
    cleaner = TextCleaningService(llm_provider=None)
    
    # Should use basic fallback
    result = cleaner.clean_text("This is test text.\n\nSecond paragraph.")
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert "..." in result[0]  # Should add pause markers

def test_text_cleaning_service_with_llm_provider(mocker):
    """Test TextCleaningService with an LLM provider"""
    mock_llm_provider = mocker.Mock(spec=ILLMProvider)
    mock_llm_provider.generate_content.return_value = "Cleaned text from LLM."
    
    cleaner = TextCleaningService(llm_provider=mock_llm_provider)
    
    result = cleaner.clean_text("Raw text to be cleaned.", llm_provider=mock_llm_provider)
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0] == "Cleaned text from LLM."
    mock_llm_provider.generate_content.assert_called_once()

def test_text_cleaning_service_handles_large_text_no_llm(mocker):
    """Test TextCleaningService can handle large text without breaking (no LLM)"""
    cleaner = TextCleaningService(llm_provider=None)
    
    # Create large text
    long_text = ("This is a sentence. " * 100 + "\n\n") * 100  # ~200,000 characters with paragraphs
    
    # Should not crash and should return a list
    result = cleaner.clean_text(long_text)
    
    assert isinstance(result, list)
    assert len(result) >= 1  # At least one chunk
    assert all(isinstance(chunk, str) for chunk in result)  # All chunks are strings
    assert all(len(chunk) > 0 for chunk in result)  # No empty chunks
    
    # Should add pause markers
    assert any("..." in chunk for chunk in result)

def test_text_cleaning_service_handles_large_text_with_llm(mocker):
    """Test TextCleaningService can handle large text with LLM"""
    mock_llm_provider = mocker.Mock(spec=ILLMProvider)
    mock_llm_provider.generate_content.side_effect = lambda x: f"Cleaned: {x}" # Simple mock for LLM
    
    cleaner = TextCleaningService(llm_provider=mock_llm_provider, max_chunk_size=1000) # Smaller max_chunk_size for testing
    
    long_text = ("This is a sentence. " * 10 + "\n\n") * 5 # ~1000 characters
    
    # Mock os.makedirs and open for debug file writing
    mocker.patch('os.makedirs')
    mocker.patch('builtins.open', mocker.mock_open())
    mocker.patch('os.path.exists', return_value=True)
    
    result = cleaner.clean_text(long_text)
    
    assert isinstance(result, list)
    assert len(result) >= 1
    assert all(isinstance(chunk, str) for chunk in result)
    assert all(len(chunk) > 0 for chunk in result)
    assert mock_llm_provider.generate_content.call_count > 0
    assert any("Cleaned:" in chunk for chunk in result)
    
    # Clean up debug files if they were created
    for i in range(mock_llm_provider.generate_content.call_count):
        debug_path = f"llm_tts_cleaned_chunk_{i+1}_debug.txt"
        if os.path.exists(debug_path):
            os.remove(debug_path)

def test_tesseract_ocr_provider_get_pdf_info_temp_file(mocker, tmp_path):
    """Test PDF info extraction using TesseractOCRProvider with a temporary file"""
    extractor = TesseractOCRProvider()
    
    # Create a temporary PDF file
    temp_pdf = tmp_path / "temp_test.pdf"
    temp_pdf.write_text("%PDF-1.4 mock PDF content")  # Mocking a simple PDF file
    
    # Mock pdfplumber to return known data
    mock_open = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open')
    # Create mock PDF object
    mock_pdf = mocker.Mock()
    mock_pdf.pages = [mocker.Mock(), mocker.Mock()]  # 2 pages
    mock_pdf.metadata = {'Title': 'Temp Test Paper', 'Author': 'Temp Author'}
    mock_open.return_value.__enter__.return_value = mock_pdf
    
    result = extractor.get_pdf_info(str(temp_pdf))
    
    assert result.total_pages == 2
    assert result.title == 'Temp Test Paper'
    assert result.author == 'Temp Author'

def test_tesseract_ocr_provider_error_handling_temp_file(mocker, tmp_path):
    """Test TesseractOCRProvider handles errors gracefully with a temporary file"""
    extractor = TesseractOCRProvider()
    
    # Create a temporary PDF file that is empty (simulating a non-existent file)
    temp_pdf = tmp_path / "empty_test.pdf"
    temp_pdf.write_text("")
    
    result = extractor.get_pdf_info(str(temp_pdf))
    
    assert result.total_pages == 0
    assert result.title == 'Unknown'
    assert result.author == 'Unknown'