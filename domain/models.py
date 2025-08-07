# domain/models.py
"""Domain models using Result[T] pattern for type-safe error handling."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .errors import ApplicationError, ErrorCode, Result, invalid_page_range_error

# --- Core Domain Models with Result[T] Pattern ---


@dataclass(frozen=True)
class PageRange:
    """Range specification for document page processing."""

    start_page: Optional[int] = None
    end_page: Optional[int] = None

    @classmethod
    def create(cls, start_page: Optional[int] = None, end_page: Optional[int] = None) -> Result["PageRange"]:
        """Create a PageRange with validation returning Result."""
        # Validate start_page
        if start_page is not None and start_page < 1:
            return Result.failure(invalid_page_range_error("start_page must be 1 or greater"))

        # Validate end_page
        if end_page is not None and end_page < 1:
            return Result.failure(invalid_page_range_error("end_page must be 1 or greater"))

        # Validate range consistency
        if start_page is not None and end_page is not None and start_page > end_page:
            return Result.failure(invalid_page_range_error("start_page cannot be greater than end_page"))

        return Result.success(cls(start_page=start_page, end_page=end_page))

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

    def validate(self) -> Result[None]:
        """Validate page range and return Result."""
        if self.start_page is not None and self.start_page < 1:
            return Result.failure(invalid_page_range_error("Start page must be 1 or greater"))

        if self.end_page is not None and self.end_page < 1:
            return Result.failure(invalid_page_range_error("End page must be 1 or greater"))

        if self.start_page is not None and self.end_page is not None and self.start_page > self.end_page:
            return Result.failure(invalid_page_range_error("Start page cannot be greater than end page"))

        return Result.success(None)

    def is_valid(self) -> bool:
        """Check if page range is valid."""
        return self.validate().is_success


def validation_error(message: str) -> ApplicationError:
    """Create a validation error."""
    return ApplicationError(code=ErrorCode.CONFIGURATION_ERROR, message=message, retryable=False)


@dataclass(frozen=True)
class ProcessingRequest:
    """Request specification for PDF processing operations."""

    pdf_path: str
    output_name: str
    page_range: PageRange

    @classmethod
    def create(cls, pdf_path: str, output_name: str, page_range: PageRange) -> Result["ProcessingRequest"]:
        """Create a ProcessingRequest with validation returning Result."""
        # Validate pdf_path
        if not pdf_path or not pdf_path.strip():
            return Result.failure(validation_error("pdf_path cannot be empty"))

        # Validate output_name
        if not output_name or not output_name.strip():
            return Result.failure(validation_error("output_name cannot be empty"))

        # Validate output name doesn't contain problematic characters
        import re

        if not re.match(r"^[a-zA-Z0-9_\-\s\.]+$", output_name):
            return Result.failure(validation_error("output_name contains invalid characters"))

        # Validate page_range itself
        page_validation = page_range.validate()
        if page_validation.is_failure:
            return Result.failure(page_validation.error)  # type: ignore[arg-type]

        return Result.success(cls(pdf_path=pdf_path, output_name=output_name, page_range=page_range))

    def validate(self) -> Result[None]:
        """Validate processing request."""
        if not self.pdf_path:
            return Result.failure(validation_error("PDF path is required"))

        if not self.output_name:
            return Result.failure(validation_error("Output name is required"))

        if not self.pdf_path.lower().endswith(".pdf"):
            return Result.failure(validation_error("File must be a PDF"))

        page_validation = self.page_range.validate()
        if page_validation.is_failure:
            return Result.failure(
                validation_error(f"Page range error: {page_validation.error.message if page_validation.error else ''}")
            )

        return Result.success(None)

    def is_valid(self) -> bool:
        """Check if processing request is valid."""
        return self.validate().is_success


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

    @classmethod
    def create(
        cls,
        filename: str,
        full_path: str,
        size_bytes: int,
        created_at: datetime,
        last_accessed: Optional[datetime] = None,
    ) -> Result["FileInfo"]:
        """Create a FileInfo with validation returning Result."""
        # Validate filename
        if not filename or not filename.strip():
            return Result.failure(validation_error("filename cannot be empty"))

        # Validate full_path
        if not full_path or not full_path.strip():
            return Result.failure(validation_error("full_path cannot be empty"))

        # Validate size_bytes
        if size_bytes < 0:
            return Result.failure(validation_error("size_bytes cannot be negative"))

        # Validate timestamps
        if last_accessed and last_accessed < created_at:
            return Result.failure(validation_error("last_accessed cannot be before created_at"))

        return Result.success(
            cls(
                filename=filename,
                full_path=full_path,
                size_bytes=size_bytes,
                created_at=created_at,
                last_accessed=last_accessed,
            )
        )

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

    @classmethod
    def create(
        cls,
        text: str,
        start_time: float,
        duration: float,
        segment_type: str,
        chunk_index: int,
        sentence_index: int,
    ) -> Result["TextSegment"]:
        """Create a TextSegment with validation returning Result."""
        # Validate text
        if not text or not text.strip():
            return Result.failure(validation_error("text cannot be empty"))

        # Validate start_time
        if start_time < 0:
            return Result.failure(validation_error("start_time cannot be negative"))

        # Validate duration
        if duration <= 0:
            return Result.failure(validation_error("duration must be positive"))

        # Validate chunk_index
        if chunk_index < 0:
            return Result.failure(validation_error("chunk_index cannot be negative"))

        # Validate sentence_index
        if sentence_index < 0:
            return Result.failure(validation_error("sentence_index cannot be negative"))

        # Validate segment_type
        valid_types = {"sentence", "paragraph", "heading", "technical", "emphasis"}
        if segment_type not in valid_types:
            return Result.failure(validation_error(f"segment_type must be one of {valid_types}"))

        return Result.success(
            cls(
                text=text,
                start_time=start_time,
                duration=duration,
                segment_type=segment_type,
                chunk_index=chunk_index,
                sentence_index=sentence_index,
            )
        )

    @property
    def end_time(self) -> float:
        """Return end time of the text segment."""
        return self.start_time + self.duration

    def validate(self) -> Result[None]:
        """Validate text segment timing data."""
        if not self.text or not self.text.strip():
            return Result.failure(validation_error("Text segment cannot be empty"))

        if self.start_time < 0:
            return Result.failure(validation_error("Start time cannot be negative"))

        if self.duration <= 0:
            return Result.failure(validation_error("Duration must be positive"))

        if self.chunk_index < 0:
            return Result.failure(validation_error("Chunk index cannot be negative"))

        if self.sentence_index < 0:
            return Result.failure(validation_error("Sentence index cannot be negative"))

        return Result.success(None)

    def is_valid(self) -> bool:
        """Check if text segment is valid."""
        return self.validate().is_success


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


# Helper functions for Result combinators


def validate_all(*results: Result[Any]) -> Result[None]:
    """Validate multiple Results and return first failure or success."""
    for result in results:
        if result.is_failure:
            return Result.failure(result.error)  # type: ignore[arg-type]
    return Result.success(None)


def combine_results(results: list[Result[Any]]) -> Result[list[Any]]:
    """Combine multiple Results into a single Result containing a list."""
    values = []
    for result in results:
        if result.is_failure:
            return Result.failure(result.error)  # type: ignore[arg-type]
        values.append(result.value)
    return Result.success(values)
