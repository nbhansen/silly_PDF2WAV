# application/config/tts_factory.py - Clean Factory for TTS Configuration
import os
from domain.config import TTSConfig
from .config_builders import (
    CoquiConfigBuilder, GTTSConfigBuilder, BarkConfigBuilder, 
    GeminiConfigBuilder, PiperConfigBuilder
)

class TTSConfigFactory:
    """Factory for creating TTS configurations from environment variables"""
    
    # Registry of builders
    _builders = {
        'coqui': CoquiConfigBuilder,
        'gtts': GTTSConfigBuilder,
        'bark': BarkConfigBuilder,
        'gemini': GeminiConfigBuilder,
        'piper': PiperConfigBuilder,
    }
    
    @classmethod
    def create_config(cls, engine_name: str) -> TTSConfig:
        """Create TTSConfig for specified engine from environment variables"""
        engine_name = engine_name.lower()
        
        # Get base config
        voice_quality = os.getenv('VOICE_QUALITY', 'medium')
        speaking_style = os.getenv('SPEAKING_STYLE', 'neutral')
        speed = float(os.getenv('TTS_SPEED', '1.0'))
        enable_ssml = os.getenv('ENABLE_SSML', 'True').lower() in ('true', '1', 'yes')
        
        # Create base config
        config = TTSConfig(
            voice_quality=voice_quality,
            speaking_style=speaking_style,
            speed=speed,
            enable_ssml=enable_ssml
        )
        
        # Add engine-specific config
        if engine_name in cls._builders:
            builder = cls._builders[engine_name]
            engine_config = builder.from_env()
            setattr(config, engine_name, engine_config)
            print(f"TTSConfigFactory: Created {engine_name} config from environment")
        else:
            print(f"TTSConfigFactory: Unknown engine '{engine_name}', using default config")
        
        return config
    
    @classmethod
    def get_supported_engines(cls) -> list[str]:
        """Get list of supported engine names"""
        return list(cls._builders.keys())
    
    @classmethod
    def register_builder(cls, engine_name: str, builder_class):
        """Register a new config builder (for extensibility)"""
        cls._builders[engine_name.lower()] = builder_class
        print(f"TTSConfigFactory: Registered builder for '{engine_name}'")
    
    @classmethod
    def is_engine_supported(cls, engine_name: str) -> bool:
        """Check if an engine is supported"""
        return engine_name.lower() in cls._builders