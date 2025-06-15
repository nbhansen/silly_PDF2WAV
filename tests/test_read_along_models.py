# tests/test_read_along_models.py
"""
Tests for read-along functionality - timing data and related models.
"""

import pytest
import time
import wave
from unittest.mock import patch
from domain.models import TextSegment, TimingMetadata, TimedAudioResult


def test_text_segment_creation():
    """Test creating TextSegment objects"""
    segment = TextSegment(
        text="This is a test sentence.",
        start_time=0.0,
        duration=2.5,
        segment_type="sentence",
        chunk_index=0,
        sentence_index=0
    )
    
    assert segment.text == "This is a test sentence."
    assert segment.start_time == 0.0
    assert segment.duration == 2.5
    assert segment.end_time == 2.5
    assert segment.segment_type == "sentence"


def test_timing_metadata_creation():
    """Test creating TimingMetadata with segments"""
    segments = [
        TextSegment("First sentence.", 0.0, 2.0, "sentence", 0, 0),
        TextSegment("Second sentence.", 2.0, 1.5, "sentence", 0, 1),
        TextSegment("Third sentence.", 3.5, 2.2, "sentence", 0, 2)
    ]
    
    metadata = TimingMetadata(
        total_duration=5.7,
        text_segments=segments,
        audio_files=["output_part01.wav"]
    )
    
    assert metadata.total_duration == 5.7
    assert len(metadata.text_segments) == 3
    assert metadata.audio_files == ["output_part01.wav"]


def test_timing_metadata_get_segment_at_time():
    """Test finding segment at specific time"""
    segments = [
        TextSegment("First.", 0.0, 2.0, "sentence", 0, 0),
        TextSegment("Second.", 2.0, 1.5, "sentence", 0, 1),
        TextSegment("Third.", 3.5, 2.2, "sentence", 0, 2)
    ]
    
    metadata = TimingMetadata(5.7, segments, ["test.wav"])
    
    # Test finding segments at different times
    assert metadata.get_segment_at_time(1.0).text == "First."
    assert metadata.get_segment_at_time(2.5).text == "Second."
    assert metadata.get_segment_at_time(4.0).text == "Third."
    assert metadata.get_segment_at_time(10.0) is None  # Beyond end


def test_timed_audio_result_creation():
    """Test creating TimedAudioResult objects"""
    # Without timing data
    result_no_timing = TimedAudioResult(
        audio_files=["test.wav"],
        combined_mp3="test.mp3"
    )
    
    assert result_no_timing.audio_files == ["test.wav"]
    assert result_no_timing.combined_mp3 == "test.mp3"
    assert result_no_timing.has_timing_data is False
    
    # With timing data
    segments = [TextSegment("Test.", 0.0, 1.0, "sentence", 0, 0)]
    timing_data = TimingMetadata(1.0, segments, ["test.wav"])
    
    result_with_timing = TimedAudioResult(
        audio_files=["test.wav"],
        combined_mp3="test.mp3",
        timing_data=timing_data
    )
    
    assert result_with_timing.has_timing_data is True
    assert result_with_timing.timing_data.total_duration == 1.0


def test_audio_generation_service_timing_method():
    """Test that AudioGenerationService.generate_audio_with_timing works"""
    from domain.services.audio_generation_service import AudioGenerationService
    from unittest.mock import MagicMock, patch
    
    # Create mock TTS engine
    mock_tts = MagicMock()
    mock_tts.generate_audio_data.return_value = b"fake_audio"
    mock_tts.get_output_format.return_value = "wav"
    
    # Create service
    audio_service = AudioGenerationService(tts_engine=mock_tts)
    
    # Mock the file operations
    with patch('os.makedirs'), \
         patch('builtins.open'), \
         patch('os.path.exists', return_value=False):
        
        # Test that the method returns TimedAudioResult with timing data
        result = audio_service.generate_audio_with_timing(
            ["Test text"], "test_output", "test_dir"
        )
        
        assert isinstance(result, TimedAudioResult)
        assert result.audio_files is not None
        assert result.has_timing_data is True  # Our implementation DOES have timing data


def test_timing_capture_implementation():
    """Test that timing capture actually works"""
    from domain.services.audio_generation_service import AudioGenerationService
    from unittest.mock import MagicMock, patch, mock_open
    import tempfile
    import os
    
    # Create mock TTS engine
    mock_tts = MagicMock()
    mock_tts.generate_audio_data.return_value = b"fake_audio_data_" + b"x" * 1000  # Longer data
    mock_tts.get_output_format.return_value = "wav"
    
    # Create service
    audio_service = AudioGenerationService(tts_engine=mock_tts)
    
    # Mock wave file reading to return a realistic duration
    mock_wave = MagicMock()
    mock_wave.__enter__.return_value.getnframes.return_value = 44100  # 1 second at 44.1kHz
    mock_wave.__enter__.return_value.getframerate.return_value = 44100
    
    with patch('os.makedirs'), \
         patch('builtins.open', mock_open()), \
         patch('os.path.exists', return_value=True), \
         patch('wave.open', return_value=mock_wave):
        
        # Test timing capture
        result = audio_service.generate_audio_with_timing(
            ["First sentence. Second sentence.", "Third sentence."], 
            "test_output", 
            "test_dir"
        )
        
        # Verify we got a TimedAudioResult with timing data
        assert isinstance(result, TimedAudioResult)
        assert result.has_timing_data is True
        assert result.timing_data is not None
        
        # Verify timing metadata structure
        timing = result.timing_data
        assert timing.total_duration > 0
        assert len(timing.text_segments) >= 2  # At least 2 sentences
        assert timing.audio_files == result.audio_files
        
        # Verify segments have reasonable timing
        for segment in timing.text_segments:
            assert segment.start_time >= 0
            assert segment.duration > 0
            assert segment.text.strip()  # Not empty
            assert segment.segment_type == "sentence"


if __name__ == "__main__":
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v"
    ])
    sys.exit(result.returncode)