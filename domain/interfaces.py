"""Defines the abstract interfaces for the application's core services.
These interfaces allow for decoupling the application logic from specific
implementations, facilitating testing and modularity.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Optional

from .errors import Result
from .models import PageRange, PDFInfo, TextSegment


class SSMLCapability(Enum):
    """Defines the SSML capability levels an engine might support."""

    NONE = auto()  # No SSML support - plain text only
    BASIC = auto()  # Basic SSML tags (break, emphasis)
    ADVANCED = auto()  # Advanced SSML (prosody, say-as, marks)
    FULL = auto()  # Full SSML support including all features


# --- Core Service Interfaces ---


class IDocumentProcessor(ABC):
    """Consolidated interface for document text processing operations."""

    @abstractmethod
    def extract_text(self, filepath: str, pages: Optional[list[int]] = None) -> list[str]:
        """Extract text from document with optional page filtering."""

    @abstractmethod
    def validate_page_range(self, filepath: str, start: Optional[int], end: Optional[int]) -> dict[str, Any]:
        """Validate page range against document."""


class ITextProcessor(ABC):
    """Consolidated interface for text cleaning and preparation."""

    @abstractmethod
    def clean_text(self, raw_text: str) -> str:
        """Clean and prepare text for TTS."""

    @abstractmethod
    def enhance_with_ssml(self, text: str) -> str:
        """Add SSML enhancements to text."""

    @abstractmethod
    def split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences for processing."""

    @abstractmethod
    def strip_ssml(self, text: str) -> str:
        """Remove SSML tags from text."""


class IFileManager(ABC):
    """Interface for managing file operations and paths."""

    @abstractmethod
    def save_temp_file(self, content: bytes, suffix: str = ".tmp") -> str:
        """Saves content to a temporary file and returns its path."""

    @abstractmethod
    def save_output_file(self, content: bytes, filename: str) -> str:
        """Saves content to a final output file and returns its path."""

    @abstractmethod
    def delete_file(self, filepath: str) -> None:
        """Deletes a file at the given path."""

    @abstractmethod
    def get_output_dir(self) -> str:
        """Returns the path to the output directory."""


class ILLMProvider(ABC):
    """Interface for a Large Language Model provider."""

    @abstractmethod
    def process_text(self, text: str) -> Result[str]:
        """Processes and enhances text."""

    @abstractmethod
    def generate_content(self, prompt: str) -> Result[str]:
        """Generates content based on a prompt."""

    @abstractmethod
    async def generate_content_async(self, prompt: str) -> Result[str]:
        """Generates content based on a prompt asynchronously.
        For providers that don't support native async, this can wrap the sync method.
        """


class IOCRProvider(ABC):
    """Interface for an Optical Character Recognition provider."""

    @abstractmethod
    def perform_ocr(self, image_path: str) -> Result[str]:
        """Performs OCR on an image and returns the extracted text."""

    @abstractmethod
    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        """Get PDF document information including page count and metadata."""

    @abstractmethod
    def validate_range(self, pdf_path: str, page_range: PageRange) -> dict[str, Any]:
        """Validate page range against PDF document."""


class ITTSEngine(ABC):
    """Interface for a Text-to-Speech engine."""

    @abstractmethod
    def generate_audio_data(self, text_to_speak: str) -> Result[bytes]:
        """Generates raw audio data from text.

        Returns:
            Result[bytes]: Success with audio content or failure with error.
        """

    @abstractmethod
    async def generate_audio_data_async(self, text_to_speak: str) -> Result[bytes]:
        """Generates raw audio data from text asynchronously.
        For engines that don't support native async, this can wrap the sync method.

        Returns:
            Result[bytes]: Success with audio content or failure with error.
        """

    @abstractmethod
    def supports_ssml(self) -> bool:
        """Check if this TTS engine supports SSML markup."""


# --- Enhanced TTS Interface ---


class IEnhancedTTSEngine(ITTSEngine):
    """Enhanced TTS interface that consolidates audio processing capabilities.
    Replaces separate IAudioProcessor and IEngineCapabilityDetector interfaces.
    """

    @abstractmethod
    def supports_ssml(self) -> bool:
        """Check if engine supports SSML."""

    @abstractmethod
    def get_ssml_capability(self) -> SSMLCapability:
        """Get SSML capability level."""

    @abstractmethod
    def supports_timestamps(self) -> bool:
        """Check if engine supports native timestamp generation."""

    @abstractmethod
    def get_audio_format(self) -> str:
        """Get preferred audio output format."""

    @abstractmethod
    def requires_rate_limiting(self) -> bool:
        """Check if engine requires rate limiting."""

    @abstractmethod
    def get_recommended_delay(self) -> float:
        """Get recommended delay between requests."""


# --- Specialized TTS Interface ---


class ITimestampedTTSEngine(ITTSEngine):
    """An interface for TTS engines that can return synchronization timestamps
    along with the generated audio. This is the 'ideal path'.
    """

    @abstractmethod
    def generate_audio_with_timestamps(self, text_to_speak: str) -> Result[tuple[bytes, list[TextSegment]]]:
        """Generates audio and returns precise timing data from the engine.

        Args:
            text_to_speak (str): The SSML or plain text to synthesize.

        Returns:
            Result[Tuple[bytes, List[TextSegment]]]: Success with audio and timing data or failure with error.
        """


# --- Legacy interfaces removed during refactor ---
# ITimingStrategy was consolidated into TimingEngine


# --- Phase 2 New Abstractions ---


class IAudioProcessor(ABC):
    """Interface for audio file processing operations (FFmpeg, etc.)."""

    @abstractmethod
    def check_ffmpeg_availability(self) -> bool:
        """Check if FFmpeg is available on the system."""

    @abstractmethod
    def combine_audio_files(self, audio_files: list[str], output_path: str) -> Result[str]:
        """Combine multiple audio files into a single file."""

    @abstractmethod
    def convert_audio_format(self, input_path: str, output_path: str, format: str) -> Result[str]:
        """Convert audio file to specified format."""

    @abstractmethod
    def get_audio_duration(self, audio_path: str) -> Result[float]:
        """Get duration of audio file in seconds."""


# ITimingCalculator was consolidated into TimingEngine


class IEngineCapabilityDetector(ABC):
    """Interface for detecting TTS engine capabilities."""

    @abstractmethod
    def detect_ssml_capability(self, engine: ITTSEngine) -> SSMLCapability:
        """Detect SSML capability level of an engine."""

    @abstractmethod
    def supports_timestamps(self, engine: ITTSEngine) -> bool:
        """Check if engine supports native timestamp generation."""

    @abstractmethod
    def get_recommended_rate_limit(self, engine: ITTSEngine) -> float:
        """Get recommended rate limiting delay for engine."""

    @abstractmethod
    def requires_async_processing(self, engine: ITTSEngine) -> bool:
        """Determine if engine should use async processing."""
