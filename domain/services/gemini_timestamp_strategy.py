"""
Implements the 'Ideal Path' timing strategy using a timestamp-enabled TTS engine.

This strategy assumes it is given a TTS engine that can return timing
information (word or sentence boundaries) along with the generated audio. It is
fast and accurate, making it the preferred approach.
"""

from domain.interfaces import ITimingStrategy, ITimestampedTTSEngine
from domain.models import TimedAudioResult, TextSegment
from domain.services.academic_ssml_service import AcademicSSMLService

# --- Fix: Import the module, not the class, to avoid circular dependency ---
from infrastructure.file import file_manager


class GeminiTimestampStrategy(ITimingStrategy):
    """
    A timing strategy that leverages native timestamping from a TTS engine.
    """

    def __init__(
        self,
        tts_engine: ITimestampedTTSEngine,
        ssml_service: AcademicSSMLService,
        file_manager, # Type hint removed to simplify import resolution
    ):
        if not hasattr(tts_engine, 'generate_audio_with_timestamps'):
            raise TypeError("The provided tts_engine does not support the required ITimestampedTTSEngine interface.")
            
        self.tts_engine = tts_engine
        self.ssml_service = ssml_service
        self.file_manager = file_manager

    def generate_with_timing(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """
        Generates audio and gets timing data in a single call to the TTS engine.
        """
        print("GeminiTimestampStrategy: Using ideal path with direct engine timestamping.")
        
        full_ssml_text = " ".join(self.ssml_service.add_ssml(chunk) for chunk in text_chunks)

        if not full_ssml_text.strip():
            return TimedAudioResult(audio_path=None, segments=[])

        try:
            audio_data, text_segments = self.tts_engine.generate_audio_with_timestamps(full_ssml_text)
            
            if not audio_data or not text_segments:
                print("GeminiTimestampStrategy: Engine returned no audio or timing data.")
                return TimedAudioResult(audio_path=None, segments=[])

            final_audio_path = self.file_manager.save_output_file(
                audio_data,
                f"{output_filename}.mp3"
            )

            print(f"GeminiTimestampStrategy: Finished. Generated {len(text_segments)} segments.")
            return TimedAudioResult(audio_path=final_audio_path, segments=text_segments)

        except Exception as e:
            print(f"GeminiTimestampStrategy: An error occurred during audio generation: {e}")
            return TimedAudioResult(audio_path=None, segments=[])
