# domain/container/service_container.py - Simple Service Container
"""
Clean, minimal service container that replaces the complex CompositionRoot.
Focuses on dependency injection without over-engineering.
"""

from typing import Dict, Type, TypeVar, Callable, Any
from abc import ABC, abstractmethod

from application.config.system_config import SystemConfig

T = TypeVar('T')


class IServiceContainer(ABC):
    """Simple service container interface"""
    
    @abstractmethod
    def register(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a service factory"""
        pass
    
    @abstractmethod
    def get(self, interface: Type[T]) -> T:
        """Get a service instance"""
        pass


class ServiceContainer(IServiceContainer):
    """
    Simple service container with lazy initialization.
    High cohesion: All dependency injection in one place.
    Low coupling: Uses factories to avoid tight dependencies.
    """
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self._factories: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._register_core_services()
    
    def register(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a service factory"""
        self._factories[interface] = factory
    
    def get(self, interface: Type[T]) -> T:
        """Get service instance (singleton pattern)"""
        if interface in self._singletons:
            return self._singletons[interface]
        
        if interface not in self._factories:
            raise ValueError(f"Service {interface.__name__} not registered")
        
        instance = self._factories[interface]()
        self._singletons[interface] = instance
        return instance
    
    def _register_core_services(self):
        """Register core services with their factories"""
        from domain.audio.audio_engine import IAudioEngine, AudioEngine
        from domain.audio.timing_engine import ITimingEngine, TimingEngine, TimingMode
        from domain.text.text_pipeline import ITextPipeline, TextPipeline
        from infrastructure.file.file_manager import FileManager
        from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
        from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
        
        # File Manager
        self.register(
            FileManager,
            lambda: FileManager(
                upload_folder=self.config.upload_folder,
                output_folder=self.config.audio_folder
            )
        )
        
        # LLM Provider (if configured)
        if self.config.gemini_api_key:
            self.register(
                GeminiLLMProvider,
                lambda: GeminiLLMProvider(api_key=self.config.gemini_api_key)
            )
        
        # Text Pipeline
        self.register(
            ITextPipeline,
            lambda: TextPipeline(
                llm_provider=self.get(GeminiLLMProvider) if self.config.gemini_api_key else None,
                enable_cleaning=self.config.enable_text_cleaning,
                enable_ssml=self.config.enable_ssml,
                document_type=self.config.document_type
            )
        )
        
        # TTS Engine (factory method)
        self.register(
            'tts_engine',
            lambda: self._create_tts_engine()
        )
        
        # Timing Engine
        self.register(
            ITimingEngine,
            lambda: TimingEngine(
                tts_engine=self.get('tts_engine'),
                file_manager=self.get(FileManager),
                ssml_service=None,  # Will be replaced by text pipeline
                text_cleaning_service=None,  # Will be replaced by text pipeline
                mode=TimingMode.MEASUREMENT if self.config.gemini_use_measurement_mode else TimingMode.ESTIMATION,
                measurement_interval=self.config.gemini_measurement_mode_interval
            )
        )
        
        # Audio Engine
        self.register(
            IAudioEngine,
            lambda: AudioEngine(
                tts_engine=self.get('tts_engine'),
                file_manager=self.get(FileManager),
                timing_engine=self.get(ITimingEngine),
                max_concurrent=self.config.max_concurrent_requests
            )
        )
        
        # OCR Provider
        self.register(
            TesseractOCRProvider,
            lambda: TesseractOCRProvider(config=self.config)
        )
    
    def _create_tts_engine(self):
        """Factory for TTS engine based on configuration"""
        from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
        from infrastructure.tts.piper_tts_provider import PiperTTSProvider
        
        if self.config.tts_engine.value == 'gemini':
            return GeminiTTSProvider(
                model_name=self.config.gemini_model_name,
                api_key=self.config.gemini_api_key,
                voice_personas_config=self.config.voice_personas_config
            )
        else:
            return PiperTTSProvider(
                self.config.get_piper_config(),
                repository_url=self.config.piper_model_repository_url
            )


def create_service_container() -> ServiceContainer:
    """Factory function to create configured service container"""
    config = SystemConfig.from_env()
    return ServiceContainer(config)