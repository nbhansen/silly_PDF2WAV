# application/composition_root.py
from application.config.system_config import SystemConfig, TTSEngine
from application.services.pdf_processing import PDFProcessingService
from domain.interfaces import ITTSEngine, ILLMProvider
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.audio_generation_service import AudioGenerationService

def create_pdf_service_from_env() -> PDFProcessingService:
    """
    Main entry point: Create PDF service with configuration from environment
    
    This replaces all the complex configuration building logic with simple,
    validated configuration loading.
    """
    try:
        # Load and validate configuration from environment
        config = SystemConfig.from_env()
        config.print_summary()  # Show what we loaded
        
        # Create providers
        text_extractor = TesseractOCRProvider()
        llm_provider = _create_llm_provider(config)
        tts_engine = _create_tts_engine(config)
        
        # Create services
        text_cleaner = TextCleaningService(
            llm_provider=llm_provider if config.enable_text_cleaning else None
        )
        
        audio_generator = AudioGenerationService(tts_engine=tts_engine)
        
        # Assemble the complete service
        return PDFProcessingService(
            text_extractor=text_extractor,
            text_cleaner=text_cleaner,
            audio_generator=audio_generator,
            page_validator=text_extractor,  # Same instance serves both roles
            llm_provider=llm_provider,
            tts_engine=tts_engine,
            enable_ssml=config.enable_ssml,
            document_type=config.document_type
        )
        
    except ValueError as e:
        print(f"CONFIGURATION ERROR: {e}")
        print("\nPlease check your environment variables and try again.")
        raise
    except Exception as e:
        print(f"SERVICE INITIALIZATION ERROR: {e}")
        raise

def _create_tts_engine(config: SystemConfig) -> ITTSEngine:
    """Create TTS engine based on configuration"""
    
    if config.tts_engine == TTSEngine.PIPER:
        print("Creating Piper TTS engine...")
        from infrastructure.tts.piper_tts_provider import PiperTTSProvider
        return PiperTTSProvider(config.get_piper_config())
    
    elif config.tts_engine == TTSEngine.GEMINI:
        print("Creating Gemini TTS engine...")
        from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
        return GeminiTTSProvider(config.get_gemini_config())
    
    else:
        # This should never happen due to validation, but be explicit
        raise ValueError(f"Unsupported TTS engine: {config.tts_engine}")

def _create_llm_provider(config: SystemConfig) -> ILLMProvider:
    """Create LLM provider if API key is available"""
    
    if config.gemini_api_key and config.gemini_api_key != "YOUR_GOOGLE_AI_API_KEY":
        print("Creating Gemini LLM provider for text cleaning...")
        return GeminiLLMProvider(config.gemini_api_key)
    else:
        print("No LLM provider available (Gemini API key not set)")
        return None

# Keep these for backwards compatibility if needed
def validate_engine_config(engine_name: str) -> dict:
    """Quick validation helper"""
    try:
        # Try to create a config with this engine
        import os
        old_engine = os.getenv('TTS_ENGINE')
        os.environ['TTS_ENGINE'] = engine_name
        
        try:
            config = SystemConfig.from_env()
            tts_engine = _create_tts_engine(config)
            return {
                'valid': True,
                'engine': engine_name,
                'available': True
            }
        finally:
            # Restore original
            if old_engine:
                os.environ['TTS_ENGINE'] = old_engine
            elif 'TTS_ENGINE' in os.environ:
                del os.environ['TTS_ENGINE']
                
    except Exception as e:
        return {
            'valid': False,
            'engine': engine_name,
            'error': str(e)
        }