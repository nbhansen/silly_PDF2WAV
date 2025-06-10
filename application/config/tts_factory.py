# application/config/tts_factory.py
import os
from domain.config import TTSConfig
from .config_builders import GeminiConfigBuilder, PiperConfigBuilder

class TTSConfigFactory:
    # Only register the engines we keep
    _builders = {
        'gemini': GeminiConfigBuilder,
        'piper': PiperConfigBuilder,
    }
    
    @classmethod
    def create_config(cls, engine_name: str) -> TTSConfig:
        engine_name = engine_name.lower()
        
        # Validate engine is supported
        if engine_name not in cls._builders:
            raise ValueError(f"Unsupported TTS engine: {engine_name}. "
                           f"Supported engines: {list(cls._builders.keys())}")
        
        # Get base config
        voice_quality = os.getenv('VOICE_QUALITY', 'medium')
        speaking_style = os.getenv('SPEAKING_STYLE', 'neutral')
        speed = float(os.getenv('TTS_SPEED', '1.0'))
        enable_ssml = os.getenv('ENABLE_SSML', 'True').lower() in ('true', '1', 'yes')
        
        config = TTSConfig(
            voice_quality=voice_quality,
            speaking_style=speaking_style,
            speed=speed,
            enable_ssml=enable_ssml
        )
        
        # Add engine-specific config
        builder = cls._builders[engine_name]
        engine_config = builder.from_env()
        setattr(config, engine_name, engine_config)
        
        return config
    
    @classmethod
    def get_supported_engines(cls) -> list[str]:
        return list(cls._builders.keys())
    
    @classmethod
    def is_engine_supported(cls, engine_name: str) -> bool:
        return engine_name.lower() in cls._builders