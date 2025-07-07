# domain/factories/tts_factory.py - TTS Engine Factory
"""Focused factory for TTS engine creation."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.config.system_config import SystemConfig
    from domain.interfaces import ITTSEngine


def create_tts_engine(config: "SystemConfig") -> "ITTSEngine":
    """Create Piper TTS engine for local audio generation."""
    from domain.config.tts_config import PiperConfig
    from infrastructure.tts.piper_tts_provider import PiperTTSProvider

    piper_config = config.get_piper_config()
    # Type narrowing: get_piper_config should return PiperConfig in normal cases
    if not isinstance(piper_config, PiperConfig):
        raise TypeError("Expected PiperConfig but got dict fallback")

    return PiperTTSProvider(piper_config, repository_url=config.piper_model_repository_url)
