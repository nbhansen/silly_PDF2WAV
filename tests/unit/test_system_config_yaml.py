# tests/unit/test_system_config_yaml.py
from pathlib import Path
import tempfile
from typing import Any

import pytest
import yaml

from application.config.system_config import SystemConfig
from domain.config.tts_config import TTSEngine


class TestSystemConfigYAMLLoading:
    """Test YAML configuration loading functionality."""

    def create_yaml_config(self, config_dict: dict[str, Any]) -> str:
        """Helper to create a temporary YAML config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_dict, f)
            return f.name

    def test_from_yaml_with_minimal_config(self):
        """Test loading minimal YAML configuration."""
        config_data = {"tts": {"engine": "piper"}}

        config_file = self.create_yaml_config(config_data)
        try:
            config = SystemConfig.from_yaml(config_file)
            assert config.tts.engine == TTSEngine.PIPER
            # Check defaults are applied
            assert config.text_processing.enable_cleaning is True
            assert config.files.max_file_size_mb == 100
        finally:
            Path(config_file).unlink()

    def test_from_yaml_with_complete_config(self):
        """Test loading complete YAML configuration."""
        config_data = {
            "tts": {
                "engine": "gemini",
                "request_delay_seconds": 1.5,
                "gemini": {
                    "model_name": "test-model",
                    "voice_name": "Aoede",
                    "use_measurement_mode": True,
                },
                "piper": {"model_name": "en_US-test-high", "models_dir": "test_models", "length_scale": 1.2},
            },
            "secrets": {"google_ai_api_key": "test-api-key-123"},
            "text_processing": {"enable_text_cleaning": False, "enable_natural_formatting": False, "chunk_size": 5000},
            "files": {
                "upload_folder": "test_uploads",
                "audio_folder": "test_audio",
                "max_file_size_mb": 50,
                "allowed_extensions": ["pdf", "txt"],
                "cleanup": {"enabled": False, "max_file_age_hours": 48.0},
            },
        }

        config_file = self.create_yaml_config(config_data)
        try:
            config = SystemConfig.from_yaml(config_file)

            # TTS settings
            assert config.tts.engine == TTSEngine.GEMINI
            assert config.gemini is not None
            assert config.gemini.model_name == "test-model"
            assert config.gemini.voice_name == "Aoede"
            assert config.tts.request_delay_seconds == 1.5
            assert config.gemini.use_measurement_mode is True
            assert config.gemini.api_key == "test-api-key-123"

            # Text processing
            assert config.text_processing.enable_cleaning is False
            assert config.text_processing.enable_natural_formatting is False
            assert config.text_processing.chunk_size == 5000

            # File settings
            assert config.files.upload_folder == "test_uploads"
            assert config.files.audio_folder == "test_audio"
            assert config.files.max_file_size_mb == 50
            assert config.files.allowed_extensions == frozenset({"pdf", "txt"})
            assert config.cleanup.enabled is False
            assert config.cleanup.max_file_age_hours == 48.0

        finally:
            Path(config_file).unlink()

    def test_from_yaml_missing_file_raises_error(self):
        """Test that missing YAML file raises appropriate error."""
        with pytest.raises(FileNotFoundError) as exc_info:
            SystemConfig.from_yaml("non_existent_file.yaml")
        assert "config.example.yaml" in str(exc_info.value)

    def test_from_yaml_invalid_yaml_raises_error(self):
        """Test that invalid YAML syntax raises appropriate error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: syntax: [[[")
            config_file = f.name

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                SystemConfig.from_yaml(config_file)
        finally:
            Path(config_file).unlink()

    def test_from_yaml_type_conversions(self):
        """Test that various type conversions work correctly."""
        config_data = {
            "tts": {"engine": "piper", "piper": {"length_scale": "1.5"}},  # String float
            "text_processing": {
                "enable_text_cleaning": "true",  # String boolean
                "enable_natural_formatting": 1,  # Integer boolean
                "chunk_size": "6000",  # String integer
                "audio_target_chunk_size": 2500,
            },
            "files": {
                "max_file_size_mb": "30",  # String integer
                "cleanup": {
                    "enabled": "yes",  # String boolean
                    "max_file_age_hours": "36.5",  # String float
                    "auto_cleanup_interval_hours": 8,  # Integer as float
                },
            },
        }

        config_file = self.create_yaml_config(config_data)
        try:
            config = SystemConfig.from_yaml(config_file)

            # Boolean conversions
            assert config.text_processing.enable_cleaning is True
            assert config.text_processing.enable_natural_formatting is True
            assert config.cleanup.enabled is True

            # Integer conversions
            assert config.text_processing.chunk_size == 6000
            assert isinstance(config.text_processing.chunk_size, int)
            assert config.files.max_file_size_mb == 30
            assert isinstance(config.files.max_file_size_mb, int)

            # Float conversions
            assert config.cleanup.max_file_age_hours == 36.5
            assert isinstance(config.cleanup.max_file_age_hours, float)
            assert config.cleanup.auto_cleanup_interval_hours == 8.0
            assert isinstance(config.cleanup.auto_cleanup_interval_hours, float)
            assert config.piper is not None
            assert config.piper.length_scale == 1.5
            assert isinstance(config.piper.length_scale, float)

        finally:
            Path(config_file).unlink()

    def test_from_yaml_boolean_variations(self):
        """Test various boolean representations."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("yes", True),
            ("Yes", True),
            ("on", True),
            ("1", True),
            (1, True),
            (True, True),
            ("false", False),
            ("False", False),
            ("no", False),
            ("off", False),
            ("0", False),
            (0, False),
            (False, False),
            ("invalid", False),  # Invalid strings default to False
        ]

        for value, expected in test_cases:
            config_data = {"tts": {"engine": "piper"}, "text_processing": {"enable_text_cleaning": value}}

            config_file = self.create_yaml_config(config_data)
            try:
                config = SystemConfig.from_yaml(config_file)
                assert config.text_processing.enable_cleaning is expected, f"Failed for value: {value}"
            finally:
                Path(config_file).unlink()

    def test_from_yaml_range_validation(self):
        """Test that numeric range validation works."""
        # Test value too low
        config_data = {"tts": {"engine": "piper"}, "files": {"max_file_size_mb": 0}}  # Min is 1

        config_file = self.create_yaml_config(config_data)
        try:
            with pytest.raises(ValueError, match=">= 1"):
                SystemConfig.from_yaml(config_file)
        finally:
            Path(config_file).unlink()

        # Test value too high
        config_data = {"tts": {"engine": "piper"}, "files": {"max_file_size_mb": 2000}}  # Max is 1000

        config_file = self.create_yaml_config(config_data)
        try:
            with pytest.raises(ValueError, match="<= 1000"):
                SystemConfig.from_yaml(config_file)
        finally:
            Path(config_file).unlink()

    def test_from_yaml_missing_required_fields(self):
        """Test that missing required fields use defaults."""
        # Missing TTS engine should use default 'piper'
        config_data: dict[str, Any] = {}

        config_file = self.create_yaml_config(config_data)
        try:
            config = SystemConfig.from_yaml(config_file)
            # Should use default value
            assert config.tts.engine == TTSEngine.PIPER
        finally:
            Path(config_file).unlink()

    def test_from_yaml_invalid_tts_engine(self):
        """Test that invalid TTS engine raises error."""
        config_data = {"tts": {"engine": "invalid_engine"}}

        config_file = self.create_yaml_config(config_data)
        try:
            with pytest.raises(ValueError, match="Invalid TTS engine.*piper.*gemini"):
                SystemConfig.from_yaml(config_file)
        finally:
            Path(config_file).unlink()

    def test_from_yaml_list_and_string_extensions(self):
        """Test that file extensions can be specified as list or string."""
        # Test list format
        config_data = {
            "tts": {"engine": "piper"},
            "files": {"allowed_extensions": ["pdf", "txt", "doc"], "audio_extensions": ["wav", "mp3", "ogg"]},
        }

        config_file = self.create_yaml_config(config_data)
        try:
            config = SystemConfig.from_yaml(config_file)
            assert config.files.allowed_extensions == frozenset({"pdf", "txt", "doc"})
            assert config.files.audio_extensions == frozenset({"wav", "mp3", "ogg"})
        finally:
            Path(config_file).unlink()

        # Test string format
        config_data = {
            "tts": {"engine": "piper"},
            "files": {"allowed_extensions": "pdf,txt,doc", "audio_extensions": "wav,mp3,ogg"},
        }

        config_file = self.create_yaml_config(config_data)
        try:
            config = SystemConfig.from_yaml(config_file)
            assert config.files.allowed_extensions == frozenset({"pdf", "txt", "doc"})
            assert config.files.audio_extensions == frozenset({"wav", "mp3", "ogg"})
        finally:
            Path(config_file).unlink()

    def test_from_yaml_gemini_validation(self):
        """Test Gemini-specific validation."""
        # Gemini without API key should fail validation
        config_data = {
            "tts": {"engine": "gemini"}
            # No secrets.google_ai_api_key provided
        }

        config_file = self.create_yaml_config(config_data)
        try:
            with pytest.raises(ValueError, match="GOOGLE_AI_API_KEY is required"):
                SystemConfig.from_yaml(config_file)
        finally:
            Path(config_file).unlink()

    def test_from_yaml_with_null_values(self):
        """Test handling of null/None values in YAML."""
        config_data = {
            "tts": {"engine": "piper"},
            "text_processing": {
                "enable_text_cleaning": None,  # Should use default
                "chunk_size": None,  # Should use default
            },
        }

        config_file = self.create_yaml_config(config_data)
        try:
            config = SystemConfig.from_yaml(config_file)
            assert config.text_processing.enable_cleaning is True  # Default value
            assert config.text_processing.chunk_size == 20000  # Default value
        finally:
            Path(config_file).unlink()

    def test_from_yaml_case_insensitive_tts_engine(self):
        """Test that TTS engine is case-insensitive."""
        test_cases = ["PIPER", "Piper", "piper", "PiPeR"]

        for engine_value in test_cases:
            config_data = {"tts": {"engine": engine_value}}

            config_file = self.create_yaml_config(config_data)
            try:
                config = SystemConfig.from_yaml(config_file)
                assert config.tts.engine == TTSEngine.PIPER
            finally:
                Path(config_file).unlink()

    def test_from_yaml_with_example_file(self):
        """Test loading the actual example YAML file if it exists."""
        example_file = Path("config.example.yaml")
        if example_file.exists():
            config = SystemConfig.from_yaml(str(example_file))
            # Verify it loads without errors and has expected defaults
            assert config.tts.engine == TTSEngine.PIPER
            assert isinstance(config.text_processing.enable_cleaning, bool)
            assert isinstance(config.files.max_file_size_mb, int)
            assert isinstance(config.tts.request_delay_seconds, float)
