# utils.py - Pure utility functions with no domain dependencies
from typing import Any, Optional, Union

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
