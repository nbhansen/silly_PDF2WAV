"""
Defines the abstract interfaces for the application's core services.
These interfaces allow for decoupling the application logic from specific
implementations, facilitating testing and modularity.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import List, Tuple

from .models import TimedAudioResult, TextSegment


class SSMLCapability(Enum):
    """Defines the SSML capability levels an engine might support."""
    NONE = auto()       # No SSML support - plain text only
    BASIC = auto()      # Basic SSML tags (break, emphasis)
    ADVANCED = auto()   # Advanced SSML (prosody, say-as, marks)
    FULL = auto()       # Full SSML support including all features


# --- Core Service Interfaces ---

class IPageRangeValidator(ABC):
    """Interface for validating page ranges."""
    @abstractmethod
    def validate(self, pages_str: str, max_pages: int) -> List[int]:
        """Validates a string of page numbers/ranges."""
        pass


class ITextExtractor(ABC):
    """Interface for a service that extracts text from a source."""
    @abstractmethod
    def extract_text(self, filepath: str) -> List[str]:
        """Extracts and returns text chunks from a file."""
        pass


class IFileManager(ABC):
    """Interface for managing file operations and paths."""

    @abstractmethod
    def save_temp_file(self, content: bytes, suffix: str = ".tmp") -> str:
        """Saves content to a temporary file and returns its path."""
        pass

    @abstractmethod
    def save_output_file(self, content: bytes, filename: str) -> str:
        """Saves content to a final output file and returns its path."""
        pass

    @abstractmethod
    def delete_file(self, filepath: str) -> None:
        """Deletes a file at the given path."""
        pass

    @abstractmethod
    def get_output_dir(self) -> str:
        """Returns the path to the output directory."""
        pass


class ITextCleaner(ABC):
    """Interface for a text cleaning and preparation service."""

    @abstractmethod
    def strip_ssml(self, ssml_text: str) -> str:
        """Removes all SSML tags from a string."""
        pass

    @abstractmethod
    def split_into_sentences(self, text: str) -> List[str]:
        """Splits a block of text into a list of sentences."""
        pass


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
