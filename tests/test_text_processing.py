# tests/test_text_processing.py
import sys
import os

# Add the parent directory to sys.path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_processing import OCRExtractor, TextCleaner
from unittest.mock import Mock, patch

def test_ocr_extractor_get_pdf_info():
    """Test PDF info extraction"""
    extractor = OCRExtractor()
    
    # Mock pdfplumber to return known data
    with patch('text_processing.pdfplumber.open') as mock_open:
        # Create mock PDF object
        mock_pdf = Mock()
        mock_pdf.pages = [Mock(), Mock(), Mock()]  # 3 pages
        mock_pdf.metadata = {'Title': 'Test Paper', 'Author': 'Test Author'}
        mock_open.return_value.__enter__.return_value = mock_pdf
        
        result = extractor.get_pdf_info("test.pdf")
        
        assert result['total_pages'] == 3
        assert result['title'] == 'Test Paper'
        assert result['author'] == 'Test Author'

def test_ocr_extractor_error_handling():
    """Test OCR extractor handles errors gracefully"""
    extractor = OCRExtractor()
    
    # Mock pdfplumber to raise an exception
    with patch('text_processing.pdfplumber.open', side_effect=Exception("File not found")):
        result = extractor.get_pdf_info("nonexistent.pdf")
        
        assert result['total_pages'] == 0
        assert result['title'] == 'Unknown'
        assert result['author'] == 'Unknown'

def test_text_cleaner_no_api_key():
    """Test TextCleaner fallback when no API key provided"""
    cleaner = TextCleaner("")  # Empty API key
    
    assert cleaner.model is None
    
    # Should use basic fallback
    result = cleaner.clean("This is test text.\n\nSecond paragraph.")
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert "..." in result[0]  # Should add pause markers

def test_text_cleaner_with_api_key():
    """Test TextCleaner initialization with API key"""
    # Mock the genai module to avoid real API calls
    with patch('text_processing.genai') as mock_genai:
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        cleaner = TextCleaner("fake_api_key")
        
        # Should have initialized model
        assert cleaner.model is not None
        mock_genai.configure.assert_called_once_with(api_key="fake_api_key")

def test_text_cleaner_handles_large_text():
    """Test TextCleaner can handle large text without breaking"""
    cleaner = TextCleaner("")  # No API key, will use fallback
    
    # Create large text 
    long_text = ("This is a sentence. " * 100 + "\n\n") * 100  # ~200,000 characters with paragraphs
    
    # Should not crash and should return a list
    result = cleaner.clean(long_text)
    
    assert isinstance(result, list)
    assert len(result) >= 1  # At least one chunk
    assert all(isinstance(chunk, str) for chunk in result)  # All chunks are strings
    assert all(len(chunk) > 0 for chunk in result)  # No empty chunks
    
    # Should add pause markers
    assert any("..." in chunk for chunk in result)