"""Tesseract OCR provider implementation for optical character recognition and PDF processing.
Combines direct text extraction with OCR fallback for reliable text extraction.
"""

from typing import Any, Optional

from pdf2image import convert_from_path
import pdfplumber
import pytesseract

from domain.errors import Result, text_extraction_error
from domain.interfaces import IOCRProvider
from domain.models import PageRange, PDFInfo


class TesseractOCRProvider(IOCRProvider):
    """OCR provider using Tesseract with PDF text extraction and validation capabilities."""

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        poppler_path_custom: Optional[str] = None,
        config: Optional[Any] = None,
    ) -> None:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.poppler_path_custom = poppler_path_custom

        # Configure OCR settings
        if config:
            self.ocr_dpi = config.ocr_dpi
            self.ocr_threshold = config.ocr_threshold
            self.ocr_language = config.ocr_language if hasattr(config, "ocr_language") else "eng"
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

    def extract_text(self, pdf_path: str, page_range: PageRange) -> str:
        """Extract text from PDF with optional page range."""
        if not page_range.is_full_document():
            return self._extract_with_page_range(pdf_path, page_range.start_page, page_range.end_page)
        else:
            return self._extract_full_pdf(pdf_path)

    def _extract_with_page_range(
        self, pdf_path: str, start_page: Optional[int] = None, end_page: Optional[int] = None
    ) -> str:
        """Extract from specified page range."""
        try:
            # Try direct extraction first
            direct_text = self._extract_direct_with_range(pdf_path, start_page, end_page)
            if direct_text and len(direct_text) > 100:
                return direct_text

            # Fall back to OCR
            return self._extract_ocr_with_range(pdf_path, start_page, end_page)

        except Exception:
            # Fall back to full PDF extraction
            return self._extract_full_pdf(pdf_path)

    def _extract_full_pdf(self, pdf_path: str) -> str:
        """Extract from entire PDF."""
        # Try direct extraction first
        direct_text = self._extract_direct(pdf_path)
        if direct_text and len(direct_text) > 100:
            return direct_text

        # Fall back to OCR
        return self._extract_ocr(pdf_path)

    def _extract_direct_with_range(
        self, pdf_path: str, start_page: Optional[int] = None, end_page: Optional[int] = None
    ) -> Optional[str]:
        """Extract text directly from specified page range."""
        try:
            text_content = ""

            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)

                # Determine actual page range
                actual_start = (start_page - 1) if start_page else 0
                actual_end = min(end_page, total_pages) if end_page else total_pages

                # Validate page range
                if actual_start < 0:
                    actual_start = 0
                if actual_end > total_pages:
                    actual_end = total_pages
                if actual_start >= actual_end:
                    return None

                for page_num in range(actual_start, actual_end):
                    page = pdf.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + f"\n\n--- Page {page_num + 1} End ---\n\n"

            return text_content.strip() if text_content.strip() else None
        except Exception:
            return None

    def _extract_direct(self, pdf_path: str) -> Optional[str]:
        """Extract text directly using pdfplumber."""
        try:
            text_content = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + f"\n\n--- Page {page_num + 1} End ---\n\n"
            return text_content.strip() if text_content.strip() else None
        except Exception:
            return None

    def _extract_ocr_with_range(
        self, pdf_path: str, start_page: Optional[int] = None, end_page: Optional[int] = None
    ) -> str:
        """OCR extraction from specified page range."""
        try:
            # Get total pages for validation
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)

            # Validate and adjust page range
            actual_start = start_page if start_page else 1
            actual_end = min(end_page, total_pages) if end_page else total_pages

            if actual_start < 1:
                actual_start = 1
            if actual_end > total_pages:
                actual_end = total_pages
            if actual_start > actual_end:
                return "Error: Invalid page range for OCR"

            # Convert specified page range to images
            convert_kwargs = {
                "dpi": self.ocr_dpi,
                "grayscale": True,
                "first_page": actual_start,
                "last_page": actual_end,
            }
            if self.poppler_path_custom:
                convert_kwargs["poppler_path"] = self.poppler_path_custom

            images = convert_from_path(pdf_path, **convert_kwargs)

            full_text = ""
            for i, image in enumerate(images):
                processed_image = image.convert("L")
                processed_image = processed_image.point(lambda p: 0 if p < self.ocr_threshold else 255)
                page_text = pytesseract.image_to_string(processed_image, lang=self.ocr_language)
                actual_page_num = actual_start + i
                full_text += page_text + f"\n\n--- Page {actual_page_num} End (OCR) ---\n\n"

            return full_text if full_text.strip() else "OCR process yielded no text."

        except Exception as e:
            return f"Error during range OCR: {e!s}"

    def _extract_ocr(self, pdf_path: str) -> str:
        """Extract text using OCR from entire PDF."""
        try:
            convert_kwargs = {"dpi": self.ocr_dpi, "grayscale": True}
            if self.poppler_path_custom:
                convert_kwargs["poppler_path"] = self.poppler_path_custom
            images = convert_from_path(pdf_path, **convert_kwargs)

            full_text = ""
            for i, image in enumerate(images):
                processed_image = image.convert("L")
                processed_image = processed_image.point(lambda p: 0 if p < self.ocr_threshold else 255)
                page_text = pytesseract.image_to_string(processed_image, lang=self.ocr_language)
                full_text += page_text + f"\n\n--- Page {i + 1} End (OCR) ---\n\n"

            return full_text if full_text.strip() else "OCR process yielded no text."

        except Exception as e:
            return f"Error during OCR: {e!s}"

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
            if page_range.start_page is not None and page_range.end_page is not None:
                if page_range.start_page > page_range.end_page:
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
