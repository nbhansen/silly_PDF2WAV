# domain/models.py - Updated with structured error handling
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

# Import error types
from .errors import ApplicationError

# --- Core Domain Models ---

@dataclass
class PageRange:
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    
    def is_full_document(self) -> bool:
        return self.start_page is None and self.end_page is None

@dataclass
class ProcessingRequest:
    pdf_path: str
    output_name: str
    page_range: PageRange
    
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
                      debug_info: Optional[Dict[str, Any]] = None) -> 'ProcessingResult':
        """Create a successful processing result"""
        return cls(
            audio_files=audio_files,
            combined_mp3_file=combined_mp3,
            debug_info=debug_info,
            error=None
        )
    
    @classmethod
    def failure_result(cls, error: ApplicationError) -> 'ProcessingResult':
        """Create a failed processing result"""
        return cls(
            audio_files=None,
            combined_mp3_file=None,
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