# application/composition_root.py - Simplified with SSML Pipeline
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
    """Create PDF processing service with centralized SSML pipeline"""
    
    # Get configuration
    google_api_key = os.getenv('GOOGLE_AI_API_KEY', '')
    tts_engine_name = os.getenv('TTS_ENGINE', 'coqui').lower()
    
    print(f"CompositionRoot: Initializing with TTS engine: {tts_engine_name}")
    
    # Create infrastructure providers
    ocr_provider = TesseractOCRProvider()
    llm_provider = GeminiLLMProvider(api_key=google_api_key)

    # Create TTS engine
    tts_config = TTSConfigFactory.create_config(tts_engine_name)
    tts_engine = _create_tts_engine_provider(tts_engine_name, tts_config)

    # Create SSML configuration and pipeline
    ssml_config = _create_ssml_config()
    ssml_pipeline = create_ssml_pipeline(tts_engine, ssml_config)
    
    # Create domain services (simplified - no SSML logic)
    text_cleaner_service = TextCleaningService(llm_provider=llm_provider)
    audio_generation_service = AudioGenerationService(tts_engine=tts_engine)
    
    # Log configuration
    _log_service_configuration(tts_engine_name, ssml_pipeline, audio_generation_service)
    
    # Wire up the service with SSML pipeline
    return PDFProcessingService(
        text_extractor=ocr_provider,
        text_cleaner=text_cleaner_service,
        audio_generator=audio_generation_service,
        page_validator=ocr_provider,
        ssml_pipeline=ssml_pipeline,  # NEW: Centralized SSML
        llm_provider=llm_provider,
        tts_engine=tts_engine
    )

def _create_ssml_config() -> SSMLConfig:
    """Create SSML configuration from environment"""
    return SSMLConfig(
        enabled=os.getenv('ENABLE_SSML', 'True').lower() in ('true', '1', 'yes', 'on'),
        document_type=os.getenv('DOCUMENT_TYPE', 'research_paper'),
        force_capability=None  # Let pipeline auto-detect
    )

def _create_tts_engine_provider(engine_name: str, config) -> ITTSEngine:
    """Create TTS engine (same as before)"""
    engine_name_lower = engine_name.lower()
    print(f"TTSFactory: Creating provider for engine: '{engine_name_lower}'")

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
    
    # Fallback to gTTS
    print("TTSFactory: Falling back to gTTS")
    from infrastructure.tts.gtts_provider import GTTSProvider
    from application.config import GTTSConfigBuilder
    fallback_config = GTTSConfigBuilder.from_env()
    return GTTSProvider(fallback_config)

def _log_service_configuration(engine_name: str, ssml_pipeline: SSMLPipeline, audio_service):
    """Simplified logging focused on SSML pipeline"""
    print(f"CompositionRoot: TTS Engine: {engine_name}")
    print(f"CompositionRoot: SSML Enabled: {ssml_pipeline.is_enabled()}")
    print(f"CompositionRoot: SSML Capability: {ssml_pipeline.get_capability().value}")
    print(f"CompositionRoot: Document Type: {ssml_pipeline.config.document_type}")
    
    if hasattr(audio_service, 'use_async') and audio_service.use_async:
        max_concurrent = getattr(audio_service, 'max_concurrent_requests', 'N/A')
        print(f"CompositionRoot: Async processing enabled (max concurrent: {max_concurrent})")
    else:
        print("CompositionRoot: Using synchronous processing")

# Helper functions for testing and configuration
def get_available_engines() -> list[str]:
    """Get list of available TTS engines"""
    return TTSConfigFactory.get_supported_engines()

def validate_engine_config(engine_name: str) -> dict:
    """Validate engine configuration with SSML support info"""
    try:
        config = TTSConfigFactory.create_config(engine_name)
        engine = _create_tts_engine_provider(engine_name, config)
        
        # Test SSML pipeline creation
        ssml_config = _create_ssml_config()
        ssml_pipeline = create_ssml_pipeline(engine, ssml_config)
        
        return {
            'valid': True,
            'engine': engine_name,
            'provider_available': engine is not None,
            'ssml_enabled': ssml_pipeline.is_enabled(),
            'ssml_capability': ssml_pipeline.get_capability().value,
            'optimal_chunk_size': ssml_pipeline.get_optimal_chunk_size()
        }
    except Exception as e:
        return {
            'valid': False,
            'engine': engine_name,
            'error': str(e),
            'ssml_enabled': False,
            'ssml_capability': 'none'
        }

def create_test_ssml_pipeline(engine_name: str) -> dict:
    """Create test SSML pipeline for development"""
    try:
        # Create engine and pipeline
        config = TTSConfigFactory.create_config(engine_name)
        engine = _create_tts_engine_provider(engine_name, config)
        
        ssml_config = SSMLConfig(enabled=True, document_type='research_paper')
        pipeline = create_ssml_pipeline(engine, ssml_config)
        
        # Test with sample text
        test_text = "However, we found a 73.2 percent increase in efficiency during 2024."
        processed = pipeline.process_text(test_text)
        
        return {
            'success': True,
            'engine': engine_name,
            'ssml_enabled': pipeline.is_enabled(),
            'capability': pipeline.get_capability().value,
            'sample_input': test_text,
            'sample_output': processed[:200] + "..." if len(processed) > 200 else processed
        }
    except Exception as e:
        return {
            'success': False,
            'engine': engine_name,
            'error': str(e)
        }

def get_ssml_configuration_guide() -> dict:
    """Get SSML configuration guide"""
    return {
        'environment_variables': {
            'ENABLE_SSML': 'Enable/disable SSML processing (True/False)',
            'DOCUMENT_TYPE': 'Type of academic document (research_paper, literature_review, etc.)',
            'TTS_ENGINE': 'TTS engine selection affects SSML capability'
        },
        'supported_engines': {
            'piper': 'Basic SSML support',
            'gemini': 'Full SSML support', 
            'coqui': 'Basic SSML support (model-dependent)',
            'gtts': 'No SSML support',
            'bark': 'No SSML support'
        },
        'recommended_config': {
            'high_quality_ssml': {
                'TTS_ENGINE': 'gemini',
                'ENABLE_SSML': 'True',
                'DOCUMENT_TYPE': 'research_paper'
            },
            'local_ssml': {
                'TTS_ENGINE': 'piper',
                'ENABLE_SSML': 'True',
                'DOCUMENT_TYPE': 'research_paper'
            },
            'fast_no_ssml': {
                'TTS_ENGINE': 'gtts',
                'ENABLE_SSML': 'False'
            }
        }
    }

# Development and testing
def test_ssml_pipeline_integration():
    """Test SSML pipeline with all available engines"""
    engines = get_available_engines()
    results = {}
    
    for engine in engines:
        print(f"\n=== Testing {engine.upper()} SSML Pipeline ===")
        result = create_test_ssml_pipeline(engine)
        results[engine] = result
        
        if result['success']:
            print(f"✅ {engine}: SSML {result['capability']}")
            if result['ssml_enabled']:
                print(f"   Sample: {result['sample_output']}")
        else:
            print(f"❌ {engine}: {result['error']}")
    
    return results

if __name__ == "__main__":
    print("🔍 Testing SSML Pipeline Integration")
    test_ssml_pipeline_integration()