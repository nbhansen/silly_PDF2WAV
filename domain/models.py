# domain/models.py
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

from .errors import ApplicationError

# --- Core Domain Models ---


@dataclass
class PageRange:
    start_page: Optional[int] = None
    end_page: Optional[int] = None

    def __post_init__(self):
        """Validate page range after initialization"""
        if self.start_page is not None and self.start_page < 1:
            raise ValueError("start_page must be 1 or greater")
        
        if self.end_page is not None and self.end_page < 1:
            raise ValueError("end_page must be 1 or greater")
        
        if (self.start_page is not None and self.end_page is not None 
            and self.start_page > self.end_page):
            raise ValueError("start_page cannot be greater than end_page")

    def is_full_document(self) -> bool:
        return self.start_page is None and self.end_page is None
    
    def validate_against_document(self, total_pages: int) -> None:
        """Validate page range against actual document"""
        if total_pages < 1:
            raise ValueError("Document must have at least 1 page")
        
        if self.start_page is not None and self.start_page > total_pages:
            raise ValueError(f"start_page {self.start_page} exceeds document pages ({total_pages})")
        
        if self.end_page is not None and self.end_page > total_pages:
            raise ValueError(f"end_page {self.end_page} exceeds document pages ({total_pages})")
    
    def validate(self) -> Optional[str]:
        """Validate page range and return error message if invalid"""
        if self.start_page is not None and self.start_page < 1:
            return "Start page must be 1 or greater"
        
        if self.end_page is not None and self.end_page < 1:
            return "End page must be 1 or greater"
        
        if (self.start_page is not None and self.end_page is not None 
            and self.start_page > self.end_page):
            return "Start page cannot be greater than end page"
        
        return None
    
    def is_valid(self) -> bool:
        """Check if page range is valid"""
        return self.validate() is None


@dataclass
class ProcessingRequest:
    pdf_path: str
    output_name: str
    page_range: PageRange

    def __post_init__(self):
        """Validate processing request after initialization"""
        if not self.pdf_path or not self.pdf_path.strip():
            raise ValueError("pdf_path cannot be empty")
        
        if not self.output_name or not self.output_name.strip():
            raise ValueError("output_name cannot be empty")
        
        # Validate output name doesn't contain problematic characters
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\s]+$', self.output_name):
            raise ValueError("output_name contains invalid characters")
        
        if self.page_range is None:
            raise ValueError("page_range cannot be None")

    def validate(self) -> Optional[str]:
        """Validate processing request"""
        if not self.pdf_path:
            return "PDF path is required"
        
        if not self.output_name:
            return "Output name is required"
        
        if not self.pdf_path.lower().endswith('.pdf'):
            return "File must be a PDF"
        
        page_error = self.page_range.validate()
        if page_error:
            return f"Page range error: {page_error}"
        
        return None
    
    def is_valid(self) -> bool:
        """Check if processing request is valid"""
        return self.validate() is None


@dataclass
class PDFInfo:
    total_pages: int
    title: str
    author: str


@dataclass
class ProcessingResult:
    """Result of PDF processing operation with structured error handling"""
    audio_files: Optional[List[str]] = None
    combined_mp3_file: Optional[str] = None
    timing_data: Optional['TimingMetadata'] = None
    debug_info: Optional[Dict[str, Any]] = None
    error: Optional[ApplicationError] = None

    @property
    def success(self) -> bool:
        """Check if processing was successful"""
        return self.error is None

    @property
    def is_retryable(self) -> bool:
        """Check if the error (if any) is retryable"""
        return self.error is not None and self.error.retryable

    @classmethod
    def success_result(cls, audio_files: List[str], combined_mp3: Optional[str] = None,
                       timing_data: Optional['TimingMetadata'] = None,
                       debug_info: Optional[Dict[str, Any]] = None) -> 'ProcessingResult':
        """Create a successful processing result"""
        return cls(
            audio_files=audio_files.copy() if audio_files is not None else None,  # Create defensive copy
            combined_mp3_file=combined_mp3,
            timing_data=timing_data,
            debug_info=debug_info.copy() if debug_info is not None else None,  # Create defensive copy
            error=None
        )

    @classmethod
    def failure_result(cls, error: ApplicationError) -> 'ProcessingResult':
        """Create a failed processing result"""
        return cls(
            audio_files=None,
            combined_mp3_file=None,
            timing_data=None,
            debug_info=None,
            error=error
        )

    def get_error_message(self) -> str:
        """Get a user-friendly error message"""
        if self.error:
            return str(self.error)
        return "No error"

    def get_error_code(self) -> Optional[str]:
        """Get the error code for logging/debugging"""
        if self.error:
            return self.error.code.value
        return None


@dataclass
class FileInfo:
    """Information about a managed file"""
    filename: str
    full_path: str
    size_bytes: int
    created_at: datetime
    last_accessed: Optional[datetime] = None

    def __post_init__(self):
        """Validate file info after initialization"""
        if not self.filename or not self.filename.strip():
            raise ValueError("filename cannot be empty")
        
        if not self.full_path or not self.full_path.strip():
            raise ValueError("full_path cannot be empty")
        
        if self.size_bytes < 0:
            raise ValueError("size_bytes cannot be negative")
        
        if self.last_accessed and self.last_accessed < self.created_at:
            raise ValueError("last_accessed cannot be before created_at")

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def age_hours(self) -> float:
        return (datetime.now() - self.created_at).total_seconds() / 3600


@dataclass
class CleanupResult:
    """Result of a cleanup operation"""
    files_removed: int
    bytes_freed: int
    errors: list[str]

    @property
    def mb_freed(self) -> float:
        return self.bytes_freed / (1024 * 1024)


@dataclass
class TextSegment:
    """Represents a segment of text with timing information"""
    text: str
    start_time: float  # seconds from beginning
    duration: float    # segment duration in seconds
    segment_type: str  # "sentence", "paragraph", "heading"
    chunk_index: int   # which audio chunk this belongs to
    sentence_index: int  # position within the chunk

    def __post_init__(self):
        """Validate text segment after initialization"""
        if not self.text or not self.text.strip():
            raise ValueError("text cannot be empty")
        
        if self.start_time < 0:
            raise ValueError("start_time cannot be negative")
        
        if self.duration <= 0:
            raise ValueError("duration must be positive")
        
        if self.chunk_index < 0:
            raise ValueError("chunk_index cannot be negative")
        
        if self.sentence_index < 0:
            raise ValueError("sentence_index cannot be negative")
        
        # Validate segment_type
        valid_types = {"sentence", "paragraph", "heading", "technical", "emphasis"}
        if self.segment_type not in valid_types:
            raise ValueError(f"segment_type must be one of {valid_types}")

    @property
    def end_time(self) -> float:
        return self.start_time + self.duration
    
    def validate(self) -> Optional[str]:
        """Validate text segment timing data"""
        if not self.text or not self.text.strip():
            return "Text segment cannot be empty"
        
        if self.start_time < 0:
            return "Start time cannot be negative"
        
        if self.duration <= 0:
            return "Duration must be positive"
        
        if self.chunk_index < 0:
            return "Chunk index cannot be negative"
        
        if self.sentence_index < 0:
            return "Sentence index cannot be negative"
        
        return None
    
    def is_valid(self) -> bool:
        """Check if text segment is valid"""
        return self.validate() is None


@dataclass
class TimingMetadata:
    """Complete timing information for a document"""
    total_duration: float
    text_segments: List[TextSegment]
    audio_files: List[str]  # just filenames for now

    def get_segment_at_time(self, time_seconds: float) -> Optional[TextSegment]:
        """Find which text segment is active at given time"""
        for segment in self.text_segments:
            if segment.start_time <= time_seconds <= segment.end_time:
                return segment
        return None


@dataclass
class TimedAudioResult:
    """Audio generation result with optional timing data"""
    audio_files: List[str]
    combined_mp3: Optional[str]
    timing_data: Optional[TimingMetadata] = None

    @property
    def has_timing_data(self) -> bool:
        return self.timing_data is not None
