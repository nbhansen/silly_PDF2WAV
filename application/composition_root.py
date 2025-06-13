# application/composition_root.py
from application.config.system_config import SystemConfig, TTSEngine
from application.services.pdf_processing import PDFProcessingService
from domain.interfaces import ITTSEngine, ILLMProvider, FileManager
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from infrastructure.file.file_manager import LocalFileManager
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.audio_generation_service import AudioGenerationService

def create_pdf_service_from_env() -> PDFProcessingService:
    """
    Main entry point: Create PDF service with file management
    """
    try:
        # Load and validate configuration from environment
        config = SystemConfig.from_env()
        config.print_summary()
        
        # Create file manager first (Infrastructure → Domain interface)
        file_manager = _create_file_manager(config)
        
        # Create providers
        text_extractor = TesseractOCRProvider()
        llm_provider = _create_llm_provider(config)
        tts_engine = _create_tts_engine(config)
        
        # Create domain services (Domain services get Domain interfaces)
        text_cleaner = TextCleaningService(
            llm_provider=llm_provider if config.enable_text_cleaning else None
        )
        
        audio_generator = AudioGenerationService(
            tts_engine=tts_engine,
            file_manager=file_manager  # Domain interface injection ✅
        )
        
        # Assemble the application service (Application service gets Domain interfaces)
        service = PDFProcessingService(
            text_extractor=text_extractor,
            text_cleaner=text_cleaner,
            audio_generator=audio_generator,
            page_validator=text_extractor,
            llm_provider=llm_provider,
            tts_engine=tts_engine,
            file_manager=file_manager,  # Domain interface injection ✅
            enable_ssml=config.enable_ssml,
            document_type=config.document_type
        )
        
        return service
        
    except ValueError as e:
        print(f"CONFIGURATION ERROR: {e}")
        print("\nPlease check your environment variables and try again.")
        raise
    except Exception as e:
        print(f"SERVICE INITIALIZATION ERROR: {e}")
        raise

def _create_file_manager(config: SystemConfig) -> FileManager:
    """Create file manager with initial cleanup (Infrastructure creation)"""
    
    # Create Infrastructure implementation
    file_manager = LocalFileManager(config.audio_folder)
    
    if config.enable_file_cleanup:
        print(f"FileManager: Cleanup enabled (max age: {config.max_file_age_hours}h, max size: {config.max_disk_usage_mb}MB)")
        
        # Run initial cleanup to clear any old files
        try:
            result = file_manager.cleanup_old_files(config.max_file_age_hours)
            if result.files_removed > 0:
                print(f"FileManager: Initial cleanup removed {result.files_removed} files ({result.mb_freed:.1f} MB)")
            
            # Show current stats
            stats = file_manager.get_stats()
            print(f"FileManager: Currently managing {stats['total_files']} files ({stats['total_size_mb']:.1f} MB)")
            
        except Exception as e:
            print(f"FileManager: Initial cleanup failed: {e}")
    else:
        print("FileManager: Auto-cleanup disabled")
    
    return file_manager  # Return as Domain interface

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
        raise ValueError(f"Unsupported TTS engine: {config.tts_engine}")

def _create_llm_provider(config: SystemConfig) -> ILLMProvider:
    """Create LLM provider if API key is available"""
    
    if config.gemini_api_key and config.gemini_api_key != "YOUR_GOOGLE_AI_API_KEY":
        print("Creating Gemini LLM provider for text cleaning...")
        return GeminiLLMProvider(config.gemini_api_key)
    else:
        print("No LLM provider available (Gemini API key not set)")
        return None

# Keep these for backwards compatibility
def validate_engine_config(engine_name: str) -> dict:
    """Quick validation helper"""
    try:
        import os
        old_engine = os.getenv('TTS_ENGINE')
        os.environ['TTS_ENGINE'] = engine_name
        
        try:
            config = SystemConfig.from_env()
            tts_engine = _create_tts_engine(config)
            file_manager = _create_file_manager(config)
            
            return {
                'valid': True,
                'engine': engine_name,
                'available': True,
                'file_management': file_manager is not None
            }
        finally:
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