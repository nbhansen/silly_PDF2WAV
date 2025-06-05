# tests/test_processors.py
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processors import PDFProcessor, ProcessingResult
from tts_utils import TTSConfig

def test_pdf_processor_initialization():
    """Test PDFProcessor initializes components"""
    with patch('processors.OCRExtractor') as mock_ocr, \
         patch('processors.TextCleaner') as mock_cleaner, \
         patch('processors.TTSGenerator') as mock_tts:
        
        processor = PDFProcessor("test_api_key", "gtts", TTSConfig())
        
        mock_ocr.assert_called_once()
        mock_cleaner.assert_called_once_with("test_api_key")
        mock_tts.assert_called_once()

def test_process_pdf_file_not_found():
    """Test processing non-existent file"""
    processor = PDFProcessor("test_key")
    
    result = processor.process_pdf("nonexistent.pdf", "output")
    
    assert result.success == False
    assert "File not found" in result.error

def test_process_pdf_success():
    """Test successful PDF processing pipeline"""
    with patch('processors.os.path.exists', return_value=True), \
         patch('processors.OCRExtractor') as mock_ocr_class, \
         patch('processors.TextCleaner') as mock_cleaner_class, \
         patch('processors.TTSGenerator') as mock_tts_class:
        
        # Setup mocks
        mock_ocr = Mock()
        mock_ocr.extract.return_value = "Extracted text from PDF"
        mock_ocr_class.return_value = mock_ocr
        
        mock_cleaner = Mock()
        mock_cleaner.clean.return_value = ["Cleaned text chunk 1", "Cleaned text chunk 2"]
        mock_cleaner_class.return_value = mock_cleaner
        
        mock_tts = Mock()
        mock_tts.generate_from_chunks.return_value = (["audio1.wav", "audio2.wav"], "combined.mp3")
        mock_tts.engine_name = "gtts"
        mock_tts.ffmpeg_available = True
        mock_tts_class.return_value = mock_tts
        
        processor = PDFProcessor("test_key")
        result = processor.process_pdf("test.pdf", "output")
        
        assert result.success == True
        assert len(result.audio_files) == 2
        assert result.combined_mp3_file == "combined.mp3"
        assert result.debug_info["tts_engine"] == "gtts"

def test_process_pdf_extraction_failure():
    """Test handling of text extraction failure"""
    with patch('processors.os.path.exists', return_value=True), \
         patch('processors.OCRExtractor') as mock_ocr_class:
        
        mock_ocr = Mock()
        mock_ocr.extract.return_value = "Error: OCR failed"
        mock_ocr_class.return_value = mock_ocr
        
        processor = PDFProcessor("test_key")
        result = processor.process_pdf("test.pdf", "output")
        
        assert result.success == False
        assert "Text extraction failed" in result.error

def test_process_pdf_with_page_range():
    """Test PDF processing with page range"""
    with patch('processors.os.path.exists', return_value=True), \
         patch('processors.OCRExtractor') as mock_ocr_class, \
         patch('processors.TextCleaner') as mock_cleaner_class, \
         patch('processors.TTSGenerator') as mock_tts_class:
        
        mock_ocr = Mock()
        mock_ocr.extract.return_value = "Extracted text from pages 5-10"
        mock_ocr_class.return_value = mock_ocr
        
        mock_cleaner = Mock()
        mock_cleaner.clean.return_value = ["Cleaned page range text"]
        mock_cleaner_class.return_value = mock_cleaner
        
        mock_tts = Mock()
        mock_tts.generate_from_chunks.return_value = (["audio.wav"], None)
        mock_tts.engine_name = "gtts"
        mock_tts.ffmpeg_available = False
        mock_tts_class.return_value = mock_tts
        
        processor = PDFProcessor("test_key")
        result = processor.process_pdf("test.pdf", "output", start_page=5, end_page=10)
        
        assert result.success == True
        assert result.debug_info["page_range"]["start_page"] == 5
        assert result.debug_info["page_range"]["end_page"] == 10
        mock_ocr.extract.assert_called_once_with("test.pdf", 5, 10)

def test_process_pdf_cleaning_failure():
    """Test handling of text cleaning failure"""
    with patch('processors.os.path.exists', return_value=True), \
         patch('processors.OCRExtractor') as mock_ocr_class, \
         patch('processors.TextCleaner') as mock_cleaner_class:
        
        mock_ocr = Mock()
        mock_ocr.extract.return_value = "Valid extracted text"
        mock_ocr_class.return_value = mock_ocr
        
        mock_cleaner = Mock()
        mock_cleaner.clean.return_value = []  # Empty result
        mock_cleaner_class.return_value = mock_cleaner
        
        processor = PDFProcessor("test_key")
        result = processor.process_pdf("test.pdf", "output")
        
        assert result.success == False
        assert "Text cleaning failed" in result.error

def test_get_pdf_info_success():
    """Test getting PDF information"""
    with patch('processors.OCRExtractor') as mock_ocr_class:
        mock_ocr = Mock()
        mock_ocr.get_pdf_info.return_value = {
            'total_pages': 15,
            'title': 'Test Document',
            'author': 'Test Author'
        }
        mock_ocr_class.return_value = mock_ocr
        
        processor = PDFProcessor("test_key")
        info = processor.get_pdf_info("test.pdf")
        
        assert info['total_pages'] == 15
        assert info['title'] == 'Test Document'

def test_validate_page_range_success():
    """Test successful page range validation"""
    processor = PDFProcessor("test_key")
    
    # Mock get_pdf_info
    processor.get_pdf_info = Mock(return_value={'total_pages': 20})
    
    result = processor.validate_page_range("test.pdf", 5, 15)
    
    assert result['valid'] == True
    assert result['actual_start'] == 5
    assert result['actual_end'] == 15
    assert result['pages_to_process'] == 11