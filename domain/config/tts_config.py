# domain/config/tts_config.py - Pure Configuration Data Classes
from dataclasses import dataclass
from typing import Optional

@dataclass
class TTSConfig:
    """Unified TTS configuration with common parameters and engine-specific sections"""
    voice_quality: str = "medium"  # low/medium/high
    speaking_style: str = "neutral"  # casual/professional/narrative
    speed: float = 1.0
    enable_ssml: bool = True  # SSML support
    
    # Engine-specific configs
    coqui: Optional['CoquiConfig'] = None
    gtts: Optional['GTTSConfig'] = None
    bark: Optional['BarkConfig'] = None
    gemini: Optional['GeminiConfig'] = None
    piper: Optional['PiperConfig'] = None

@dataclass
class CoquiConfig:
    model_name: str = "tts_models/en/ljspeech/vits"
    speaker: Optional[str] = None
    use_gpu: bool = True

@dataclass
class GTTSConfig:
    lang: str = "en"
    tld: str = "co.uk"
    slow: bool = False

@dataclass
class BarkConfig:
    use_gpu: bool = True
    use_small_models: bool = True
    history_prompt: Optional[str] = None

@dataclass
class GeminiConfig:
    voice_name: str = "Kore"
    style_prompt: Optional[str] = None
    api_key: Optional[str] = None
    min_request_interval: float = 2.0
    max_retries: int = 3
    base_retry_delay: int = 16

@dataclass
class PiperConfig:
    """Configuration for Piper TTS"""
    model_name: str = "en_US-lessac-medium"
    model_path: Optional[str] = None
    config_path: Optional[str] = None
    speaker_id: Optional[int] = None
    length_scale: float = 1.0  # Speed: 1.0=normal, <1.0=faster, >1.0=slower
    noise_scale: float = 0.667  # Speech variability
    noise_w: float = 0.8  # Pronunciation variability
    sentence_silence: float = 0.2  # Seconds of silence between sentences
    download_dir: str = "piper_models"
    use_gpu: bool = False  # Piper is CPU-optimized