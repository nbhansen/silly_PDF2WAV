# application/config/system_config.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
import yaml
from pathlib import Path


class TTSEngine(Enum):
    PIPER = "piper"
    GEMINI = "gemini"


@dataclass
class SystemConfig:
    """Single source of truth for all application configuration"""

    # Core TTS settings (required fields first)
    tts_engine: TTSEngine
    llm_model_name: str  # Required: LLM model for text cleaning
    gemini_model_name: str  # Required: Gemini TTS model name

    # File handling
    upload_folder: str = "uploads"
    audio_folder: str = "audio_outputs"
    max_file_size_mb: int = 100
    local_storage_dir: str = ".local"

    # Processing settings
    enable_text_cleaning: bool = True
    enable_ssml: bool = True
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
    gemini_voice_name: str = "Kore"
    gemini_min_request_interval: float = 6.5  # Optimized for 10 RPM limit (6s + buffer)
    gemini_measurement_mode_interval: float = 0.8  # Faster rate for measurement mode batches
    gemini_use_measurement_mode: bool = False  # Enable for accurate read-along timing
    gemini_max_concurrent_requests: int = 2  # Optimal concurrency for rate limits
    gemini_requests_per_minute: int = 10  # Official Gemini TTS rate limit
    gemini_chunk_size_multiplier: float = 2.0  # Increase chunk sizes for efficiency

    # LLM specific (text cleaning) - Conservative Pro limits
    llm_min_request_interval: float = 0.5  # Conservative for Pro (120 RPM with buffer)
    llm_max_concurrent_requests: int = 3  # Safe concurrency for text cleaning
    llm_requests_per_minute: int = 120  # Buffer under Pro 150 RPM limit
    text_cleaning_chunk_size: int = 8000  # Doubled for efficiency

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
    
    # Model repository settings
    piper_model_repository_url: str = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
    model_cache_dir: str = "model_cache"

    # OCR settings
    ocr_dpi: int = 300
    ocr_threshold: int = 180
    ocr_language: str = "eng"  # Tesseract language code

    # Flask application settings
    flask_debug: bool = True
    flask_host: str = "0.0.0.0"
    flask_port: int = 5000

    # Text processing
    llm_max_chunk_size: int = 100000
    audio_target_chunk_size: int = 3000
    audio_max_chunk_size: int = 5000

    def __post_init__(self):
        """Initialize mutable default values"""
        if self.allowed_extensions is None:
            self.allowed_extensions = {'pdf'}
        if self.audio_extensions is None:
            self.audio_extensions = {'wav', 'mp3'}

    @classmethod
    def from_yaml(cls, config_path: str = "config.yaml") -> 'SystemConfig':
        """Load configuration from YAML file only (no environment variable fallback)"""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(
                f"Configuration file {config_path} not found. "
                "Please copy config.example.yaml to config.yaml and customize it."
            )
        
        try:
            with open(config_file, 'r') as f:
                yaml_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_path}: {e}")
        
        # Helper function to get nested config values from YAML only
        def get_config(yaml_path: str, default=None):
            keys = yaml_path.split('.')
            value = yaml_config
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            return value
        
        # Parse TTS engine
        tts_engine_str = get_config('tts.engine', 'piper')
        if not tts_engine_str:
            raise ValueError("Missing required configuration: tts.engine")
        tts_engine_str = str(tts_engine_str).strip().lower()
        try:
            tts_engine = TTSEngine(tts_engine_str)
        except ValueError:
            valid_engines = [e.value for e in TTSEngine]
            raise ValueError(f"Invalid TTS engine '{tts_engine_str}'. Must be one of: {valid_engines}")
        
        # Create config from YAML with proper type parsing
        config = cls(
            tts_engine=tts_engine,
            
            # App settings
            upload_folder=get_config('files.upload_folder', 'uploads'),
            audio_folder=get_config('files.audio_folder', 'audio_outputs'),
            max_file_size_mb=cls._parse_int_value(get_config('files.max_file_size_mb', 20), 20, min_val=1, max_val=1000),
            local_storage_dir=get_config('files.local_storage_dir', '.local'),
            
            # Text processing
            enable_text_cleaning=cls._parse_bool_value(get_config('text_processing.enable_text_cleaning', True), True),
            enable_ssml=cls._parse_bool_value(get_config('text_processing.enable_ssml', True), True),
            chunk_size=cls._parse_int_value(get_config('text_processing.chunk_size', 4000), 4000, min_val=1000, max_val=100000),
            llm_max_chunk_size=cls._parse_int_value(get_config('text_processing.llm_max_chunk_size', 100000), 100000, min_val=1000, max_val=500000),
            audio_target_chunk_size=cls._parse_int_value(get_config('text_processing.audio_target_chunk_size', 2000), 2000, min_val=500, max_val=10000),
            audio_max_chunk_size=cls._parse_int_value(get_config('text_processing.audio_max_chunk_size', 3000), 3000, min_val=1000, max_val=20000),
            
            # Performance
            enable_async_audio=cls._parse_bool_value(get_config('performance.enable_async_audio', True), True),
            max_concurrent_requests=cls._parse_int_value(get_config('performance.max_concurrent_tts_requests', 3), 3, min_val=1, max_val=20),
            
            # File cleanup
            enable_file_cleanup=cls._parse_bool_value(get_config('files.cleanup.enabled', True), True),
            max_file_age_hours=cls._parse_float_value(get_config('files.cleanup.max_file_age_hours', 24.0), 24.0, min_val=0.1, max_val=168.0),
            auto_cleanup_interval_hours=cls._parse_float_value(get_config('files.cleanup.auto_cleanup_interval_hours', 6.0), 6.0, min_val=0.1, max_val=24.0),
            max_disk_usage_mb=cls._parse_int_value(get_config('files.cleanup.max_disk_usage_mb', 500), 500, min_val=10, max_val=10000),
            
            # LLM settings (for text cleaning)
            llm_model_name=get_config('llm.model_name'),
            llm_min_request_interval=cls._parse_float_value(get_config('llm.min_request_interval', 0.5), 0.5, min_val=0.1, max_val=5.0),
            llm_max_concurrent_requests=cls._parse_int_value(get_config('llm.max_concurrent_requests', 3), 3, min_val=1, max_val=10),
            llm_requests_per_minute=cls._parse_int_value(get_config('llm.requests_per_minute', 120), 120, min_val=10, max_val=1000),
            
            # Gemini settings
            gemini_api_key=get_config('secrets.google_ai_api_key'),
            gemini_model_name=get_config('tts.gemini.model_name'),
            gemini_voice_name=get_config('tts.gemini.voice_name', 'Kore'),
            gemini_min_request_interval=cls._parse_float_value(get_config('tts.gemini.min_request_interval', 2.0), 2.0, min_val=0.1, max_val=10.0),
            gemini_measurement_mode_interval=cls._parse_float_value(get_config('tts.gemini.measurement_mode_interval', 0.8), 0.8, min_val=0.1, max_val=5.0),
            gemini_use_measurement_mode=cls._parse_bool_value(get_config('tts.gemini.use_measurement_mode', False), False),
            
            # Piper settings
            piper_model_name=get_config('tts.piper.model_name', 'en_US-lessac-medium'),
            piper_models_dir=get_config('tts.piper.models_dir', 'piper_models'),
            piper_length_scale=cls._parse_float_value(get_config('tts.piper.length_scale', 1.0), 1.0, min_val=0.5, max_val=2.0),
            
            # Audio processing
            audio_bitrate=get_config('audio.bitrate', '128k'),
            audio_sample_rate=cls._parse_int_value(get_config('audio.sample_rate', 22050), 22050, min_val=8000, max_val=48000),
            mp3_codec=get_config('audio.mp3_codec', 'libmp3lame'),
            
            # Timeouts
            tts_timeout_seconds=cls._parse_int_value(get_config('timeouts.tts_seconds', 60), 60, min_val=10, max_val=300),
            ocr_timeout_seconds=cls._parse_int_value(get_config('ocr.timeout_seconds', 30), 30, min_val=5, max_val=120),
            ffmpeg_timeout_seconds=cls._parse_int_value(get_config('timeouts.ffmpeg_seconds', 300), 300, min_val=30, max_val=600),
            
            # OCR settings
            ocr_dpi=cls._parse_int_value(get_config('ocr.dpi', 300), 300, min_val=150, max_val=600),
            ocr_threshold=cls._parse_int_value(get_config('ocr.threshold', 180), 180, min_val=100, max_val=240),
            ocr_language=get_config('ocr.language', 'eng'),
            
            # Flask application settings
            flask_debug=cls._parse_bool_value(get_config('app.debug', True), True),
            flask_host=get_config('app.host', '0.0.0.0'),
            flask_port=cls._parse_int_value(get_config('app.port', 5000), 5000, min_val=1000, max_val=65535),
            
            # Model repository settings
            piper_model_repository_url=get_config('tts.piper.model_repository_url', 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0'),
            model_cache_dir=get_config('model_cache_dir', 'model_cache')
        )
        
        # Handle file extensions
        allowed_ext = get_config('files.allowed_extensions', ['pdf'])
        if isinstance(allowed_ext, list):
            config.allowed_extensions = set(allowed_ext)
        else:
            config.allowed_extensions = set(ext.strip() for ext in str(allowed_ext).split(','))
            
        audio_ext = get_config('files.audio_extensions', ['wav', 'mp3'])
        if isinstance(audio_ext, list):
            config.audio_extensions = set(audio_ext)
        else:
            config.audio_extensions = set(ext.strip() for ext in str(audio_ext).split(','))
        
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

        # Validate file management settings
        if self.enable_file_cleanup:
            if self.max_file_age_hours <= 0:
                raise ValueError("MAX_FILE_AGE_HOURS must be positive when file cleanup is enabled")
            if self.auto_cleanup_interval_hours <= 0:
                raise ValueError("AUTO_CLEANUP_INTERVAL_HOURS must be positive when file cleanup is enabled")
            if self.max_disk_usage_mb <= 0:
                raise ValueError("MAX_DISK_USAGE_MB must be positive when file cleanup is enabled")


    @staticmethod
    def _parse_bool_value(value: Any, default: bool = None) -> bool:
        """Parse boolean from various representations (for YAML values)"""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return default if default is not None else False

    @staticmethod
    def _parse_int_value(value: Any, default: int, min_val: int = None, max_val: int = None) -> int:
        """Parse integer from various representations with validation"""
        if value is None:
            return default
        
        try:
            if isinstance(value, bool):
                # Handle bool before int since bool is subclass of int
                parsed = 1 if value else 0
            else:
                parsed = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Value must be a valid integer, got: {value}")

        if min_val is not None and parsed < min_val:
            raise ValueError(f"Value must be >= {min_val}, got: {parsed}")
        if max_val is not None and parsed > max_val:
            raise ValueError(f"Value must be <= {max_val}, got: {parsed}")

        return parsed

    @staticmethod
    def _parse_float_value(value: Any, default: float, min_val: float = None, max_val: float = None) -> float:
        """Parse float from various representations with validation"""
        if value is None:
            return default

        try:
            parsed = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Value must be a valid number, got: {value}")

        if min_val is not None and parsed < min_val:
            raise ValueError(f"Value must be >= {min_val}, got: {parsed}")
        if max_val is not None and parsed > max_val:
            raise ValueError(f"Value must be <= {max_val}, got: {parsed}")

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
