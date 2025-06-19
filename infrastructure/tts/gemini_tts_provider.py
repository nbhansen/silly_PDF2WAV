"""
Provides Text-to-Speech services using the Google Gemini API.
This implementation is capable of returning timing information (timestamps)
for generated audio, making it suitable for the 'ideal path' strategy.
"""

from typing import List, Tuple, Optional
import google.generativeai as genai

# Correctly import the new interface and domain models
from domain.interfaces import ITimestampedTTSEngine
from domain.models import TextSegment
from domain.services.text_cleaning_service import TextCleaningService

class GeminiTTSProvider(ITimestampedTTSEngine):
    """
    An implementation of the ITTSEngine that uses Google's generative AI
    for text-to-speech conversion and supports fetching timestamps.
    """

    def __init__(self, model_name: str, api_key: Optional[str] = None):
        if not api_key:
            raise ValueError("Google API key is required for GeminiTTSProvider.")
        
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.text_cleaner = TextCleaningService() # To strip SSML for display text
        print(f"GeminiTTSProvider initialized with model: {self.model_name}")

    def generate_audio_data(self, text_to_speak: str) -> bytes:
        """
        Generates audio for the given text without timing information.
        This method fulfills the basic ITTSEngine interface.
        """
        print(f"GeminiTTSProvider: Generating audio data (no timestamps).")
        try:
            # The API call for simple audio generation
            response = genai.text_to_speech(
                model=self.model_name,
                text=text_to_speak,
            )
            return response['audio_content']
        except Exception as e:
            print(f"Error in Gemini TTS (generate_audio_data): {e}")
            raise  # Re-raise the exception to be handled by the caller

    def generate_audio_with_timestamps(self, text_to_speak: str) -> Tuple[bytes, List[TextSegment]]:
        """
        Generates audio and returns a list of timed text segments.
        This method fulfills the ITimestampedTTSEngine interface and is the
        core of the 'ideal path' strategy.
        """
        print(f"GeminiTTSProvider: Generating audio WITH timestamps.")
        
        # The API documentation specifies using `SynthesizeTextRequest` to get timepoints
        # As of the latest google-generativeai library, this is done via a flag.
        try:
            response = genai.text_to_speech(
                model=self.model_name,
                text=text_to_speak,
                # This is the crucial flag to get timing information
                request_options={"enable_time_pointing": ["SSML_MARK"]}
            )

            audio_content = response['audio_content']
            timepoints = response['timepoints']
            
            if not audio_content or not timepoints:
                print("GeminiTTSProvider Warning: API response was missing audio or timepoints.")
                return b'', []

            # Process the raw timepoints from the API into our domain model
            text_segments = self._create_segments_from_timepoints(timepoints)

            print(f"GeminiTTSProvider: Successfully generated {len(text_segments)} timed segments.")
            return audio_content, text_segments

        except Exception as e:
            print(f"Error in Gemini TTS (generate_audio_with_timestamps): {e}")
            raise

    def _create_segments_from_timepoints(self, timepoints: list) -> List[TextSegment]:
        """
        Converts the timepoint data from the Gemini API into a list of TextSegment objects.
        
        The Gemini API returns timepoints for SSML <mark> tags. We must have injected
        these marks around our sentences for this to work.
        """
        segments = []
        
        # The timepoints list contains dicts like:
        # [{'mark_name': 's_0', 'time_seconds': 0.123}, {'mark_name': 's_1', 'time_seconds': 2.456}, ...]
        # We need to calculate duration between marks.
        
        if len(timepoints) < 2:
            # Cannot calculate duration with fewer than two points.
            # This can happen if there's only one sentence. We estimate the duration.
            if timepoints:
                # A rough estimate for a single segment
                # We need the original text to do this better, but this is a simple fallback.
                segment = TextSegment(
                    text=timepoints[0]['mark_name'], # The mark name is the sentence text
                    start_time=0.0,
                    duration=3.0 # A default guess
                )
                segments.append(segment)
            return segments

        # Sort timepoints just in case the API doesn't guarantee order
        sorted_timepoints = sorted(timepoints, key=lambda x: x['time_seconds'])

        for i in range(len(sorted_timepoints) - 1):
            current_mark = sorted_timepoints[i]
            next_mark = sorted_timepoints[i+1]
            
            start_time = current_mark['time_seconds']
            duration = next_mark['time_seconds'] - start_time
            
            # We assume the 'mark_name' holds the sentence text we want to display
            display_text = self.text_cleaner.strip_ssml(current_mark['mark_name'])

            segment = TextSegment(
                text=display_text,
                start_time=start_time,
                duration=duration
            )
            segments.append(segment)

        # We need to handle the very last segment, as it has no 'next' mark
        # We estimate its duration based on the audio length, but for now we give it an average
        if segments:
            last_segment = segments[-1]
            avg_duration = sum(s.duration for s in segments) / len(segments)
            
            # The last timepoint from the API
            final_mark = sorted_timepoints[-1]
            final_display_text = self.text_cleaner.strip_ssml(final_mark['mark_name'])

            final_segment = TextSegment(
                text=final_display_text,
                start_time=final_mark['time_seconds'],
                duration=avg_duration # Estimate duration for the last segment
            )
            segments.append(final_segment)


        return segments

