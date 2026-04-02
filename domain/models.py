# domain/models.py
"""Domain models using Result[T] pattern for type-safe error handling."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .errors import ApplicationError, Result, invalid_page_range_error

# --- Core Domain Models with Result[T] Pattern ---


@dataclass(frozen=True)
class PageRange:
    """Range specification for document page processing."""

    start_page: Optional[int] = None
    end_page: Optional[int] = None

    def is_full_document(self) -> bool:
        """Return True if this range covers the entire document."""
        return self.start_page is None and self.end_page is None

    def validate_against_document(self, total_pages: int) -> Result[None]:
        """Validate page range against actual document."""
        if total_pages < 1:
            return Result.failure(invalid_page_range_error("Document must have at least 1 page"))

        if self.start_page is not None and self.start_page > total_pages:
            return Result.failure(
                invalid_page_range_error(f"start_page {self.start_page} exceeds document pages ({total_pages})")
            )

        if self.end_page is not None and self.end_page > total_pages:
            return Result.failure(
                invalid_page_range_error(f"end_page {self.end_page} exceeds document pages ({total_pages})")
            )

        return Result.success(None)


@dataclass(frozen=True)
class ProcessingRequest:
    """Request specification for PDF processing operations."""

    pdf_path: str
    output_name: str
    page_range: PageRange


@dataclass(frozen=True)
class PDFInfo:
    """Information about a PDF document."""

    total_pages: int
    title: str
    author: str


@dataclass(frozen=True)
class ProcessingResult:
    """Result of PDF processing operation with structured error handling."""

    audio_files: Optional[list[str]] = None
    combined_mp3_file: Optional[str] = None
    timing_data: Optional["TimingMetadata"] = None
    debug_info: Optional[dict[str, Any]] = None
    error: Optional[ApplicationError] = None

    @property
    def success(self) -> bool:
        """Check if processing was successful."""
        return self.error is None

    @property
    def is_retryable(self) -> bool:
        """Check if the error (if any) is retryable."""
        return self.error is not None and self.error.retryable

    @classmethod
    def success_result(
        cls,
        audio_files: list[str],
        combined_mp3: Optional[str] = None,
        timing_data: Optional["TimingMetadata"] = None,
        debug_info: Optional[dict[str, Any]] = None,
    ) -> "ProcessingResult":
        """Create a successful processing result."""
        return cls(
            audio_files=audio_files.copy() if audio_files is not None else None,  # Create defensive copy
            combined_mp3_file=combined_mp3,
            timing_data=timing_data,
            debug_info=debug_info.copy() if debug_info is not None else None,  # Create defensive copy
            error=None,
        )

    @classmethod
    def failure_result(cls, error: ApplicationError) -> "ProcessingResult":
        """Create a failed processing result."""
        return cls(audio_files=None, combined_mp3_file=None, timing_data=None, debug_info=None, error=error)

    def get_error_message(self) -> str:
        """Get a user-friendly error message."""
        if self.error:
            return str(self.error)
        return "No error"

    def get_error_code(self) -> Optional[str]:
        """Get the error code for logging/debugging."""
        if self.error:
            return self.error.code.value
        return None


@dataclass(frozen=True)
class FileInfo:
    """Information about a managed file."""

    filename: str
    full_path: str
    size_bytes: int
    created_at: datetime
    last_accessed: Optional[datetime] = None

    @property
    def size_mb(self) -> float:
        """Return file size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    @property
    def age_hours(self) -> float:
        """Return file age in hours."""
        return (datetime.now() - self.created_at).total_seconds() / 3600


@dataclass(frozen=True)
class CleanupResult:
    """Result of a cleanup operation."""

    files_removed: int
    bytes_freed: int
    errors: list[str]

    @property
    def mb_freed(self) -> float:
        """Return freed space in megabytes."""
        return self.bytes_freed / (1024 * 1024)


@dataclass(frozen=True)
class TextSegment:
    """Represents a segment of text with timing information."""

    text: str
    start_time: float  # seconds from beginning
    duration: float  # segment duration in seconds
    segment_type: str  # "sentence", "paragraph", "heading"
    chunk_index: int  # which audio chunk this belongs to
    sentence_index: int  # position within the chunk

    @property
    def end_time(self) -> float:
        """Return end time of the text segment."""
        return self.start_time + self.duration


@dataclass(frozen=True)
class TimingMetadata:
    """Complete timing information for a document."""

    total_duration: float
    text_segments: list[TextSegment]
    audio_files: list[str]  # just filenames for now

    def get_segment_at_time(self, time_seconds: float) -> Optional[TextSegment]:
        """Find which text segment is active at given time."""
        for segment in self.text_segments:
            if segment.start_time <= time_seconds <= segment.end_time:
                return segment
        return None


@dataclass(frozen=True)
class TimedAudioResult:
    """Audio generation result with optional timing data."""

    audio_files: list[str]
    combined_mp3: Optional[str]
    timing_data: Optional[TimingMetadata] = None

    @property
    def has_timing_data(self) -> bool:
        """Return True if timing data is available."""
        return self.timing_data is not None
