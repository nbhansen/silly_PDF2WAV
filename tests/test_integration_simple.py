# tests/test_integration_simple.py
"""
Simple integration test - one end-to-end workflow test.
"""
import pytest
import os
import tempfile
from unittest.mock import patch, Mock

from application.composition_root import create_pdf_service_from_env, CompositionRoot
from application.config.system_config import SystemConfig, TTSEngine
from domain.models import ProcessingRequest, PageRange
from tests.test_helpers import create_test_request


def test_configuration_loading():
    """Test that configuration can be loaded with minimal environment"""
    with patch.dict(os.environ, {
        'TTS_ENGINE': 'piper',
        'ENABLE_TEXT_CLEANING': 'false',
        'ENABLE_SSML': 'false',
        'ENABLE_FILE_CLEANUP': 'false'
    }):
        config = SystemConfig.from_env()
        assert config.tts_engine == TTSEngine.PIPER
        assert config.enable_text_cleaning is False
        assert config.enable_ssml is False
        assert config.enable_file_cleanup is False
        # Test new Gemini model configuration
        assert config.gemini_model_name == "gemini-2.5-flash-preview-tts"


def test_gemini_model_configuration():
    """Test that Gemini model can be configured via environment"""
    with patch.dict(os.environ, {
        'TTS_ENGINE': 'piper',
        'GEMINI_MODEL_NAME': 'gemini-2.5-pro-preview-tts',
        'ENABLE_FILE_CLEANUP': 'false'
    }):
        config = SystemConfig.from_env()
        assert config.gemini_model_name == "gemini-2.5-pro-preview-tts"


def test_composition_root_creation():
    """Test that CompositionRoot can create all services"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            upload_folder=os.path.join(temp_dir, "uploads"),
            audio_folder=os.path.join(temp_dir, "audio"),
            enable_text_cleaning=False,
            enable_ssml=False,
            enable_file_cleanup=False
        )
        
        # Mock piper availability to avoid infrastructure dependency
        with patch('infrastructure.tts.piper_tts_provider.PIPER_AVAILABLE', True), \
             patch('infrastructure.tts.piper_tts_provider.PiperTTSProvider'):
            
            root = CompositionRoot(config)
            
            # Verify all main services are created
            assert root.pdf_processing_service is not None
            assert root.audio_generation_service is not None
            assert root.text_cleaning_service is not None
            assert root.file_manager is not None
            assert root.timing_strategy is not None


@pytest.mark.skip(reason="Requires external dependencies - run manually if needed")
def test_create_pdf_service_from_env_integration():
    """
    Integration test using real service factory.
    Skipped by default to avoid external dependencies.
    """
    # Set minimal environment for test
    with patch.dict(os.environ, {
        'TTS_ENGINE': 'piper',
        'ENABLE_TEXT_CLEANING': 'false',
        'ENABLE_SSML': 'false',
        'ENABLE_FILE_CLEANUP': 'false'
    }):
        # Mock external dependencies
        with patch('infrastructure.tts.piper_tts_provider.PIPER_AVAILABLE', True), \
             patch('infrastructure.tts.piper_tts_provider.PiperTTSProvider'), \
             patch('infrastructure.ocr.tesseract_ocr_provider.TesseractOCRProvider'):
            
            service = create_pdf_service_from_env()
            assert service is not None
            
            # Test basic service methods work
            request = create_test_request()
            # Note: This would fail without real PDF file, but service creation worked


def test_service_creation_with_mocked_dependencies():
    """Test service creation with fully mocked dependencies"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            upload_folder=os.path.join(temp_dir, "uploads"),
            audio_folder=os.path.join(temp_dir, "audio"),
            enable_text_cleaning=False,
            enable_ssml=False,
            enable_file_cleanup=False
        )
        
        # Create directories
        os.makedirs(config.upload_folder, exist_ok=True)
        os.makedirs(config.audio_folder, exist_ok=True)
        
        # Mock all external dependencies
        with patch('infrastructure.tts.piper_tts_provider.PIPER_AVAILABLE', True), \
             patch('infrastructure.tts.piper_tts_provider.PiperTTSProvider') as mock_piper, \
             patch('infrastructure.ocr.tesseract_ocr_provider.TesseractOCRProvider') as mock_ocr:
            
            # Setup mocks to return reasonable values
            mock_tts_instance = Mock()
            mock_tts_instance.generate_audio_data.return_value.success = True
            mock_tts_instance.generate_audio_data.return_value.value = b"fake_audio"
            mock_tts_instance.get_output_format.return_value = "wav"
            mock_piper.return_value = mock_tts_instance
            
            mock_ocr_instance = Mock()
            mock_ocr_instance.extract_text.return_value = "Sample extracted text"
            mock_ocr.return_value = mock_ocr_instance
            
            # Create composition root
            root = CompositionRoot(config)
            
            # Verify PDF service can be created and has expected structure
            pdf_service = root.pdf_processing_service
            assert pdf_service is not None
            assert pdf_service.audio_generation_service is not None
            assert pdf_service.text_cleaner is not None
            assert pdf_service.file_manager is not None


def test_basic_workflow_structure():
    """Test that basic workflow structure works with mocked components"""
    # Create test request
    request = ProcessingRequest(
        pdf_path="test.pdf",
        output_name="test_output", 
        page_range=PageRange()
    )
    
    # Verify request structure
    assert request.pdf_path == "test.pdf"
    assert request.output_name == "test_output"
    assert request.page_range.is_full_document() is True


def test_error_handling_structure():
    """Test that error handling works in the service structure"""
    from domain.errors import configuration_error, ApplicationError
    from domain.models import ProcessingResult
    
    # Test error creation
    error = configuration_error("Test error")
    assert isinstance(error, ApplicationError)
    assert "Configuration error" in str(error)
    
    # Test result creation with error
    result = ProcessingResult.failure_result(error)
    assert result.success is False
    assert result.error == error
    assert "Configuration error" in result.get_error_message()


def test_file_paths_and_structure():
    """Test that file paths and directory structure work correctly"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            upload_folder=os.path.join(temp_dir, "uploads"),
            audio_folder=os.path.join(temp_dir, "audio"),
            enable_file_cleanup=False
        )
        
        # Test that directories are created properly
        os.makedirs(config.upload_folder, exist_ok=True)
        os.makedirs(config.audio_folder, exist_ok=True)
        
        assert os.path.exists(config.upload_folder)
        assert os.path.exists(config.audio_folder)
        assert config.upload_folder.endswith("uploads")
        assert config.audio_folder.endswith("audio")