"""
Implements the 'Ideal Path' timing strategy using a timestamp-enabled TTS engine.

This strategy assumes it is given a TTS engine that can return timing
information (word or sentence boundaries) along with the generated audio. It is
fast and accurate, making it the preferred approach.
"""

from domain.interfaces import ITimingStrategy, ITimestampedTTSEngine, IFileManager
from domain.models import TimedAudioResult, TextSegment, TimingMetadata
from domain.services.academic_ssml_service import AcademicSSMLService


class GeminiTimestampStrategy(ITimingStrategy):
    """
    A timing strategy that leverages native timestamping from a TTS engine.
    """

    def __init__(
        self,
        tts_engine: ITimestampedTTSEngine,
        ssml_service: AcademicSSMLService,
        file_manager: IFileManager,
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
        
        # FIXED: Use the correct method name
        print(f"GeminiTimestampStrategy: Enhancing {len(text_chunks)} text chunks with SSML...")
        enhanced_chunks = self.ssml_service.enhance_text_chunks(text_chunks)
        
        # Combine enhanced chunks into full SSML text
        full_ssml_text = " ".join(enhanced_chunks)

        if not full_ssml_text.strip():
            print("GeminiTimestampStrategy: No text to process after SSML enhancement")
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

        try:
            print("GeminiTimestampStrategy: Generating audio with timestamps...")
            result = self.tts_engine.generate_audio_with_timestamps(full_ssml_text)
            
            if result.is_failure:
                print(f"GeminiTimestampStrategy: Engine failed: {result.error}")
                return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
            
            audio_data, text_segments = result.value
            
            if not audio_data:
                print("GeminiTimestampStrategy: Engine returned no audio data.")
                return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)
            
            if not text_segments:
                print("GeminiTimestampStrategy: Engine returned no timing data.")
                # Still save the audio even without timing
                
            # Save the audio file
            final_audio_filename = f"{output_filename}_combined.mp3"
            final_audio_path = self.file_manager.save_output_file(
                audio_data,
                final_audio_filename
            )
            
            if not final_audio_path:
                print("GeminiTimestampStrategy: Failed to save audio file")
                return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)

            # Create timing metadata if we have segments
            timing_metadata = None
            if text_segments:
                # Calculate total duration from segments
                total_duration = max(seg.start_time + seg.duration for seg in text_segments) if text_segments else 0.0
                
                timing_metadata = TimingMetadata(
                    total_duration=total_duration,
                    text_segments=text_segments,
                    audio_files=[final_audio_filename]
                )
                
                print(f"GeminiTimestampStrategy: Generated {len(text_segments)} timed segments, total duration: {total_duration:.2f}s")
            else:
                print("GeminiTimestampStrategy: No timing segments available")

            return TimedAudioResult(
                audio_files=[final_audio_filename],
                combined_mp3=final_audio_filename,
                timing_data=timing_metadata
            )

        except Exception as e:
            print(f"GeminiTimestampStrategy: An error occurred during audio generation: {e}")
            import traceback
            traceback.print_exc()
            return TimedAudioResult(audio_files=[], combined_mp3=None, timing_data=None)