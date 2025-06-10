# application/config/config_builders.py - Simplified
import os
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from domain.config import GeminiConfig, PiperConfig

T = TypeVar('T')

class ConfigBuilder(ABC, Generic[T]):
    @classmethod
    @abstractmethod
    def from_env(cls) -> T:
        pass
    
    @staticmethod
    def _get_bool(env_var: str, default: bool = False) -> bool:
        value = os.getenv(env_var)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    @staticmethod
    def _get_float(env_var: str, default: float) -> float:
        value = os.getenv(env_var)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default
    
    @staticmethod
    def _get_int(env_var: str, default: int) -> int:
        value = os.getenv(env_var)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

class GeminiConfigBuilder(ConfigBuilder[GeminiConfig]):
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
