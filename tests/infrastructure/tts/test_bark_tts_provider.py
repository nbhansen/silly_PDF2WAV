# tests/infrastructure/tts/test_bark_tts_provider.py
from domain.models import BarkConfig

def test_bark_config():
    config = BarkConfig(use_gpu=True, use_small_models=False, history_prompt="test")
    assert config.use_gpu == True
    assert config.use_small_models == False
    assert config.history_prompt == "test"