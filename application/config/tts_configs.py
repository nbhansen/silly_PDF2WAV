# application/config/tts_configs.py
"""Specialized configuration classes for TTS engines."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TTSEngine(Enum):
    """Enumeration of supported TTS engines."""

    PIPER = "piper"
    GEMINI = "gemini"


@dataclass(frozen=True)
class TTSConfig:
    """Base TTS configuration applicable to all engines."""

    engine: TTSEngine
    concurrent_requests: int = 4
    request_delay_seconds: float = 2.0


@dataclass(frozen=True)
class GeminiConfig:
    """Gemini TTS specific configuration."""

    api_key: Optional[str] = None
    voice_name: str = "Kore"
    model_name: str = "gemini-2.5-flash"
    use_measurement_mode: bool = False
    measurement_mode_interval: float = 0.8


@dataclass(frozen=True)
class PiperConfig:
    """Piper TTS specific configuration."""

    model_name: str = "en_US-lessac-medium"
    models_dir: str = ".local/piper_models"
    length_scale: float = 1.0
    model_repository_url: str = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
