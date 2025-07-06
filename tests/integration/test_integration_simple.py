# tests/test_integration_simple.py
"""Simple integration test - focused on core service factory functionality."""
import tempfile
from unittest.mock import patch

from application.config.system_config import SystemConfig, TTSEngine
from domain.factories.service_factory import create_pdf_service_from_env
from domain.models import PageRange, ProcessingRequest


def create_test_config() -> SystemConfig:
    """Create a minimal SystemConfig for testing."""
    return SystemConfig(
        tts_engine=TTSEngine.PIPER,
        llm_model_name="test-llm-model",
        gemini_model_name="test-gemini-model",
        enable_text_cleaning=False,
        enable_ssml=False,
        enable_file_cleanup=False,
    )


def test_configuration_loading():
    """Test that configuration can be loaded with minimal setup."""
    config = create_test_config()
    assert config.tts_engine == TTSEngine.PIPER
    assert config.enable_text_cleaning is False
    assert config.enable_ssml is False
    assert config.enable_file_cleanup is False
    # Test new Gemini model configuration
    assert config.gemini_model_name == "test-gemini-model"


def test_service_factory_creation():
    """Test that service factory can create all services."""
    with tempfile.TemporaryDirectory():
        # Mock piper availability to avoid infrastructure dependency
        with (
            patch("infrastructure.tts.piper_tts_provider.PIPER_VOICE_AVAILABLE", True),
            patch("infrastructure.tts.piper_tts_provider.PiperTTSProvider"),
        ):

            config = create_test_config()
            container = create_pdf_service_from_env(config)

            # Verify all main services are available
            from domain.audio.audio_engine import IAudioEngine
            from domain.document.document_engine import IDocumentEngine
            from domain.text.text_pipeline import ITextPipeline
            from infrastructure.file.file_manager import FileManager

            assert container.get(IAudioEngine) is not None
            assert container.get(ITextPipeline) is not None
            assert container.get(IDocumentEngine) is not None
            assert container.get(FileManager) is not None


def test_basic_workflow_structure():
    """Test that basic workflow structure works with domain models."""
    # Create test request
    request = ProcessingRequest(pdf_path="test.pdf", output_name="test_output", page_range=PageRange())

    # Verify request structure
    assert request.pdf_path == "test.pdf"
    assert request.output_name == "test_output"
    assert request.page_range.is_full_document() is True


def test_error_handling_structure():
    """Test that error handling works in the service structure."""
    from domain.errors import ApplicationError, configuration_error
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
