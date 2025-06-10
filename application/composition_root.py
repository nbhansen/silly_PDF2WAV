# application/composition_root.py - Updated with SSML Support
import os
from application.services.pdf_processing import PDFProcessingService
from application.config import TTSConfigFactory
from domain.interfaces import ITTSEngine, ISSMLProcessor, SSMLCapability
from domain.services.ssml_generation_service import SSMLGenerationService, AcademicSSMLEnhancer
from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.audio_generation_service import AudioGenerationService

def create_pdf_service_from_env() -> PDFProcessingService:
    """Create fully configured PDF processing service with SSML support from environment variables"""
    
    # Get basic config
    google_api_key = os.getenv('GOOGLE_AI_API_KEY', '')
    tts_engine_name = os.getenv('TTS_ENGINE', 'coqui').lower()
    enable_ssml = os.getenv('ENABLE_SSML', 'True').lower() in ('true', '1', 'yes', 'on')
    document_type = os.getenv('DOCUMENT_TYPE', 'research_paper')  # research_paper, literature_review, etc.
    
    print(f"CompositionRoot: Initializing with TTS engine: {tts_engine_name}")
    print(f"CompositionRoot: SSML enabled: {enable_ssml}")
    
    # Create infrastructure providers
    ocr_provider = TesseractOCRProvider()
    llm_provider = GeminiLLMProvider(api_key=google_api_key)

    # Create TTS engine using clean config system
    tts_config = TTSConfigFactory.create_config(tts_engine_name)
    tts_engine = _create_tts_engine_provider(tts_engine_name, tts_config)

    # Determine SSML capability and create SSML generator
    ssml_generator = None
    target_ssml_capability = SSMLCapability.NONE
    
    if enable_ssml and tts_engine:
        target_ssml_capability = _determine_ssml_capability(tts_engine)
        
        if target_ssml_capability != SSMLCapability.NONE:
            print(f"CompositionRoot: Creating SSML generator with capability: {target_ssml_capability.value}")
            
            # Choose between basic and academic SSML enhancer
            if document_type in ['research_paper', 'literature_review', 'dissertation']:
                ssml_generator = AcademicSSMLEnhancer(document_type)
                print(f"CompositionRoot: Using Academic SSML Enhancer for {document_type}")
            else:
                ssml_generator = SSMLGenerationService(target_ssml_capability)
                print(f"CompositionRoot: Using Basic SSML Generator")
        else:
            print("CompositionRoot: TTS engine doesn't support SSML, SSML generation disabled")
    else:
        print("CompositionRoot: SSML disabled via configuration")

    # Create domain services with SSML support
    text_cleaner_service = TextCleaningService(
        llm_provider=llm_provider,
        ssml_generator=ssml_generator
    )
    
    audio_generation_service = AudioGenerationService(tts_engine=tts_engine)
    
    # Log configuration summary
    _log_service_configuration(tts_engine_name, tts_config, audio_generation_service, 
                              target_ssml_capability, ssml_generator)
    
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
    """Factory function to get an instance of a TTS engine provider with SSML support"""
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
    
    # Try Piper first (best open source option with SSML support)
    try:
        from infrastructure.tts.piper_tts_provider import PIPER_AVAILABLE
        if PIPER_AVAILABLE:
            print("TTSFactory: Falling back to Piper TTS with SSML support")
            from infrastructure.tts.piper_tts_provider import PiperTTSProvider
            from application.config import PiperConfigBuilder
            fallback_config = PiperConfigBuilder.from_env()
            return PiperTTSProvider(fallback_config)
    except ImportError:
        pass
    
    # Fall back to gTTS as last resort (no SSML)
    print("TTSFactory: Falling back to gTTS (no SSML support)")
    from infrastructure.tts.gtts_provider import GTTSProvider
    from application.config import GTTSConfigBuilder
    fallback_config = GTTSConfigBuilder.from_env()
    return GTTSProvider(fallback_config)

def _determine_ssml_capability(tts_engine: ITTSEngine) -> SSMLCapability:
    """Determine the SSML capability of the TTS engine"""
    if not tts_engine:
        return SSMLCapability.NONE
    
    # Check if engine implements SSML processor interface
    if isinstance(tts_engine, ISSMLProcessor):
        capability = tts_engine.get_ssml_capability()
        print(f"CompositionRoot: TTS engine SSML capability detected: {capability.value}")
        return capability
    
    # Check if engine supports SSML via the base interface
    if hasattr(tts_engine, 'supports_ssml') and tts_engine.supports_ssml():
        print("CompositionRoot: TTS engine supports SSML (basic detection)")
        return SSMLCapability.BASIC
    
    print("CompositionRoot: TTS engine does not support SSML")
    return SSMLCapability.NONE

def _log_service_configuration(engine_name: str, config, audio_service, 
                              ssml_capability: SSMLCapability, ssml_generator):
    """Enhanced service configuration logging with SSML details"""
    print(f"CompositionRoot: TTS Engine: {engine_name}")
    print(f"CompositionRoot: Voice Quality: {config.voice_quality}")
    print(f"CompositionRoot: Speaking Style: {config.speaking_style}")
    print(f"CompositionRoot: SSML Capability: {ssml_capability.value}")
    
    # Log engine-specific config
    engine_config = getattr(config, engine_name.lower(), None)
    if engine_config:
        if hasattr(engine_config, 'model_name'):
            print(f"CompositionRoot: Model: {engine_config.model_name}")
        if hasattr(engine_config, 'voice_name'):
            print(f"CompositionRoot: Voice: {engine_config.voice_name}")
    
    # Log SSML generator details
    if ssml_generator:
        generator_type = type(ssml_generator).__name__
        print(f"CompositionRoot: SSML Generator: {generator_type}")
        
        if hasattr(ssml_generator, 'target_capability'):
            print(f"CompositionRoot: SSML Target Capability: {ssml_generator.target_capability.value}")
        
        if hasattr(ssml_generator, 'document_type'):
            print(f"CompositionRoot: Document Type: {ssml_generator.document_type}")
    else:
        print("CompositionRoot: SSML Generator: None")
    
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
    """Validate that an engine can be properly configured with SSML support"""
    try:
        config = TTSConfigFactory.create_config(engine_name)
        engine = _create_tts_engine_provider(engine_name, config)
        
        # Check SSML support
        ssml_capability = _determine_ssml_capability(engine)
        supported_tags = []
        if isinstance(engine, ISSMLProcessor):
            supported_tags = engine.get_supported_tags()
        
        return {
            'valid': True,
            'engine': engine_name,
            'config': config,
            'provider_available': engine is not None,
            'ssml_capability': ssml_capability.value,
            'supported_ssml_tags': supported_tags,
            'supports_ssml': ssml_capability != SSMLCapability.NONE
        }
    except Exception as e:
        return {
            'valid': False,
            'engine': engine_name,
            'error': str(e),
            'ssml_capability': 'none',
            'supported_ssml_tags': [],
            'supports_ssml': False
        }

def create_ssml_test_service(engine_name: str, ssml_capability: SSMLCapability) -> dict:
    """Create a test service for SSML development and debugging"""
    try:
        # Mock environment for testing
        test_env = {
            'TTS_ENGINE': engine_name,
            'ENABLE_SSML': 'True',
            'GOOGLE_AI_API_KEY': 'test_key',
            'DOCUMENT_TYPE': 'research_paper'
        }
        
        # Temporarily set environment
        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            # Create test service
            service = create_pdf_service_from_env()
            
            # Test SSML generation
            if service.text_cleaner.supports_ssml_generation():
                test_text = "However, we found a 73.2 percent increase in efficiency during 2024."
                
                ssml_result = service.text_cleaner.clean_text(
                    test_text, 
                    target_ssml_capability=ssml_capability
                )
                
                return {
                    'success': True,
                    'service_created': True,
                    'ssml_generated': len(ssml_result) > 0,
                    'sample_output': ssml_result[0] if ssml_result else '',
                    'ssml_capability': ssml_capability.value
                }
            else:
                return {
                    'success': True,
                    'service_created': True,
                    'ssml_generated': False,
                    'message': 'SSML generation not available',
                    'ssml_capability': 'none'
                }
        
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'ssml_capability': 'error'
        }

def get_ssml_configuration_guide() -> dict:
    """Get comprehensive SSML configuration guide"""
    return {
        'environment_variables': {
            'ENABLE_SSML': {
                'description': 'Enable/disable SSML generation',
                'values': ['True', 'False'],
                'default': 'True'
            },
            'DOCUMENT_TYPE': {
                'description': 'Type of academic document for specialized SSML',
                'values': ['research_paper', 'literature_review', 'dissertation', 'general'],
                'default': 'research_paper'
            },
            'TTS_ENGINE': {
                'description': 'TTS engine selection affects SSML capability',
                'values': ['piper', 'gemini', 'coqui', 'gtts', 'bark'],
                'ssml_support': {
                    'piper': 'basic',
                    'gemini': 'full', 
                    'coqui': 'basic',
                    'gtts': 'none',
                    'bark': 'none'
                }
            }
        },
        'ssml_capabilities': {
            'none': {
                'description': 'No SSML support, tags stripped',
                'engines': ['gtts', 'bark']
            },
            'basic': {
                'description': 'Basic SSML: breaks, emphasis, prosody',
                'engines': ['piper', 'coqui'],
                'features': ['break', 'emphasis', 'prosody', 'say-as']
            },
            'advanced': {
                'description': 'Advanced SSML with numbers and academic features',
                'engines': ['piper', 'coqui', 'gemini'],
                'features': ['all basic', 'advanced say-as', 'complex prosody']
            },
            'full': {
                'description': 'Complete SSML specification',
                'engines': ['gemini'],
                'features': ['all advanced', 'voice changes', 'audio insertion', 'markers']
            }
        },
        'recommended_configurations': {
            'high_quality_ssml': {
                'TTS_ENGINE': 'gemini',
                'ENABLE_SSML': 'True',
                'DOCUMENT_TYPE': 'research_paper',
                'VOICE_QUALITY': 'high'
            },
            'local_ssml': {
                'TTS_ENGINE': 'piper',
                'ENABLE_SSML': 'True',
                'PIPER_MODEL_NAME': 'en_US-lessac-high',
                'VOICE_QUALITY': 'high'
            },
            'fast_processing': {
                'TTS_ENGINE': 'coqui',
                'ENABLE_SSML': 'True',
                'VOICE_QUALITY': 'medium'
            },
            'no_ssml_fallback': {
                'TTS_ENGINE': 'gtts',
                'ENABLE_SSML': 'False',
                'VOICE_QUALITY': 'medium'
            }
        }
    }

# Development and testing helpers
def test_all_engines_ssml_support():
    """Test SSML support across all available engines"""
    engines = get_available_engines()
    results = {}
    
    for engine in engines:
        print(f"\n=== Testing {engine.upper()} SSML Support ===")
        result = validate_engine_config(engine)
        results[engine] = result
        
        if result['valid']:
            print(f"✅ {engine}: {result['ssml_capability']} SSML")
            if result['supported_ssml_tags']:
                print(f"   Supported tags: {', '.join(result['supported_ssml_tags'])}")
        else:
            print(f"❌ {engine}: {result['error']}")
    
    return results

def demo_ssml_processing():
    """Demonstrate SSML processing with sample academic content"""
    sample_text = """
    Introduction. This research demonstrates significant improvements in machine learning efficiency. 
    However, previous studies showed mixed results with 73.2 percent accuracy in 2024. 
    Furthermore, the methodology revealed important findings.
    """
    
    print("=== SSML Processing Demo ===\n")
    
    # Test with different engines and capabilities
    test_cases = [
        ('piper', SSMLCapability.BASIC),
        ('gemini', SSMLCapability.FULL),
        ('coqui', SSMLCapability.BASIC),
        ('gtts', SSMLCapability.NONE)
    ]
    
    for engine, capability in test_cases:
        print(f"\n--- {engine.upper()} with {capability.value} SSML ---")
        result = create_ssml_test_service(engine, capability)
        
        if result['success'] and result.get('sample_output'):
            output = result['sample_output']
            print(f"Input:  {sample_text.strip()}")
            print(f"Output: {output[:200]}{'...' if len(output) > 200 else ''}")
        else:
            print(f"Failed: {result.get('error', 'No SSML generated')}")

if __name__ == "__main__":
    # Run diagnostics
    print("🔍 Testing SSML Support Across All Engines")
    test_all_engines_ssml_support()
    
    print("\n🎵 Demonstrating SSML Processing")
    demo_ssml_processing()
    
    print("\n📋 SSML Configuration Guide")
    guide = get_ssml_configuration_guide()
    
    print("\nRecommended Configuration for Academic Papers:")
    for name, config in guide['recommended_configurations'].items():
        print(f"\n{name}:")
        for key, value in config.items():
            print(f"  {key}={value}")