# utils.py - Pure utility functions extracted from app.py
import re
from typing import Any

from application.config.system_config import SystemConfig
from domain.errors import ApplicationError, ErrorCode
from domain.models import PageRange


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"pdf"}


def parse_page_range_from_form(form: Any) -> PageRange:
    """Parse page range from Flask form data."""
    use_page_range = form.get("use_page_range") == "on"

    if not use_page_range:
        return PageRange()

    start_page = None
    end_page = None

    start_page_str = form.get("start_page", "").strip()
    end_page_str = form.get("end_page", "").strip()

    if start_page_str:
        start_page = int(start_page_str)

    if end_page_str:
        end_page = int(end_page_str)

    return PageRange(start_page=start_page, end_page=end_page)


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
            if config.enable_text_cleaning:
                return "Try again or consider disabling text cleaning if the problem persists."
            else:
                return "Text cleaning is already disabled. This might be a temporary issue - please try again."
        else:
            return "This error might be temporary. Please try again."
    else:
        if error.code == ErrorCode.TEXT_EXTRACTION_FAILED:
            return "Try a different PDF file, or ensure the PDF is not password-protected or image-only."
        elif error.code == ErrorCode.FILE_SIZE_ERROR:
            return f"Please use a smaller PDF file (maximum {config.max_file_size_mb}MB)."
        elif error.code == ErrorCode.INVALID_PAGE_RANGE:
            return "Please check the page numbers and try again."

    return ""
