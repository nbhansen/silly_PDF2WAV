# application/composition_root.py - Updated for enhanced features
"""
Enhanced Composition Root with audiobook-quality components
"""
from typing import Optional

# Configuration and Application Service
from application.config.system_config import SystemConfig
from application.services.pdf_processing import PDFProcessingService

# Domain Interfaces and Services
from domain.interfaces import ITTSEngine, ITimingStrategy, IOCRProvider, ILLMProvider, IAudioProcessor
from domain.services.academic_ssml_service import AcademicSSMLService
from domain.services.audio_generation_service import AudioGenerationService
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.gemini_timestamp_strategy import GeminiTimestampStrategy
from domain.services.sentence_measurement_strategy import SentenceMeasurementStrategy
from domain.services.enhanced_timing_strategy import EnhancedTimingStrategy  # NEW
from domain.services.audio_generation_coordinator import AudioGenerationCoordinator
from domain.services.audio_processor import AudioProcessor

# Infrastructure Providers
from infrastructure.file.file_manager import FileManager
from infrastructure.file.cleanup_scheduler import FileCleanupScheduler
from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
from infrastructure.tts.piper_tts_provider import PiperTTSProvider


class CompositionRoot:
    """
    Enhanced composition root for audiobook-quality output
    """

    def __init__(self, config: SystemConfig):
        self.config = config

        # Core Infrastructure
        self.file_manager = FileManager(
            upload_folder=self.config.upload_folder,
            output_folder=self.config.audio_folder
        )
        self.audio_processor = AudioProcessor(config=self.config)
        self.ocr_provider = TesseractOCRProvider(config=self.config)
        self.llm_provider = self._create_llm_provider()
        self.tts_engine = self._create_enhanced_tts_engine()  # ENHANCED

        # Domain Services with enhancements
        self.text_cleaning_service = TextCleaningService(
            llm_provider=self.llm_provider,
            config=self.config
        )
        self.academic_ssml_service = AcademicSSMLService(
            tts_engine=self.tts_engine,
            document_type=self.config.document_type,
            academic_terms_config=self.config.academic_terms_config
        )

        # Enhanced Timing Strategy Selection
        self.timing_strategy = self._create_enhanced_timing_strategy()  # ENHANCED

        # Audio Generation Coordinator for async operations
        self.audio_coordinator = AudioGenerationCoordinator(
            tts_engine=self.tts_engine,
            file_manager=self.file_manager,
            audio_processor=self.audio_processor,
            max_concurrent_requests=self.config.max_concurrent_requests
        )

        self.audio_generation_service = AudioGenerationService(
            timing_strategy=self.timing_strategy,
            async_coordinator=self.audio_coordinator
        )

        # Cleanup Scheduler
        self.cleanup_scheduler = self._create_and_start_scheduler()

        # Main Application Service
        self.pdf_processing_service = PDFProcessingService(
            ocr_provider=self.ocr_provider,
            audio_generation_service=self.audio_generation_service,
            file_manager=self.file_manager,
            text_cleaner=self.text_cleaning_service,
            ssml_service=self.academic_ssml_service,
            llm_provider=self.llm_provider
        )

        print("Enhanced CompositionRoot: All services initialized with audiobook features")

    def _create_llm_provider(self) -> Optional[ILLMProvider]:
        if self.config.gemini_api_key:
            return GeminiLLMProvider(api_key=self.config.gemini_api_key)
        return None

    def _create_enhanced_tts_engine(self) -> ITTSEngine:
        """Create TTS engine with audiobook enhancements"""
        if self.config.tts_engine == self.config.tts_engine.GEMINI:
            # Use enhanced Gemini provider with multi-voice support
            print("INFO: Using Enhanced Gemini TTS with audiobook features")
            return GeminiTTSProvider(
                model_name="gemini-2.0-flash-exp",
                api_key=self.config.gemini_api_key,
                voice_personas_config=self.config.voice_personas_config
            )
        elif self.config.tts_engine == self.config.tts_engine.PIPER:
            return PiperTTSProvider(
                self.config.get_piper_config(),
                repository_url=self.config.piper_model_repository_url
            )

        raise ValueError(f"Unsupported TTS provider: {self.config.tts_engine}")

    def _create_enhanced_timing_strategy(self) -> ITimingStrategy:
        """Create timing strategy with enhanced accuracy"""

        # Check if we should use enhanced strategy
        use_enhanced = self.config.enable_enhanced_timing if hasattr(self.config, 'enable_enhanced_timing') else True

        if self.config.tts_engine == self.config.tts_engine.GEMINI:
            if use_enhanced and hasattr(self.tts_engine, 'generate_audio_with_timestamps'):
                # Use the Gemini timestamp strategy wrapper
                print("INFO: Using Enhanced Gemini Timing Strategy (Audiobook Quality)")
                return GeminiTimestampStrategy(
                    tts_engine=self.tts_engine,
                    ssml_service=self.academic_ssml_service,
                    file_manager=self.file_manager
                )
            else:
                # Fallback to enhanced estimation strategy
                print("INFO: Using Enhanced Timing Estimation Strategy")
                return EnhancedTimingStrategy(
                    tts_engine=self.tts_engine,
                    ssml_service=self.academic_ssml_service,
                    file_manager=self.file_manager
                )
        else:
            # For local TTS, use enhanced measurement strategy
            print("INFO: Using Enhanced Sentence Measurement Strategy")
            return SentenceMeasurementStrategy(
                tts_engine=self.tts_engine,
                ssml_service=self.academic_ssml_service,
                file_manager=self.file_manager,
                text_cleaning_service=self.text_cleaning_service,
                audio_processor=self.audio_processor
            )

    def _create_and_start_scheduler(self) -> Optional[FileCleanupScheduler]:
        if not self.config.enable_file_cleanup:
            print("INFO: File cleanup is disabled")
            return None

        max_file_age_seconds = int(self.config.max_file_age_hours * 3600)
        check_interval_seconds = int(self.config.auto_cleanup_interval_hours * 3600)

        scheduler = FileCleanupScheduler(
            file_manager=self.file_manager,
            max_file_age_seconds=max_file_age_seconds,
            check_interval_seconds=check_interval_seconds
        )
        scheduler.start()
        return scheduler


def create_pdf_service_from_env() -> PDFProcessingService:
    """
    Creates enhanced PDF service with audiobook features
    """
    config = SystemConfig.from_env()

    # Enable enhanced features by default
    if not hasattr(config, 'enable_enhanced_timing'):
        config.enable_enhanced_timing = True

    config.print_summary()

    root = CompositionRoot(config)
    return root.pdf_processing_service
