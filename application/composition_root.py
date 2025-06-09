# application/composition_root.py - Simplified with Clean Config System
import os
from application.services.pdf_processing import PDFProcessingService
from application.config import TTSConfigFactory
from domain.interfaces import ITTSEngine
from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.audio_generation_service import AudioGenerationService

def create_pdf_service_from_env() -> PDFProcessingService:
    """Create fully configured PDF processing service from environment variables"""
    
    # Get basic config
    google_api_key = os.getenv('GOOGLE_AI_API_KEY', '')
    tts_engine_name = os.getenv('TTS_ENGINE', 'coqui').lower()
    
    print(f"CompositionRoot: Initializing with TTS engine: {tts_engine_name}")
    
    # Create infrastructure providers
    ocr_provider = TesseractOCRProvider()
    llm_provider = GeminiLLMProvider(api_key=google_api_key)

    # Create TTS engine using clean config system
    tts_config = TTSConfigFactory.create_config(tts_engine_name)
    tts_engine = _create_tts_engine_provider(tts_engine_name, tts_config)

    # Create domain services
    text_cleaner_service = TextCleaningService(llm_provider=llm_provider)
    audio_generation_service = AudioGenerationService(tts_engine=tts_engine)
    
    # Log configuration summary
    _log_service_configuration(tts_engine_name, tts_config, audio_generation_service)
    
    # Wire up the service
    return PDFProcessingService(
        text_extractor=ocr_provider,
        text_cleaner=text_cleaner_service,
        audio_generator=audio_generation_service,
        page_validator=ocr_provider,
        llm_provider=llm_provider,
        tts_engine=tts_engine
    )

def _create_tts_engine_provider(engine_name: str, config) -> ITTSEngine:
    """Factory function to get an instance of a TTS engine provider"""
    engine_name_lower = engine_name.lower()
    print(f"TTSFactory: Creating provider for engine: '{engine_name_lower}'")

    # Import and create engine based on name
    if engine_name_lower == "piper":
        from infrastructure.tts.piper_tts_provider import PiperTTSProvider
        return PiperTTSProvider(config.piper)
    elif engine_name_lower == "coqui":
        from infrastructure.tts.coqui_tts_provider import CoquiTTSProvider
        return CoquiTTSProvider(config.coqui)
    elif engine_name_lower == "gtts":
        from infrastructure.tts.gtts_provider import GTTSProvider
        return GTTSProvider(config.gtts)
    elif engine_name_lower == "bark":
        from infrastructure.tts.bark_tts_provider import BarkTTSProvider
        return BarkTTSProvider(config.bark)
    elif engine_name_lower == "gemini":
        from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
        return GeminiTTSProvider(config.gemini)
    
    # Fallback logic with clear preference order
    print(f"TTSFactory: Engine '{engine_name_lower}' not found. Trying fallbacks...")
    
    # Try Piper first (best open source option)
    try:
        from infrastructure.tts.piper_tts_provider import PIPER_AVAILABLE
        if PIPER_AVAILABLE:
            print("TTSFactory: Falling back to Piper TTS")
            from infrastructure.tts.piper_tts_provider import PiperTTSProvider
            from application.config import PiperConfigBuilder
            fallback_config = PiperConfigBuilder.from_env()
            return PiperTTSProvider(fallback_config)
    except ImportError:
        pass
    
    # Fall back to gTTS as last resort
    print("TTSFactory: Falling back to gTTS")
    from infrastructure.tts.gtts_provider import GTTSProvider
    from application.config import GTTSConfigBuilder
    fallback_config = GTTSConfigBuilder.from_env()
    return GTTSProvider(fallback_config)

def _log_service_configuration(engine_name: str, config, audio_service):
    """Log service configuration for debugging"""
    print(f"CompositionRoot: TTS Engine: {engine_name}")
    print(f"CompositionRoot: Voice Quality: {config.voice_quality}")
    print(f"CompositionRoot: Speaking Style: {config.speaking_style}")
    
    # Log engine-specific config
    engine_config = getattr(config, engine_name.lower(), None)
    if engine_config:
        if hasattr(engine_config, 'model_name'):
            print(f"CompositionRoot: Model: {engine_config.model_name}")
        if hasattr(engine_config, 'voice_name'):
            print(f"CompositionRoot: Voice: {engine_config.voice_name}")
    
    # Log async capabilities
    if hasattr(audio_service, 'use_async') and audio_service.use_async:
        max_concurrent = getattr(audio_service, 'max_concurrent_requests', 'N/A')
        print(f"CompositionRoot: Async processing enabled (max concurrent: {max_concurrent})")
    else:
        print("CompositionRoot: Using synchronous processing")

def get_available_engines() -> list[str]:
    """Get list of available TTS engines for UI/debugging"""
    return TTSConfigFactory.get_supported_engines()

def validate_engine_config(engine_name: str) -> dict:
    """Validate that an engine can be properly configured"""
    try:
        config = TTSConfigFactory.create_config(engine_name)
        engine = _create_tts_engine_provider(engine_name, config)
        return {
            'valid': True,
            'engine': engine_name,
            'config': config,
            'provider_available': engine is not None
        }
    except Exception as e:
        return {
            'valid': False,
            'engine': engine_name,
            'error': str(e)
        }