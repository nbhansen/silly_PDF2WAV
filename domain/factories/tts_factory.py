# domain/factories/tts_factory.py - TTS Engine Factory
"""
Focused factory for TTS engine creation.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.config.system_config import SystemConfig
    from domain.interfaces import ITTSEngine


def create_tts_engine(config: 'SystemConfig') -> 'ITTSEngine':
    """Create TTS engine based on configuration"""
    from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
    from infrastructure.tts.piper_tts_provider import PiperTTSProvider
    
    if config.tts_engine.value == 'gemini':
        # CRITICAL: This creates Gemini TTS for AUDIO GENERATION, not text processing
        # Uses TTS models like 'text-to-speech-1', NOT language models like 'gemini-1.5-flash'
        # This is completely different from GeminiLLMProvider used for text cleaning
        return GeminiTTSProvider(
            model_name=config.gemini_model_name,  # TTS model name, not LLM model
            api_key=config.gemini_api_key,
            voice_name=config.gemini_voice_name,
            min_request_interval=config.gemini_min_request_interval,
            max_concurrent_requests=config.gemini_max_concurrent_requests,
            requests_per_minute=config.gemini_requests_per_minute
        )
    else:
        return PiperTTSProvider(
            config.get_piper_config(),
            repository_url=config.piper_model_repository_url
        )
