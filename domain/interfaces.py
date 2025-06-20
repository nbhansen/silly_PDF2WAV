"""
Defines the abstract interfaces for the application's core services.
These interfaces allow for decoupling the application logic from specific
implementations, facilitating testing and modularity.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import List, Tuple, Optional

from .models import TimedAudioResult, TextSegment
from .errors import Result


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
    def process_text(self, text: str) -> Result[str]:
        """Processes and enhances text."""
        pass
    
    @abstractmethod
    def generate_content(self, prompt: str) -> Result[str]:
        """Generates content based on a prompt."""
        pass


class IOCRProvider(ABC):
    """Interface for an Optical Character Recognition provider."""

    @abstractmethod
    def perform_ocr(self, image_path: str) -> Result[str]:
        """Performs OCR on an image and returns the extracted text."""
        pass


class ITTSEngine(ABC):
    """Interface for a Text-to-Speech engine."""

    @abstractmethod
    def generate_audio_data(self, text_to_speak: str) -> Result[bytes]:
        """
        Generates raw audio data from text.
        Returns:
            Result[bytes]: Success with audio content or failure with error.
        """
        pass


# --- New Specialised TTS Interface ---

class ITimestampedTTSEngine(ITTSEngine):
    """
    An interface for TTS engines that can return synchronization timestamps
    along with the generated audio. This is the 'ideal path'.
    """

    @abstractmethod
    def generate_audio_with_timestamps(self, text_to_speak: str) -> Result[Tuple[bytes, List[TextSegment]]]:
        """
        Generates audio and returns precise timing data from the engine.
        Args:
            text_to_speak (str): The SSML or plain text to synthesize.
        Returns:
            Result[Tuple[bytes, List[TextSegment]]]: Success with audio and timing data or failure with error.
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


# --- Phase 2 New Abstractions ---

class IAudioProcessor(ABC):
    """Interface for audio file processing operations (FFmpeg, etc.)"""
    
    @abstractmethod
    def check_ffmpeg_availability(self) -> bool:
        """Check if FFmpeg is available on the system."""
        pass
    
    @abstractmethod
    def combine_audio_files(self, audio_files: List[str], output_path: str) -> Result[str]:
        """Combine multiple audio files into a single file."""
        pass
    
    @abstractmethod
    def convert_audio_format(self, input_path: str, output_path: str, format: str) -> Result[str]:
        """Convert audio file to specified format."""
        pass
    
    @abstractmethod
    def get_audio_duration(self, audio_path: str) -> Result[float]:
        """Get duration of audio file in seconds."""
        pass


class ITimingCalculator(ABC):
    """Interface for calculating audio timing and duration estimation"""
    
    @abstractmethod
    def estimate_text_duration(self, text: str, engine_type: str) -> float:
        """Estimate duration for text based on engine characteristics."""
        pass
    
    @abstractmethod
    def calculate_phoneme_duration(self, text: str) -> float:
        """Calculate duration based on phoneme analysis."""
        pass
    
    @abstractmethod
    def add_punctuation_pauses(self, text: str) -> float:
        """Calculate additional time for punctuation pauses."""
        pass


class IEngineCapabilityDetector(ABC):
    """Interface for detecting TTS engine capabilities"""
    
    @abstractmethod
    def detect_ssml_capability(self, engine: ITTSEngine) -> SSMLCapability:
        """Detect SSML capability level of an engine."""
        pass
    
    @abstractmethod
    def supports_timestamps(self, engine: ITTSEngine) -> bool:
        """Check if engine supports native timestamp generation."""
        pass
    
    @abstractmethod
    def get_recommended_rate_limit(self, engine: ITTSEngine) -> float:
        """Get recommended rate limiting delay for engine."""
        pass
    
    @abstractmethod
    def requires_async_processing(self, engine: ITTSEngine) -> bool:
        """Determine if engine should use async processing."""
        pass
