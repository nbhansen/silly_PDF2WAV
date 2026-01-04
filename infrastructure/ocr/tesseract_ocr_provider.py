"""Tesseract OCR provider implementation for optical character recognition and PDF processing.

Combines direct text extraction with OCR fallback for reliable text extraction.
"""

import logging
from typing import Any, Optional

import pdfplumber
import pytesseract

from domain.errors import Result, text_extraction_error
from domain.interfaces import IOCRProvider
from domain.models import PageRange, PDFInfo

logger = logging.getLogger("ocr")


class TesseractOCRProvider(IOCRProvider):
    """OCR provider using Tesseract with PDF text extraction and validation capabilities."""

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        poppler_path_custom: Optional[str] = None,
        config: Optional[object] = None,
    ) -> None:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.poppler_path_custom = poppler_path_custom

        # Configure OCR settings with type safety
        if config:
            self.ocr_dpi = getattr(config, "ocr_dpi", 300)
            self.ocr_threshold = getattr(config, "ocr_threshold", 180)
            self.ocr_language = getattr(config, "ocr_language", "eng")
        else:
            # Default settings
            self.ocr_dpi = 300
            self.ocr_threshold = 180
            self.ocr_language = "eng"

    def perform_ocr(self, image_path: str) -> Result[str]:
        """Perform OCR on a single image file."""
        try:
            text = pytesseract.image_to_string(image_path, lang=self.ocr_language)
            if not text.strip():
                return Result.failure(text_extraction_error("OCR process yielded no text"))
            return Result.success(text)
        except Exception as e:
            return Result.failure(text_extraction_error(f"OCR failed on {image_path}: {e!s}"))

    def get_pdf_info(self, pdf_path: str) -> PDFInfo:
        """Get basic PDF information."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return PDFInfo(
                    total_pages=len(pdf.pages),
                    title=pdf.metadata.get("Title", "Unknown") if pdf.metadata else "Unknown",
                    author=pdf.metadata.get("Author", "Unknown") if pdf.metadata else "Unknown",
                )
        except Exception:
            return PDFInfo(total_pages=0, title="Unknown", author="Unknown")

    def validate_range(self, pdf_path: str, page_range: PageRange) -> dict[str, Any]:
        """Validate page range against PDF. Returns validation result."""
        try:
            pdf_info = self.get_pdf_info(pdf_path)
            total_pages = pdf_info.total_pages

            if total_pages == 0:
                return {"valid": False, "error": "Could not determine PDF page count", "total_pages": 0}

            # Validate start page
            if page_range.start_page is not None:
                if page_range.start_page < 1:
                    return self._error_result("Start page must be 1 or greater", total_pages)
                if page_range.start_page > total_pages:
                    return self._error_result(
                        f"Start page {page_range.start_page} exceeds total pages ({total_pages})", total_pages
                    )

            # Validate end page
            if page_range.end_page is not None:
                if page_range.end_page < 1:
                    return self._error_result("End page must be 1 or greater", total_pages)
                if page_range.end_page > total_pages:
                    return self._error_result(
                        f"End page {page_range.end_page} exceeds total pages ({total_pages})", total_pages
                    )

            # Validate range consistency
            if (
                page_range.start_page is not None
                and page_range.end_page is not None
                and page_range.start_page > page_range.end_page
            ):
                return self._error_result(
                    f"Start page ({page_range.start_page}) cannot be greater than end page ({page_range.end_page})",
                    total_pages,
                )

            # All validations passed
            actual_start = page_range.start_page if page_range.start_page is not None else 1
            actual_end = page_range.end_page if page_range.end_page is not None else total_pages

            return {
                "valid": True,
                "total_pages": total_pages,
                "actual_start": actual_start,
                "actual_end": actual_end,
                "pages_to_process": actual_end - actual_start + 1,
                "percentage_of_document": ((actual_end - actual_start + 1) / total_pages) * 100,
            }

        except Exception as e:
            return {"valid": False, "error": f"Page range validation failed: {e!s}", "total_pages": 0}

    def _error_result(self, error: str, total_pages: int) -> dict[str, Any]:
        return {"valid": False, "error": error, "total_pages": total_pages}