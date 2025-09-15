# utils.py - Pure utility functions extracted from app.py
from pathlib import Path
import re
import shutil
from typing import Any, Optional, Union

from application.config.system_config import SystemConfig
from domain.errors import ApplicationError, ErrorCode
from domain.models import PageRange

# Type alias for form data (can be dict-like or Flask's ImmutableMultiDict)
FormData = Union[dict[str, Any], Any]  # Any covers Flask's ImmutableMultiDict


def allowed_file(filename: str) -> bool:
    """Check if the filename has an allowed file extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"pdf"}


def parse_page_range_from_form(form: FormData) -> PageRange:
    """Parse page range from Flask form data."""
    use_page_range = form.get("use_page_range") == "on"

    if not use_page_range:
        return PageRange()

    start_page: Optional[int] = None
    end_page: Optional[int] = None

    start_page_str = str(form.get("start_page", "")).strip()
    end_page_str = str(form.get("end_page", "")).strip()

    if start_page_str:
        start_page = int(start_page_str)

    if end_page_str:
        end_page = int(end_page_str)

    return PageRange(start_page=start_page, end_page=end_page)


def parse_plain_english_from_form(form: FormData) -> bool:
    """Parse plain English conversion setting from Flask form data."""
    return bool(form.get("enable_plain_english") == "on")


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
            return "This PDF is password-protected and cannot be processed. Please remove the password protection and try again."
        elif context == "image_only":
            return "This PDF contains only scanned images without selectable text. You'll need a PDF with actual text content, or use OCR software to convert your scanned PDF first."
        elif context == "corrupted":
            return "The PDF file appears to be corrupted or damaged. Please check if the file opens correctly in a PDF viewer and try again with a different file."
        elif context == "no_text":
            return "No readable text was found in this PDF. The file may be empty, image-only, or use an unsupported text format."
        else:
            return (
                "Could not extract text from the PDF. The file might be corrupted, image-only, or password-protected."
            )

    elif error.code in [ErrorCode.TTS_ENGINE_ERROR, ErrorCode.AUDIO_GENERATION_FAILED]:
        if context == "rate_limited":
            return "Audio generation rate limit reached. Please wait a few minutes before trying again, or try processing a smaller document."
        elif context == "model_missing":
            return "The voice model is not available. Check your internet connection - the model may need to be downloaded automatically."
        elif context == "network_error":
            return "Cannot connect to the text-to-speech service. Check your internet connection and try again."
        elif context == "timeout":
            return "Audio generation timed out. This usually happens with very long documents. Try processing smaller sections or wait for the service to respond."
        elif context == "resource_exhaustion":
            return "Insufficient system resources for audio generation. Try closing other applications or processing a smaller document."
        else:
            return "Failed to generate audio from the text. This might be a temporary issue with the text-to-speech service."

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
            return "Try using a PDF that contains selectable text, or use OCR software like Adobe Acrobat to make the text searchable first."
        elif context == "corrupted":
            return "Try opening the PDF in a PDF reader first to verify it works, or try re-downloading/re-saving the file."
        else:
            return "Try a different PDF file, or ensure the PDF is not password-protected or image-only."

    elif error.code in [ErrorCode.TTS_ENGINE_ERROR, ErrorCode.AUDIO_GENERATION_FAILED]:
        if context == "rate_limited":
            return "Wait 2-5 minutes before trying again. For large documents, consider processing smaller page ranges."
        elif context == "model_missing":
            return "Ensure you have a stable internet connection. The voice model will be downloaded automatically on first use."
        elif context == "network_error":
            return "Check your internet connection and firewall settings. The application needs to connect to external TTS services."
        elif context == "timeout":
            return "For large documents, try processing smaller sections (10-20 pages at a time) or be patient - processing can take several minutes."
        elif context == "resource_exhaustion":
            return "Close other applications to free up memory, or try processing a smaller document (fewer pages)."
        elif error.retryable:
            return "Please try again in a few moments. If the problem persists, the text-to-speech service might be temporarily unavailable."

    elif error.code == ErrorCode.FILE_SIZE_ERROR:
        size_info = _extract_size_info(error.details) if error.details else None
        if size_info:
            return f"Your PDF is {size_info['actual']}MB but the limit is {size_info['limit']}MB. Try compressing the PDF or splitting it into smaller files."
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
    import re

    # Look for patterns like "45.2MB exceeds limit of 100MB"
    match = re.search(r"(\d+\.?\d*)\s*MB.*?(\d+\.?\d*)\s*MB", details)
    if match:
        return {"actual": match.group(1), "limit": match.group(2)}
    return None


def _get_available_disk_space() -> str:
    """Get available disk space in a human-readable format."""
    try:
        total, used, free = shutil.disk_usage(Path.cwd())
        free_mb = free // (1024 * 1024)
        return f"{free_mb:,}"
    except Exception:
        return "unknown"


def get_contextual_error_message(error: ApplicationError, config: SystemConfig, filename: Optional[str] = None) -> str:
    """Get a complete, contextual error message with filename and suggestions."""
    enhanced_message = _get_enhanced_error_message(error)
    enhanced_suggestion = _get_enhanced_retry_suggestion(error, config)

    # Add filename context if available
    if filename:
        file_context = f"Error processing '{filename}': "
    else:
        file_context = "Processing error: "

    # Combine message with suggestion
    if enhanced_suggestion:
        return f"{file_context}{enhanced_message}<br><br>💡 <strong>What to try:</strong> {enhanced_suggestion}"
    else:
        return f"{file_context}{enhanced_message}"


def get_processing_stage_error(stage: str, error: Exception, filename: Optional[str] = None) -> str:
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
