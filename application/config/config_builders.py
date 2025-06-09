# application/config/config_builders.py - Environment-Aware Config Builders
import os
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from domain.config import (
    TTSConfig, CoquiConfig, GTTSConfig, BarkConfig, GeminiConfig, PiperConfig
)

T = TypeVar('T')

class ConfigBuilder(ABC, Generic[T]):
    """Base class for configuration builders"""
    
    @classmethod
    @abstractmethod
    def from_env(cls) -> T:
        """Build configuration from environment variables"""
        pass
    
    @staticmethod
    def _get_bool(env_var: str, default: bool = False) -> bool:
        """Helper to parse boolean environment variables"""
        value = os.getenv(env_var)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    @staticmethod
    def _get_float(env_var: str, default: float) -> float:
        """Helper to parse float environment variables"""
        value = os.getenv(env_var)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            print(f"Warning: Invalid float value for {env_var}: {value}, using default {default}")
            return default
    
    @staticmethod
    def _get_int(env_var: str, default: int) -> int:
        """Helper to parse int environment variables"""
        value = os.getenv(env_var)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            print(f"Warning: Invalid int value for {env_var}: {value}, using default {default}")
            return default

class CoquiConfigBuilder(ConfigBuilder[CoquiConfig]):
    """Builds CoquiConfig from environment variables"""
    
    @classmethod
    def from_env(cls) -> CoquiConfig:
        return CoquiConfig(
            model_name=os.getenv('COQUI_MODEL_NAME') or CoquiConfig.model_name,
            speaker=os.getenv('COQUI_SPEAKER'),
            use_gpu=cls._get_bool('COQUI_USE_GPU_IF_AVAILABLE', CoquiConfig.use_gpu)
        )

class GTTSConfigBuilder(ConfigBuilder[GTTSConfig]):
    """Builds GTTSConfig from environment variables"""
    
    @classmethod
    def from_env(cls) -> GTTSConfig:
        return GTTSConfig(
            lang=os.getenv('GTTS_LANG') or GTTSConfig.lang,
            tld=os.getenv('GTTS_TLD') or GTTSConfig.tld,
            slow=cls._get_bool('GTTS_SLOW', GTTSConfig.slow)
        )

class BarkConfigBuilder(ConfigBuilder[BarkConfig]):
    """Builds BarkConfig from environment variables"""
    
    @classmethod
    def from_env(cls) -> BarkConfig:
        return BarkConfig(
            use_gpu=cls._get_bool('BARK_USE_GPU_IF_AVAILABLE', BarkConfig.use_gpu),
            use_small_models=cls._get_bool('BARK_USE_SMALL_MODELS', BarkConfig.use_small_models),
            history_prompt=os.getenv('BARK_HISTORY_PROMPT')
        )

class GeminiConfigBuilder(ConfigBuilder[GeminiConfig]):
    """Builds GeminiConfig from environment variables"""
    
    @classmethod
    def from_env(cls) -> GeminiConfig:
        return GeminiConfig(
            voice_name=os.getenv('GEMINI_VOICE_NAME') or GeminiConfig.voice_name,
            style_prompt=os.getenv('GEMINI_STYLE_PROMPT'),
            api_key=os.getenv('GOOGLE_AI_API_KEY'),
            min_request_interval=cls._get_float('GEMINI_MIN_REQUEST_INTERVAL', GeminiConfig.min_request_interval),
            max_retries=cls._get_int('GEMINI_MAX_RETRIES', GeminiConfig.max_retries),
            base_retry_delay=cls._get_int('GEMINI_BASE_RETRY_DELAY', GeminiConfig.base_retry_delay)
        )

class PiperConfigBuilder(ConfigBuilder[PiperConfig]):
    """Builds PiperConfig from environment variables"""
    
    @classmethod
    def from_env(cls) -> PiperConfig:
        return PiperConfig(
            model_name=os.getenv('PIPER_MODEL_NAME') or PiperConfig.model_name,
            model_path=os.getenv('PIPER_MODEL_PATH'),
            config_path=os.getenv('PIPER_CONFIG_PATH'),
            speaker_id=cls._get_int('PIPER_SPEAKER_ID', 0) if os.getenv('PIPER_SPEAKER_ID') else None,
            length_scale=cls._get_float('PIPER_SPEED', PiperConfig.length_scale),
            noise_scale=cls._get_float('PIPER_NOISE_SCALE', PiperConfig.noise_scale),
            noise_w=cls._get_float('PIPER_NOISE_W', PiperConfig.noise_w),
            sentence_silence=cls._get_float('PIPER_SENTENCE_SILENCE', PiperConfig.sentence_silence),
            download_dir=os.getenv('PIPER_MODELS_DIR') or PiperConfig.download_dir,
            use_gpu=cls._get_bool('PIPER_USE_GPU', PiperConfig.use_gpu)
        )