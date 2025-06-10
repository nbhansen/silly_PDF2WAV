# application/composition_root.py
import os
from application.services.pdf_processing import PDFProcessingService
from application.config import TTSConfigFactory
from domain.interfaces import ITTSEngine
from domain.services.ssml_pipeline import SSMLPipeline, SSMLConfig, create_ssml_pipeline
from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.audio_generation_service import AudioGenerationService

def create_pdf_service_from_env() -> PDFProcessingService:
    """Create PDFProcessingService with configuration from environment variables."""  
    # Get basic config
    google_api_key = os.getenv('GOOGLE_AI_API_KEY', '')
    tts_engine_name = os.getenv('TTS_ENGINE', 'piper').lower()  # Default to piper
    
    print(f"CompositionRoot: Initializing with TTS engine: {tts_engine_name}")
    
    # Create the core providers
    ocr_provider = TesseractOCRProvider()
    llm_provider = GeminiLLMProvider(api_key=google_api_key)
    tts_engine = _create_tts_engine(tts_engine_name)
    
    # Create SSML pipeline (keep for now, but simplified)
    ssml_config = SSMLConfig(
        enabled=os.getenv('ENABLE_SSML', 'True').lower() in ('true', '1', 'yes'),
        document_type=os.getenv('DOCUMENT_TYPE', 'research_paper')
    )
    ssml_pipeline = create_ssml_pipeline(tts_engine, ssml_config)
    
    # Create domain services
    text_cleaner = TextCleaningService(llm_provider=llm_provider)
    audio_generator = AudioGenerationService(tts_engine=tts_engine)
    
    print(f"CompositionRoot: TTS={tts_engine_name}, SSML={ssml_pipeline.is_enabled()}")
    
    return PDFProcessingService(
        text_extractor=ocr_provider,
        text_cleaner=text_cleaner,
        audio_generator=audio_generator,
        page_validator=ocr_provider,
        ssml_pipeline=ssml_pipeline,
        llm_provider=llm_provider,
        tts_engine=tts_engine
    )

def _create_tts_engine(engine_name: str) -> ITTSEngine:
    """Create TTS engine - ONLY PIPER AND GEMINI"""
    engine_name = engine_name.lower()
    
    if engine_name == "piper":
        print("TTSFactory: Creating Piper TTS engine")
        from infrastructure.tts.piper_tts_provider import PiperTTSProvider
        config = TTSConfigFactory.create_config('piper')
        return PiperTTSProvider(config.piper)
    
    elif engine_name == "gemini":
        print("TTSFactory: Creating Gemini TTS engine")
        from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
        config = TTSConfigFactory.create_config('gemini')
        return GeminiTTSProvider(config.gemini)
    
    else:
        # No fallbacks - be explicit about what's supported
        raise ValueError(
            f"Unsupported TTS engine: '{engine_name}'. "
            f"Supported engines: piper, gemini. "
            f"Set TTS_ENGINE environment variable to 'piper' or 'gemini'."
        )

# Optional: Keep this if you actually use it for testing
def validate_engine_config(engine_name: str) -> dict:
    """Quick validation - only if you actually use this"""
    try:
        engine = _create_tts_engine(engine_name)
        return {
            'valid': True,
            'engine': engine_name,
            'available': True
        }
    except Exception as e:
        return {
            'valid': False,
            'engine': engine_name,
            'error': str(e)
        }

# DELETE ALL THE REST - unless you specifically use these functions:
# - get_available_engines() 
# - create_test_ssml_pipeline()
# - get_ssml_configuration_guide()
# - test_ssml_pipeline_integration()
# - _log_service_configuration()