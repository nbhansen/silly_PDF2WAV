# tests/test_phase1_services.py
import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock

from domain.services.rate_limiting_service import RateLimitingService
from domain.services.audio_file_processor import AudioFileProcessor
from domain.services.audio_generation_coordinator import AudioGenerationCoordinator
from domain.errors import Result, tts_engine_error, audio_generation_error
from tests.test_helpers import FakeTTSEngine, FakeFileManager, FakeAudioProcessor


class TestRateLimitingService:
    """Test the rate limiting service"""
    
    def test_get_base_delay_for_engine(self):
        """Test engine-specific delay calculation"""
        rate_limiter = RateLimitingService()
        
        # Mock engines
        gemini_engine = Mock()
        gemini_engine.__class__.__name__ = "GeminiTTSProvider"
        
        piper_engine = Mock()
        piper_engine.__class__.__name__ = "PiperTTSProvider"
        
        unknown_engine = Mock()
        unknown_engine.__class__.__name__ = "UnknownEngine"
        
        # Test delays
        assert rate_limiter.get_base_delay_for_engine(gemini_engine) == 2.0
        assert rate_limiter.get_base_delay_for_engine(piper_engine) == 0.1
        assert rate_limiter.get_base_delay_for_engine(unknown_engine) == 1.0
    
    def test_get_retry_delay(self):
        """Test exponential backoff calculation"""
        rate_limiter = RateLimitingService()
        
        assert rate_limiter.get_retry_delay(0, 1.0) == 1.0
        assert rate_limiter.get_retry_delay(1, 1.0) == 2.0
        assert rate_limiter.get_retry_delay(2, 1.0) == 4.0
        assert rate_limiter.get_retry_delay(10, 1.0) == 30.0  # Max cap
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self):
        """Test successful operation without retries"""
        rate_limiter = RateLimitingService(max_concurrent_requests=1)
        
        async def success_operation():
            return "success"
        
        result = await rate_limiter.execute_with_retry(success_operation, max_retries=3, base_delay=0.01)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_eventual_success(self):
        """Test operation that succeeds after retries"""
        rate_limiter = RateLimitingService(max_concurrent_requests=1)
        
        call_count = 0
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await rate_limiter.execute_with_retry(flaky_operation, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_final_failure(self):
        """Test operation that fails all retries"""
        rate_limiter = RateLimitingService(max_concurrent_requests=1)
        
        async def failing_operation():
            raise Exception("Permanent failure")
        
        with pytest.raises(Exception, match="Permanent failure"):
            await rate_limiter.execute_with_retry(failing_operation, max_retries=2, base_delay=0.01)


class TestAudioFileProcessor:
    """Test the audio file processor"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.file_manager = FakeFileManager(output_dir=self.temp_dir)
        self.audio_processor = FakeAudioProcessor()
        self.processor = AudioFileProcessor(self.file_manager, self.audio_processor)
    
    def test_save_audio_chunk_success(self):
        """Test successful audio chunk saving"""
        audio_data = b"fake audio data"
        result = self.processor.save_audio_chunk(audio_data, self.temp_dir, "test.wav")
        
        assert result.is_success
        assert result.value.endswith("test.wav")
        assert os.path.exists(result.value)
    
    def test_save_audio_chunk_empty_data(self):
        """Test saving empty audio data"""
        result = self.processor.save_audio_chunk(b"", self.temp_dir, "test.wav")
        
        assert result.is_failure
        assert "No audio data to save" in result.error.details
    
    def test_validate_audio_files(self):
        """Test audio file validation"""
        # Create valid file
        valid_file = os.path.join(self.temp_dir, "valid.wav")
        with open(valid_file, 'wb') as f:
            f.write(b"audio data")
        
        # Non-existent file
        invalid_file = os.path.join(self.temp_dir, "invalid.wav")
        
        valid, invalid = self.processor.validate_audio_files([valid_file, invalid_file])
        
        assert len(valid) == 1
        assert len(invalid) == 1
        assert valid_file in valid
        assert invalid_file in invalid
    
    def test_create_combined_mp3_single_file(self):
        """Test MP3 creation from single file using AudioProcessor"""
        # Create a fake input file
        input_path = os.path.join(self.temp_dir, "input.wav")
        with open(input_path, 'wb') as f:
            f.write(b"fake audio data")
        
        audio_files = [input_path]
        result = self.processor.create_combined_mp3(audio_files, "test", self.temp_dir)
        
        # Should succeed with our FakeAudioProcessor
        assert result.is_success
        
        # Result should be the expected output path
        expected_path = os.path.join(self.temp_dir, "test_combined.mp3")
        assert result.value == expected_path


class TestAudioGenerationCoordinator:
    """Test the audio generation coordinator"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.file_manager = FakeFileManager(output_dir=self.temp_dir)
        self.audio_processor = FakeAudioProcessor()
        self.tts_engine = FakeTTSEngine()
        self.coordinator = AudioGenerationCoordinator(
            tts_engine=self.tts_engine,
            file_manager=self.file_manager,
            audio_processor=self.audio_processor,
            max_concurrent_requests=2
        )
    
    def test_filter_valid_chunks(self):
        """Test chunk filtering logic"""
        chunks = [
            "Valid text chunk",
            "",  # Empty
            "Error: Something went wrong",  # Error
            "LLM cleaning skipped due to error",  # Skip
            "Another valid chunk"
        ]
        
        valid = self.coordinator._filter_valid_chunks(chunks)
        
        assert len(valid) == 2
        assert valid[0] == (0, "Valid text chunk")
        assert valid[1] == (4, "Another valid chunk")
    
    def test_sync_generate_audio_success(self):
        """Test synchronous audio generation"""
        chunks = ["Hello", "World"]
        
        audio_files, combined_mp3 = self.coordinator.sync_generate_audio(
            chunks, "test", self.temp_dir
        )
        
        assert len(audio_files) == 2
        assert all("test_part" in f for f in audio_files)
        assert len(self.tts_engine.generated_texts) == 2
    
    def test_sync_generate_audio_with_failures(self):
        """Test audio generation with TTS failures"""
        self.tts_engine.should_fail = True
        chunks = ["Hello", "World"]
        
        audio_files, combined_mp3 = self.coordinator.sync_generate_audio(
            chunks, "test", self.temp_dir
        )
        
        # Should handle failures gracefully
        assert len(audio_files) == 0  # All failed
        assert combined_mp3 is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])