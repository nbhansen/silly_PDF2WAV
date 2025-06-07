# tests/test_integration.py
import pytest
import os
import tempfile
from unittest.mock import patch, mock_open
from application.composition_root import create_pdf_service_from_env
from domain.models import ProcessingRequest, PageRange
from tests.test_helpers import FakeLLMProvider, FakeTTSEngine

class TestIntegration:
    """Integration tests for the complete PDF to audio pipeline"""
    
    def test_full_pipeline_with_mocked_dependencies(self, tmp_path):
        """Test complete pipeline with mocked external dependencies"""
        # Create a fake PDF file
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_text("fake pdf content")
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'GOOGLE_AI_API_KEY': 'test_key',
            'TTS_ENGINE': 'coqui',
            'COQUI_MODEL_NAME': 'test_model'
        }):
            # Mock external dependencies
            with patch('infrastructure.llm.gemini_llm_provider.genai.configure'), \
                 patch('infrastructure.llm.gemini_llm_provider.genai.GenerativeModel') as mock_model, \
                 patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open') as mock_pdf, \
                 patch('infrastructure.tts.coqui_tts_provider.CoquiTTS_API') as mock_tts, \
                 patch('os.makedirs'), \
                 patch('builtins.open', mock_open()), \
                 patch('os.path.exists', return_value=True), \
                 patch('os.remove'):
                
                # Setup mocks
                mock_pdf.return_value.__enter__.return_value.pages = [
                    type('Page', (), {'extract_text': lambda: 'Sample PDF text content'})()
                ]
                mock_pdf.return_value.__enter__.return_value.metadata = {'Title': 'Test', 'Author': 'Test'}
                
                mock_model.return_value.generate_content.return_value.candidates = [
                    type('Candidate', (), {
                        'content': type('Content', (), {
                            'parts': [type('Part', (), {'text': 'Cleaned text with... natural pauses'})()]
                        })()
                    })()
                ]
                
                mock_tts.return_value.tts_to_file = lambda **kwargs: None
                mock_tts.return_value.is_multi_speaker = False
                
                # Create service and test
                service = create_pdf_service_from_env()
                request = ProcessingRequest(
                    pdf_path=str(fake_pdf),
                    output_name="integration_test",
                    page_range=PageRange()
                )
                
                result = service.process_pdf(request)
                
                # Verify pipeline completed successfully
                assert result.success == True
                assert result.audio_files is not None
                assert len(result.audio_files) > 0
                assert result.debug_info is not None
                assert 'raw_text_length' in result.debug_info

    def test_page_range_integration(self, tmp_path):
        """Test integration with page range selection"""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_text("fake pdf content")
        
        with patch.dict(os.environ, {'TTS_ENGINE': 'gtts'}):
            with patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open') as mock_pdf, \
                 patch('infrastructure.tts.gtts_provider.gTTS') as mock_gtts, \
                 patch('os.makedirs'), \
                 patch('builtins.open', mock_open()), \
                 patch('os.path.exists', return_value=True), \
                 patch('os.remove'):
                
                # Setup PDF with multiple pages
                mock_pdf.return_value.__enter__.return_value.pages = [
                    type('Page', (), {'extract_text': lambda: f'Page {i} content'})() 
                    for i in range(1, 6)  # 5 pages
                ]
                mock_pdf.return_value.__enter__.return_value.metadata = {}
                mock_gtts.return_value.save = lambda path: None
                
                service = create_pdf_service_from_env()
                
                # Test partial page range
                request = ProcessingRequest(
                    pdf_path=str(fake_pdf),
                    output_name="page_range_test",
                    page_range=PageRange(start_page=2, end_page=4)
                )
                
                result = service.process_pdf(request)
                
                assert result.success == True
                assert 'page_range' in result.debug_info
                assert result.debug_info['page_range']['start_page'] == 2
                assert result.debug_info['page_range']['end_page'] == 4

    def test_error_propagation_integration(self, tmp_path):
        """Test that errors propagate correctly through the pipeline"""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_text("fake pdf content")
        
        with patch.dict(os.environ, {'TTS_ENGINE': 'coqui'}):
            with patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open') as mock_pdf:
                # Simulate OCR failure
                mock_pdf.side_effect = Exception("PDF reading failed")
                
                service = create_pdf_service_from_env()
                request = ProcessingRequest(
                    pdf_path=str(fake_pdf),
                    output_name="error_test",
                    page_range=PageRange()
                )
                
                result = service.process_pdf(request)
                
                assert result.success == False
                assert "PDF reading failed" in result.error


class TestChunkingBehavior:
    """Test text chunking behavior for large documents"""
    
    def test_small_text_no_chunking(self):
        """Test that small texts aren't unnecessarily chunked"""
        from domain.services.text_cleaning_service import TextCleaningService
        
        fake_llm = FakeLLMProvider()
        service = TextCleaningService(llm_provider=fake_llm, max_chunk_size=1000)
        
        small_text = "This is a small text that should not be chunked."
        result = service.clean_text(small_text, fake_llm)
        
        assert len(fake_llm.prompts) == 1  # Only one LLM call
        assert len(result) == 1  # Single chunk output

    def test_large_text_chunking(self):
        """Test that large texts are properly chunked"""
        from domain.services.text_cleaning_service import TextCleaningService
        
        fake_llm = FakeLLMProvider()
        service = TextCleaningService(llm_provider=fake_llm, max_chunk_size=100)  # Small for testing
        
        # Create text larger than max_chunk_size
        large_text = "This is a sentence. " * 20  # ~400 chars
        
        with patch('time.sleep'):  # Skip rate limiting in tests
            result = service.clean_text(large_text, fake_llm)
        
        assert len(fake_llm.prompts) > 1  # Multiple LLM calls
        assert all(isinstance(chunk, str) for chunk in result)
        assert all(len(chunk) > 0 for chunk in result)

    def test_audio_chunking_behavior(self):
        """Test audio generation chunking for large cleaned text"""
        from domain.services.audio_generation_service import AudioGenerationService
        
        fake_tts = FakeTTSEngine()
        service = AudioGenerationService(tts_engine=fake_tts)
        
        # Create multiple text chunks
        large_chunks = [f"This is chunk number {i}. " * 50 for i in range(5)]
        
        with patch('os.makedirs'), \
             patch('builtins.open', mock_open()), \
             patch('os.path.exists', return_value=False):  # Disable MP3 creation
            
            result = service.generate_audio(large_chunks, "chunking_test", "audio_outputs")
            files, combined = result
        
        assert len(files) == 5  # One file per chunk
        assert len(fake_tts.generated_texts) == 5  # TTS called for each chunk
        assert all("chunk number" in text for text in fake_tts.generated_texts)

    def test_chunking_preserves_content(self):
        """Test that chunking doesn't lose content"""
        from domain.services.text_cleaning_service import TextCleaningService
        
        fake_llm = FakeLLMProvider()
        service = TextCleaningService(llm_provider=fake_llm, max_chunk_size=50)
        
        # Text with distinct sentences
        test_text = "First sentence here. Second sentence follows. Third sentence ends."
        
        with patch('time.sleep'):
            result = service.clean_text(test_text, fake_llm)
        
        combined_result = " ".join(result)
        
        # Verify key content is preserved (accounting for LLM cleaning)
        assert "First" in combined_result or "first" in combined_result
        assert "Second" in combined_result or "second" in combined_result  
        assert "Third" in combined_result or "third" in combined_result

    def test_empty_chunk_handling(self):
        """Test handling of empty or error chunks"""
        from domain.services.audio_generation_service import AudioGenerationService
        
        fake_tts = FakeTTSEngine()
        service = AudioGenerationService(tts_engine=fake_tts)
        
        # Mix of valid and invalid chunks
        mixed_chunks = [
            "Valid text chunk",
            "",  # Empty
            "Error: Processing failed",  # Error
            "Another valid chunk",
            "   ",  # Whitespace only
        ]
        
        with patch('os.makedirs'), \
             patch('builtins.open', mock_open()), \
             patch('os.path.exists', return_value=False):
            
            result = service.generate_audio(mixed_chunks, "mixed_test", "audio_outputs")
            files, combined = result
        
        # Should only generate audio for valid chunks
        assert len(files) == 2  # Only 2 valid chunks
        assert len(fake_tts.generated_texts) == 2
        assert "Valid text chunk" in fake_tts.generated_texts
        assert "Another valid chunk" in fake_tts.generated_texts

    def test_memory_efficient_chunking(self):
        """Test that chunking works with simulated memory constraints"""
        from domain.services.text_cleaning_service import TextCleaningService
        
        fake_llm = FakeLLMProvider()
        service = TextCleaningService(llm_provider=fake_llm, max_chunk_size=200)
        
        # Simulate a very large document
        large_doc = "Academic paper content. " * 100  # ~2400 chars
        
        with patch('time.sleep'):
            result = service.clean_text(large_doc, fake_llm)
        
        # Verify chunking occurred
        assert len(fake_llm.prompts) > 1
        
        # Verify no individual chunk was too large for LLM
        for prompt in fake_llm.prompts:
            # Account for prompt template overhead
            assert len(prompt) < 2000  # Reasonable LLM input size


# Add to existing test files or run separately
if __name__ == "__main__":
    pytest.main([__file__, "-v"])