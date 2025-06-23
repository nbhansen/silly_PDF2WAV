# tests/unit/test_system_config_tdd.py
"""
TDD tests for SystemConfig - comprehensive coverage following red-green-refactor cycle.
Tests configuration loading, validation, and error handling without external dependencies.
"""
import pytest
import os
from unittest.mock import patch

from application.config.system_config import SystemConfig, TTSEngine


class TestTTSEngineEnum:
    """TDD tests for TTSEngine enumeration"""
    
    def test_tts_engine_enum_values(self):
        """Should define correct TTS engine values"""
        assert TTSEngine.PIPER.value == "piper"
        assert TTSEngine.GEMINI.value == "gemini"
    
    def test_tts_engine_enum_creation_from_string(self):
        """Should create enum from valid string values"""
        assert TTSEngine("piper") == TTSEngine.PIPER
        assert TTSEngine("gemini") == TTSEngine.GEMINI
    
    def test_tts_engine_enum_invalid_value_raises_error(self):
        """Should raise ValueError for invalid TTS engine values"""
        with pytest.raises(ValueError):
            TTSEngine("invalid_engine")
    
    def test_tts_engine_enum_case_sensitivity(self):
        """Should be case-sensitive for enum values"""
        with pytest.raises(ValueError):
            TTSEngine("PIPER")
        with pytest.raises(ValueError):
            TTSEngine("Gemini")


class TestSystemConfigCreation:
    """TDD tests for SystemConfig basic creation and defaults"""
    
    def test_system_config_minimal_creation(self):
        """Should create SystemConfig with minimal required parameters"""
        config = SystemConfig(tts_engine=TTSEngine.PIPER)
        
        assert config.tts_engine == TTSEngine.PIPER
        assert config.upload_folder == "uploads"
        assert config.audio_folder == "audio_outputs"
        assert config.enable_text_cleaning is True
        assert config.enable_ssml is True
        assert config.document_type == "research_paper"
    
    def test_system_config_with_custom_values(self):
        """Should create SystemConfig with custom values"""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            upload_folder="custom_uploads",
            audio_folder="custom_audio",
            enable_text_cleaning=False,
            enable_ssml=False,
            document_type="general"
        )
        
        assert config.tts_engine == TTSEngine.GEMINI
        assert config.upload_folder == "custom_uploads"
        assert config.audio_folder == "custom_audio"
        assert config.enable_text_cleaning is False
        assert config.enable_ssml is False
        assert config.document_type == "general"
    
    def test_system_config_post_init_sets_default_extensions(self):
        """Should set default file extensions in __post_init__"""
        config = SystemConfig(tts_engine=TTSEngine.PIPER)
        
        # __post_init__ should be called automatically
        assert config.allowed_extensions == {"pdf"}
        assert config.audio_extensions == {"wav", "mp3"}
    
    def test_system_config_post_init_respects_environment_extensions(self):
        """Should use environment variables for extensions when available"""
        with patch.dict(os.environ, {
            'ALLOWED_EXTENSIONS': 'pdf,docx,txt',
            'AUDIO_EXTENSIONS': 'wav,mp3,ogg'
        }):
            config = SystemConfig(tts_engine=TTSEngine.PIPER)
            
            assert config.allowed_extensions == {"pdf", "docx", "txt"}
            assert config.audio_extensions == {"wav", "mp3", "ogg"}


class TestSystemConfigFromEnvTDD:
    """TDD tests for SystemConfig.from_env() method"""
    
    def test_from_env_with_minimal_environment(self):
        """Should create config with minimal environment variables"""
        with patch.dict(os.environ, {'TTS_ENGINE': 'piper'}, clear=True):
            config = SystemConfig.from_env()
            
            assert config.tts_engine == TTSEngine.PIPER
            assert config.upload_folder == "uploads"  # default
            assert config.gemini_api_key is None
    
    def test_from_env_with_comprehensive_environment(self):
        """Should create config from comprehensive environment variables"""
        env_vars = {
            'TTS_ENGINE': 'gemini',
            'UPLOAD_FOLDER': 'test_uploads',
            'AUDIO_FOLDER': 'test_audio',
            'MAX_FILE_SIZE_MB': '200',
            'ENABLE_TEXT_CLEANING': 'false',
            'ENABLE_SSML': 'true',
            'DOCUMENT_TYPE': 'literature_review',
            'GOOGLE_AI_API_KEY': 'test_api_key_12345',
            'GEMINI_VOICE_NAME': 'Aoede',
            'PIPER_MODEL_NAME': 'en_US-amy-high',
            'MAX_CONCURRENT_TTS_REQUESTS': '8',
            'CHUNK_SIZE': '15000'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = SystemConfig.from_env()
            
            assert config.tts_engine == TTSEngine.GEMINI
            assert config.upload_folder == "test_uploads"
            assert config.audio_folder == "test_audio"
            assert config.max_file_size_mb == 200
            assert config.enable_text_cleaning is False
            assert config.enable_ssml is True
            assert config.document_type == "literature_review"
            assert config.gemini_api_key == "test_api_key_12345"
            assert config.gemini_voice_name == "Aoede"
            assert config.piper_model_name == "en_US-amy-high"
            assert config.max_concurrent_requests == 8
            assert config.chunk_size == 15000
    
    def test_from_env_invalid_tts_engine_raises_error(self):
        """Should raise clear error for invalid TTS engine"""
        with patch.dict(os.environ, {'TTS_ENGINE': 'invalid_engine'}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                SystemConfig.from_env()
            
            assert "Invalid TTS_ENGINE 'invalid_engine'" in str(exc_info.value)
            assert "piper" in str(exc_info.value)
            assert "gemini" in str(exc_info.value)
    
    def test_from_env_case_insensitive_tts_engine(self):
        """Should handle case-insensitive TTS engine values"""
        # Test Piper variations (no API key required)
        piper_cases = ['PIPER', 'Piper', 'pIpEr']
        for engine_value in piper_cases:
            with patch.dict(os.environ, {'TTS_ENGINE': engine_value}, clear=True):
                config = SystemConfig.from_env()
                assert config.tts_engine == TTSEngine.PIPER
        
        # Test Gemini variations (with API key to pass validation)
        gemini_cases = ['GEMINI', 'Gemini', 'GeMiNi']
        for engine_value in gemini_cases:
            env_vars = {'TTS_ENGINE': engine_value, 'GOOGLE_AI_API_KEY': 'test_key'}
            with patch.dict(os.environ, env_vars, clear=True):
                config = SystemConfig.from_env()
                assert config.tts_engine == TTSEngine.GEMINI
    
    def test_from_env_missing_tts_engine_uses_default(self):
        """Should use default TTS engine when not specified"""
        with patch.dict(os.environ, {}, clear=True):
            config = SystemConfig.from_env()
            
            assert config.tts_engine == TTSEngine.PIPER  # default


class TestEnvironmentVariableParsingTDD:
    """TDD tests for environment variable parsing methods"""
    
    def test_parse_bool_with_valid_true_values(self):
        """Should parse various true values correctly"""
        true_values = ['true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES', 'on', 'On', 'ON']
        
        for true_val in true_values:
            with patch.dict(os.environ, {'TEST_BOOL': true_val}):
                result = SystemConfig._parse_bool('TEST_BOOL', False)
                assert result is True, f"Failed to parse '{true_val}' as True"
    
    def test_parse_bool_with_valid_false_values(self):
        """Should parse various false values correctly"""
        false_values = ['false', 'False', 'FALSE', '0', 'no', 'No', 'NO', 'off', 'Off', 'OFF']
        
        for false_val in false_values:
            with patch.dict(os.environ, {'TEST_BOOL': false_val}):
                result = SystemConfig._parse_bool('TEST_BOOL', True)
                assert result is False, f"Failed to parse '{false_val}' as False"
    
    def test_parse_bool_with_missing_variable_returns_default(self):
        """Should return default value when environment variable is missing"""
        with patch.dict(os.environ, {}, clear=True):
            assert SystemConfig._parse_bool('MISSING_VAR', True) is True
            assert SystemConfig._parse_bool('MISSING_VAR', False) is False
    
    def test_parse_bool_with_invalid_values_returns_false(self):
        """Should return False for invalid boolean values"""
        invalid_values = ['maybe', 'invalid', 'true1', '2', '']
        
        for invalid_val in invalid_values:
            with patch.dict(os.environ, {'TEST_BOOL': invalid_val}):
                result = SystemConfig._parse_bool('TEST_BOOL', True)
                assert result is False, f"Should parse '{invalid_val}' as False"
    
    def test_parse_int_with_valid_values(self):
        """Should parse valid integer values correctly"""
        test_cases = [
            ('123', 123),
            ('0', 0),
            ('-42', -42),
            ('1000000', 1000000)
        ]
        
        for str_val, expected in test_cases:
            with patch.dict(os.environ, {'TEST_INT': str_val}):
                result = SystemConfig._parse_int('TEST_INT', 999)
                assert result == expected
    
    def test_parse_int_with_missing_variable_returns_default(self):
        """Should return default value when environment variable is missing"""
        with patch.dict(os.environ, {}, clear=True):
            result = SystemConfig._parse_int('MISSING_VAR', 42)
            assert result == 42
    
    def test_parse_int_with_invalid_values_raises_error(self):
        """Should raise ValueError for invalid integer values"""
        invalid_values = ['abc', '12.5', '12a', '', '1 2', 'true']
        
        for invalid_val in invalid_values:
            with patch.dict(os.environ, {'TEST_INT': invalid_val}):
                with pytest.raises(ValueError) as exc_info:
                    SystemConfig._parse_int('TEST_INT', 42)
                
                assert "TEST_INT must be a valid integer" in str(exc_info.value)
                assert invalid_val in str(exc_info.value)
    
    def test_parse_int_with_range_validation(self):
        """Should validate integer ranges correctly"""
        # Test minimum validation
        with patch.dict(os.environ, {'TEST_INT': '5'}):
            result = SystemConfig._parse_int('TEST_INT', 10, min_val=1, max_val=100)
            assert result == 5
        
        # Test maximum validation
        with patch.dict(os.environ, {'TEST_INT': '95'}):
            result = SystemConfig._parse_int('TEST_INT', 10, min_val=1, max_val=100)
            assert result == 95
        
        # Test value below minimum
        with patch.dict(os.environ, {'TEST_INT': '0'}):
            with pytest.raises(ValueError) as exc_info:
                SystemConfig._parse_int('TEST_INT', 10, min_val=1, max_val=100)
            assert "must be >= 1" in str(exc_info.value)
        
        # Test value above maximum
        with patch.dict(os.environ, {'TEST_INT': '150'}):
            with pytest.raises(ValueError) as exc_info:
                SystemConfig._parse_int('TEST_INT', 10, min_val=1, max_val=100)
            assert "must be <= 100" in str(exc_info.value)
    
    def test_parse_float_with_valid_values(self):
        """Should parse valid float values correctly"""
        test_cases = [
            ('123.45', 123.45),
            ('0.0', 0.0),
            ('-42.5', -42.5),
            ('1000000.123', 1000000.123),
            ('42', 42.0)  # Integer should convert to float
        ]
        
        for str_val, expected in test_cases:
            with patch.dict(os.environ, {'TEST_FLOAT': str_val}):
                result = SystemConfig._parse_float('TEST_FLOAT', 999.0)
                assert result == expected
    
    def test_parse_float_with_missing_variable_returns_default(self):
        """Should return default value when environment variable is missing"""
        with patch.dict(os.environ, {}, clear=True):
            result = SystemConfig._parse_float('MISSING_VAR', 42.5)
            assert result == 42.5
    
    def test_parse_float_with_invalid_values_raises_error(self):
        """Should raise ValueError for invalid float values"""
        invalid_values = ['abc', '12.5.3', '12a', '', '1 2', 'true']
        
        for invalid_val in invalid_values:
            with patch.dict(os.environ, {'TEST_FLOAT': invalid_val}):
                with pytest.raises(ValueError) as exc_info:
                    SystemConfig._parse_float('TEST_FLOAT', 42.0)
                
                assert "TEST_FLOAT must be a valid number" in str(exc_info.value)
                assert invalid_val in str(exc_info.value)
    
    def test_parse_float_with_range_validation(self):
        """Should validate float ranges correctly"""
        # Test minimum validation
        with patch.dict(os.environ, {'TEST_FLOAT': '5.5'}):
            result = SystemConfig._parse_float('TEST_FLOAT', 10.0, min_val=1.0, max_val=100.0)
            assert result == 5.5
        
        # Test maximum validation
        with patch.dict(os.environ, {'TEST_FLOAT': '95.7'}):
            result = SystemConfig._parse_float('TEST_FLOAT', 10.0, min_val=1.0, max_val=100.0)
            assert result == 95.7
        
        # Test value below minimum
        with patch.dict(os.environ, {'TEST_FLOAT': '0.5'}):
            with pytest.raises(ValueError) as exc_info:
                SystemConfig._parse_float('TEST_FLOAT', 10.0, min_val=1.0, max_val=100.0)
            assert "must be >= 1.0" in str(exc_info.value)
        
        # Test value above maximum
        with patch.dict(os.environ, {'TEST_FLOAT': '150.5'}):
            with pytest.raises(ValueError) as exc_info:
                SystemConfig._parse_float('TEST_FLOAT', 10.0, min_val=1.0, max_val=100.0)
            assert "must be <= 100.0" in str(exc_info.value)


class TestSystemConfigValidationTDD:
    """TDD tests for SystemConfig validation logic"""
    
    def test_validate_gemini_requires_api_key(self):
        """Should require API key for Gemini TTS engine"""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            gemini_api_key=None
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "GOOGLE_AI_API_KEY is required when TTS_ENGINE=gemini" in str(exc_info.value)
    
    def test_validate_gemini_rejects_placeholder_api_key(self):
        """Should reject placeholder API key for Gemini"""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            gemini_api_key="YOUR_GOOGLE_AI_API_KEY"
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "Please set a valid GOOGLE_AI_API_KEY" in str(exc_info.value)
    
    def test_validate_gemini_accepts_valid_api_key(self):
        """Should accept valid API key for Gemini"""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            gemini_api_key="valid_api_key_12345"
        )
        
        # Should not raise exception
        config.validate()
    
    def test_validate_piper_requires_model_name(self):
        """Should require model name for Piper TTS engine"""
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            piper_model_name=""
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "PIPER_MODEL_NAME cannot be empty when using Piper TTS" in str(exc_info.value)
    
    def test_validate_piper_accepts_valid_model_name(self):
        """Should accept valid model name for Piper"""
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            piper_model_name="en_US-lessac-medium"
        )
        
        # Should not raise exception
        config.validate()
    
    def test_validate_folder_paths_cannot_be_empty(self):
        """Should reject empty folder paths"""
        test_cases = [
            ("upload_folder", ""),
            ("audio_folder", ""),
            ("piper_models_dir", ""),
            ("upload_folder", "   "),  # whitespace only
            ("audio_folder", "\t\n"),  # whitespace only
        ]
        
        for folder_attr, invalid_path in test_cases:
            config = SystemConfig(tts_engine=TTSEngine.PIPER)
            setattr(config, folder_attr, invalid_path)
            
            with pytest.raises(ValueError) as exc_info:
                config.validate()
            
            assert "cannot be empty or whitespace" in str(exc_info.value)
    
    def test_validate_document_type_must_be_valid(self):
        """Should validate document type is one of allowed values"""
        # Test valid document types
        valid_types = ['research_paper', 'literature_review', 'general']
        for doc_type in valid_types:
            config = SystemConfig(
                tts_engine=TTSEngine.PIPER,
                document_type=doc_type
            )
            config.validate()  # Should not raise
        
        # Test invalid document type
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            document_type="invalid_type"
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        
        assert "DOCUMENT_TYPE must be one of" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)
    
    def test_validate_file_cleanup_settings_when_enabled(self):
        """Should validate file cleanup settings when cleanup is enabled"""
        # Test valid file cleanup settings
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            enable_file_cleanup=True,
            max_file_age_hours=24.0,
            auto_cleanup_interval_hours=6.0,
            max_disk_usage_mb=1000
        )
        config.validate()  # Should not raise
        
        # Test invalid max_file_age_hours
        config.max_file_age_hours = 0.0
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "MAX_FILE_AGE_HOURS must be positive" in str(exc_info.value)
        
        # Test invalid auto_cleanup_interval_hours
        config.max_file_age_hours = 24.0  # Reset to valid
        config.auto_cleanup_interval_hours = -1.0
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "AUTO_CLEANUP_INTERVAL_HOURS must be positive" in str(exc_info.value)
        
        # Test invalid max_disk_usage_mb
        config.auto_cleanup_interval_hours = 6.0  # Reset to valid
        config.max_disk_usage_mb = 0
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "MAX_DISK_USAGE_MB must be positive" in str(exc_info.value)
    
    def test_validate_file_cleanup_settings_when_disabled(self):
        """Should skip file cleanup validation when cleanup is disabled"""
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            enable_file_cleanup=False,
            max_file_age_hours=0.0,  # Invalid values
            auto_cleanup_interval_hours=-1.0,
            max_disk_usage_mb=0
        )
        
        # Should not raise exception since cleanup is disabled
        config.validate()


class TestSystemConfigHelperMethodsTDD:
    """TDD tests for SystemConfig helper methods"""
    
    def test_get_gemini_config_creates_correct_config(self):
        """Should create proper Gemini configuration object"""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            gemini_api_key="test_key_123",
            gemini_voice_name="Aoede",
            gemini_min_request_interval=1.5
        )
        
        result = config.get_gemini_config()
        
        # Should return a config object with correct values
        assert hasattr(result, 'voice_name')
        assert hasattr(result, 'api_key')
        assert hasattr(result, 'min_request_interval')
        assert result.voice_name == "Aoede"
        assert result.api_key == "test_key_123"
        assert result.min_request_interval == 1.5
    
    def test_get_piper_config_creates_correct_config(self):
        """Should create proper Piper configuration object"""
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            piper_model_name="en_US-amy-high",
            piper_models_dir="/custom/models",
            piper_length_scale=1.2
        )
        
        result = config.get_piper_config()
        
        # Should return a config object with correct values
        assert hasattr(result, 'model_name')
        assert hasattr(result, 'download_dir')
        assert hasattr(result, 'length_scale')
        assert result.model_name == "en_US-amy-high"
        assert result.download_dir == "/custom/models"
        assert result.length_scale == 1.2
    
    def test_print_summary_displays_configuration_info(self):
        """Should print comprehensive configuration summary"""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            enable_text_cleaning=True,
            enable_ssml=False,
            document_type="literature_review",
            enable_async_audio=True,
            max_concurrent_requests=8,
            upload_folder="test_uploads",
            audio_folder="test_audio",
            enable_file_cleanup=True,
            max_file_age_hours=48.0,
            auto_cleanup_interval_hours=12.0,
            max_disk_usage_mb=2000,
            gemini_api_key="test_key",
            gemini_voice_name="Charon"
        )
        
        # Capture print output
        with patch('builtins.print') as mock_print:
            config.print_summary()
            
            # Verify key information is printed
            printed_text = ' '.join(str(call) for call in mock_print.call_args_list)
            
            assert "TTS Engine: gemini" in printed_text
            assert "Text Cleaning: Enabled" in printed_text
            assert "SSML Enhancement: Disabled" in printed_text
            assert "Document Type: literature_review" in printed_text
            assert "Async Audio: Enabled" in printed_text
            assert "Max Concurrent: 8" in printed_text
            assert "Upload Folder: test_uploads" in printed_text
            assert "Audio Folder: test_audio" in printed_text
            assert "File Cleanup: Enabled" in printed_text
            assert "Max File Age: 48.0 hours" in printed_text
            assert "Gemini API Key: Set" in printed_text
            assert "Gemini Voice: Charon" in printed_text
    
    def test_print_summary_handles_missing_api_key(self):
        """Should show 'Missing' for unset API key"""
        config = SystemConfig(
            tts_engine=TTSEngine.GEMINI,
            gemini_api_key=None
        )
        
        with patch('builtins.print') as mock_print:
            config.print_summary()
            
            printed_text = ' '.join(str(call) for call in mock_print.call_args_list)
            assert "Gemini API Key: Missing" in printed_text
    
    def test_print_summary_shows_piper_specific_info(self):
        """Should show Piper-specific configuration when using Piper"""
        config = SystemConfig(
            tts_engine=TTSEngine.PIPER,
            piper_model_name="en_US-lessac-high",
            piper_models_dir="/custom/piper/models"
        )
        
        with patch('builtins.print') as mock_print:
            config.print_summary()
            
            printed_text = ' '.join(str(call) for call in mock_print.call_args_list)
            assert "TTS Engine: piper" in printed_text
            assert "Piper Model: en_US-lessac-high" in printed_text
            assert "Piper Models Dir: /custom/piper/models" in printed_text


class TestSystemConfigIntegrationTDD:
    """TDD tests for SystemConfig integration scenarios"""
    
    def test_complete_gemini_configuration_workflow(self):
        """Should handle complete Gemini configuration from environment"""
        gemini_env = {
            'TTS_ENGINE': 'gemini',
            'GOOGLE_AI_API_KEY': 'real_api_key_12345',
            'GEMINI_VOICE_NAME': 'Leda',
            'GEMINI_MODEL_NAME': 'gemini-2.5-pro-preview-tts',
            'GEMINI_MIN_REQUEST_INTERVAL': '1.5',
            'GEMINI_MEASUREMENT_MODE_INTERVAL': '0.5',
            'GEMINI_USE_MEASUREMENT_MODE': 'true',
            'ENABLE_TEXT_CLEANING': 'true',
            'ENABLE_SSML': 'true',
            'DOCUMENT_TYPE': 'research_paper'
        }
        
        with patch.dict(os.environ, gemini_env, clear=True):
            config = SystemConfig.from_env()
            
            # Validation should pass
            config.validate()
            
            # Verify Gemini-specific settings
            assert config.tts_engine == TTSEngine.GEMINI
            assert config.gemini_api_key == "real_api_key_12345"
            assert config.gemini_voice_name == "Leda"
            assert config.gemini_model_name == "gemini-2.5-pro-preview-tts"
            assert config.gemini_min_request_interval == 1.5
            assert config.gemini_measurement_mode_interval == 0.5
            assert config.gemini_use_measurement_mode is True
    
    def test_complete_piper_configuration_workflow(self):
        """Should handle complete Piper configuration from environment"""
        piper_env = {
            'TTS_ENGINE': 'piper',
            'PIPER_MODEL_NAME': 'en_US-amy-high',
            'PIPER_MODELS_DIR': '/data/piper_models',
            'PIPER_LENGTH_SCALE': '0.9',
            'ENABLE_TEXT_CLEANING': 'false',
            'ENABLE_SSML': 'true',
            'DOCUMENT_TYPE': 'general',
            'MAX_CONCURRENT_TTS_REQUESTS': '6',
            'AUDIO_BITRATE': '256k',
            'AUDIO_SAMPLE_RATE': '44100'
        }
        
        with patch.dict(os.environ, piper_env, clear=True):
            config = SystemConfig.from_env()
            
            # Validation should pass
            config.validate()
            
            # Verify Piper-specific settings
            assert config.tts_engine == TTSEngine.PIPER
            assert config.piper_model_name == "en_US-amy-high"
            assert config.piper_models_dir == "/data/piper_models"
            assert config.piper_length_scale == 0.9
            assert config.max_concurrent_requests == 6
            assert config.audio_bitrate == "256k"
            assert config.audio_sample_rate == 44100
    
    def test_configuration_with_all_edge_case_values(self):
        """Should handle edge case values within valid ranges"""
        edge_case_env = {
            'TTS_ENGINE': 'piper',
            'MAX_FILE_SIZE_MB': '1',  # minimum
            'MAX_CONCURRENT_TTS_REQUESTS': '20',  # maximum
            'CHUNK_SIZE': '1000',  # minimum
            'MAX_FILE_AGE_HOURS': '0.1',  # minimum
            'AUTO_CLEANUP_INTERVAL_HOURS': '24.0',  # maximum
            'MAX_DISK_USAGE_MB': '10000',  # maximum
            'PIPER_LENGTH_SCALE': '2.0',  # maximum
            'AUDIO_SAMPLE_RATE': '48000',  # maximum
            'TTS_TIMEOUT_SECONDS': '300',  # maximum
            'OCR_DPI': '600'  # maximum
        }
        
        with patch.dict(os.environ, edge_case_env, clear=True):
            config = SystemConfig.from_env()
            
            # Should create valid configuration
            config.validate()
            
            # Verify edge case values
            assert config.max_file_size_mb == 1
            assert config.max_concurrent_requests == 20
            assert config.chunk_size == 1000
            assert config.max_file_age_hours == 0.1
            assert config.auto_cleanup_interval_hours == 24.0
            assert config.max_disk_usage_mb == 10000
            assert config.piper_length_scale == 2.0
            assert config.audio_sample_rate == 48000
            assert config.tts_timeout_seconds == 300
            assert config.ocr_dpi == 600
    
    def test_configuration_error_messages_are_user_friendly(self):
        """Should provide clear, actionable error messages"""
        # Test missing Gemini API key
        with patch.dict(os.environ, {'TTS_ENGINE': 'gemini'}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                SystemConfig.from_env()
            
            error_msg = str(exc_info.value)
            assert "GOOGLE_AI_API_KEY is required" in error_msg
            assert "TTS_ENGINE=gemini" in error_msg
            assert "environment variable" in error_msg
        
        # Test invalid integer value
        with patch.dict(os.environ, {
            'TTS_ENGINE': 'piper',
            'MAX_FILE_SIZE_MB': 'not_a_number'
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                SystemConfig.from_env()
            
            error_msg = str(exc_info.value)
            assert "MAX_FILE_SIZE_MB must be a valid integer" in error_msg
            assert "not_a_number" in error_msg
        
        # Test out of range value
        with patch.dict(os.environ, {
            'TTS_ENGINE': 'piper',
            'MAX_FILE_SIZE_MB': '2000'  # Above maximum of 1000
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                SystemConfig.from_env()
            
            error_msg = str(exc_info.value)
            assert "MAX_FILE_SIZE_MB must be <= 1000" in error_msg
            assert "2000" in error_msg


class TestSystemConfigEdgeCasesTDD:
    """TDD tests for edge cases and unusual scenarios"""
    
    def test_environment_variables_with_whitespace(self):
        """Should handle environment variables with extra whitespace"""
        # Test that TTS_ENGINE whitespace is stripped (implemented behavior)
        with patch.dict(os.environ, {'TTS_ENGINE': '  piper  '}, clear=True):
            config = SystemConfig.from_env()
            assert config.tts_engine == TTSEngine.PIPER
        
        # Test behavior with whitespace in string values
        # Current design: most values preserve whitespace as-is
        env_with_whitespace = {
            'TTS_ENGINE': 'piper',
            'UPLOAD_FOLDER': '  uploads  ',  # Preserves whitespace
            'GEMINI_VOICE_NAME': '  Kore  '  # Preserves whitespace
        }
        
        with patch.dict(os.environ, env_with_whitespace, clear=True):
            config = SystemConfig.from_env()
            
            # TTS engine should be parsed correctly
            assert config.tts_engine == TTSEngine.PIPER
            # Other values preserve whitespace (documenting current behavior)
            assert config.upload_folder == "  uploads  "
            assert config.gemini_voice_name == "  Kore  "
    
    def test_very_long_string_values(self):
        """Should handle very long string values appropriately"""
        very_long_path = "a" * 1000  # 1000 character path
        very_long_key = "b" * 500   # 500 character API key
        
        env_vars = {
            'TTS_ENGINE': 'gemini',
            'UPLOAD_FOLDER': very_long_path,
            'GOOGLE_AI_API_KEY': very_long_key,
            'PIPER_MODEL_NAME': very_long_path
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = SystemConfig.from_env()
            
            # Should handle long strings without errors
            assert config.upload_folder == very_long_path
            assert config.gemini_api_key == very_long_key
            assert len(config.upload_folder) == 1000
            assert len(config.gemini_api_key) == 500
    
    def test_unicode_and_special_characters_in_strings(self):
        """Should handle unicode and special characters appropriately"""
        unicode_values = {
            'TTS_ENGINE': 'piper',
            'UPLOAD_FOLDER': 'uploads_测试_фолдер',
            'GEMINI_VOICE_NAME': 'Ĥëłłø_Wørłđ',
            'DOCUMENT_TYPE': 'general'
        }
        
        with patch.dict(os.environ, unicode_values, clear=True):
            config = SystemConfig.from_env()
            
            # Should preserve unicode characters
            assert config.upload_folder == 'uploads_测试_фолдер'
            assert config.gemini_voice_name == 'Ĥëłłø_Wørłđ'
    
    def test_numeric_string_edge_cases(self):
        """Should handle edge cases in numeric string parsing"""
        # Test scientific notation
        with patch.dict(os.environ, {
            'TTS_ENGINE': 'piper',
            'PIPER_LENGTH_SCALE': '1e0'  # Scientific notation for 1.0
        }, clear=True):
            config = SystemConfig.from_env()
            assert config.piper_length_scale == 1.0
        
        # Test very large numbers within range
        with patch.dict(os.environ, {
            'TTS_ENGINE': 'piper',
            'CHUNK_SIZE': '99999'  # Near maximum
        }, clear=True):
            config = SystemConfig.from_env()
            assert config.chunk_size == 99999
        
        # Test decimal precision
        with patch.dict(os.environ, {
            'TTS_ENGINE': 'piper',
            'PIPER_LENGTH_SCALE': '1.123456789'
        }, clear=True):
            config = SystemConfig.from_env()
            assert config.piper_length_scale == 1.123456789
    
    def test_simultaneous_multiple_invalid_values(self):
        """Should report first validation error when multiple issues exist"""
        invalid_env = {
            'TTS_ENGINE': 'invalid_engine',  # First error
            'MAX_FILE_SIZE_MB': 'not_number',  # Second error
            'CHUNK_SIZE': '0'  # Third error (below minimum)
        }
        
        with patch.dict(os.environ, invalid_env, clear=True):
            # Should raise error for the first validation issue encountered
            with pytest.raises(ValueError) as exc_info:
                SystemConfig.from_env()
            
            # Should mention the TTS engine error (first validation step)
            assert "Invalid TTS_ENGINE" in str(exc_info.value)
    
    def test_configuration_immutability_after_creation(self):
        """Should test if configuration objects maintain integrity"""
        config = SystemConfig(tts_engine=TTSEngine.PIPER)
        
        # Store original values
        original_tts_engine = config.tts_engine
        original_upload_folder = config.upload_folder
        
        # Attempt to modify (note: dataclass is not immutable by default)
        config.tts_engine = TTSEngine.GEMINI
        config.upload_folder = "modified"
        
        # Verify changes were applied (documenting current behavior)
        assert config.tts_engine == TTSEngine.GEMINI
        assert config.upload_folder == "modified"
        
        # This test documents that the config is mutable
        # If immutability is desired, this test should be updated accordingly