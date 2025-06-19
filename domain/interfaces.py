"""
Defines the abstract interfaces for the application's core services.
These interfaces allow for decoupling the application logic from specific
implementations, facilitating testing and modularity.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple
from .models import TimedAudioResult, TextSegment

# --- Core Service Interfaces ---

class ILLMProvider(ABC):
    """Interface for a Large Language Model provider."""
    @abstractmethod
    def process_text(self, text: str) -> str:
        """Processes and enhances text."""
        pass

class IOCRProvider(ABC):
    """Interface for an Optical Character Recognition provider."""
    @abstractmethod
    def perform_ocr(self, image_path: str) -> str:
        """Performs OCR on an image and returns the extracted text."""
        pass

class ITTSEngine(ABC):
    """Interface for a Text-to-Speech engine."""
    @abstractmethod
    def generate_audio_data(self, text_to_speak: str) -> bytes:
        """
        Generates raw audio data from text.
        Returns:
            bytes: The raw audio content.
        """
        pass

# --- New Specialised TTS Interface ---

class ITimestampedTTSEngine(ITTSEngine):
    """
    An interface for TTS engines that can return synchronization timestamps
    along with the generated audio. This is the 'ideal path'.
    """
    @abstractmethod
    def generate_audio_with_timestamps(self, text_to_speak: str) -> Tuple[bytes, List[TextSegment]]:
        """
        Generates audio and returns precise timing data from the engine.
        Args:
            text_to_speak (str): The SSML or plain text to synthesize.
        Returns:
            A tuple containing:
            - bytes: The raw audio content.
            - List[TextSegment]: A list of text segments with precise start
                                 and duration times provided by the engine.
        """
        pass


# --- New Timing Strategy Interface ---

class ITimingStrategy(ABC):
    """
    Interface for a strategy that generates a timed audio result.
    This encapsulates the logic for how timing information is derived,
    whether from the TTS engine directly or through manual measurement.
    """
    @abstractmethod
    def generate_with_timing(self, text_chunks: list[str], output_filename: str) -> TimedAudioResult:
        """
        Generates a complete audio file and a corresponding TimedAudioResult
        object with precise timing information for each segment.

        Args:
            text_chunks (list[str]): A list of text chunks to be synthesized.
            output_filename (str): The path to save the final combined audio file.

        Returns:
            TimedAudioResult: An object containing the path to the final audio
                              and a list of timed text segments.
        """
        pass
