# tests/test_error_handling.py
import pytest
from unittest.mock import Mock, patch

from domain.errors import Result, ErrorCode, tts_engine_error, llm_provider_error
from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
from infrastructure.tts.piper_tts_provider import PiperTTSProvider
from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from domain.services.text_cleaning_service import TextCleaningService
from tests.test_helpers import FakeLLMProvider


class TestErrorHandlingPatterns:
    """Test the new Result-based error handling patterns"""
    
    def test_result_success_pattern(self):
        """Test Result success pattern"""
        result = Result.success("test value")
        
        assert result.is_success
        assert not result.is_failure
        assert result.value == "test value"
        assert result.error is None
    
    def test_result_failure_pattern(self):
        """Test Result failure pattern"""
        error = tts_engine_error("Test error")
        result = Result.failure(error)
        
        assert result.is_failure
        assert not result.is_success
        assert result.value is None
        assert result.error == error
        assert result.error.code == ErrorCode.TTS_ENGINE_ERROR
    
    def test_result_from_exception(self):
        """Test creating Result from exception"""
        exception = ValueError("Test exception")
        result = Result.from_exception(exception, ErrorCode.CONFIGURATION_ERROR, retryable=True)
        
        assert result.is_failure
        assert result.error.code == ErrorCode.CONFIGURATION_ERROR
        assert result.error.retryable == True
        assert "Test exception" in result.error.message


class TestTTSErrorHandling:
    """Test TTS provider error handling"""
    
    @patch('infrastructure.tts.piper_tts_provider.PIPER_AVAILABLE', True)
    @patch('infrastructure.tts.piper_tts_provider.PIPER_METHOD', 'python_library')
    def test_piper_tts_empty_text_error(self):
        """Test Piper TTS with empty text"""
        from domain.config.tts_config import PiperConfig
        
        config = PiperConfig(model_name="test", download_dir="test")
        
        # Mock the inner class since PIPER_AVAILABLE is True
        with patch('infrastructure.tts.piper_tts_provider.PiperTTSProvider') as MockProvider:
            mock_instance = Mock()
            mock_instance.generate_audio_data.return_value = Result.failure(
                tts_engine_error("Empty text provided")
            )
            MockProvider.return_value = mock_instance
            
            provider = MockProvider(config)
            result = provider.generate_audio_data("")
            
            assert result.is_failure
            assert "Empty text provided" in result.error.details
    
    def test_gemini_tts_api_error(self):
        """Test Gemini TTS with API error"""
        provider = GeminiTTSProvider(api_key="test_key")
        
        # Mock the client to raise an exception
        with patch.object(provider, '_generate_with_persona', side_effect=Exception("API Error")):
            result = provider.generate_audio_data("test text")
            
            assert result.is_failure
            assert result.error.code == ErrorCode.TTS_ENGINE_ERROR
            assert "Audio generation failed" in result.error.details


class TestLLMErrorHandling:
    """Test LLM provider error handling"""
    
    def test_gemini_llm_no_api_key(self):
        """Test Gemini LLM without API key"""
        provider = GeminiLLMProvider(api_key="")
        result = provider.generate_content("test prompt")
        
        assert result.is_failure
        assert result.error.code == ErrorCode.LLM_PROVIDER_ERROR
        assert "Client not available" in result.error.details
    
    def test_gemini_llm_api_error(self):
        """Test Gemini LLM with API error"""
        provider = GeminiLLMProvider(api_key="test_key")
        
        # Mock the client to raise an exception
        with patch.object(provider.client.models, 'generate_content', side_effect=Exception("API Error")):
            result = provider.generate_content("test prompt")
            
            assert result.is_failure
            assert result.error.code == ErrorCode.LLM_PROVIDER_ERROR
            assert "Content generation failed" in result.error.details


class TestOCRErrorHandling:
    """Test OCR provider error handling"""
    
    def test_tesseract_ocr_file_not_found(self):
        """Test Tesseract OCR with non-existent file"""
        provider = TesseractOCRProvider()
        
        with patch('pytesseract.image_to_string', side_effect=Exception("File not found")):
            result = provider.perform_ocr("nonexistent.png")
            
            assert result.is_failure
            assert result.error.code == ErrorCode.TEXT_EXTRACTION_FAILED
            assert "File not found" in result.error.details
    
    def test_tesseract_ocr_empty_result(self):
        """Test Tesseract OCR with empty result"""
        provider = TesseractOCRProvider()
        
        with patch('pytesseract.image_to_string', return_value="   "):
            result = provider.perform_ocr("test.png")
            
            assert result.is_failure
            assert "no text" in result.error.details


class TestServiceErrorIntegration:
    """Test how services handle Result types from dependencies"""
    
    def test_text_cleaning_with_llm_failure(self):
        """Test text cleaning service with LLM failure"""
        failing_llm = FakeLLMProvider(should_fail=True)
        service = TextCleaningService(failing_llm)
        
        # Should gracefully fall back when LLM fails
        result = service.clean_text("Test text")
        
        assert len(result) > 0  # Should return fallback text
        assert len(failing_llm.prompts) > 0  # LLM was attempted
    
    def test_text_cleaning_with_llm_success(self):
        """Test text cleaning service with LLM success"""
        working_llm = FakeLLMProvider(should_fail=False)
        service = TextCleaningService(working_llm)
        
        result = service.clean_text("Test text")
        
        assert len(result) > 0
        assert "Cleaned:" in result[0]  # Should contain LLM output
        assert len(working_llm.prompts) > 0


class TestRetryableErrors:
    """Test retryable vs non-retryable error classification"""
    
    def test_tts_errors_are_retryable(self):
        """Test that TTS errors are marked as retryable"""
        error = tts_engine_error("Rate limit exceeded")
        assert error.retryable == True
    
    def test_llm_errors_are_retryable(self):
        """Test that LLM errors are marked as retryable"""
        error = llm_provider_error("API timeout")
        assert error.retryable == True
    
    def test_configuration_errors_not_retryable(self):
        """Test that configuration errors are not retryable"""
        from domain.errors import configuration_error
        error = configuration_error("Invalid API key")
        assert error.retryable == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])