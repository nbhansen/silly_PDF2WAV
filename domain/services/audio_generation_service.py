"""
This service orchestrates the process of generating audio from text chunks
by using a configured timing strategy.
"""

from ..interfaces import ITimingStrategy
from ..models import TimedAudioResult

class AudioGenerationService:
    """
    A service that generates audio with timing information by delegating
    to a provided timing strategy. This class acts as the 'Context' in the
    Strategy design pattern.
    """

    def __init__(self, timing_strategy: ITimingStrategy):
        """
        Initializes the AudioGenerationService with a specific timing strategy.

        Args:
            timing_strategy (ITimingStrategy): An object that implements the
                                               ITimingStrategy interface. This
                                               strategy will be used to generate
                                               the audio and timing data.
        """
        if not isinstance(timing_strategy, ITimingStrategy):
            raise TypeError("timing_strategy must be an instance of ITimingStrategy")
        self.timing_strategy = timing_strategy

    def generate_audio_with_timing(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """
        Generates an audio file with corresponding timing data for text chunks.

        This method delegates the entire process to the configured ITimingStrategy
        object.

        Args:
            text_chunks (list[str]): The list of text chunks to convert to speech.
            output_filename (str): The desired path for the final output audio file.

        Returns:
            TimedAudioResult: An object containing the path to the generated
                              audio file and a list of timed TextSegments.
        """
        # Delegate the call directly to the strategy object
        return self.timing_strategy.generate_with_timing(text_chunks, output_filename)
