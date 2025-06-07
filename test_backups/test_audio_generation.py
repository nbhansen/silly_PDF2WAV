# tests/test_audio_generation.py - FIXED VERSION
import pytest
from domain.services.audio_generation_service import AudioGenerationService
from domain.models import TTSConfig


def test_audio_generation_service_initialization(mocker):
    """Test AudioGenerationService initializes correctly"""
    mock_tts_engine = mocker.Mock()
    
    service = AudioGenerationService(tts_engine=mock_tts_engine)  # FIXED: added required parameter
    
    assert service.tts_engine == mock_tts_engine
    assert service.chunk_size == 20000

def test_ffmpeg_detection_audio_generation_service(mocker):
    """Test FFmpeg availability detection in AudioGenerationService"""
    mock_tts_engine = mocker.Mock()
    
    # Test FFmpeg available
    mock_run = mocker.patch('domain.services.audio_generation_service.subprocess.run')
    mock_run.return_value.returncode = 0
    service = AudioGenerationService(tts_engine=mock_tts_engine)  # FIXED
    assert service.ffmpeg_available == True
    
    # Test FFmpeg unavailable
    mocker.patch('domain.services.audio_generation_service.subprocess.run', side_effect=FileNotFoundError)
    service = AudioGenerationService(tts_engine=mock_tts_engine)  # FIXED
    assert service.ffmpeg_available == False

def test_generate_audio_error_handling_audio_generation_service(mocker):
    """Test audio generation handles errors gracefully in AudioGenerationService"""
    mock_tts_engine = mocker.Mock()
    mock_tts_engine.generate_audio_data.side_effect = Exception("TTS Error")
    
    service = AudioGenerationService(tts_engine=mock_tts_engine)  # FIXED
    
    # Should handle errors during audio generation
    text_chunks = ["Test chunk 1", "Test chunk 2"]
    audio_files, combined_mp3 = service.generate_audio(text_chunks, "output", "audio_outputs")
    
    assert len(audio_files) == 0
    assert combined_mp3 is None

def test_generate_audio_audio_generation_service(mocker):
    """Test generating audio from multiple text chunks using AudioGenerationService"""
    mock_tts_engine = mocker.Mock()
    mock_tts_engine.generate_audio_data.return_value = b"audio_data"
    mock_tts_engine.get_output_format.return_value = "wav"
    
    # Mock os.makedirs and open for file writing
    mocker.patch('os.makedirs')
    mock_open = mocker.patch('builtins.open', mocker.mock_open())
    mocker.patch('os.path.exists', return_value=True) # For _convert_single_to_mp3
    mocker.patch('os.path.getsize', return_value=1000) # For _convert_single_to_mp3
    
    service = AudioGenerationService(tts_engine=mock_tts_engine)  # FIXED
    service.ffmpeg_available = False  # Disable MP3 creation for simpler test
    
    text_chunks = ["First chunk text.", "Second chunk text."]
    audio_files, combined_mp3 = service.generate_audio(
        text_chunks, "test_output", "audio_outputs"
    )
    
    assert len(audio_files) == 2
    assert combined_mp3 is None  # MP3 creation disabled
    assert mock_tts_engine.generate_audio_data.call_count == 2
    assert mock_open.call_count == 2