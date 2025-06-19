"""
The Composition Root of the application, responsible for creating and
wiring together all the necessary objects and services.
"""
from typing import Optional

# Configuration and Application Service
from application.config.system_config import SystemConfig
from application.services.pdf_processing import PDFProcessingService

# Domain Interfaces and Services
from domain.interfaces import ITTSEngine, ITimingStrategy, IOCRProvider, ILLMProvider
from domain.services.academic_ssml_service import AcademicSSMLService
from domain.services.audio_generation_service import AudioGenerationService
from domain.services.text_cleaning_service import TextCleaningService
from domain.services.gemini_timestamp_strategy import GeminiTimestampStrategy
from domain.services.sentence_measurement_strategy import SentenceMeasurementStrategy

# Infrastructure Providers - Direct and explicit imports
from infrastructure.file.file_manager import FileManager
from infrastructure.file.cleanup_scheduler import FileCleanupScheduler
from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
from infrastructure.tts.piper_tts_provider import PiperTTSProvider

class CompositionRoot:
    """
    Manages the object graph and dependencies for the application.
    """
    def __init__(self, config: SystemConfig):
        self.config = config
        
        # --- 1. Instantiate Core Infrastructure ---
        self.file_manager = FileManager(
            upload_folder=self.config.upload_folder,
            output_folder=self.config.audio_folder
        )
        self.ocr_provider = TesseractOCRProvider()
        self.llm_provider = self._create_llm_provider()
        self.tts_engine = self._create_tts_engine()

        # --- 2. Instantiate Core Domain Services ---
        self.text_cleaning_service = TextCleaningService()
        self.academic_ssml_service = AcademicSSMLService()

        # --- 3. Instantiate Timing Strategy & Dependent Service ---
        self.timing_strategy = self._create_timing_strategy()
        self.audio_generation_service = AudioGenerationService(self.timing_strategy)

        # --- 4. Instantiate and Start Cleanup Scheduler (if enabled) ---
        self.cleanup_scheduler = self._create_and_start_scheduler()

        # --- 5. Instantiate the Main Application Service ---
        self.pdf_processing_service = PDFProcessingService(
            ocr_provider=self.ocr_provider,
            audio_generation_service=self.audio_generation_service,
            file_manager=self.file_manager,
            text_cleaner=self.text_cleaning_service,
            ssml_service=self.academic_ssml_service,
            llm_provider=self.llm_provider
        )
        print("CompositionRoot: All services instantiated successfully.")

    def _create_llm_provider(self) -> Optional[ILLMProvider]:
        if self.config.gemini_api_key:
            return GeminiLLMProvider(api_key=self.config.gemini_api_key)
        return None

    def _create_tts_engine(self) -> ITTSEngine:
        if self.config.tts_engine == self.config.tts_engine.GEMINI:
            return GeminiTTSProvider(
                model_name=self.config.gemini_voice_name,
                api_key=self.config.gemini_api_key
            )
        elif self.config.tts_engine == self.config.tts_engine.PIPER:
            # Note: Your PiperTTSProvider may need adjustment to accept these params
            return PiperTTSProvider(model_path=self.config.piper_model_name)
        raise ValueError(f"Unsupported TTS provider: {self.config.tts_engine}")

    def _create_timing_strategy(self) -> ITimingStrategy:
        if self.config.tts_engine == self.config.tts_engine.GEMINI:
            print("INFO: Using GeminiTimestampStrategy (Ideal Path)")
            return GeminiTimestampStrategy(
                tts_engine=self.tts_engine,
                ssml_service=self.academic_ssml_service,
                file_manager=self.file_manager
            )
        else:
            print("INFO: Using SentenceMeasurementStrategy (Pragmatic Path)")
            return SentenceMeasurementStrategy(
                tts_engine=self.tts_engine,
                ssml_service=self.academic_ssml_service,
                file_manager=self.file_manager,
                text_cleaning_service=self.text_cleaning_service
            )
            
    def _create_and_start_scheduler(self) -> Optional[FileCleanupScheduler]:
        if not self.config.enable_file_cleanup:
            print("INFO: File cleanup is disabled by configuration.")
            return None
            
        max_age_seconds = int(self.config.max_file_age_hours * 3600)
        interval_seconds = int(self.config.auto_cleanup_interval_hours * 3600)
        
        scheduler = FileCleanupScheduler(
            file_manager=self.file_manager,
            max_file_age_seconds=max_age_seconds,
            check_interval_seconds=interval_seconds
        )
        scheduler.start()
        return scheduler

def create_pdf_service_from_env() -> PDFProcessingService:
    """
    Creates and returns a fully configured PDFProcessingService based on
    environment variables and the application's configuration.
    """
    config = SystemConfig.from_env()
    config.print_summary()
    
    root = CompositionRoot(config)
    return root.pdf_processing_service
