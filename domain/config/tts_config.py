# domain/config/tts_config.py - Unified TTS Configuration
from dataclasses import dataclass
from enum import Enum


class TTSEngine(Enum):
    """Enumeration of supported TTS engines."""

    PIPER = "piper"
    GEMINI = "gemini"


@dataclass(frozen=True)
class GeminiConfig:
    """Configuration for Gemini TTS engine."""

    api_key: str | None = None
    voice_name: str = "Kore"
    model_name: str = "gemini-2.5-flash"
    style_prompt: str | None = None
    min_request_interval: float = 2.0
    max_retries: int = 3
    base_retry_delay: int = 16
    use_measurement_mode: bool = False
    measurement_mode_interval: float = 0.8


@dataclass(frozen=True)
class PiperConfig:
    """Configuration for Piper TTS engine."""

    model_name: str = "en_US-lessac-medium"
    models_dir: str = ".local/piper_models"
    length_scale: float = 1.0  # Speed: 1.0=normal, <1.0=faster, >1.0=slower
    model_repository_url: str = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
    model_path: str | None = None
    config_path: str | None = None
    speaker_id: int | None = None
    noise_scale: float = 0.667  # Speech variability
    noise_w: float = 0.8  # Pronunciation variability
    sentence_silence: float = 0.2  # Seconds of silence between sentences
    download_dir: str = "piper_models"
    use_gpu: bool = True  # Not yet implemented: Piper currently runs CPU-only. Kept for future use.


@dataclass(frozen=True)
class TTSConfig:
    """Base TTS configuration applicable to all engines."""

    engine: TTSEngine
    concurrent_requests: int = 4
    request_delay_seconds: float = 2.0
