# tests/unit/test_system_config_tdd.py
"""TDD tests for SystemConfig - comprehensive coverage following red-green-refactor cycle.
Tests configuration loading, validation, and error handling without external dependencies.
"""

from unittest.mock import patch

import pytest

from application.config.system_config import SystemConfig, TTSEngine


class TestTTSEngineEnum:
    """TDD tests for TTSEngine enumeration."""

    def test_tts_engine_enum_values(self):
        """Should define correct TTS engine values."""
        assert TTSEngine.PIPER.value == "piper"
        assert TTSEngine.GEMINI.value == "gemini"

    def test_tts_engine_enum_creation_from_string(self):
        """Should create enum from valid string values."""
        assert TTSEngine("piper") == TTSEngine.PIPER
        assert TTSEngine("gemini") == TTSEngine.GEMINI

    def test_tts_engine_enum_invalid_value_raises_error(self):
        """Should raise ValueError for invalid TTS engine values."""
        with pytest.raises(ValueError):
            TTSEngine("invalid_engine")

    def test_tts_engine_enum_case_sensitivity(self):
        """Should be case-sensitive for enum values."""
        with pytest.raises(ValueError):
            TTSEngine("PIPER")
        with pytest.raises(ValueError):
            TTSEngine("Gemini")


class TestSystemConfigCreation:
    """TDD tests for SystemConfig basic creation and defaults."""

    def test_system_config_minimal_creation(self):
        """Should create SystemConfig with minimal required parameters."""
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
        )

        assert config.tts_engine == TTSEngine.PIPER
        assert config.upload_folder == "uploads"
        assert config.audio_folder == "audio_outputs"
        assert config.enable_text_cleaning is True
        assert config.enable_ssml is True

    def test_system_config_with_custom_values(self):
        """Should create SystemConfig with custom values."""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            upload_folder="custom_uploads",
            audio_folder="custom_audio",
            enable_text_cleaning=False,
            enable_ssml=False,
        )

        assert config.tts_engine == TTSEngine.GEMINI
        assert config.upload_folder == "custom_uploads"
        assert config.audio_folder == "custom_audio"
        assert config.enable_text_cleaning is False
        assert config.enable_ssml is False

    def test_system_config_post_init_sets_default_extensions(self):
        """Should set default file extensions in __post_init__."""
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
        )

        # __post_init__ should be called automatically
        assert config.allowed_extensions == frozenset({"pdf"})
        assert config.audio_extensions == frozenset({"wav", "mp3"})

    def test_system_config_post_init_uses_provided_extensions(self):
        """Should use provided extensions or set defaults if None."""
        # Test with provided extensions
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            allowed_extensions=frozenset({"pdf", "docx", "txt"}),
            audio_extensions=frozenset({"wav", "mp3", "ogg"}),
        )

        assert config.allowed_extensions == frozenset({"pdf", "docx", "txt"})
        assert config.audio_extensions == frozenset({"wav", "mp3", "ogg"})

        # Test with None (should set defaults)
        config2 = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            allowed_extensions=None,
            audio_extensions=None,
        )

        assert config2.allowed_extensions == frozenset({"pdf"})
        assert config2.audio_extensions == frozenset({"wav", "mp3"})


class TestSystemConfigValidationTDD:
    """TDD tests for SystemConfig validation logic."""

    def test_validate_gemini_requires_api_key(self):
        """Should require API key for Gemini TTS engine."""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            gemini_api_key=None,
        )

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "GOOGLE_AI_API_KEY is required when TTS_ENGINE=gemini" in str(exc_info.value)

    def test_validate_gemini_rejects_placeholder_api_key(self):
        """Should reject placeholder API key for Gemini."""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            gemini_api_key="YOUR_GOOGLE_AI_API_KEY",
        )

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "Please set a valid GOOGLE_AI_API_KEY" in str(exc_info.value)

    def test_validate_gemini_accepts_valid_api_key(self):
        """Should accept valid API key for Gemini."""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            gemini_api_key="valid_api_key_12345",
        )

        # Should not raise exception
        config.validate()

    def test_validate_piper_requires_model_name(self):
        """Should require model name for Piper TTS engine."""
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            piper_model_name="",
        )

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "PIPER_MODEL_NAME cannot be empty when using Piper TTS" in str(exc_info.value)

    def test_validate_piper_accepts_valid_model_name(self):
        """Should accept valid model name for Piper."""
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            piper_model_name="en_US-lessac-medium",
        )

        # Should not raise exception
        config.validate()

    def test_validate_folder_paths_cannot_be_empty(self):
        """Should reject empty folder paths at creation time (immutable design)."""
        test_cases = [
            ("upload_folder", ""),
            ("audio_folder", ""),
            ("piper_models_dir", ""),
            ("upload_folder", "   "),  # whitespace only
            ("audio_folder", "\t\n"),  # whitespace only
        ]

        for folder_attr, invalid_path in test_cases:
            # Test creation with invalid path should be allowed but validation should fail
            config_kwargs = {
                "tts_engine": TTSEngine.PIPER,
                "llm_model_name": "gemini-1.5-flash",
                "gemini_model_name": "gemini-1.5-flash",
                folder_attr: invalid_path,
            }
            config = SystemConfig(**config_kwargs)  # type: ignore[arg-type]

            # Validation should catch empty/whitespace paths
            with pytest.raises(ValueError) as exc_info:
                config.validate()

            assert "cannot be empty or whitespace" in str(exc_info.value)

    def test_validate_file_cleanup_settings_when_enabled(self):
        """Should validate file cleanup settings when cleanup is enabled."""
        # Test valid file cleanup settings
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            enable_file_cleanup=True,
            max_file_age_hours=24.0,
            auto_cleanup_interval_hours=6.0,
            max_disk_usage_mb=1000,
        )
        config.validate()  # Should not raise

        # Test invalid max_file_age_hours - create new config with invalid value
        config_invalid_age = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            enable_file_cleanup=True,
            max_file_age_hours=0.0,
            auto_cleanup_interval_hours=6.0,
            max_disk_usage_mb=1000,
        )
        with pytest.raises(ValueError) as exc_info:
            config_invalid_age.validate()
        assert "MAX_FILE_AGE_HOURS must be positive" in str(exc_info.value)

        # Test invalid auto_cleanup_interval_hours - create new config with invalid value
        config_invalid_interval = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            enable_file_cleanup=True,
            max_file_age_hours=24.0,
            auto_cleanup_interval_hours=-1.0,
            max_disk_usage_mb=1000,
        )
        with pytest.raises(ValueError) as exc_info:
            config_invalid_interval.validate()
        assert "AUTO_CLEANUP_INTERVAL_HOURS must be positive" in str(exc_info.value)

        # Test invalid max_disk_usage_mb - create new config with invalid value
        config_invalid_disk = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            enable_file_cleanup=True,
            max_file_age_hours=24.0,
            auto_cleanup_interval_hours=6.0,
            max_disk_usage_mb=0,
        )
        with pytest.raises(ValueError) as exc_info:
            config_invalid_disk.validate()
        assert "MAX_DISK_USAGE_MB must be positive" in str(exc_info.value)

    def test_validate_file_cleanup_settings_when_disabled(self):
        """Should skip file cleanup validation when cleanup is disabled."""
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            enable_file_cleanup=False,
            max_file_age_hours=0.0,  # Invalid values
            auto_cleanup_interval_hours=-1.0,
            max_disk_usage_mb=0,
        )

        # Should not raise exception since cleanup is disabled
        config.validate()


class TestSystemConfigHelperMethodsTDD:
    """TDD tests for SystemConfig helper methods."""

    def test_get_gemini_config_creates_correct_config(self):
        """Should create proper Gemini configuration object."""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            gemini_api_key="test_key_123",
            gemini_voice_name="Aoede",
            tts_request_delay_seconds=1.5,
        )

        result = config.get_gemini_config()

        # Should return a config object with correct values
        assert hasattr(result, "voice_name")
        assert hasattr(result, "api_key")
        assert hasattr(result, "min_request_interval")
        assert result.voice_name == "Aoede"
        assert result.api_key == "test_key_123"
        assert result.min_request_interval == 1.5

    def test_get_piper_config_creates_correct_config(self):
        """Should create proper Piper configuration object."""
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            piper_model_name="en_US-amy-high",
            piper_models_dir="/custom/models",
            piper_length_scale=1.2,
        )

        result = config.get_piper_config()

        # Should return a config object with correct values
        assert hasattr(result, "model_name")
        assert hasattr(result, "download_dir")
        assert hasattr(result, "length_scale")
        assert result.model_name == "en_US-amy-high"
        assert result.download_dir == "/custom/models"
        assert result.length_scale == 1.2

    def test_print_summary_displays_configuration_info(self):
        """Should print comprehensive configuration summary."""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            enable_text_cleaning=True,
            enable_ssml=False,
            enable_async_audio=True,
            audio_concurrent_chunks=8,
            upload_folder="test_uploads",
            audio_folder="test_audio",
            enable_file_cleanup=True,
            max_file_age_hours=48.0,
            auto_cleanup_interval_hours=12.0,
            max_disk_usage_mb=2000,
            gemini_api_key="test_key",
            gemini_voice_name="Charon",
        )

        # Capture print output
        with patch("builtins.print") as mock_print:
            config.print_summary()

            # Verify key information is printed
            printed_text = " ".join(str(call) for call in mock_print.call_args_list)

            assert "TTS Engine: gemini" in printed_text
            assert "Text Cleaning: Enabled" in printed_text
            assert "SSML Enhancement: Disabled" in printed_text
            assert "Async Audio: Enabled" in printed_text
            assert "Audio Concurrent Chunks: 8" in printed_text
            assert "Upload Folder: test_uploads" in printed_text
            assert "Audio Folder: test_audio" in printed_text
            assert "File Cleanup: Enabled" in printed_text
            assert "Max File Age: 48.0 hours" in printed_text
            assert "Gemini API Key: Set" in printed_text
            assert "Gemini Voice: Charon" in printed_text

    def test_print_summary_handles_missing_api_key(self):
        """Should show 'Missing' for unset API key."""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            gemini_api_key=None,
        )

        with patch("builtins.print") as mock_print:
            config.print_summary()

            printed_text = " ".join(str(call) for call in mock_print.call_args_list)
            assert "Gemini API Key: Missing" in printed_text

    def test_print_summary_shows_piper_specific_info(self):
        """Should show Piper-specific configuration when using Piper."""
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            llm_model_name="gemini-1.5-flash",
            gemini_model_name="gemini-1.5-flash",
            piper_model_name="en_US-lessac-high",
            piper_models_dir="/custom/piper/models",
        )

        with patch("builtins.print") as mock_print:
            config.print_summary()

            printed_text = " ".join(str(call) for call in mock_print.call_args_list)
            assert "TTS Engine: piper" in printed_text
            assert "Piper Model: en_US-lessac-high" in printed_text
            assert "Piper Models Dir: /custom/piper/models" in printed_text
