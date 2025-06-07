# tests/test_config.py - FIXED VERSION
from domain.models import TTSConfig, CoquiConfig, GTTSConfig, GeminiConfig

def test_tts_config_creation():
    """Test that we can create a basic TTSConfig"""
    config = TTSConfig()
    assert config.voice_quality == "medium"
    assert config.speaking_style == "neutral" 
    assert config.speed == 1.0

def test_tts_config_with_coqui():
    """Test creating TTSConfig with Coqui settings"""
    coqui_config = CoquiConfig(model_name="test_model", use_gpu=True)
    config = TTSConfig(voice_quality="high", coqui=coqui_config)
    
    assert config.voice_quality == "high"
    assert config.coqui.model_name == "test_model"
    assert config.coqui.use_gpu == True

def test_gemini_config_creation():
    """Test creating TTSConfig with Gemini settings"""
    gemini_config = GeminiConfig(voice_name="Charon", style_prompt="professional tone")
    config = TTSConfig(voice_quality="high", speaking_style="professional", gemini=gemini_config)
    
    assert config.voice_quality == "high"
    assert config.speaking_style == "professional"
    assert config.gemini.voice_name == "Charon"
    assert config.gemini.style_prompt == "professional tone"