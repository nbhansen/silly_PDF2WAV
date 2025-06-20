# tests/test_phase1_integration.py
import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from application.composition_root import CompositionRoot
from application.config.system_config import SystemConfig, TTSEngine
from domain.models import ProcessingRequest, PageRange
from tests.test_helpers import FakeTTSEngine, FakeLLMProvider


class TestPhase1Integration:
    """Integration tests for Phase 1 architectural improvements"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test configuration
        self.config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            upload_folder=os.path.join(self.temp_dir, "uploads"),
            audio_folder=os.path.join(self.temp_dir, "audio"),
            enable_text_cleaning=True,
            enable_ssml=True,
            max_concurrent_requests=2
        )
        
        # Ensure directories exist
        os.makedirs(self.config.upload_folder, exist_ok=True)
        os.makedirs(self.config.audio_folder, exist_ok=True)
    
    def test_composition_root_with_proper_dependency_injection(self):
        """Test that CompositionRoot properly injects all dependencies"""
        
        with patch('infrastructure.tts.piper_tts_provider.PIPER_AVAILABLE', True):
            root = CompositionRoot(self.config)
            
            # Verify main service is created
            assert root.pdf_processing_service is not None
            
            # Verify timing strategy is injected
            assert root.timing_strategy is not None
            
            # Verify audio coordinator is created and injected
            assert root.audio_coordinator is not None
            assert root.audio_generation_service.async_coordinator is not None
            
            # Verify all core services are wired
            assert root.file_manager is not None
            assert root.tts_engine is not None
            assert root.text_cleaning_service is not None
            assert root.academic_ssml_service is not None
    
    def test_error_propagation_through_layers(self):
        """Test that errors properly propagate through architectural layers"""
        
        # Create composition root with failing TTS
        failing_tts = FakeTTSEngine(should_fail=True)
        
        with patch('infrastructure.tts.piper_tts_provider.PiperTTSProvider', return_value=failing_tts):
            root = CompositionRoot(self.config)
            
            # Create a test request
            request = ProcessingRequest(
                pdf_path="test.pdf",
                output_name="test_output",
                page_range=PageRange()
            )
            
            # Mock PDF text extraction to return some text
            with patch.object(root.pdf_processing_service, 'extract_text', return_value=["Test text"]):
                result = root.pdf_processing_service.process_pdf(request)
                
                # Should gracefully handle TTS failure
                assert not result.success
                assert result.error is not None
                assert "TTS generation failed" in str(result.error) or "failed" in str(result.error).lower()
    
    def test_successful_workflow_with_new_architecture(self):
        """Test successful end-to-end workflow with new architecture"""
        
        # Create composition root with working services
        working_tts = FakeTTSEngine(should_fail=False)
        working_llm = FakeLLMProvider(should_fail=False)
        
        with patch('infrastructure.tts.piper_tts_provider.PiperTTSProvider', return_value=working_tts), \
             patch('infrastructure.llm.gemini_llm_provider.GeminiLLMProvider', return_value=working_llm):
            
            root = CompositionRoot(self.config)
            
            # Create test request
            request = ProcessingRequest(
                pdf_path="test.pdf",
                output_name="test_output",
                page_range=PageRange()
            )
            
            # Mock successful text extraction
            with patch.object(root.pdf_processing_service, 'extract_text', return_value=["Hello world", "This is a test"]):
                result = root.pdf_processing_service.process_pdf(request)
                
                # Should succeed with new architecture
                assert result.success
                assert result.audio_files is not None
                assert len(result.audio_files) > 0
                assert len(working_tts.generated_texts) > 0
    
    def test_async_coordinator_fallback_behavior(self):
        """Test that AudioGenerationService can work with or without coordinator"""
        
        from domain.services.audio_generation_service import AudioGenerationService
        from domain.services.sentence_measurement_strategy import SentenceMeasurementStrategy
        
        # Create service without coordinator (tests fallback)
        working_tts = FakeTTSEngine()
        
        with patch('infrastructure.file.file_manager.FileManager'):
            timing_strategy = Mock()
            timing_strategy.generate_with_timing.return_value = Mock(
                audio_files=["test.wav"],
                combined_mp3="test.mp3",
                timing_data=None
            )
            
            service = AudioGenerationService(timing_strategy)  # No coordinator
            
            # Should still work via fallback path
            result = service.generate_audio_with_timing(
                ["test text"], "output", "output_dir", working_tts
            )
            
            assert result is not None
    
    def test_rate_limiting_in_coordinator(self):
        """Test that rate limiting works in the coordinator"""
        
        from domain.services.audio_generation_coordinator import AudioGenerationCoordinator
        
        working_tts = FakeTTSEngine()
        
        with patch('infrastructure.file.file_manager.FileManager') as MockFileManager:
            mock_file_manager = Mock()
            MockFileManager.return_value = mock_file_manager
            mock_file_manager.get_output_dir.return_value = self.temp_dir
            
            coordinator = AudioGenerationCoordinator(
                tts_engine=working_tts,
                file_manager=mock_file_manager,
                max_concurrent_requests=1  # Low concurrency for testing
            )
            
            # Test with multiple chunks
            chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]
            
            # Mock the file processor to avoid actual file operations
            with patch.object(coordinator.file_processor, 'save_audio_chunk') as mock_save:
                mock_save.return_value = Mock(is_success=True, value="test.wav")
                
                audio_files, combined_mp3 = coordinator.sync_generate_audio(
                    chunks, "test", self.temp_dir
                )
                
                # Should process all chunks
                assert len(working_tts.generated_texts) == len(chunks)
                
                # Should have called save for each chunk
                assert mock_save.call_count == len(chunks)
    
    def test_error_handling_consistency_across_providers(self):
        """Test that all providers handle errors consistently"""
        
        from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
        from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
        from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
        
        # Test TTS provider error handling
        tts_provider = GeminiTTSProvider(api_key="test")
        with patch.object(tts_provider, '_generate_with_persona', side_effect=Exception("TTS Error")):
            tts_result = tts_provider.generate_audio_data("test")
            assert tts_result.is_failure
            assert tts_result.error is not None
        
        # Test LLM provider error handling
        llm_provider = GeminiLLMProvider(api_key="")  # Invalid key
        llm_result = llm_provider.generate_content("test")
        assert llm_result.is_failure
        assert llm_result.error is not None
        
        # Test OCR provider error handling
        ocr_provider = TesseractOCRProvider()
        with patch('pytesseract.image_to_string', side_effect=Exception("OCR Error")):
            ocr_result = ocr_provider.perform_ocr("test.png")
            assert ocr_result.is_failure
            assert ocr_result.error is not None
        
        # All should return Result types with proper error structure
        for result in [tts_result, llm_result, ocr_result]:
            assert hasattr(result, 'is_failure')
            assert hasattr(result, 'error')
            assert result.error.code is not None
            assert result.error.message is not None


class TestBackwardCompatibility:
    """Test that Phase 1 changes maintain backward compatibility"""
    
    def test_existing_interfaces_still_work(self):
        """Test that existing code can still use the services"""
        
        # Test that old-style service creation still works
        from domain.services.audio_generation_service import AudioGenerationService
        from domain.services.sentence_measurement_strategy import SentenceMeasurementStrategy
        
        # Create minimal dependencies
        mock_strategy = Mock()
        mock_strategy.generate_with_timing.return_value = Mock(
            audio_files=["test.wav"],
            combined_mp3="test.mp3",
            timing_data=None
        )
        
        # Should work without coordinator (backward compatibility)
        service = AudioGenerationService(mock_strategy)
        assert service.timing_strategy == mock_strategy
        assert service.async_coordinator is None  # Optional
    
    def test_configuration_backward_compatibility(self):
        """Test that configuration still works as expected"""
        
        # Test that SystemConfig can still be created with old patterns
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            enable_text_cleaning=True
        )
        
        assert config.tts_engine == TTSEngine.PIPER
        assert config.enable_text_cleaning == True
        assert hasattr(config, 'max_concurrent_requests')  # New field with default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])