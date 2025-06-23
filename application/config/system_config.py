# application/config/system_config.py
from dataclasses import dataclass
from typing import Optional
import os
from enum import Enum


class TTSEngine(Enum):
    PIPER = "piper"
    GEMINI = "gemini"


@dataclass
class SystemConfig:
    """Single source of truth for all application configuration"""

    # Core TTS settings
    tts_engine: TTSEngine

    # File handling
    upload_folder: str = "uploads"
    audio_folder: str = "audio_outputs"
    max_file_size_mb: int = 100
    local_storage_dir: str = ".local"

    # Processing settings
    enable_text_cleaning: bool = True
    enable_ssml: bool = True
    document_type: str = "research_paper"  # research_paper, literature_review, general
    enable_async_audio: bool = True
    max_concurrent_requests: int = 4
    chunk_size: int = 20000

    # File management settings
    enable_file_cleanup: bool = True
    max_file_age_hours: float = 24.0  # Clean up files older than 24 hours
    auto_cleanup_interval_hours: float = 6.0  # Run cleanup every 6 hours
    max_disk_usage_mb: int = 1000  # Maximum disk usage before forced cleanup

    # Gemini specific
    gemini_api_key: Optional[str] = None
    gemini_model_name: str = "gemini-2.5-flash-preview-tts"  # TTS-capable model
    gemini_voice_name: str = "Kore"
    gemini_min_request_interval: float = 2.0
    gemini_measurement_mode_interval: float = 0.8  # Faster rate for measurement mode batches
    gemini_use_measurement_mode: bool = False  # Enable for accurate read-along timing

    # Piper specific
    piper_model_name: str = "en_US-lessac-medium"
    piper_models_dir: str = ".local/piper_models"
    piper_length_scale: float = 1.0

    # Audio processing settings
    audio_bitrate: str = "128k"
    audio_sample_rate: int = 22050
    mp3_codec: str = "libmp3lame"

    # Processing timeouts (seconds)
    tts_timeout_seconds: int = 60
    ocr_timeout_seconds: int = 30
    ffmpeg_timeout_seconds: int = 300

    # File type configuration
    allowed_extensions: set = None  # Will be set in __post_init__
    audio_extensions: set = None    # Will be set in __post_init__
    timing_file_suffix: str = "_timing.json"
    combined_file_suffix: str = "_combined"
    
    # Configuration file paths
    academic_terms_config: str = "config/academic_terms_en.json"
    rate_limits_config: str = "config/rate_limits.json"
    
    # Model repository settings
    piper_model_repository_url: str = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
    model_cache_dir: str = "model_cache"

    # OCR settings
    ocr_dpi: int = 300
    ocr_threshold: int = 180
    ocr_language: str = "eng"  # Tesseract language code

    # Text processing
    llm_max_chunk_size: int = 100000
    audio_target_chunk_size: int = 3000
    audio_max_chunk_size: int = 5000

    def __post_init__(self):
        """Initialize mutable default values"""
        if self.allowed_extensions is None:
            # Parse from environment variable or use default
            allowed_ext_str = os.getenv('ALLOWED_EXTENSIONS', 'pdf')
            self.allowed_extensions = set(ext.strip() for ext in allowed_ext_str.split(','))
        if self.audio_extensions is None:
            audio_ext_str = os.getenv('AUDIO_EXTENSIONS', 'wav,mp3')
            self.audio_extensions = set(ext.strip() for ext in audio_ext_str.split(','))

    @classmethod
    def from_env(cls) -> 'SystemConfig':
        """Load configuration from environment variables with validation"""

        # Parse TTS engine (strip whitespace and handle case-insensitive)
        tts_engine_str = os.getenv('TTS_ENGINE', 'piper').strip().lower()
        try:
            tts_engine = TTSEngine(tts_engine_str)
        except ValueError:
            valid_engines = [e.value for e in TTSEngine]
            raise ValueError(f"Invalid TTS_ENGINE '{tts_engine_str}'. Must be one of: {valid_engines}")

        # Create config
        config = cls(
            tts_engine=tts_engine,
            upload_folder=os.getenv('UPLOAD_FOLDER', 'uploads'),
            audio_folder=os.getenv('AUDIO_FOLDER', 'audio_outputs'),
            max_file_size_mb=cls._parse_int('MAX_FILE_SIZE_MB', 100, min_val=1, max_val=1000),
            enable_text_cleaning=cls._parse_bool('ENABLE_TEXT_CLEANING', True),
            enable_ssml=cls._parse_bool('ENABLE_SSML', True),
            document_type=os.getenv('DOCUMENT_TYPE', 'research_paper'),
            enable_async_audio=cls._parse_bool('ENABLE_ASYNC_AUDIO', True),
            max_concurrent_requests=cls._parse_int('MAX_CONCURRENT_TTS_REQUESTS', 4, min_val=1, max_val=20),
            chunk_size=cls._parse_int('CHUNK_SIZE', 20000, min_val=1000, max_val=100000),

            # File management
            enable_file_cleanup=cls._parse_bool('ENABLE_FILE_CLEANUP', True),
            max_file_age_hours=cls._parse_float('MAX_FILE_AGE_HOURS', 24.0, min_val=0.1, max_val=168.0),  # Max 1 week
            auto_cleanup_interval_hours=cls._parse_float('AUTO_CLEANUP_INTERVAL_HOURS', 6.0, min_val=0.1, max_val=24.0),
            max_disk_usage_mb=cls._parse_int('MAX_DISK_USAGE_MB', 1000, min_val=10, max_val=10000),

            gemini_api_key=os.getenv('GOOGLE_AI_API_KEY'),
            gemini_model_name=os.getenv('GEMINI_MODEL_NAME', 'gemini-2.5-flash-preview-tts'),
            gemini_voice_name=os.getenv('GEMINI_VOICE_NAME', 'Kore'),
            gemini_min_request_interval=cls._parse_float('GEMINI_MIN_REQUEST_INTERVAL', 2.0, min_val=0.1, max_val=10.0),
            gemini_measurement_mode_interval=cls._parse_float('GEMINI_MEASUREMENT_MODE_INTERVAL', 0.8, min_val=0.1, max_val=5.0),
            gemini_use_measurement_mode=cls._parse_bool('GEMINI_USE_MEASUREMENT_MODE', False),
            piper_model_name=os.getenv('PIPER_MODEL_NAME', 'en_US-lessac-medium'),
            piper_models_dir=os.getenv('PIPER_MODELS_DIR', 'piper_models'),
            piper_length_scale=cls._parse_float('PIPER_LENGTH_SCALE', 1.0, min_val=0.5, max_val=2.0),

            # Audio processing settings
            audio_bitrate=os.getenv('AUDIO_BITRATE', '128k'),
            audio_sample_rate=cls._parse_int('AUDIO_SAMPLE_RATE', 22050, min_val=8000, max_val=48000),
            mp3_codec=os.getenv('MP3_CODEC', 'libmp3lame'),

            # Processing timeouts
            tts_timeout_seconds=cls._parse_int('TTS_TIMEOUT_SECONDS', 60, min_val=10, max_val=300),
            ocr_timeout_seconds=cls._parse_int('OCR_TIMEOUT_SECONDS', 30, min_val=5, max_val=120),
            ffmpeg_timeout_seconds=cls._parse_int('FFMPEG_TIMEOUT_SECONDS', 300, min_val=30, max_val=600),

            # OCR settings
            ocr_dpi=cls._parse_int('OCR_DPI', 300, min_val=150, max_val=600),
            ocr_threshold=cls._parse_int('OCR_THRESHOLD', 180, min_val=100, max_val=240),
            ocr_language=os.getenv('OCR_LANGUAGE', 'eng'),

            # Text processing
            llm_max_chunk_size=cls._parse_int('LLM_MAX_CHUNK_SIZE', 100000, min_val=1000, max_val=500000),
            audio_target_chunk_size=cls._parse_int('AUDIO_TARGET_CHUNK_SIZE', 3000, min_val=500, max_val=10000),
            audio_max_chunk_size=cls._parse_int('AUDIO_MAX_CHUNK_SIZE', 5000, min_val=1000, max_val=20000),
            
            # Configuration file paths
            academic_terms_config=os.getenv('ACADEMIC_TERMS_CONFIG', 'config/academic_terms_en.json'),
            rate_limits_config=os.getenv('RATE_LIMITS_CONFIG', 'config/rate_limits.json'),
            
            # Model repository settings
            piper_model_repository_url=os.getenv('PIPER_MODEL_REPOSITORY_URL', 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0'),
            model_cache_dir=os.getenv('MODEL_CACHE_DIR', 'model_cache')
        )

        # Validate the complete configuration
        config.validate()
        return config

    def validate(self) -> None:
        """Validate configuration and fail fast with clear error messages"""

        # Engine-specific validation
        if self.tts_engine == TTSEngine.GEMINI:
            if not self.gemini_api_key:
                raise ValueError(
                    "GOOGLE_AI_API_KEY is required when TTS_ENGINE=gemini. "
                    "Please set this environment variable."
                )
            if self.gemini_api_key == "YOUR_GOOGLE_AI_API_KEY":
                raise ValueError(
                    "Please set a valid GOOGLE_AI_API_KEY (not the placeholder value)"
                )

        if self.tts_engine == TTSEngine.PIPER:
            if not self.piper_model_name:
                raise ValueError("PIPER_MODEL_NAME cannot be empty when using Piper TTS")

        # Validate directory names
        for folder_name, folder_path in [
            ("UPLOAD_FOLDER", self.upload_folder),
            ("AUDIO_FOLDER", self.audio_folder),
            ("PIPER_MODELS_DIR", self.piper_models_dir)
        ]:
            if not folder_path or folder_path.isspace():
                raise ValueError(f"{folder_name} cannot be empty or whitespace")

        # Validate document type
        valid_doc_types = ['research_paper', 'literature_review', 'general']
        if self.document_type not in valid_doc_types:
            raise ValueError(f"DOCUMENT_TYPE must be one of: {valid_doc_types}, got: {self.document_type}")

        # Validate file management settings
        if self.enable_file_cleanup:
            if self.max_file_age_hours <= 0:
                raise ValueError("MAX_FILE_AGE_HOURS must be positive when file cleanup is enabled")
            if self.auto_cleanup_interval_hours <= 0:
                raise ValueError("AUTO_CLEANUP_INTERVAL_HOURS must be positive when file cleanup is enabled")
            if self.max_disk_usage_mb <= 0:
                raise ValueError("MAX_DISK_USAGE_MB must be positive when file cleanup is enabled")

    @staticmethod
    def _parse_bool(env_var: str, default: bool) -> bool:
        """Parse boolean from environment variable"""
        value = os.getenv(env_var)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    @staticmethod
    def _parse_int(env_var: str, default: int, min_val: int = None, max_val: int = None) -> int:
        """Parse integer from environment variable with validation"""
        value = os.getenv(env_var)
        if value is None:
            return default

        try:
            parsed = int(value)
        except ValueError:
            raise ValueError(f"{env_var} must be a valid integer, got: {value}")

        if min_val is not None and parsed < min_val:
            raise ValueError(f"{env_var} must be >= {min_val}, got: {parsed}")
        if max_val is not None and parsed > max_val:
            raise ValueError(f"{env_var} must be <= {max_val}, got: {parsed}")

        return parsed

    @staticmethod
    def _parse_float(env_var: str, default: float, min_val: float = None, max_val: float = None) -> float:
        """Parse float from environment variable with validation"""
        value = os.getenv(env_var)
        if value is None:
            return default

        try:
            parsed = float(value)
        except ValueError:
            raise ValueError(f"{env_var} must be a valid number, got: {value}")

        if min_val is not None and parsed < min_val:
            raise ValueError(f"{env_var} must be >= {min_val}, got: {parsed}")
        if max_val is not None and parsed > max_val:
            raise ValueError(f"{env_var} must be <= {max_val}, got: {parsed}")

        return parsed

    def get_gemini_config(self):
        """Get Gemini-specific configuration"""
        try:
            from domain.config.tts_config import GeminiConfig
            return GeminiConfig(
                voice_name=self.gemini_voice_name,
                api_key=self.gemini_api_key,
                min_request_interval=self.gemini_min_request_interval
            )
        except ImportError:
            # Return a simple dict if the config class doesn't exist yet
            return {
                'voice_name': self.gemini_voice_name,
                'api_key': self.gemini_api_key,
                'min_request_interval': self.gemini_min_request_interval
            }

    def get_piper_config(self):
        """Get Piper-specific configuration"""
        try:
            from domain.config.tts_config import PiperConfig
            return PiperConfig(
                model_name=self.piper_model_name,
                download_dir=self.piper_models_dir,
                length_scale=self.piper_length_scale
            )
        except ImportError:
            # Return a simple dict if the config class doesn't exist yet
            return {
                'model_name': self.piper_model_name,
                'download_dir': self.piper_models_dir,
                'length_scale': self.piper_length_scale
            }

    def print_summary(self) -> None:
        """Print configuration summary for debugging"""
        print("=" * 50)
        print("PDF to Audio Converter - Configuration")
        print("=" * 50)
        print(f"TTS Engine: {self.tts_engine.value}")
        print(f"Text Cleaning: {'Enabled' if self.enable_text_cleaning else 'Disabled'}")
        print(f"SSML Enhancement: {'Enabled' if self.enable_ssml else 'Disabled'}")
        print(f"Document Type: {self.document_type}")
        print(f"Async Audio: {'Enabled' if self.enable_async_audio else 'Disabled'}")
        print(f"Max Concurrent: {self.max_concurrent_requests}")
        print(f"Upload Folder: {self.upload_folder}")
        print(f"Audio Folder: {self.audio_folder}")

        # File management
        print(f"File Cleanup: {'Enabled' if self.enable_file_cleanup else 'Disabled'}")
        if self.enable_file_cleanup:
            print(f"Max File Age: {self.max_file_age_hours} hours")
            print(f"Cleanup Interval: {self.auto_cleanup_interval_hours} hours")
            print(f"Max Disk Usage: {self.max_disk_usage_mb} MB")

        if self.tts_engine == TTSEngine.GEMINI:
            api_key_status = "Set" if self.gemini_api_key else "Missing"
            print(f"Gemini API Key: {api_key_status}")
            print(f"Gemini Voice: {self.gemini_voice_name}")
        elif self.tts_engine == TTSEngine.PIPER:
            print(f"Piper Model: {self.piper_model_name}")
            print(f"Piper Models Dir: {self.piper_models_dir}")

        print("=" * 50)
