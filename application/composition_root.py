# application/composition_root.py
import os
from application.services.pdf_processing import PDFProcessingService
from infrastructure.ocr.ocr_extractor_adapter import OCRExtractorAdapter
from infrastructure.tts.text_cleaner_adapter import TextCleanerAdapter
from infrastructure.tts.audio_generator_adapter import AudioGeneratorAdapter
from infrastructure.ocr.page_range_validator_adapter import PageRangeValidatorAdapter
from tts_utils import TTSConfig, CoquiConfig, GTTSConfig, BarkConfig, GeminiConfig

def create_pdf_service_from_env() -> PDFProcessingService:
    """Create fully configured PDF processing service from environment variables"""
    
    # Get config from environment
    google_api_key = os.getenv('GOOGLE_AI_API_KEY', '')
    tts_engine = os.getenv('TTS_ENGINE', 'coqui').lower()
    
    # Create TTS config
    tts_config = _create_tts_config(tts_engine)
    
    # Create adapters
    ocr_extractor = OCRExtractorAdapter()
    page_validator = PageRangeValidatorAdapter(ocr_extractor._extractor)
    text_cleaner = TextCleanerAdapter(google_api_key)
    audio_generator = AudioGeneratorAdapter(tts_engine, tts_config)
    
    # Wire up the service
    return PDFProcessingService(
        text_extractor=ocr_extractor,
        text_cleaner=text_cleaner,
        audio_generator=audio_generator,
        page_validator=page_validator
    )

def _create_tts_config(engine: str) -> TTSConfig:
    """Create TTS config based on engine and environment"""
    
    if engine == "coqui":
        return TTSConfig(
            voice_quality=os.getenv('VOICE_QUALITY', 'medium'),
            coqui=CoquiConfig(
                model_name=os.getenv('COQUI_MODEL_NAME'),
                speaker=os.getenv('COQUI_SPEAKER'), # Allow explicit speaker selection
                use_gpu=os.getenv('COQUI_USE_GPU_IF_AVAILABLE', 'True').lower() == 'true'
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