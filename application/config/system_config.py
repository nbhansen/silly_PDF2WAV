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
    
    # Processing settings
    enable_text_cleaning: bool = True
    enable_ssml: bool = True
    document_type: str = "research_paper"  # research_paper, literature_review, general
    enable_async_audio: bool = True
    max_concurrent_requests: int = 4
    chunk_size: int = 20000
    
    # Gemini specific
    gemini_api_key: Optional[str] = None
    gemini_voice_name: str = "Kore"
    gemini_min_request_interval: float = 2.0
    
    # Piper specific  
    piper_model_name: str = "en_US-lessac-medium"
    piper_models_dir: str = "piper_models"
    piper_length_scale: float = 1.0
    
    @classmethod
    def from_env(cls) -> 'SystemConfig':
        """Load configuration from environment variables with validation"""
        
        # Parse TTS engine
        tts_engine_str = os.getenv('TTS_ENGINE', 'piper').lower()
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
            gemini_api_key=os.getenv('GOOGLE_AI_API_KEY'),
            gemini_voice_name=os.getenv('GEMINI_VOICE_NAME', 'Kore'),
            gemini_min_request_interval=cls._parse_float('GEMINI_MIN_REQUEST_INTERVAL', 2.0, min_val=0.1, max_val=10.0),
            piper_model_name=os.getenv('PIPER_MODEL_NAME', 'en_US-lessac-medium'),
            piper_models_dir=os.getenv('PIPER_MODELS_DIR', 'piper_models'),
            piper_length_scale=cls._parse_float('PIPER_LENGTH_SCALE', 1.0, min_val=0.5, max_val=2.0)
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
        from domain.config.tts_config import GeminiConfig
        return GeminiConfig(
            voice_name=self.gemini_voice_name,
            api_key=self.gemini_api_key,
            min_request_interval=self.gemini_min_request_interval
        )
    
    def get_piper_config(self):
        """Get Piper-specific configuration"""
        from domain.config.tts_config import PiperConfig
        return PiperConfig(
            model_name=self.piper_model_name,
            download_dir=self.piper_models_dir,
            length_scale=self.piper_length_scale
        )
    
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
        
        if self.tts_engine == TTSEngine.GEMINI:
            api_key_status = "Set" if self.gemini_api_key else "Missing"
            print(f"Gemini API Key: {api_key_status}")
            print(f"Gemini Voice: {self.gemini_voice_name}")
        elif self.tts_engine == TTSEngine.PIPER:
            print(f"Piper Model: {self.piper_model_name}")
            print(f"Piper Models Dir: {self.piper_models_dir}")
        
        print("=" * 50)