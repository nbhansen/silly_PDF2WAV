# tests/domain/services/test_audio_generation_simple.py
import pytest
from domain.services.audio_generation_service import AudioGenerationService
from tests.test_helpers import FakeTTSEngine

def test_audio_service_creation():
    fake_tts = FakeTTSEngine()
    service = AudioGenerationService(tts_engine=fake_tts)
    assert service.tts_engine == fake_tts

def test_audio_service_with_no_engine():
    service = AudioGenerationService(tts_engine=None)
    result = service.generate_audio(["test"], "output", "audio_outputs")
    assert result == ([], None)

def test_audio_service_interface():
    fake_tts = FakeTTSEngine()
    service = AudioGenerationService(tts_engine=fake_tts)
    
    # Mock file operations to avoid actual file creation
    import unittest.mock
    with unittest.mock.patch('os.makedirs'), \
         unittest.mock.patch('builtins.open'), \
         unittest.mock.patch('os.path.exists', return_value=False):
        
        result = service.generate_audio(["test text"], "output", "audio_outputs")
        files, combined = result
        assert isinstance(files, list)
        assert len(files) >= 0