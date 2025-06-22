# domain/factories/service_factory.py - Simple Service Factory
"""
Clean, minimal factory functions that replace the complex CompositionRoot.
Focuses on creating consolidated services with clear dependencies.
"""

from typing import Optional

from application.config.system_config import SystemConfig
from domain.audio.audio_engine import AudioEngine, IAudioEngine
from domain.audio.timing_engine import TimingEngine, ITimingEngine, TimingMode
from domain.text.text_pipeline import TextPipeline, ITextPipeline
from domain.document.document_engine import DocumentEngine, IDocumentEngine
from domain.container.service_container import ServiceContainer

from infrastructure.file.file_manager import FileManager
from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
from infrastructure.tts.piper_tts_provider import PiperTTSProvider


def create_text_pipeline(config: SystemConfig) -> ITextPipeline:
    """Create text pipeline with optional LLM provider"""
    llm_provider = None
    if config.gemini_api_key:
        llm_provider = GeminiLLMProvider(api_key=config.gemini_api_key)
    
    return TextPipeline(
        llm_provider=llm_provider,
        enable_cleaning=config.enable_text_cleaning,
        enable_ssml=config.enable_ssml,
        document_type=config.document_type
    )


def create_tts_engine(config: SystemConfig):
    """Create TTS engine based on configuration"""
    if config.tts_engine.value == 'gemini':
        return GeminiTTSProvider(
            model_name=config.gemini_model_name,
            api_key=config.gemini_api_key,
            voice_name=config.gemini_voice_name,
            document_type=config.document_type
        )
    else:
        return PiperTTSProvider(
            config.get_piper_config(),
            repository_url=config.piper_model_repository_url
        )


def create_timing_engine(config: SystemConfig, tts_engine, file_manager: FileManager, text_pipeline: ITextPipeline) -> ITimingEngine:
    """Create timing engine with appropriate mode"""
    mode = TimingMode.MEASUREMENT if config.gemini_use_measurement_mode else TimingMode.ESTIMATION
    
    return TimingEngine(
        tts_engine=tts_engine,
        file_manager=file_manager,
        text_pipeline=text_pipeline,
        mode=mode,
        measurement_interval=config.gemini_measurement_mode_interval
    )


def create_audio_engine(config: SystemConfig) -> IAudioEngine:
    """Create audio engine with all dependencies"""
    # Create dependencies
    file_manager = FileManager(
        upload_folder=config.upload_folder,
        output_folder=config.audio_folder
    )
    
    text_pipeline = create_text_pipeline(config)
    tts_engine = create_tts_engine(config)
    timing_engine = create_timing_engine(config, tts_engine, file_manager, text_pipeline)
    
    return AudioEngine(
        tts_engine=tts_engine,
        file_manager=file_manager,
        timing_engine=timing_engine,
        max_concurrent=config.max_concurrent_requests
    )


def create_document_engine(config: SystemConfig) -> IDocumentEngine:
    """Create document engine with dependencies"""
    file_manager = FileManager(
        upload_folder=config.upload_folder,
        output_folder=config.audio_folder
    )
    
    ocr_provider = TesseractOCRProvider(config=config)
    
    return DocumentEngine(
        ocr_provider=ocr_provider,
        file_manager=file_manager
    )


def create_complete_service_set(config: Optional[SystemConfig] = None):
    """Create complete set of consolidated services"""
    if config is None:
        config = SystemConfig.from_env()
    
    # Create shared file manager
    file_manager = FileManager(
        upload_folder=config.upload_folder,
        output_folder=config.audio_folder
    )
    
    # Create services
    text_pipeline = create_text_pipeline(config)
    audio_engine = create_audio_engine(config)
    document_engine = create_document_engine(config)
    
    return {
        'config': config,
        'file_manager': file_manager,
        'text_pipeline': text_pipeline,
        'audio_engine': audio_engine,
        'document_engine': document_engine
    }


def create_pdf_service_from_env():
    """
    Factory function that replaces CompositionRoot.create_pdf_service_from_env()
    Returns a simple service container with all dependencies configured
    """
    config = SystemConfig.from_env()
    services = create_complete_service_set(config)
    
    # Create a simple container
    container = ServiceContainer(config)
    
    # Register the consolidated services
    container.register(ITextPipeline, lambda: services['text_pipeline'])
    container.register(IAudioEngine, lambda: services['audio_engine'])
    container.register(IDocumentEngine, lambda: services['document_engine'])
    container.register(FileManager, lambda: services['file_manager'])
    
    # Register string-based accessors for compatibility
    container.register('ITextPipeline', lambda: services['text_pipeline'])
    container.register('IAudioEngine', lambda: services['audio_engine'])
    container.register('IDocumentEngine', lambda: services['document_engine'])
    
    return container