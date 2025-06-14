# tests/test_integration_fresh.py
"""
Fresh integration tests for PDF to Audio Converter.
Simple, clean tests that work with the current architecture.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Simple imports - no complex fixtures
from application.services.pdf_processing import PDFProcessingService
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.audio_generation_service import AudioGenerationService
from domain.models import ProcessingRequest, PageRange, PDFInfo


def test_can_create_processing_request():
    """Test we can create basic domain objects"""
    request = ProcessingRequest(
        pdf_path="test.pdf",
        output_name="test_output",
        page_range=PageRange(start_page=1, end_page=5)
    )
    
    assert request.pdf_path == "test.pdf"
    assert request.output_name == "test_output" 
    assert request.page_range.start_page == 1
    assert request.page_range.end_page == 5
    assert not request.page_range.is_full_document()


def test_can_create_services():
    """Test we can create the main services"""
    # Create simple mocks for dependencies
    mock_tts = MagicMock()
    mock_tts.generate_audio_data.return_value = b"fake_audio"
    mock_tts.get_output_format.return_value = "wav"
    
    mock_extractor = MagicMock()
    mock_extractor.extract_text.return_value = "Sample extracted text"
    mock_extractor.get_pdf_info.return_value = PDFInfo(total_pages=5, title="Test", author="Test")
    
    # Create services
    text_cleaner = TextCleaningService(llm_provider=None)
    audio_generator = AudioGenerationService(tts_engine=mock_tts)
    
    pdf_service = PDFProcessingService(
        text_extractor=mock_extractor,
        text_cleaner=text_cleaner,
        audio_generator=audio_generator,
        page_validator=mock_extractor,
        llm_provider=None,
        tts_engine=mock_tts
    )
    
    assert pdf_service is not None
    assert pdf_service.text_extractor == mock_extractor
    assert pdf_service.tts_engine == mock_tts


def test_configuration_loading():
    """Test that configuration loads correctly"""
    from application.config.system_config import SystemConfig, TTSEngine
    
    # Test configuration with environment variables
    test_env = {
        'TTS_ENGINE': 'piper',
        'ENABLE_TEXT_CLEANING': 'True',
        'ENABLE_SSML': 'True',
        'DOCUMENT_TYPE': 'research_paper'
    }
    
    with patch.dict(os.environ, test_env):
        config = SystemConfig.from_env()
        
        assert config.tts_engine == TTSEngine.PIPER
        assert config.enable_text_cleaning is True
        assert config.enable_ssml is True
        assert config.document_type == "research_paper"


def test_error_handling_structure():
    """Test that error handling works"""
    from domain.errors import ErrorCode, ApplicationError, file_not_found_error
    from domain.models import ProcessingResult
    
    # Test error creation
    error = file_not_found_error("missing.pdf")
    assert error.code == ErrorCode.FILE_NOT_FOUND
    assert "missing.pdf" in error.message
    assert error.retryable is False
    
    # Test ProcessingResult with error
    result = ProcessingResult.failure_result(error)
    assert result.success is False
    assert result.error == error
    assert result.get_error_code() == "file_not_found"


@patch('os.makedirs')
@patch('builtins.open')
@patch('os.path.exists')
def test_simple_pdf_processing_flow(mock_exists, mock_open, mock_makedirs):
    """Test a simple PDF processing flow end-to-end"""
    
    # Setup mocks
    mock_exists.return_value = True
    
    # Create mock components
    mock_extractor = MagicMock()
    mock_extractor.extract_text.return_value = "This is extracted text from the PDF."
    mock_extractor.get_pdf_info.return_value = PDFInfo(total_pages=1, title="Test", author="Test")
    
    mock_tts = MagicMock()
    mock_tts.generate_audio_data.return_value = b"fake_audio_data"
    mock_tts.get_output_format.return_value = "wav"
    
    # Create services
    text_cleaner = TextCleaningService(llm_provider=None)  # No LLM for simplicity
    audio_generator = AudioGenerationService(tts_engine=mock_tts)
    
    pdf_service = PDFProcessingService(
        text_extractor=mock_extractor,
        text_cleaner=text_cleaner,
        audio_generator=audio_generator,
        page_validator=mock_extractor,
        llm_provider=None,
        tts_engine=mock_tts
    )
    
    # Create request
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
        temp_pdf.write(b"fake pdf content")
        temp_pdf_path = temp_pdf.name
    
    request = ProcessingRequest(
        pdf_path=temp_pdf_path,
        output_name="test_output",
        page_range=PageRange()
    )
    
    try:
        # Process the PDF
        result = pdf_service.process_pdf(request)
        
        # Verify success
        assert result.success is True
        assert result.audio_files is not None
        assert len(result.audio_files) > 0
        
        # Verify components were called
        mock_extractor.extract_text.assert_called_once()
        mock_tts.generate_audio_data.assert_called()
        
        # Verify debug info
        assert result.debug_info is not None
        assert 'raw_text_length' in result.debug_info
        
    finally:
        # Cleanup
        os.unlink(temp_pdf_path)


def test_service_creation_from_config():
    """Test creating services from configuration"""
    
    test_env = {
        'TTS_ENGINE': 'piper',
        'GOOGLE_AI_API_KEY': 'test_key',
        'ENABLE_TEXT_CLEANING': 'True'
    }
    
    with patch.dict(os.environ, test_env):
        # Mock the TTS provider creation to avoid actual model loading
        with patch('infrastructure.tts.piper_tts_provider.PiperTTSProvider') as mock_piper:
            mock_piper_instance = MagicMock()
            mock_piper.return_value = mock_piper_instance
            
            with patch('infrastructure.llm.gemini_llm_provider.GeminiLLMProvider') as mock_gemini:
                mock_gemini_instance = MagicMock()
                mock_gemini.return_value = mock_gemini_instance
                
                from application.composition_root import create_pdf_service_from_env
                
                service = create_pdf_service_from_env()
                
                assert service is not None
                assert hasattr(service, 'text_extractor')
                assert hasattr(service, 'text_cleaner')
                assert hasattr(service, 'audio_generator')


def test_text_cleaning_service():
    """Test text cleaning service independently"""
    
    text_cleaner = TextCleaningService(llm_provider=None)
    
    input_text = "This is some test text.\n\nWith multiple paragraphs."
    result = text_cleaner.clean_text(input_text)
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(chunk, str) for chunk in result)


def test_audio_generation_service():
    """Test audio generation service independently"""
    
    mock_tts = MagicMock()
    mock_tts.generate_audio_data.return_value = b"mock_audio"
    mock_tts.get_output_format.return_value = "wav"
    
    audio_service = AudioGenerationService(tts_engine=mock_tts)
    
    with patch('os.makedirs'), \
         patch('builtins.open'), \
         patch('os.path.exists', return_value=False):  # Disable MP3 creation
        
        text_chunks = ["First chunk", "Second chunk"]
        audio_files, combined_mp3 = audio_service.generate_audio(
            text_chunks, "test_output", "test_audio_dir"
        )
        
        assert isinstance(audio_files, list)
        assert len(audio_files) == 2
        assert mock_tts.generate_audio_data.call_count == 2


def test_page_range_validation():
    """Test page range functionality"""
    
    # Test full document
    full_range = PageRange()
    assert full_range.is_full_document() is True
    
    # Test partial range
    partial_range = PageRange(start_page=2, end_page=10)
    assert partial_range.is_full_document() is False
    assert partial_range.start_page == 2
    assert partial_range.end_page == 10


def test_file_management_integration():
    """Test file management functionality if available"""
    
    try:
        from infrastructure.file.file_manager import LocalFileManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_manager = LocalFileManager(temp_dir)
            
            # Test getting stats
            stats = file_manager.get_stats()
            assert isinstance(stats, dict)
            assert 'total_files' in stats
            assert 'directory' in stats
            
    except ImportError:
        # File management not available, skip
        pytest.skip("File management not available")


if __name__ == "__main__":
    # Allow running this file directly for quick testing
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v"
    ])
    sys.exit(result.returncode)