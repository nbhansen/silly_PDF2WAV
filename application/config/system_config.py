# application/config/system_config.py
from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

import yaml

# Type for YAML configuration values (more specific for actual usage)
YAMLValue = Union[str, int, float, bool, list[str], dict[str, object], None]
# Type for simple YAML values (no containers)
SimpleYAMLValue = Union[str, int, float, bool, None]

if TYPE_CHECKING:
    from domain.config.tts_config import GeminiConfig, PiperConfig


class TTSEngine(Enum):
    """Enumeration of supported TTS engines."""

    PIPER = "piper"
    GEMINI = "gemini"


@dataclass(frozen=True)
class SystemConfig:
    """Single source of truth for all application configuration."""

    # Core TTS settings (required fields first)
    tts_engine: TTSEngine
    llm_model_name: Optional[str]  # LLM model for text cleaning

    # File handling
    upload_folder: str = "uploads"
    audio_folder: str = "audio_outputs"
    max_file_size_mb: int = 100

    # Processing settings
    enable_text_cleaning: bool = True
    enable_natural_formatting: bool = True
    enable_async_audio: bool = True

    # Audio processing parallelism - how many chunks AudioEngine processes simultaneously
    audio_concurrent_chunks: int = 4

    # Text chunk configuration - different optimal sizes for different APIs
    chunk_size: int = 20000  # Legacy setting
    llm_chunk_size: int = 50000  # Large chunks for LLM text cleaning (fewer API calls)

    # File management settings
    enable_file_cleanup: bool = True
    max_file_age_hours: float = 24.0  # Clean up files older than 24 hours
    auto_cleanup_interval_hours: float = 6.0  # Run cleanup every 6 hours
    max_disk_usage_mb: int = 1000  # Maximum disk usage before forced cleanup

    # TTS API configuration - applies to any TTS provider (Gemini, Piper, etc.)
    tts_concurrent_requests: int = 4  # How many simultaneous TTS API calls
    tts_request_delay_seconds: float = 2.0  # Delay between TTS requests for rate limiting

    # Gemini TTS specific settings
    gemini_api_key: Optional[str] = None
    gemini_voice_name: str = "Kore"
    gemini_model_name: str = "gemini-2.5-flash-preview-tts"
    gemini_use_measurement_mode: bool = False  # Enable for accurate read-along timing
    gemini_measurement_mode_interval: float = 0.8  # Faster rate for measurement mode batches

    # LLM API configuration - for text cleaning (separate from TTS)
    llm_concurrent_requests: int = 3  # How many simultaneous LLM calls for text cleaning
    llm_request_delay_seconds: float = 0.5  # Delay between LLM requests

    # Piper specific
    piper_model_name: str = "en_US-lessac-medium"
    piper_models_dir: str = ".local/piper_models"
    piper_length_scale: float = 1.0

    # File type configuration - immutable sets (defaults set in __post_init__)
    allowed_extensions: Optional[frozenset[str]] = None
    audio_extensions: Optional[frozenset[str]] = None

    # Model repository settings
    piper_model_repository_url: str = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

    # OCR settings
    ocr_dpi: int = 300
    ocr_threshold: int = 180
    ocr_language: str = "eng"  # Tesseract language code

    # Flask application settings
    flask_debug: bool = True
    flask_host: str = "127.0.0.1"  # Secure default: localhost only
    flask_port: int = 5000

    # Security: Project root path (auto-detected, environment override allowed)
    project_root: str = ""

    # Text processing
    audio_target_chunk_size: int = 3000
    audio_max_chunk_size: int = 5000

    def __post_init__(self) -> None:
        """Initialize immutable defaults for None values (backwards compatibility)."""
        if self.allowed_extensions is None:
            object.__setattr__(self, "allowed_extensions", frozenset({"pdf"}))
        if self.audio_extensions is None:
            object.__setattr__(self, "audio_extensions", frozenset({"wav", "mp3"}))

        # Security: Initialize project_root if not set
        if not self.project_root:
            secure_root = self._get_secure_project_root()
            object.__setattr__(self, "project_root", secure_root)

    @classmethod
    def from_yaml(cls, config_path: str = "config.yaml") -> "SystemConfig":
        """Load configuration from YAML file using organized parsing methods."""
        # Load and validate YAML file
        yaml_config = cls._load_and_validate_yaml(config_path)

        # Create configuration accessor function
        get_config = cls._create_config_accessor(yaml_config)

        # Parse each configuration section
        tts_engine = cls._parse_tts_engine(get_config)
        extensions = cls._parse_file_extensions(get_config)
        file_settings = cls._parse_file_settings(get_config)
        text_processing = cls._parse_text_processing_settings(get_config)
        performance = cls._parse_performance_settings(get_config)
        llm_tts = cls._parse_llm_and_tts_settings(get_config)
        system = cls._parse_system_settings(get_config)

        # Combine all settings and create config
        config = cls(
            tts_engine=tts_engine,
            **extensions,
            **file_settings,
            **text_processing,
            **performance,
            **llm_tts,
            **system,
        )

        config.validate()
        return config

    @classmethod
    def _load_and_validate_yaml(cls, config_path: str) -> dict:
        """Load and validate YAML configuration file."""
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(
                f"Configuration file {config_path} not found. "
                "Please copy config.example.yaml to config.yaml and customize it."
            )

        try:
            with Path(config_file).open() as f:
                yaml_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_path}: {e}") from e

        return yaml_config

    @classmethod
    def _create_config_accessor(cls, yaml_config: dict[str, object]) -> object:
        """Create helper function to access nested YAML values."""

        def get_config(yaml_path: str, default: YAMLValue = None) -> YAMLValue:
            keys = yaml_path.split(".")
            value: YAMLValue = yaml_config  # Cast to our expected type
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]  # type: ignore[assignment]  # YAML parsing limitation
                else:
                    return default
            return value

        return get_config

    @classmethod
    def _parse_tts_engine(cls, get_config: object) -> TTSEngine:
        """Parse and validate TTS engine configuration."""
        tts_engine_str = get_config("tts.engine", "piper")
        if not tts_engine_str:
            raise ValueError("Missing required configuration: tts.engine")
        tts_engine_str = str(tts_engine_str).strip().lower()
        try:
            return TTSEngine(tts_engine_str)
        except ValueError as e:
            valid_engines = [e.value for e in TTSEngine]
            raise ValueError(f"Invalid TTS engine '{tts_engine_str}'. Must be one of: {valid_engines}") from e

    @classmethod
    def _parse_file_extensions(cls, get_config: object) -> dict[str, frozenset[str]]:
        """Parse allowed and audio extensions from YAML configuration."""
        # Process allowed extensions
        allowed_ext = get_config("files.allowed_extensions", ["pdf"])
        allowed_extensions: frozenset[str]
        if isinstance(allowed_ext, list):
            allowed_extensions = frozenset(allowed_ext)
        else:
            allowed_extensions = frozenset(ext.strip() for ext in str(allowed_ext).split(","))

        # Process audio extensions
        audio_ext = get_config("files.audio_extensions", ["wav", "mp3"])
        audio_extensions: frozenset[str]
        if isinstance(audio_ext, list):
            audio_extensions = frozenset(audio_ext)
        else:
            audio_extensions = frozenset(ext.strip() for ext in str(audio_ext).split(","))

        return {
            "allowed_extensions": allowed_extensions,
            "audio_extensions": audio_extensions,
        }

    @classmethod
    def _parse_file_settings(cls, get_config: object) -> dict[str, object]:
        """Parse file-related configuration settings."""
        return {
            "upload_folder": cls._parse_string_value(get_config("files.upload_folder", "uploads"), "uploads"),
            "audio_folder": cls._parse_string_value(get_config("files.audio_folder", "audio_outputs"), "audio_outputs"),
            "max_file_size_mb": cls._parse_int_value(
                get_config("files.max_file_size_mb", 20), 20, min_val=1, max_val=1000
            ),
        }

    @classmethod
    def _parse_text_processing_settings(cls, get_config: object) -> dict[str, object]:
        """Parse text processing configuration settings."""
        return {
            "enable_text_cleaning": cls._parse_bool_value(
                get_config("text_processing.enable_text_cleaning", True),
                True,  # type: ignore[misc]
            ),
            "enable_natural_formatting": cls._parse_bool_value(
                get_config("text_processing.enable_natural_formatting", True), True
            ),
            "chunk_size": cls._parse_int_value(
                get_config("text_processing.chunk_size", 4000), 4000, min_val=1000, max_val=100000
            ),
            "llm_chunk_size": cls._parse_int_value(
                get_config("text_processing.llm_chunk_size", 50000), 50000, min_val=10000, max_val=200000
            ),
            "audio_target_chunk_size": cls._parse_int_value(
                get_config("text_processing.audio_target_chunk_size", 3000), 3000, min_val=100, max_val=10000
            ),
            "audio_max_chunk_size": cls._parse_int_value(
                get_config("text_processing.audio_max_chunk_size", 5000), 5000, min_val=100, max_val=20000
            ),
        }

    @classmethod
    def _parse_performance_settings(cls, get_config: object) -> dict[str, object]:
        """Parse performance and resource management settings."""
        return {
            "enable_async_audio": cls._parse_bool_value(get_config("performance.enable_async_audio", True), True),
            "audio_concurrent_chunks": cls._parse_int_value(
                get_config("audio.concurrent_chunks", 4), 4, min_val=1, max_val=20
            ),
            "tts_concurrent_requests": cls._parse_int_value(
                get_config("tts.concurrent_requests", 4), 4, min_val=1, max_val=10
            ),
            "tts_request_delay_seconds": cls._parse_float_value(
                get_config("tts.request_delay_seconds", 2.0), 2.0, min_val=0.1, max_val=10.0
            ),
            "enable_file_cleanup": cls._parse_bool_value(get_config("files.cleanup.enabled", True), True),
            "max_file_age_hours": cls._parse_float_value(
                get_config("files.cleanup.max_file_age_hours", 24.0), 24.0, min_val=0.1, max_val=168.0
            ),
            "auto_cleanup_interval_hours": cls._parse_float_value(
                get_config("files.cleanup.auto_cleanup_interval_hours", 6.0), 6.0, min_val=0.1, max_val=24.0
            ),
            "max_disk_usage_mb": cls._parse_int_value(
                get_config("files.cleanup.max_disk_usage_mb", 1000), 1000, min_val=10, max_val=10000
            ),
        }

    @classmethod
    def _parse_llm_and_tts_settings(cls, get_config: object) -> dict[str, object]:
        """Parse LLM and TTS provider configuration settings."""
        return {
            # LLM settings
            "llm_model_name": cls._parse_optional_string_value(get_config("llm.model_name")),
            "llm_concurrent_requests": cls._parse_int_value(
                get_config("llm.concurrent_requests", 3), 3, min_val=1, max_val=10
            ),
            "llm_request_delay_seconds": cls._parse_float_value(
                get_config("llm.request_delay_seconds", 0.5), 0.5, min_val=0.1, max_val=5.0
            ),
            # Gemini TTS settings
            "gemini_api_key": cls._parse_optional_string_value(get_config("secrets.google_ai_api_key")),
            "gemini_model_name": cls._parse_string_value(
                get_config("tts.gemini.model_name", "gemini-2.5-flash-preview-tts"), "gemini-2.5-flash-preview-tts"
            ),
            "gemini_voice_name": cls._parse_string_value(get_config("tts.gemini.voice_name", "Kore"), "Kore"),
            "gemini_use_measurement_mode": cls._parse_bool_value(
                get_config("tts.gemini.use_measurement_mode", False), False
            ),
            "gemini_measurement_mode_interval": cls._parse_float_value(
                get_config("tts.gemini.measurement_mode_interval", 0.8), 0.8, min_val=0.1, max_val=5.0
            ),
            # Piper settings
            "piper_model_name": cls._parse_string_value(
                get_config("tts.piper.model_name", "en_US-lessac-medium"), "en_US-lessac-medium"
            ),
            "piper_models_dir": cls._parse_string_value(
                get_config("tts.piper.models_dir", "piper_models"), "piper_models"
            ),
            "piper_length_scale": cls._parse_float_value(
                get_config("tts.piper.length_scale", 1.0), 1.0, min_val=0.5, max_val=2.0
            ),
        }

    @classmethod
    def _parse_system_settings(cls, get_config: object) -> dict[str, object]:
        """Parse system-level configuration settings."""
        return {
            # OCR settings
            "ocr_dpi": cls._parse_int_value(get_config("ocr.dpi", 300), 300, min_val=150, max_val=600),
            "ocr_threshold": cls._parse_int_value(get_config("ocr.threshold", 180), 180, min_val=100, max_val=240),
            "ocr_language": cls._parse_string_value(get_config("ocr.language", "eng"), "eng"),
            # Flask application settings
            "flask_debug": cls._parse_bool_value(get_config("app.debug", True), True),
            "flask_host": cls._parse_string_value(
                get_config("app.host", "127.0.0.1"), "127.0.0.1"
            ),  # Secure default: localhost only
            "flask_port": cls._parse_int_value(get_config("app.port", 5000), 5000, min_val=1000, max_val=65535),
            # Model repository settings
            "piper_model_repository_url": cls._parse_string_value(
                get_config(
                    "tts.piper.model_repository_url", "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
                ),
                "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0",
            ),
        }

    def validate(self) -> None:
        """Validate configuration and fail fast with clear error messages."""
        # Engine-specific validation
        if self.tts_engine == TTSEngine.GEMINI:
            if not self.gemini_api_key:
                raise ValueError(
                    "GOOGLE_AI_API_KEY is required when TTS_ENGINE=gemini. " "Please set this environment variable."
                )
            if self.gemini_api_key == "YOUR_GOOGLE_AI_API_KEY":
                raise ValueError("Please set a valid GOOGLE_AI_API_KEY (not the placeholder value)")

        if self.tts_engine == TTSEngine.PIPER and not self.piper_model_name:
            raise ValueError("PIPER_MODEL_NAME cannot be empty when using Piper TTS")

        # Security validation for all directory paths
        for folder_name, folder_path in [
            ("UPLOAD_FOLDER", self.upload_folder),
            ("AUDIO_FOLDER", self.audio_folder),
            ("PIPER_MODELS_DIR", self.piper_models_dir),
        ]:
            self._validate_directory_security(folder_name, folder_path, self.project_root)

        # Validate file management settings
        if self.enable_file_cleanup:
            if self.max_file_age_hours <= 0:
                raise ValueError("MAX_FILE_AGE_HOURS must be positive when file cleanup is enabled")
            if self.auto_cleanup_interval_hours <= 0:
                raise ValueError("AUTO_CLEANUP_INTERVAL_HOURS must be positive when file cleanup is enabled")
            if self.max_disk_usage_mb <= 0:
                raise ValueError("MAX_DISK_USAGE_MB must be positive when file cleanup is enabled")

    @staticmethod
    def _get_secure_project_root() -> str:
        """Get secure project root path with environment override support."""
        # Allow environment override (for deployment flexibility)
        env_root = os.environ.get("PROJECT_ROOT")
        if env_root:
            # Validate environment path for security
            env_path = Path(env_root).resolve()
            if env_path.exists() and env_path.is_dir():
                return str(env_path)

        # Default to current working directory (deployment-safe)
        return str(Path.cwd())

    @staticmethod
    def _validate_directory_security(name: str, path: str, project_root: str) -> None:
        """Validate directory path for security vulnerabilities."""
        if not path or path.isspace():
            raise ValueError(f"{name} cannot be empty or whitespace")

        # Convert to Path object for security validation
        path_obj = Path(path)

        # If relative path, resolve relative to project root
        if not path_obj.is_absolute():
            path_obj = Path(project_root) / path_obj

        path_resolved = path_obj.resolve()
        project_resolved = Path(project_root).resolve()

        # Prevent path traversal outside project boundaries
        try:
            path_resolved.relative_to(project_resolved)
        except ValueError as e:
            raise ValueError(f"{name} must be within project directory: {path}") from e

    @staticmethod
    def _parse_string_value(value: YAMLValue, default: str) -> str:
        """Parse string from YAML value."""
        if value is None:
            return default
        return str(value)

    @staticmethod
    def _parse_optional_string_value(value: YAMLValue, default: Optional[str] = None) -> Optional[str]:
        """Parse optional string from YAML value."""
        if value is None:
            return default
        return str(value)

    @staticmethod
    def _parse_bool_value(value: YAMLValue, default: Optional[bool] = None) -> bool:
        """Parse boolean from various representations (for YAML values)."""
        if value is None:
            if default is None:
                raise ValueError("Boolean value cannot be None without a default")
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return default if default is not None else False

    @staticmethod
    def _parse_int_value(
        value: YAMLValue, default: int, min_val: Optional[int] = None, max_val: Optional[int] = None
    ) -> int:
        """Parse integer from various representations with validation."""
        if value is None:
            return default

        try:
            # Handle bool before int since bool is subclass of int
            if isinstance(value, bool):
                parsed = 1 if value else 0
            elif isinstance(value, (str, int, float)):
                parsed = int(value)
            else:
                raise ValueError(f"Cannot convert {type(value)} to int")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Value must be a valid integer, got: {value}") from e

        if min_val is not None and parsed < min_val:
            raise ValueError(f"Value must be >= {min_val}, got: {parsed}")
        if max_val is not None and parsed > max_val:
            raise ValueError(f"Value must be <= {max_val}, got: {parsed}")

        return parsed

    @staticmethod
    def _parse_float_value(
        value: YAMLValue, default: float, min_val: Optional[float] = None, max_val: Optional[float] = None
    ) -> float:
        """Parse float from various representations with validation."""
        if value is None:
            return default

        try:
            if isinstance(value, (str, int, float)):
                parsed = float(value)
            else:
                raise ValueError(f"Cannot convert {type(value)} to float")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Value must be a valid number, got: {value}") from e

        if min_val is not None and parsed < min_val:
            raise ValueError(f"Value must be >= {min_val}, got: {parsed}")
        if max_val is not None and parsed > max_val:
            raise ValueError(f"Value must be <= {max_val}, got: {parsed}")

        return parsed

    def get_gemini_config(self) -> Union["GeminiConfig", dict[str, Union[str, float, None]]]:
        """Get Gemini-specific configuration."""
        try:
            from domain.config.tts_config import GeminiConfig

            return GeminiConfig(
                voice_name=self.gemini_voice_name,
                api_key=self.gemini_api_key,
                min_request_interval=self.tts_request_delay_seconds,
            )
        except ImportError:
            # Return a simple dict if the config class doesn't exist yet
            return {
                "voice_name": self.gemini_voice_name,
                "api_key": self.gemini_api_key,
                "min_request_interval": self.tts_request_delay_seconds,
            }

    def get_piper_config(self) -> Union["PiperConfig", dict[str, Union[str, float]]]:
        """Get Piper-specific configuration."""
        try:
            from domain.config.tts_config import PiperConfig

            return PiperConfig(
                model_name=self.piper_model_name,
                download_dir=self.piper_models_dir,
                length_scale=self.piper_length_scale,
            )
        except ImportError:
            # Return a simple dict if the config class doesn't exist yet
            return {
                "model_name": self.piper_model_name,
                "download_dir": self.piper_models_dir,
                "length_scale": self.piper_length_scale,
            }

    def print_summary(self) -> None:
        """Print configuration summary for debugging."""
        print("=" * 50)
        print("PDF to Audio Converter - Configuration")
        print("=" * 50)
        print(f"TTS Engine: {self.tts_engine.value}")
        print(f"Text Cleaning: {'Enabled' if self.enable_text_cleaning else 'Disabled'}")
        print(f"Natural Formatting: {'Enabled' if self.enable_natural_formatting else 'Disabled'}")
        print(f"Async Audio: {'Enabled' if self.enable_async_audio else 'Disabled'}")
        print(f"Audio Concurrent Chunks: {self.audio_concurrent_chunks}")
        print(f"TTS Concurrent Requests: {self.tts_concurrent_requests}")
        print(f"LLM Concurrent Requests: {self.llm_concurrent_requests}")
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
