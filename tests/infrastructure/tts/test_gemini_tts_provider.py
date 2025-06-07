# tests/infrastructure/tts/test_gemini_tts_provider.py  
from domain.models import GeminiConfig

def test_gemini_config():
    config = GeminiConfig(voice_name="test_voice", api_key="test_key")
    assert config.voice_name == "test_voice"
    assert config.api_key == "test_key"