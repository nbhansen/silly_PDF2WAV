"""Error formatting utilities for user-facing error messages.

These functions reference domain types (ApplicationError, ErrorCode, SystemConfig)
and belong in the application layer rather than root-level utils.
"""

from pathlib import Path
import re
import shutil
from typing import Optional

from application.config.system_config import SystemConfig
from domain.errors import ApplicationError, ErrorCode


def clean_text_for_display(text: str) -> str:
    """Remove SSML markup and pause markers from text for display."""
    # Remove SSML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove pause markers
    text = re.sub(r"\.{3,}", "", text)  # Remove ... sequences
    text = re.sub(r"\(\s*\)", "", text)  # Remove ( ) sequences
    text = re.sub(r"\s+", " ", text)  # Clean up multiple spaces

    return text.strip()


def _get_user_friendly_error_message(error: ApplicationError) -> str:
    """Convert technical error to user-friendly message."""
    if error.code == ErrorCode.FILE_NOT_FOUND:
        return "The uploaded file could not be found or accessed."
    elif error.code == ErrorCode.TEXT_EXTRACTION_FAILED:
        return "Could not extract text from the PDF. The file might be corrupted, image-only, or password-protected."
    elif error.code == ErrorCode.TEXT_CLEANING_FAILED:
        return "Failed to process the extracted text for audio conversion."
    elif error.code == ErrorCode.AUDIO_GENERATION_FAILED:
        return (
            "Failed to generate audio from the text. This might be a temporary issue with the text-to-speech service."
        )
    elif error.code == ErrorCode.TTS_ENGINE_ERROR:
        return "Text-to-speech service encountered an error. This might be temporary."
    elif error.code == ErrorCode.LLM_PROVIDER_ERROR:
        return "Text cleaning service encountered an error. This might be temporary."
    elif error.code == ErrorCode.INVALID_PAGE_RANGE:
        return f"Invalid page range: {error.details}"
    elif error.code == ErrorCode.FILE_SIZE_ERROR:
        return str(error.message)
    elif error.code == ErrorCode.UNSUPPORTED_FILE_TYPE:
        return "Only PDF files are supported for conversion."
    else:
        return str(error.message)


def _get_retry_suggestion(error: ApplicationError, config: SystemConfig) -> str:
    """Get retry suggestion based on error type."""
    if error.retryable:
        if error.code in [ErrorCode.TTS_ENGINE_ERROR, ErrorCode.AUDIO_GENERATION_FAILED]:
            return (
                "Please try again in a few moments. If the problem persists, "
                "the text-to-speech service might be temporarily unavailable."
            )
        elif error.code == ErrorCode.LLM_PROVIDER_ERROR:
            return "Please try again in a few moments, or disable text cleaning in your configuration."
        elif error.code == ErrorCode.TEXT_CLEANING_FAILED:
            if config.text_processing.enable_cleaning:
                return "Try again or consider disabling text cleaning if the problem persists."
            else:
                return "Text cleaning is already disabled. This might be a temporary issue - please try again."
        else:
            return "This error might be temporary. Please try again."
    else:
        if error.code == ErrorCode.TEXT_EXTRACTION_FAILED:
            return "Try a different PDF file, or ensure the PDF is not password-protected or image-only."
        elif error.code == ErrorCode.FILE_SIZE_ERROR:
            return f"Please use a smaller PDF file (maximum {config.files.max_file_size_mb}MB)."
        elif error.code == ErrorCode.INVALID_PAGE_RANGE:
            return "Please check the page numbers and try again."

    return ""


# Enhanced Error Message Functions for Better User Experience


def _get_specific_error_context(error: ApplicationError) -> Optional[str]:
    """Extract specific context from error details for more helpful messages."""
    if not error.details:
        return None

    details = error.details.lower()

    # Text extraction specific issues
    if error.code == ErrorCode.TEXT_EXTRACTION_FAILED:
        if "password" in details or "encrypted" in details:
            return "password_protected"
        elif "image" in details or "scanned" in details:
            return "image_only"
        elif "corrupted" in details or "damaged" in details:
            return "corrupted"
        elif "empty" in details or "no text" in details:
            return "no_text"

    # TTS specific issues
    elif error.code in [ErrorCode.TTS_ENGINE_ERROR, ErrorCode.AUDIO_GENERATION_FAILED]:
        if "rate limit" in details or "quota" in details:
            return "rate_limited"
        elif "model" in details and ("not found" in details or "missing" in details):
            return "model_missing"
        elif "network" in details or "connection" in details:
            return "network_error"
        elif "timeout" in details:
            return "timeout"
        elif "memory" in details or "resource" in details:
            return "resource_exhaustion"

    # File system issues
    elif "disk" in details and "space" in details:
        return "disk_space"
    elif "permission" in details or "access denied" in details:
        return "permission_denied"

    return None


def _get_enhanced_error_message(error: ApplicationError) -> str:
    """Get enhanced, context-aware error message."""
    context = _get_specific_error_context(error)

    if error.code == ErrorCode.TEXT_EXTRACTION_FAILED:
        if context == "password_protected":
            return (
                "This PDF is password-protected and cannot be processed. "
                "Please remove the password protection and try again."
            )
        elif context == "image_only":
            return (
                "This PDF contains only scanned images without selectable text. "
                "You'll need a PDF with actual text content, or use OCR software "
                "to convert your scanned PDF first."
            )
        elif context == "corrupted":
            return (
                "The PDF file appears to be corrupted or damaged. Please check "
                "if the file opens correctly in a PDF viewer and try again "
                "with a different file."
            )
        elif context == "no_text":
            return (
                "No readable text was found in this PDF. The file may be empty, "
                "image-only, or use an unsupported text format."
            )
        else:
            return (
                "Could not extract text from the PDF. The file might be corrupted, image-only, or password-protected."
            )

    elif error.code in [ErrorCode.TTS_ENGINE_ERROR, ErrorCode.AUDIO_GENERATION_FAILED]:
        if context == "rate_limited":
            return (
                "Audio generation rate limit reached. Please wait a few minutes "
                "before trying again, or try processing a smaller document."
            )
        elif context == "model_missing":
            return (
                "The voice model is not available. Check your internet "
                "connection - the model may need to be downloaded automatically."
            )
        elif context == "network_error":
            return "Cannot connect to the text-to-speech service. Check your internet connection and try again."
        elif context == "timeout":
            return (
                "Audio generation timed out. This usually happens with very "
                "long documents. Try processing smaller sections or wait for "
                "the service to respond."
            )
        elif context == "resource_exhaustion":
            return (
                "Insufficient system resources for audio generation. "
                "Try closing other applications or processing a smaller document."
            )
        else:
            return (
                "Failed to generate audio from the text. "
                "This might be a temporary issue with the text-to-speech service."
            )

    elif error.code == ErrorCode.LLM_PROVIDER_ERROR:
        if context == "rate_limited":
            return "Text processing rate limit reached. Please wait a moment before trying again."
        elif context == "network_error":
            return (
                "Cannot connect to the text processing service. Check your internet connection and API configuration."
            )
        else:
            return "Text cleaning service encountered an error. This might be temporary."

    # Use original function for other cases
    return _get_user_friendly_error_message(error)


def _get_enhanced_retry_suggestion(error: ApplicationError, config: SystemConfig) -> str:
    """Get enhanced, context-aware retry suggestion."""
    context = _get_specific_error_context(error)

    if error.code == ErrorCode.TEXT_EXTRACTION_FAILED:
        if context == "password_protected":
            return "Remove the password from your PDF using a PDF editor, or try a different PDF file."
        elif context == "image_only":
            return (
                "Try using a PDF that contains selectable text, or use OCR "
                "software like Adobe Acrobat to make the text searchable first."
            )
        elif context == "corrupted":
            return (
                "Try opening the PDF in a PDF reader first to verify it works, "
                "or try re-downloading/re-saving the file."
            )
        else:
            return "Try a different PDF file, or ensure the PDF is not password-protected or image-only."

    elif error.code in [ErrorCode.TTS_ENGINE_ERROR, ErrorCode.AUDIO_GENERATION_FAILED]:
        if context == "rate_limited":
            return "Wait 2-5 minutes before trying again. For large documents, consider processing smaller page ranges."
        elif context == "model_missing":
            return (
                "Ensure you have a stable internet connection. The voice model "
                "will be downloaded automatically on first use."
            )
        elif context == "network_error":
            return (
                "Check your internet connection and firewall settings. "
                "The application needs to connect to external TTS services."
            )
        elif context == "timeout":
            return (
                "For large documents, try processing smaller sections "
                "(10-20 pages at a time) or be patient - processing can "
                "take several minutes."
            )
        elif context == "resource_exhaustion":
            return "Close other applications to free up memory, or try processing a smaller document (fewer pages)."
        elif error.retryable:
            return (
                "Please try again in a few moments. If the problem persists, "
                "the text-to-speech service might be temporarily unavailable."
            )

    elif error.code == ErrorCode.FILE_SIZE_ERROR:
        size_info = _extract_size_info(error.details) if error.details else None
        if size_info:
            return (
                f"Your PDF is {size_info['actual']}MB but the limit is "
                f"{size_info['limit']}MB. Try compressing the PDF or "
                f"splitting it into smaller files."
            )
        else:
            return f"Please use a smaller PDF file (maximum {config.files.max_file_size_mb}MB)."

    # Check for system resource issues
    if context == "disk_space":
        free_space = _get_available_disk_space()
        return f"Free up at least 500MB of disk space (currently {free_space}MB available) and try again."
    elif context == "permission_denied":
        return "Check file permissions and ensure the application has write access to its folders."

    # Use original function for other cases
    return _get_retry_suggestion(error, config)


def _extract_size_info(details: str) -> Optional[dict[str, str]]:
    """Extract file size information from error details."""
    # Look for patterns like "45.2MB exceeds limit of 100MB"
    match = re.search(r"(\d+\.?\d*)\s*MB.*?(\d+\.?\d*)\s*MB", details)
    if match:
        return {"actual": match.group(1), "limit": match.group(2)}
    return None


def _get_available_disk_space() -> str:
    """Get available disk space in a human-readable format."""
    try:
        _total, _used, free = shutil.disk_usage(Path.cwd())
        free_mb = free // (1024 * 1024)
        return f"{free_mb:,}"
    except Exception:
        return "unknown"


def get_contextual_error_message(
    error: ApplicationError,
    config: SystemConfig,
    filename: Optional[str] = None,
) -> str:
    """Get a complete, contextual error message with filename and suggestions."""
    enhanced_message = _get_enhanced_error_message(error)
    enhanced_suggestion = _get_enhanced_retry_suggestion(error, config)

    # Add filename context if available
    file_context = f"Error processing '{filename}': " if filename else "Processing error: "

    # Combine message with suggestion
    if enhanced_suggestion:
        return f"{file_context}{enhanced_message}<br><br>\U0001f4a1 <strong>What to try:</strong> {enhanced_suggestion}"
    return f"{file_context}{enhanced_message}"


def get_processing_stage_error(
    stage: str,
    error: Exception,
    filename: Optional[str] = None,
) -> str:
    """Get error message for specific processing stages with context."""
    file_info = f" for '{filename}'" if filename else ""

    stage_messages = {
        "text_extraction": f"Failed to extract text from PDF{file_info}",
        "text_processing": f"Failed to process and clean text{file_info}",
        "audio_generation": f"Failed to generate audio{file_info}",
        "file_combination": f"Failed to create final audio file{file_info}",
        "file_validation": f"File validation failed{file_info}",
        "configuration": f"Configuration error{file_info}",
    }

    base_message = stage_messages.get(stage, f"Processing failed at {stage}{file_info}")
    error_detail = str(error)

    # Add specific suggestions based on stage and error type
    if stage == "text_extraction" and ("password" in error_detail.lower() or "encrypted" in error_detail.lower()):
        return f"{base_message}: The PDF is password-protected. Please remove the password and try again."
    elif stage == "audio_generation" and "model" in error_detail.lower():
        return f"{base_message}: Voice model unavailable. Check your internet connection for automatic download."
    elif stage == "file_validation" and "size" in error_detail.lower():
        return f"{base_message}: File is too large. Try compressing or splitting the PDF."
    else:
        return f"{base_message}: {error_detail}"


def get_error_code_suggestion(error_code: ErrorCode) -> str:
    """Get a brief suggestion string for a given error code."""
    suggestions = {
        ErrorCode.FILE_NOT_FOUND: "Check that the file was uploaded correctly.",
        ErrorCode.TEXT_EXTRACTION_FAILED: ("Try a different PDF or ensure it's not password-protected."),
        ErrorCode.TEXT_CLEANING_FAILED: ("Try disabling text cleaning in settings."),
        ErrorCode.AUDIO_GENERATION_FAILED: ("Try again or check TTS service status."),
        ErrorCode.TTS_ENGINE_ERROR: "Check TTS configuration and try again.",
        ErrorCode.LLM_PROVIDER_ERROR: "Check API key and network connection.",
        ErrorCode.INVALID_PAGE_RANGE: ("Verify page numbers are within document range."),
        ErrorCode.FILE_SIZE_ERROR: "Use a smaller PDF file.",
        ErrorCode.UNSUPPORTED_FILE_TYPE: "Only PDF files are supported.",
    }
    return suggestions.get(error_code, "Please try again.")


def get_disk_space_info() -> dict[str, str]:
    """Get disk space information as a dictionary."""
    try:
        total, used, free = shutil.disk_usage(Path.cwd())
        return {
            "total_mb": f"{total // (1024 * 1024):,}",
            "used_mb": f"{used // (1024 * 1024):,}",
            "free_mb": f"{free // (1024 * 1024):,}",
        }
    except Exception:
        return {
            "total_mb": "unknown",
            "used_mb": "unknown",
            "free_mb": "unknown",
        }


def get_file_size_info(file_path: str) -> Optional[str]:
    """Get human-readable file size for a given path."""
    try:
        size = Path(file_path).stat().st_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    except Exception:
        return None
