# application/config/system_config_refactored.py
"""Refactored SystemConfig using composition of specialized configs."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Callable, Optional, Union, cast

import yaml

from .app_configs import FlaskConfig
from .file_configs import FileCleanupConfig, FileConfig
from .processing_configs import LLMConfig, OCRConfig, PerformanceConfig, TextProcessingConfig
from .tts_configs import GeminiConfig, PiperConfig, TTSConfig, TTSEngine

# Type for YAML configuration values
YAMLValue = Union[str, int, float, bool, list[str], dict[str, object], None]
# Type for config accessor function
ConfigAccessor = Callable[[str, Optional[YAMLValue]], YAMLValue]


@dataclass(frozen=True)
class SystemConfig:
    """Single source of truth for all application configuration using composition."""

    # Core configurations
    tts: TTSConfig
    files: FileConfig
    cleanup: FileCleanupConfig
    text_processing: TextProcessingConfig
    performance: PerformanceConfig
    flask: FlaskConfig
    ocr: OCRConfig
    llm: LLMConfig

    # Engine-specific configs (only one should be set based on tts.engine)
    gemini: Optional[GeminiConfig] = None
    piper: Optional[PiperConfig] = None

    # System-level settings
    project_root: str = ""

    def __post_init__(self) -> None:
        """Initialize project root if not set."""
        if not self.project_root:
            secure_root = self._get_secure_project_root()
            object.__setattr__(self, "project_root", secure_root)

    @classmethod
    def from_yaml(cls, config_path: str = "config.yaml") -> "SystemConfig":
        """Load configuration from YAML file."""
        # Load and validate YAML file
        yaml_config = cls._load_and_validate_yaml(config_path)

        # Create configuration accessor function
        get_config = cls._create_config_accessor(yaml_config)

        # Parse TTS configuration
        tts_config = cls._parse_tts_config(get_config)

        # Always parse both engine configs for backward compatibility
        # The appropriate one will be used based on tts.engine
        gemini_config = cls._parse_gemini_config(get_config)
        piper_config = cls._parse_piper_config(get_config)

        # Parse all other configurations
        file_config = cls._parse_file_config(get_config)
        cleanup_config = cls._parse_cleanup_config(get_config)
        text_config = cls._parse_text_processing_config(get_config)
        performance_config = cls._parse_performance_config(get_config)
        flask_config = cls._parse_flask_config(get_config)
        ocr_config = cls._parse_ocr_config(get_config)
        llm_config = cls._parse_llm_config(get_config)

        # Get project root
        project_root = str(get_config("system.project_root", ""))

        # Create the composed configuration
        config = cls(
            tts=tts_config,
            files=file_config,
            cleanup=cleanup_config,
            text_processing=text_config,
            performance=performance_config,
            flask=flask_config,
            ocr=ocr_config,
            llm=llm_config,
            gemini=gemini_config,
            piper=piper_config,
            project_root=project_root,
        )

        config.validate()
        return config

    @classmethod
    def _load_and_validate_yaml(cls, config_path: str) -> dict[str, object]:
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

        return cast(dict[str, object], yaml_config)

    @classmethod
    def _create_config_accessor(cls, yaml_config: dict[str, object]) -> ConfigAccessor:
        """Create helper function to access nested YAML values."""

        def get_config(yaml_path: str, default: Optional[YAMLValue] = None) -> YAMLValue:
            keys = yaml_path.split(".")
            value: YAMLValue = yaml_config
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]  # type: ignore[assignment]
                else:
                    return default
            return value

        return get_config

    @classmethod
    def _parse_tts_config(cls, get_config: ConfigAccessor) -> TTSConfig:
        """Parse TTS configuration."""
        engine_str = get_config("tts.engine", "piper")
        if not engine_str:
            raise ValueError("Missing required configuration: tts.engine")
        engine_str = str(engine_str).strip().lower()
        try:
            engine = TTSEngine(engine_str)
        except ValueError as e:
            valid_engines = [e.value for e in TTSEngine]
            raise ValueError(f"Invalid TTS engine '{engine_str}'. Must be one of: {valid_engines}") from e

        return TTSConfig(
            engine=engine,
            concurrent_requests=cls._parse_int_value(get_config("tts.concurrent_requests", 4), 4, 1, 10),
            request_delay_seconds=cls._parse_float_value(get_config("tts.request_delay_seconds", 2.0), 2.0, 0.1, 10.0),
        )

    @classmethod
    def _parse_gemini_config(cls, get_config: ConfigAccessor) -> GeminiConfig:
        """Parse Gemini-specific configuration."""
        return GeminiConfig(
            api_key=cls._parse_optional_string_value(get_config("secrets.google_ai_api_key", None)),
            voice_name=cls._parse_string_value(get_config("tts.gemini.voice_name", "Kore"), "Kore"),
            model_name=cls._parse_string_value(
                get_config("tts.gemini.model_name", "gemini-2.5-flash"), "gemini-2.5-flash"
            ),
            use_measurement_mode=cls._parse_bool_value(get_config("tts.gemini.use_measurement_mode", False), False),
            measurement_mode_interval=cls._parse_float_value(
                get_config("tts.gemini.measurement_mode_interval", 0.8), 0.8, 0.1, 5.0
            ),
        )

    @classmethod
    def _parse_piper_config(cls, get_config: ConfigAccessor) -> PiperConfig:
        """Parse Piper-specific configuration."""
        return PiperConfig(
            model_name=cls._parse_string_value(
                get_config("tts.piper.model_name", "en_US-lessac-medium"), "en_US-lessac-medium"
            ),
            models_dir=cls._parse_string_value(
                get_config("tts.piper.models_dir", ".local/piper_models"), ".local/piper_models"
            ),
            length_scale=cls._parse_float_value(get_config("tts.piper.length_scale", 1.0), 1.0, 0.5, 2.0),
            model_repository_url=cls._parse_string_value(
                get_config(
                    "tts.piper.model_repository_url", "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
                ),
                "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0",
            ),
        )

    @classmethod
    def _parse_file_config(cls, get_config: ConfigAccessor) -> FileConfig:
        """Parse file handling configuration."""
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

        return FileConfig(
            upload_folder=cls._parse_string_value(get_config("files.upload_folder", "uploads"), "uploads"),
            audio_folder=cls._parse_string_value(get_config("files.audio_folder", "audio_outputs"), "audio_outputs"),
            max_file_size_mb=cls._parse_int_value(get_config("files.max_file_size_mb", 100), 100, 1, 1000),
            allowed_extensions=allowed_extensions,
            audio_extensions=audio_extensions,
        )

    @classmethod
    def _parse_cleanup_config(cls, get_config: ConfigAccessor) -> FileCleanupConfig:
        """Parse file cleanup configuration."""
        return FileCleanupConfig(
            enabled=cls._parse_bool_value(get_config("files.cleanup.enabled", True), True),
            max_file_age_hours=cls._parse_float_value(
                get_config("files.cleanup.max_file_age_hours", 24.0), 24.0, 0.1, 168.0
            ),
            auto_cleanup_interval_hours=cls._parse_float_value(
                get_config("files.cleanup.auto_cleanup_interval_hours", 6.0), 6.0, 0.1, 24.0
            ),
            max_disk_usage_mb=cls._parse_int_value(
                get_config("files.cleanup.max_disk_usage_mb", 1000), 1000, 10, 10000
            ),
        )

    @classmethod
    def _parse_text_processing_config(cls, get_config: ConfigAccessor) -> TextProcessingConfig:
        """Parse text processing configuration."""
        return TextProcessingConfig(
            enable_cleaning=cls._parse_bool_value(get_config("text_processing.enable_text_cleaning", True), True),
            enable_natural_formatting=cls._parse_bool_value(
                get_config("text_processing.enable_natural_formatting", True), True
            ),
            enable_plain_english=cls._parse_bool_value(
                get_config("text_processing.enable_plain_english_conversion", False), False
            ),
            chunk_size=cls._parse_int_value(get_config("text_processing.chunk_size", 20000), 20000, 1000, 100000),
            llm_chunk_size=cls._parse_int_value(
                get_config("text_processing.llm_chunk_size", 50000), 50000, 10000, 200000
            ),
            audio_target_chunk_size=cls._parse_int_value(
                get_config("text_processing.audio_target_chunk_size", 3000), 3000, 100, 10000
            ),
            audio_max_chunk_size=cls._parse_int_value(
                get_config("text_processing.audio_max_chunk_size", 5000), 5000, 100, 20000
            ),
        )

    @classmethod
    def _parse_performance_config(cls, get_config: ConfigAccessor) -> PerformanceConfig:
        """Parse performance configuration."""
        return PerformanceConfig(
            enable_async_audio=cls._parse_bool_value(get_config("performance.enable_async_audio", True), True),
            audio_concurrent_chunks=cls._parse_int_value(get_config("audio.concurrent_chunks", 4), 4, 1, 20),
        )

    @classmethod
    def _parse_flask_config(cls, get_config: ConfigAccessor) -> FlaskConfig:
        """Parse Flask application configuration."""
        return FlaskConfig(
            debug=cls._parse_bool_value(get_config("app.debug", True), True),
            host=cls._parse_string_value(get_config("app.host", "127.0.0.1"), "127.0.0.1"),
            port=cls._parse_int_value(get_config("app.port", 5000), 5000, 1000, 65535),
        )

    @classmethod
    def _parse_ocr_config(cls, get_config: ConfigAccessor) -> OCRConfig:
        """Parse OCR configuration."""
        return OCRConfig(
            dpi=cls._parse_int_value(get_config("ocr.dpi", 300), 300, 150, 600),
            threshold=cls._parse_int_value(get_config("ocr.threshold", 180), 180, 100, 240),
            language=cls._parse_string_value(get_config("ocr.language", "eng"), "eng"),
        )

    @classmethod
    def _parse_llm_config(cls, get_config: ConfigAccessor) -> LLMConfig:
        """Parse LLM configuration."""
        # Get the API key which may be shared with Gemini
        api_key = cls._parse_optional_string_value(get_config("secrets.google_ai_api_key", None))

        return LLMConfig(
            model_name=cls._parse_optional_string_value(get_config("llm.model_name", None)),
            concurrent_requests=cls._parse_int_value(get_config("llm.concurrent_requests", 3), 3, 1, 10),
            request_delay_seconds=cls._parse_float_value(get_config("llm.request_delay_seconds", 0.5), 0.5, 0.1, 5.0),
            api_key=api_key,
        )

    def validate(self) -> None:
        """Validate configuration and fail fast with clear error messages."""
        # Engine-specific validation
        if self.tts.engine == TTSEngine.GEMINI:
            if self.gemini and not self.gemini.api_key:
                raise ValueError("GOOGLE_AI_API_KEY is required when TTS_ENGINE=gemini")
            if self.gemini and self.gemini.api_key == "YOUR_GOOGLE_AI_API_KEY":
                raise ValueError("Please set a valid GOOGLE_AI_API_KEY (not the placeholder value)")

        if self.tts.engine == TTSEngine.PIPER and self.piper and not self.piper.model_name:
            raise ValueError("PIPER_MODEL_NAME cannot be empty when using Piper TTS")

        # Security validation for all directory paths
        for folder_name, folder_path in [
            ("UPLOAD_FOLDER", self.files.upload_folder),
            ("AUDIO_FOLDER", self.files.audio_folder),
            ("PIPER_MODELS_DIR", self.piper.models_dir if self.piper else ""),
        ]:
            if folder_path:  # Skip if piper is None
                self._validate_directory_security(folder_name, folder_path, self.project_root)

        # Validate file management settings
        if self.cleanup.enabled:
            if self.cleanup.max_file_age_hours <= 0:
                raise ValueError("MAX_FILE_AGE_HOURS must be positive when file cleanup is enabled")
            if self.cleanup.auto_cleanup_interval_hours <= 0:
                raise ValueError("AUTO_CLEANUP_INTERVAL_HOURS must be positive when file cleanup is enabled")
            if self.cleanup.max_disk_usage_mb <= 0:
                raise ValueError("MAX_DISK_USAGE_MB must be positive when file cleanup is enabled")

    @staticmethod
    def _get_secure_project_root() -> str:
        """Get secure project root path with environment override support."""
        env_root = os.environ.get("PROJECT_ROOT")
        if env_root:
            env_path = Path(env_root).resolve()
            if env_path.exists() and env_path.is_dir():
                return str(env_path)
        return str(Path.cwd())

    @staticmethod
    def _validate_directory_security(name: str, path: str, project_root: str) -> None:
        """Validate directory path for security vulnerabilities."""
        if not path or path.isspace():
            raise ValueError(f"{name} cannot be empty or whitespace")

        path_obj = Path(path)
        if not path_obj.is_absolute():
            path_obj = Path(project_root) / path_obj

        path_resolved = path_obj.resolve()
        project_resolved = Path(project_root).resolve()

        try:
            path_resolved.relative_to(project_resolved)
        except ValueError as e:
            raise ValueError(f"{name} must be within project directory: {path}") from e

    # Parsing helper methods
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
        """Parse boolean from various representations."""
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

    def print_summary(self) -> None:
        """Print configuration summary for debugging."""
        print("=" * 50)
        print("PDF to Audio Converter - Configuration")
        print("=" * 50)
        print(f"TTS Engine: {self.tts.engine.value}")
        print(f"Text Cleaning: {'Enabled' if self.text_processing.enable_cleaning else 'Disabled'}")
        print(f"Natural Formatting: {'Enabled' if self.text_processing.enable_natural_formatting else 'Disabled'}")
        print(f"Plain English Conversion: {'Enabled' if self.text_processing.enable_plain_english else 'Disabled'}")
        print(f"Async Audio: {'Enabled' if self.performance.enable_async_audio else 'Disabled'}")
        print(f"Audio Concurrent Chunks: {self.performance.audio_concurrent_chunks}")
        print(f"TTS Concurrent Requests: {self.tts.concurrent_requests}")
        print(f"LLM Concurrent Requests: {self.llm.concurrent_requests}")
        print(f"Upload Folder: {self.files.upload_folder}")
        print(f"Audio Folder: {self.files.audio_folder}")

        # File management
        print(f"File Cleanup: {'Enabled' if self.cleanup.enabled else 'Disabled'}")
        if self.cleanup.enabled:
            print(f"Max File Age: {self.cleanup.max_file_age_hours} hours")
            print(f"Cleanup Interval: {self.cleanup.auto_cleanup_interval_hours} hours")
            print(f"Max Disk Usage: {self.cleanup.max_disk_usage_mb} MB")

        if self.tts.engine == TTSEngine.GEMINI and self.gemini:
            api_key_status = "Set" if self.gemini.api_key else "Missing"
            print(f"Gemini API Key: {api_key_status}")
            print(f"Gemini Voice: {self.gemini.voice_name}")
        elif self.tts.engine == TTSEngine.PIPER and self.piper:
            print(f"Piper Model: {self.piper.model_name}")
            print(f"Piper Models Dir: {self.piper.models_dir}")

        print("=" * 50)

    # Backward compatibility methods
    @property
    def tts_engine(self) -> TTSEngine:
        """Backward compatibility property."""
        return self.tts.engine

    @property
    def upload_folder(self) -> str:
        """Backward compatibility property."""
        return self.files.upload_folder

    @property
    def audio_folder(self) -> str:
        """Backward compatibility property."""
        return self.files.audio_folder

    @property
    def max_file_size_mb(self) -> int:
        """Backward compatibility property."""
        return self.files.max_file_size_mb

    @property
    def enable_text_cleaning(self) -> bool:
        """Backward compatibility property."""
        return self.text_processing.enable_cleaning

    @property
    def enable_natural_formatting(self) -> bool:
        """Backward compatibility property."""
        return self.text_processing.enable_natural_formatting

    @property
    def enable_plain_english_conversion(self) -> bool:
        """Backward compatibility property."""
        return self.text_processing.enable_plain_english

    @property
    def enable_async_audio(self) -> bool:
        """Backward compatibility property."""
        return self.performance.enable_async_audio

    @property
    def audio_concurrent_chunks(self) -> int:
        """Backward compatibility property."""
        return self.performance.audio_concurrent_chunks

    @property
    def enable_file_cleanup(self) -> bool:
        """Backward compatibility property."""
        return self.cleanup.enabled

    @property
    def max_file_age_hours(self) -> float:
        """Backward compatibility property."""
        return self.cleanup.max_file_age_hours

    @property
    def auto_cleanup_interval_hours(self) -> float:
        """Backward compatibility property."""
        return self.cleanup.auto_cleanup_interval_hours

    @property
    def max_disk_usage_mb(self) -> int:
        """Backward compatibility property."""
        return self.cleanup.max_disk_usage_mb

    @property
    def llm_chunk_size(self) -> int:
        """Backward compatibility property."""
        return self.text_processing.llm_chunk_size

    @property
    def audio_target_chunk_size(self) -> int:
        """Backward compatibility property."""
        return self.text_processing.audio_target_chunk_size

    @property
    def audio_max_chunk_size(self) -> int:
        """Backward compatibility property."""
        return self.text_processing.audio_max_chunk_size

    @property
    def flask_debug(self) -> bool:
        """Backward compatibility property."""
        return self.flask.debug

    @property
    def flask_host(self) -> str:
        """Backward compatibility property."""
        return self.flask.host

    @property
    def flask_port(self) -> int:
        """Backward compatibility property."""
        return self.flask.port

    @property
    def gemini_api_key(self) -> Optional[str]:
        """Backward compatibility property."""
        return self.gemini.api_key if self.gemini else None

    @property
    def gemini_voice_name(self) -> str:
        """Backward compatibility property."""
        return self.gemini.voice_name if self.gemini else "Kore"

    @property
    def gemini_model_name(self) -> str:
        """Backward compatibility property."""
        return self.gemini.model_name if self.gemini else "gemini-2.5-flash"

    @property
    def gemini_use_measurement_mode(self) -> bool:
        """Backward compatibility property."""
        return self.gemini.use_measurement_mode if self.gemini else False

    @property
    def gemini_measurement_mode_interval(self) -> float:
        """Backward compatibility property."""
        return self.gemini.measurement_mode_interval if self.gemini else 0.8

    @property
    def piper_model_name(self) -> str:
        """Backward compatibility property."""
        return self.piper.model_name if self.piper else "en_US-lessac-medium"

    @property
    def piper_models_dir(self) -> str:
        """Backward compatibility property."""
        return self.piper.models_dir if self.piper else ".local/piper_models"

    @property
    def piper_length_scale(self) -> float:
        """Backward compatibility property."""
        return self.piper.length_scale if self.piper else 1.0

    @property
    def piper_model_repository_url(self) -> str:
        """Backward compatibility property."""
        return (
            self.piper.model_repository_url
            if self.piper
            else "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
        )

    @property
    def llm_model_name(self) -> Optional[str]:
        """Backward compatibility property."""
        return self.llm.model_name

    @property
    def llm_concurrent_requests(self) -> int:
        """Backward compatibility property."""
        return self.llm.concurrent_requests

    @property
    def llm_request_delay_seconds(self) -> float:
        """Backward compatibility property."""
        return self.llm.request_delay_seconds

    @property
    def tts_concurrent_requests(self) -> int:
        """Backward compatibility property."""
        return self.tts.concurrent_requests

    @property
    def tts_request_delay_seconds(self) -> float:
        """Backward compatibility property."""
        return self.tts.request_delay_seconds

    @property
    def ocr_dpi(self) -> int:
        """Backward compatibility property."""
        return self.ocr.dpi

    @property
    def ocr_threshold(self) -> int:
        """Backward compatibility property."""
        return self.ocr.threshold

    @property
    def ocr_language(self) -> str:
        """Backward compatibility property."""
        return self.ocr.language

    @property
    def allowed_extensions(self) -> frozenset[str]:
        """Backward compatibility property."""
        return self.files.allowed_extensions

    @property
    def audio_extensions(self) -> frozenset[str]:
        """Backward compatibility property."""
        return self.files.audio_extensions

    @property
    def chunk_size(self) -> int:
        """Backward compatibility property."""
        return self.text_processing.chunk_size
