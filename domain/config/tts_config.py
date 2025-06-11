# domain/config/tts_config.py - Simplified Engine-Specific Configuration
from dataclasses import dataclass
from typing import Optional

@dataclass
class GeminiConfig:
    """Configuration for Gemini TTS engine"""
    voice_name: str = "Kore"
    style_prompt: Optional[str] = None
    api_key: Optional[str] = None
    min_request_interval: float = 2.0
    max_retries: int = 3
    base_retry_delay: int = 16

@dataclass
class PiperConfig:
    """Configuration for Piper TTS engine"""
    model_name: str = "en_US-lessac-medium"
    model_path: Optional[str] = None
    config_path: Optional[str] = None
    speaker_id: Optional[int] = None
    length_scale: float = 1.0  # Speed: 1.0=normal, <1.0=faster, >1.0=slower
    noise_scale: float = 0.667  # Speech variability
    noise_w: float = 0.8  # Pronunciation variability
    sentence_silence: float = 0.2  # Seconds of silence between sentences
    download_dir: str = "piper_models"
    use_gpu: bool = True  # Piper is CPU-optimized, but keeping for compatibility