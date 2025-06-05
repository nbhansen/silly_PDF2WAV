# tests/test_config.py
import sys
import os

# Add the parent directory to sys.path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tts_utils import TTSConfig, CoquiConfig, GTTSConfig, GeminiConfig, GeminiConfigAdapter, get_tts_processor
from processors import PDFProcessor

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

def test_page_range_validation_valid_ranges():
    """Test page range validation with valid inputs"""
    # Create a mock processor - we don't need real PDF files for this test
    processor = PDFProcessor("fake_api_key", "gtts")
    
    # Mock the get_pdf_info method to return a fixed page count
    def mock_get_pdf_info(pdf_path):
        return {'total_pages': 10, 'title': 'Test', 'author': 'Test'}
    
    processor.get_pdf_info = mock_get_pdf_info
    
    # Test valid page ranges
    result = processor.validate_page_range("dummy.pdf", 1, 5)
    assert result['valid'] == True
    assert result['actual_start'] == 1
    assert result['actual_end'] == 5
    assert result['pages_to_process'] == 5

def test_gemini_config_creation():
    """Test creating TTSConfig with Gemini settings"""
    gemini_config = GeminiConfig(voice_name="Charon", style_prompt="professional tone")
    config = TTSConfig(voice_quality="high", speaking_style="professional", gemini=gemini_config)
    
    assert config.voice_quality == "high"
    assert config.speaking_style == "professional"
    assert config.gemini.voice_name == "Charon"
    assert config.gemini.style_prompt == "professional tone"

def test_gemini_config_adapter():
    """Test Gemini config adapter functionality"""
    adapter = GeminiConfigAdapter()
    
    # Test with explicit Gemini config
    gemini_config = GeminiConfig(voice_name="Puck", style_prompt="casual", api_key="test_key")
    config = TTSConfig(gemini=gemini_config)
    adapted = adapter.adapt(config)
    
    assert adapted["voice_name"] == "Puck"
    assert adapted["style_prompt"] == "casual"
    assert adapted["api_key"] == "test_key"
    
    # Test with speaking style mapping
    config_casual = TTSConfig(speaking_style="casual")
    adapted_casual = adapter.adapt(config_casual)
    assert adapted_casual["voice_name"] == "Puck"
    
    config_professional = TTSConfig(speaking_style="professional")
    adapted_professional = adapter.adapt(config_professional)
    assert adapted_professional["voice_name"] == "Charon"

def test_tts_factory_gemini():
    """Test TTS factory creates appropriate processor"""
    # Test factory with different engines
    processor = get_tts_processor("gemini", TTSConfig())
    # Should return either GeminiTTSProcessor or fallback (gTTS/Coqui)
    assert processor is not None
    
    # Test with non-existent engine falls back gracefully
    fallback_processor = get_tts_processor("nonexistent")
    assert fallback_processor is not None  # Should get fallback