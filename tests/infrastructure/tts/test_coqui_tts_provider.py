# tests/infrastructure/tts/test_coqui_tts_provider.py
import pytest
from domain.models import CoquiConfig

def test_coqui_config():
    config = CoquiConfig(model_name="test_model", speaker="test_speaker", use_gpu=True)
    assert config.model_name == "test_model"
    assert config.speaker == "test_speaker" 
    assert config.use_gpu == True

def test_coqui_config_defaults():
    config = CoquiConfig()
    assert config.model_name is None
    assert config.speaker is None
    assert config.use_gpu is None

@pytest.mark.skipif(True, reason="Skip implementation tests - test interface")
def test_coqui_provider_placeholder():
    pass