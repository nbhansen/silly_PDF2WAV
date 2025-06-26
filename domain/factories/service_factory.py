# domain/factories/service_factory.py - Simple Service Factory
"""
Simplified service factory that delegates to focused factories.
Main orchestration point for service creation.
"""

from application.config.system_config import SystemConfig
from domain.audio.audio_engine import IAudioEngine
from domain.text.text_pipeline import ITextPipeline
from domain.document.document_engine import DocumentEngine, IDocumentEngine
from domain.container.service_container import ServiceContainer

from infrastructure.file.file_manager import FileManager
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider

from .audio_factory import create_audio_engine, create_timing_engine
from .text_factory import create_text_pipeline
from .tts_factory import create_tts_engine

def create_complete_audio_engine(config: SystemConfig) -> IAudioEngine:
    """Create audio engine with all dependencies using focused factories"""
    # Create dependencies in order
    file_manager = FileManager(
        upload_folder=config.upload_folder,
        output_folder=config.audio_folder
    )
    
    # Create TTS engine first to determine SSML support
    tts_engine = create_tts_engine(config)
    
    # Create text pipeline with TTS engine's SSML support status
    text_pipeline = create_text_pipeline(config, tts_supports_ssml=tts_engine.supports_ssml())
    
    # Create timing engine with all dependencies
    timing_engine = create_timing_engine(config, tts_engine, file_manager, text_pipeline)
    
    # Create final audio engine
    return create_audio_engine(config, tts_engine, file_manager, timing_engine)


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


def create_complete_service_set(config: SystemConfig):
    """Create complete set of consolidated services using focused factories"""
    # Create shared file manager
    file_manager = FileManager(
        upload_folder=config.upload_folder,
        output_folder=config.audio_folder
    )
    
    # Create TTS engine first to determine SSML support
    tts_engine = create_tts_engine(config)
    
    # Create text pipeline with TTS engine's SSML support status
    text_pipeline = create_text_pipeline(config, tts_supports_ssml=tts_engine.supports_ssml())
    
    # Create timing engine with all dependencies
    timing_engine = create_timing_engine(config, tts_engine, file_manager, text_pipeline)
    
    # Create audio engine with all dependencies
    audio_engine = create_audio_engine(config, tts_engine, file_manager, timing_engine)
    
    # Create document engine
    document_engine = create_document_engine(config)
    
    return {
        'config': config,
        'file_manager': file_manager,
        'text_pipeline': text_pipeline,
        'audio_engine': audio_engine,
        'document_engine': document_engine,
        'tts_engine': tts_engine,
        'timing_engine': timing_engine
    }


def create_pdf_service_from_env(config: SystemConfig):
    """
    Factory function that replaces CompositionRoot.create_pdf_service_from_env()
    Returns a simple service container with all dependencies configured
    """
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