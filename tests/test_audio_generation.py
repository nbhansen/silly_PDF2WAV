# tests/test_audio_generation.py
import sys
import os
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio_generation import TTSGenerator, SimpleTTSEnhancer
from tts_utils import TTSConfig

def test_simple_tts_enhancer():
    """Test SimpleTTSEnhancer adds pause markers"""
    enhancer = SimpleTTSEnhancer()
    
    # Test basic enhancement
    text = "This is text.\n\nNew paragraph."
    enhanced = enhancer.enhance_text_for_tts(text)
    
    assert "... " in enhanced
    assert "paragraph" in enhanced

def test_tts_generator_initialization():
    """Test TTSGenerator initializes correctly"""
    with patch('audio_generation.get_tts_processor') as mock_get_processor:
        mock_processor = Mock()
        mock_get_processor.return_value = mock_processor
        
        config = TTSConfig()
        generator = TTSGenerator("gtts", config)
        
        assert generator.processor == mock_processor
        assert generator.engine_name == "gtts"
        assert generator.chunk_size == 20000

def test_ffmpeg_detection():
    """Test FFmpeg availability detection"""
    with patch('audio_generation.get_tts_processor') as mock_get_processor:
        mock_get_processor.return_value = Mock()
        
        # Test FFmpeg available
        with patch('audio_generation.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            generator = TTSGenerator("gtts", TTSConfig())
            assert generator.ffmpeg_available == True
        
        # Test FFmpeg unavailable  
        with patch('audio_generation.subprocess.run', side_effect=FileNotFoundError):
            generator = TTSGenerator("gtts", TTSConfig())
            assert generator.ffmpeg_available == False

def test_text_splitting():
    """Test text gets split appropriately for TTS"""
    with patch('audio_generation.get_tts_processor') as mock_get_processor:
        mock_get_processor.return_value = Mock()
        
        generator = TTSGenerator("gtts", TTSConfig())
        
        # Short text - no splitting
        short_text = "This is short."
        chunks = generator._split_for_tts(short_text)
        assert len(chunks) == 1
        
        # Long text - should split
        long_text = "This is a sentence. " * 2000  # ~40,000 chars
        chunks = generator._split_for_tts(long_text)
        assert len(chunks) > 1
        assert all(len(chunk) <= generator.chunk_size for chunk in chunks)

def test_generate_audio_error_handling():
    """Test audio generation handles errors gracefully"""
    with patch('audio_generation.get_tts_processor') as mock_get_processor:
        mock_get_processor.return_value = None  # No processor
        
        generator = TTSGenerator("invalid", TTSConfig())
        
        # Should handle missing processor
        result = generator.generate("test text", "output", "audio_outputs")
        assert result is None
        
        # Should handle error text
        mock_processor = Mock()
        mock_get_processor.return_value = mock_processor
        generator = TTSGenerator("gtts", TTSConfig())
        
        result = generator.generate("Error: something failed", "output", "audio_outputs")
        assert result is None

def test_generate_from_chunks():
    """Test generating audio from multiple text chunks"""
    with patch('audio_generation.get_tts_processor') as mock_get_processor:
        mock_processor = Mock()
        mock_processor.generate_audio_file.return_value = "test.mp3"
        mock_get_processor.return_value = mock_processor
        
        generator = TTSGenerator("gtts", TTSConfig())
        generator.ffmpeg_available = False  # Disable MP3 creation for simpler test
        
        chunks = ["First chunk text.", "Second chunk text."]
        audio_files, combined_mp3 = generator.generate_from_chunks(
            chunks, "test_output", create_combined_mp3=False
        )
        
        assert len(audio_files) == 2
        assert combined_mp3 is None  # MP3 creation disabled
        assert mock_processor.generate_audio_file.call_count == 2