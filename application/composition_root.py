# application/composition_root.py - Updated for async support with Piper
import os
from application.services.pdf_processing import PDFProcessingService
from domain.models import TTSConfig, CoquiConfig, GTTSConfig, BarkConfig, GeminiConfig, PiperConfig, ITTSEngine
from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from infrastructure.tts.coqui_tts_provider import CoquiTTSProvider
from infrastructure.tts.gtts_provider import GTTSProvider
from infrastructure.tts.bark_tts_provider import BarkTTSProvider
from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider as InfrastructureGeminiTTSProvider
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.audio_generation_service import AudioGenerationService

def create_pdf_service_from_env() -> PDFProcessingService:
    """Create fully configured PDF processing service from environment variables with async support"""
    
    # Get config from environment
    google_api_key = os.getenv('GOOGLE_AI_API_KEY', '')
    tts_engine_name = os.getenv('TTS_ENGINE', 'coqui').lower()
    
    # Create infrastructure providers
    ocr_provider = TesseractOCRProvider()
    llm_provider = GeminiLLMProvider(api_key=google_api_key)

    # Create TTS engine based on environment
    tts_config = _create_tts_config_dataclass(tts_engine_name)
    tts_engine = _create_tts_engine_provider(tts_engine_name, tts_config)

    # Create domain services (enhanced with async support)
    text_cleaner_service = TextCleaningService(llm_provider=llm_provider)
    audio_generation_service = AudioGenerationService(tts_engine=tts_engine)
    
    # Log async capabilities
    if hasattr(audio_generation_service, 'use_async') and audio_generation_service.use_async:
        print("CompositionRoot: Async audio processing is available and enabled")
        print(f"CompositionRoot: Max concurrent requests: {getattr(audio_generation_service, 'max_concurrent_requests', 'N/A')}")
    else:
        print("CompositionRoot: Using synchronous audio processing")
    
    # Wire up the service
    return PDFProcessingService(
        text_extractor=ocr_provider,
        text_cleaner=text_cleaner_service,
        audio_generator=audio_generation_service,
        page_validator=ocr_provider,
        llm_provider=llm_provider,
        tts_engine=tts_engine
    )

def _create_tts_config_dataclass(engine: str) -> TTSConfig:
    """Create TTS config dataclass based on engine and environment"""
    
    if engine == "coqui":
        return TTSConfig(
            voice_quality=os.getenv('VOICE_QUALITY', 'medium'),
            coqui=CoquiConfig(
                model_name=os.getenv('COQUI_MODEL_NAME'),
                speaker=os.getenv('COQUI_SPEAKER'),
                use_gpu=os.getenv('COQUI_USE_GPU_IF_AVAILABLE', 'True').lower() == 'true'
            )
        )
    elif engine == "piper":
        return TTSConfig(
            voice_quality=os.getenv('VOICE_QUALITY', 'medium'),
            piper=PiperConfig(
                model_path=os.getenv('PIPER_MODEL_PATH'),
                config_path=os.getenv('PIPER_CONFIG_PATH'), 
                speaker_id=int(os.getenv('PIPER_SPEAKER_ID')) if os.getenv('PIPER_SPEAKER_ID') else None,
                length_scale=float(os.getenv('PIPER_SPEED', '1.0')),
                noise_scale=float(os.getenv('PIPER_NOISE_SCALE', '0.667')),
                noise_w=float(os.getenv('PIPER_NOISE_W', '0.8')),
                sentence_silence=float(os.getenv('PIPER_SENTENCE_SILENCE', '0.2')),
                download_dir=os.getenv('PIPER_MODELS_DIR', 'piper_models')
            )
        )
    elif engine == "gtts":
        return TTSConfig(
            voice_quality=os.getenv('VOICE_QUALITY', 'medium'),
            gtts=GTTSConfig(
                lang=os.getenv('GTTS_LANG', 'en'),
                tld=os.getenv('GTTS_TLD', 'co.uk')
            )
        )
    elif engine == "bark":
        return TTSConfig(
            voice_quality=os.getenv('VOICE_QUALITY', 'medium'),
            bark=BarkConfig(
                use_gpu=os.getenv('BARK_USE_GPU_IF_AVAILABLE', 'True').lower() == 'true',
                use_small_models=os.getenv('BARK_USE_SMALL_MODELS', 'True').lower() == 'true'
            )
        )
    elif engine == "gemini":
        return TTSConfig(
            voice_quality=os.getenv('VOICE_QUALITY', 'medium'),
            speaking_style=os.getenv('SPEAKING_STYLE', 'professional'),
            gemini=GeminiConfig(
                voice_name=os.getenv('GEMINI_VOICE_NAME'),
                style_prompt=os.getenv('GEMINI_STYLE_PROMPT'),
                api_key=os.getenv('GOOGLE_AI_API_KEY')
            )
        )
    else:
        return TTSConfig()

def _create_tts_engine_provider(engine_name: str, config: TTSConfig) -> ITTSEngine:
    """Factory function to get an instance of a TTS engine provider."""
    engine_name_lower = engine_name.lower()
    print(f"TTSFactory: Attempting to create provider for engine: '{engine_name_lower}'")

    if engine_name_lower == "piper":
        from infrastructure.tts.piper_tts_provider import PiperTTSProvider
        return PiperTTSProvider(config.piper or PiperConfig())
    elif engine_name_lower == "coqui":
        return CoquiTTSProvider(config.coqui or CoquiConfig())
    elif engine_name_lower == "gtts":
        return GTTSProvider(config.gtts or GTTSConfig())
    elif engine_name_lower == "bark":
        return BarkTTSProvider(config.bark or BarkConfig())
    elif engine_name_lower == "gemini":
        return InfrastructureGeminiTTSProvider(config.gemini or GeminiConfig())
    
    # Enhanced fallback logic - try Piper if available, then gTTS
    print(f"TTSFactory: Engine '{engine_name_lower}' not found. Trying fallbacks...")
    
    # Try Piper first (best open source option)
    try:
        from infrastructure.tts.piper_tts_provider import PIPER_AVAILABLE
        if PIPER_AVAILABLE:
            print("TTSFactory: Falling back to Piper TTS")
            from infrastructure.tts.piper_tts_provider import PiperTTSProvider
            return PiperTTSProvider(PiperConfig())
    except ImportError:
        pass
    
    # Fall back to gTTS as last resort
    print("TTSFactory: Falling back to gTTS")
    return GTTSProvider(GTTSConfig())

# Optional: Environment variable configuration for async settings
def _get_async_config_from_env():
    """Get async configuration from environment variables (optional)"""
    return {
        'max_concurrent_requests': int(os.getenv('MAX_CONCURRENT_TTS_REQUESTS', '3')),
        'enable_async': os.getenv('ENABLE_ASYNC_AUDIO', 'True').lower() == 'true'
    }