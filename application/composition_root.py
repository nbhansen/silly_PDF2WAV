"""
The Composition Root of the application, responsible for creating and
wiring together all the necessary objects and services.
"""

from application.config.system_config import SystemConfig
from domain.interfaces import ITTSEngine, ITimingStrategy
from domain.services.academic_ssml_service import AcademicSSMLService
from domain.services.audio_generation_service import AudioGenerationService
from domain.services.text_cleaning_service import TextCleaningService
from infrastructure.file.file_manager import FileManager
from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
from infrastructure.tts.piper_tts_provider import PiperTTSProvider

# --- Import the new strategy implementations ---
# NOTE: These files will need to be created.
from domain.services.gemini_timestamp_strategy import GeminiTimestampStrategy
from domain.services.sentence_measurement_strategy import SentenceMeasurementStrategy


class CompositionRoot:
    """
    Manages the object graph and dependencies for the application.
    """
    def __init__(self, config: SystemConfig):
        self.config = config
        self.file_manager = FileManager(
            upload_folder=self.config.get('UPLOAD_FOLDER'),
            output_folder=self.config.get('OUTPUT_FOLDER')
        )
        self.text_cleaning_service = TextCleaningService()
        self.academic_ssml_service = AcademicSSMLService()

        # 1. Create the appropriate TTS Engine based on config
        self.tts_engine = self._create_tts_engine()

        # 2. Create the appropriate Timing Strategy based on config and engine type
        self.timing_strategy = self._create_timing_strategy(self.tts_engine)

        # 3. Inject the chosen strategy into the AudioGenerationService
        self.audio_generation_service = AudioGenerationService(
            timing_strategy=self.timing_strategy
        )

    def _create_tts_engine(self) -> ITTSEngine:
        """Factory method to create a TTS engine instance based on configuration."""
        provider = self.config.get("TTS_PROVIDER", "piper").lower()
        if provider == "gemini":
            return GeminiTTSProvider(
                model_name=self.config.get("GEMINI_TTS_MODEL"),
                api_key=self.config.get("GOOGLE_API_KEY")
            )
        elif provider == "piper":
            return PiperTTSProvider(
                model_path=self.config.get("PIPER_MODEL_PATH")
            )
        else:
            raise ValueError(f"Unsupported TTS provider: {provider}")

    def _create_timing_strategy(self, tts_engine: ITTSEngine) -> ITimingStrategy:
        """
        Factory method to select and create the correct timing strategy.

        This is the core of the Strategy Pattern implementation. It decides
        whether to use the 'ideal path' (native timestamps) or the 'pragmatic path'
        (manual measurement).
        """
        provider = self.config.get("TTS_PROVIDER", "piper").lower()

        # IDEAL PATH: If using Gemini, use the strategy that gets
        # timestamps directly from the API.
        if provider == "gemini":
            print("INFO: Using GeminiTimestampStrategy (Ideal Path)")
            return GeminiTimestampStrategy(
                tts_engine=tts_engine,
                ssml_service=self.academic_ssml_service,
                file_manager=self.file_manager
            )

        # PRAGMATIC PATH: For Piper or any other engine, use the fallback
        # strategy that generates audio per sentence and measures duration.
        else:
            print("INFO: Using SentenceMeasurementStrategy (Pragmatic Path)")
            return SentenceMeasurementStrategy(
                tts_engine=tts_engine,
                ssml_service=self.academic_ssml_service,
                file_manager=self.file_manager,
                text_cleaning_service=self.text_cleaning_service
            )

