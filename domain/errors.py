# domain/errors.py
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any, Generic, TypeVar


class ErrorCode(Enum):
    """Standard error codes for the application"""
    FILE_NOT_FOUND = "file_not_found"
    TEXT_EXTRACTION_FAILED = "text_extraction_failed"
    TEXT_CLEANING_FAILED = "text_cleaning_failed"
    AUDIO_GENERATION_FAILED = "audio_generation_failed"
    INVALID_PAGE_RANGE = "invalid_page_range"
    CONFIGURATION_ERROR = "configuration_error"
    TTS_ENGINE_ERROR = "tts_engine_error"
    LLM_PROVIDER_ERROR = "llm_provider_error"
    SSML_PROCESSING_ERROR = "ssml_processing_error"
    FILE_SIZE_ERROR = "file_size_error"
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ApplicationError:
    """Structured error information"""
    code: ErrorCode
    message: str
    details: Optional[str] = None
    retryable: bool = False

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"

    def __repr__(self) -> str:
        return f"ApplicationError(code={self.code.value}, message='{self.message}', retryable={self.retryable})"


# Result type for better error handling
T = TypeVar('T')


@dataclass
class Result(Generic[T]):
    """Result type that either contains a value or an error"""
    value: Optional[T] = None
    error: Optional[ApplicationError] = None

    @property
    def is_success(self) -> bool:
        return self.error is None

    @property
    def is_failure(self) -> bool:
        return self.error is not None

    @classmethod
    def success(cls, value: T) -> 'Result[T]':
        return cls(value=value)

    @classmethod
    def failure(cls, error: ApplicationError) -> 'Result[T]':
        return cls(error=error)

    @classmethod
    def from_exception(cls, ex: Exception, code: ErrorCode = ErrorCode.UNKNOWN_ERROR, retryable: bool = False) -> 'Result[T]':
        return cls.failure(ApplicationError(
            code=code,
            message=str(ex),
            details=ex.__class__.__name__,
            retryable=retryable
        ))

# Helper functions for common error types


def file_not_found_error(file_path: str) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.FILE_NOT_FOUND,
        message=f"File not found: {file_path}",
        retryable=False
    )


def text_extraction_error(details: str) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.TEXT_EXTRACTION_FAILED,
        message="Failed to extract text from PDF",
        details=details,
        retryable=False
    )


def text_cleaning_error(details: str = None) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.TEXT_CLEANING_FAILED,
        message="Text cleaning failed",
        details=details,
        retryable=True  # LLM errors might be transient
    )


def audio_generation_error(details: str = None) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.AUDIO_GENERATION_FAILED,
        message="Audio generation failed",
        details=details,
        retryable=True  # TTS errors might be transient
    )


def tts_engine_error(details: str = None) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.TTS_ENGINE_ERROR,
        message="TTS engine error",
        details=details,
        retryable=True  # Rate limits, API issues, etc.
    )


def llm_provider_error(details: str = None) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.LLM_PROVIDER_ERROR,
        message="LLM provider error",
        details=details,
        retryable=True  # API issues, rate limits, etc.
    )


def invalid_page_range_error(details: str) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.INVALID_PAGE_RANGE,
        message="Invalid page range",
        details=details,
        retryable=False
    )


def configuration_error(details: str) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.CONFIGURATION_ERROR,
        message="Configuration error",
        details=details,
        retryable=False
    )


def file_size_error(size_mb: float, max_size_mb: int) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.FILE_SIZE_ERROR,
        message=f"File too large: {size_mb:.1f}MB exceeds maximum {max_size_mb}MB",
        retryable=False
    )


def unsupported_file_type_error(file_type: str) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.UNSUPPORTED_FILE_TYPE,
        message=f"Unsupported file type: {file_type}",
        details="Only PDF files are supported",
        retryable=False
    )
