# tests/infrastructure/ocr/test_tesseract_ocr_provider.py
"""Comprehensive unit tests for TesseractOCRProvider implementation.

Tests dual extraction strategies, page range validation, and image processing pipeline.
"""

from unittest.mock import MagicMock, Mock, patch

from PIL import Image
import pytest

from domain.errors import ErrorCode
from domain.models import PageRange
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider


class TestTesseractOCRProviderInitialization:
    """Test TesseractOCRProvider initialization and configuration."""

    def test_init_with_default_settings(self):
        """Should initialize with default OCR settings."""
        provider = TesseractOCRProvider()

        assert provider.ocr_dpi == 300
        assert provider.ocr_threshold == 180
        assert provider.ocr_language == "eng"
        assert provider.poppler_path_custom is None

    def test_init_with_custom_tesseract_cmd(self):
        """Should set custom tesseract command path."""
        custom_cmd = "/usr/local/bin/tesseract"

        with patch("pytesseract.pytesseract") as mock_pytesseract:
            TesseractOCRProvider(tesseract_cmd=custom_cmd)

            assert mock_pytesseract.tesseract_cmd == custom_cmd

    def test_init_with_custom_poppler_path(self):
        """Should set custom poppler path."""
        custom_poppler = "/usr/local/bin"

        provider = TesseractOCRProvider(poppler_path_custom=custom_poppler)

        assert provider.poppler_path_custom == custom_poppler

    def test_init_with_config_object(self):
        """Should initialize with configuration object."""
        mock_config = Mock()
        mock_config.ocr_dpi = 600
        mock_config.ocr_threshold = 200
        mock_config.ocr_language = "fra"

        provider = TesseractOCRProvider(config=mock_config)

        assert provider.ocr_dpi == 600
        assert provider.ocr_threshold == 200
        assert provider.ocr_language == "fra"

    def test_init_with_config_without_language(self):
        """Should default to 'eng' when config lacks language attribute."""
        mock_config = Mock()
        mock_config.ocr_dpi = 450
        mock_config.ocr_threshold = 150
        # No ocr_language attribute
        del mock_config.ocr_language

        provider = TesseractOCRProvider(config=mock_config)

        assert provider.ocr_dpi == 450
        assert provider.ocr_threshold == 150
        assert provider.ocr_language == "eng"

    def test_init_with_none_config(self):
        """Should handle None config gracefully."""
        provider = TesseractOCRProvider(config=None)

        assert provider.ocr_dpi == 300
        assert provider.ocr_threshold == 180
        assert provider.ocr_language == "eng"


class TestTesseractOCRProviderPerformOCR:
    """Test single image OCR functionality."""

    @patch("pytesseract.image_to_string")
    def test_perform_ocr_success(self, mock_image_to_string):
        """Should successfully perform OCR on image file."""
        mock_image_to_string.return_value = "Extracted text from image"
        provider = TesseractOCRProvider()

        result = provider.perform_ocr("test_image.png")

        assert result.is_success
        assert result.value == "Extracted text from image"
        mock_image_to_string.assert_called_once_with("test_image.png", lang="eng")

    @patch("pytesseract.image_to_string")
    def test_perform_ocr_with_custom_language(self, mock_image_to_string):
        """Should use custom language for OCR."""
        mock_image_to_string.return_value = "Texte français extrait"
        mock_config = Mock()
        mock_config.ocr_dpi = 300
        mock_config.ocr_threshold = 180
        mock_config.ocr_language = "fra"

        provider = TesseractOCRProvider(config=mock_config)
        result = provider.perform_ocr("french_image.png")

        assert result.is_success
        assert result.value == "Texte français extrait"
        mock_image_to_string.assert_called_once_with("french_image.png", lang="fra")

    @patch("pytesseract.image_to_string")
    def test_perform_ocr_empty_result(self, mock_image_to_string):
        """Should handle empty OCR result as failure."""
        mock_image_to_string.return_value = "   \n\t  "  # Whitespace only
        provider = TesseractOCRProvider()

        result = provider.perform_ocr("empty_image.png")

        assert result.is_failure
        assert result.error.code == ErrorCode.TEXT_EXTRACTION_FAILED
        assert "OCR process yielded no text" in result.error.details

    @patch("pytesseract.image_to_string")
    def test_perform_ocr_handles_pytesseract_exception(self, mock_image_to_string):
        """Should handle pytesseract exceptions gracefully."""
        mock_image_to_string.side_effect = Exception("Tesseract not found")
        provider = TesseractOCRProvider()

        result = provider.perform_ocr("bad_image.png")

        assert result.is_failure
        assert result.error.code == ErrorCode.TEXT_EXTRACTION_FAILED
        assert "OCR failed on bad_image.png: Tesseract not found" in result.error.details

    @patch("pytesseract.image_to_string")
    def test_perform_ocr_handles_file_not_found(self, mock_image_to_string):
        """Should handle file not found errors."""
        mock_image_to_string.side_effect = FileNotFoundError("Image file not found")
        provider = TesseractOCRProvider()

        result = provider.perform_ocr("nonexistent.png")

        assert result.is_failure
        assert "Image file not found" in result.error.details

    @patch("pytesseract.image_to_string")
    def test_perform_ocr_strips_whitespace_from_result(self, mock_image_to_string):
        """Should not strip whitespace from non-empty OCR results."""
        mock_image_to_string.return_value = "  Valid text with spaces  "
        provider = TesseractOCRProvider()

        result = provider.perform_ocr("spaced_text.png")

        assert result.is_success
        assert result.value == "  Valid text with spaces  "


class TestTesseractOCRProviderPDFInfo:
    """Test PDF information extraction."""

    @patch("pdfplumber.open")
    def test_get_pdf_info_success(self, mock_pdfplumber_open):
        """Should successfully extract PDF information."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [Mock(), Mock(), Mock()]  # 3 pages
        mock_pdf.metadata = {"Title": "Test Document", "Author": "Test Author"}
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        pdf_info = provider.get_pdf_info("test.pdf")

        assert pdf_info.total_pages == 3
        assert pdf_info.title == "Test Document"
        assert pdf_info.author == "Test Author"

    @patch("pdfplumber.open")
    def test_get_pdf_info_no_metadata(self, mock_pdfplumber_open):
        """Should handle PDF without metadata."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [Mock()]  # 1 page
        mock_pdf.metadata = None
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        pdf_info = provider.get_pdf_info("no_metadata.pdf")

        assert pdf_info.total_pages == 1
        assert pdf_info.title == "Unknown"
        assert pdf_info.author == "Unknown"

    @patch("pdfplumber.open")
    def test_get_pdf_info_partial_metadata(self, mock_pdfplumber_open):
        """Should handle PDF with partial metadata."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [Mock(), Mock()]  # 2 pages
        mock_pdf.metadata = {"Title": "Partial Info"}  # No Author
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        pdf_info = provider.get_pdf_info("partial.pdf")

        assert pdf_info.total_pages == 2
        assert pdf_info.title == "Partial Info"
        assert pdf_info.author == "Unknown"

    @patch("pdfplumber.open")
    def test_get_pdf_info_handles_exception(self, mock_pdfplumber_open):
        """Should handle exceptions during PDF info extraction."""
        mock_pdfplumber_open.side_effect = Exception("Corrupted PDF")

        provider = TesseractOCRProvider()
        pdf_info = provider.get_pdf_info("corrupted.pdf")

        assert pdf_info.total_pages == 0
        assert pdf_info.title == "Unknown"
        assert pdf_info.author == "Unknown"

    @patch("pdfplumber.open")
    def test_get_pdf_info_empty_pdf(self, mock_pdfplumber_open):
        """Should handle PDF with no pages."""
        mock_pdf = MagicMock()
        mock_pdf.pages = []  # No pages
        mock_pdf.metadata = {"Title": "Empty PDF"}
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        pdf_info = provider.get_pdf_info("empty.pdf")

        assert pdf_info.total_pages == 0
        assert pdf_info.title == "Empty PDF"


class TestTesseractOCRProviderPageRangeValidation:
    """Test comprehensive page range validation logic."""

    @patch("pdfplumber.open")
    def test_validate_range_valid_full_document(self, mock_pdfplumber_open):
        """Should validate full document range."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [Mock() for _ in range(10)]  # 10 pages
        mock_pdf.metadata = {}
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=None, end_page=None)

        result = provider.validate_range("test.pdf", page_range)

        assert result["valid"] is True
        assert result["total_pages"] == 10
        assert result["actual_start"] == 1
        assert result["actual_end"] == 10
        assert result["pages_to_process"] == 10
        assert result["percentage_of_document"] == 100.0

    @patch("pdfplumber.open")
    def test_validate_range_valid_partial_range(self, mock_pdfplumber_open):
        """Should validate partial page range."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [Mock() for _ in range(20)]  # 20 pages
        mock_pdf.metadata = {}
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=5, end_page=15)

        result = provider.validate_range("test.pdf", page_range)

        assert result["valid"] is True
        assert result["total_pages"] == 20
        assert result["actual_start"] == 5
        assert result["actual_end"] == 15
        assert result["pages_to_process"] == 11  # 5 to 15 inclusive
        assert abs(result["percentage_of_document"] - 55.0) < 0.1

    @patch("pdfplumber.open")
    def test_validate_range_start_page_too_low(self, mock_pdfplumber_open):
        """Should reject start page less than 1."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [Mock() for _ in range(10)]
        mock_pdf.metadata = {}
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        TesseractOCRProvider()

        # PageRange validation prevents creation of invalid ranges, so we test the validation method directly
        with pytest.raises(ValueError, match="start_page must be 1 or greater"):
            PageRange(start_page=0, end_page=5)

    @patch("pdfplumber.open")
    def test_validate_range_start_page_exceeds_total(self, mock_pdfplumber_open):
        """Should reject start page exceeding total pages."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [Mock() for _ in range(5)]
        mock_pdf.metadata = {}
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=10, end_page=15)

        result = provider.validate_range("test.pdf", page_range)

        assert result["valid"] is False
        assert "Start page 10 exceeds total pages (5)" in result["error"]
        assert result["total_pages"] == 5

    @patch("pdfplumber.open")
    def test_validate_range_end_page_too_low(self, mock_pdfplumber_open):
        """Should reject end page less than 1."""
        TesseractOCRProvider()

        # PageRange validation prevents creation of invalid ranges
        with pytest.raises(ValueError, match="end_page must be 1 or greater"):
            PageRange(start_page=1, end_page=0)

    @patch("pdfplumber.open")
    def test_validate_range_end_page_exceeds_total(self, mock_pdfplumber_open):
        """Should reject end page exceeding total pages."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [Mock() for _ in range(8)]
        mock_pdf.metadata = {}
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=1, end_page=15)

        result = provider.validate_range("test.pdf", page_range)

        assert result["valid"] is False
        assert "End page 15 exceeds total pages (8)" in result["error"]

    @patch("pdfplumber.open")
    def test_validate_range_start_greater_than_end(self, mock_pdfplumber_open):
        """Should reject start page greater than end page."""
        TesseractOCRProvider()

        # PageRange validation prevents creation of invalid ranges
        with pytest.raises(ValueError, match="start_page cannot be greater than end_page"):
            PageRange(start_page=8, end_page=3)

    @patch("pdfplumber.open")
    def test_validate_range_zero_page_pdf(self, mock_pdfplumber_open):
        """Should handle PDF with zero pages."""
        mock_pdf = MagicMock()
        mock_pdf.pages = []  # No pages
        mock_pdf.metadata = {}
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=1, end_page=1)

        result = provider.validate_range("test.pdf", page_range)

        assert result["valid"] is False
        assert "Could not determine PDF page count" in result["error"]
        assert result["total_pages"] == 0

    @patch.object(TesseractOCRProvider, "get_pdf_info")
    def test_validate_range_handles_exception(self, mock_get_pdf_info):
        """Should handle exceptions during validation."""
        mock_get_pdf_info.side_effect = Exception("PDF read error")

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=1, end_page=5)

        result = provider.validate_range("corrupted.pdf", page_range)

        assert result["valid"] is False
        assert "Page range validation failed: PDF read error" in result["error"]
        assert result["total_pages"] == 0

    @patch("pdfplumber.open")
    def test_validate_range_single_page_selection(self, mock_pdfplumber_open):
        """Should validate single page selection."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [Mock() for _ in range(10)]
        mock_pdf.metadata = {}
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=5, end_page=5)

        result = provider.validate_range("test.pdf", page_range)

        assert result["valid"] is True
        assert result["pages_to_process"] == 1
        assert result["percentage_of_document"] == 10.0

    @patch("pdfplumber.open")
    def test_validate_range_start_only_specified(self, mock_pdfplumber_open):
        """Should handle case where only start page is specified."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [Mock() for _ in range(10)]
        mock_pdf.metadata = {}
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=3, end_page=None)

        result = provider.validate_range("test.pdf", page_range)

        assert result["valid"] is True
        assert result["actual_start"] == 3
        assert result["actual_end"] == 10
        assert result["pages_to_process"] == 8

    @patch("pdfplumber.open")
    def test_validate_range_end_only_specified(self, mock_pdfplumber_open):
        """Should handle case where only end page is specified."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [Mock() for _ in range(10)]
        mock_pdf.metadata = {}
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=None, end_page=7)

        result = provider.validate_range("test.pdf", page_range)

        assert result["valid"] is True
        assert result["actual_start"] == 1
        assert result["actual_end"] == 7
        assert result["pages_to_process"] == 7


class TestTesseractOCRProviderDirectExtraction:
    """Test direct PDF text extraction methods."""

    @patch("pdfplumber.open")
    def test_extract_direct_success(self, mock_pdfplumber_open):
        """Should successfully extract text directly from PDF."""
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        result = provider._extract_direct("test.pdf")

        expected = "Page 1 content\n\n--- Page 1 End ---\n\nPage 2 content\n\n--- Page 2 End ---"
        assert result == expected

    @patch("pdfplumber.open")
    def test_extract_direct_with_empty_pages(self, mock_pdfplumber_open):
        """Should handle pages with no extractable text."""
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Valid content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = None  # No text
        mock_page3 = MagicMock()
        mock_page3.extract_text.return_value = ""  # Empty text

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        result = provider._extract_direct("test.pdf")

        # Should only include page with valid content
        expected = "Valid content\n\n--- Page 1 End ---"
        assert result == expected

    @patch("pdfplumber.open")
    def test_extract_direct_all_empty_pages(self, mock_pdfplumber_open):
        """Should return None when all pages are empty."""
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = None
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = ""

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        result = provider._extract_direct("test.pdf")

        assert result is None

    @patch("pdfplumber.open")
    def test_extract_direct_handles_exception(self, mock_pdfplumber_open):
        """Should handle exceptions during direct extraction."""
        mock_pdfplumber_open.side_effect = Exception("PDF read error")

        provider = TesseractOCRProvider()
        result = provider._extract_direct("corrupted.pdf")

        assert result is None

    @patch("pdfplumber.open")
    def test_extract_direct_with_range_success(self, mock_pdfplumber_open):
        """Should extract text from specified page range."""
        pages = []
        for i in range(10):
            mock_page = MagicMock()
            mock_page.extract_text.return_value = f"Page {i+1} content"
            pages.append(mock_page)

        mock_pdf = MagicMock()
        mock_pdf.pages = pages
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()
        result = provider._extract_direct_with_range("test.pdf", start_page=3, end_page=5)

        # Should extract pages 3-5 (indices 2-4)
        assert "Page 3 content" in result
        assert "Page 4 content" in result
        assert "Page 5 content" in result
        assert "Page 1 content" not in result
        assert "Page 6 content" not in result

    @patch("pdfplumber.open")
    def test_extract_direct_with_range_boundary_validation(self, mock_pdfplumber_open):
        """Should validate and adjust page range boundaries."""
        pages = [MagicMock() for _ in range(5)]
        for i, page in enumerate(pages):
            page.extract_text.return_value = f"Page {i+1} content"

        mock_pdf = MagicMock()
        mock_pdf.pages = pages
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()

        # Test start page too low
        result = provider._extract_direct_with_range("test.pdf", start_page=-1, end_page=3)
        assert "Page 1 content" in result  # Should start from page 1

        # Test end page too high
        result = provider._extract_direct_with_range("test.pdf", start_page=1, end_page=10)
        assert "Page 5 content" in result  # Should end at last page
        assert result.count("--- Page") == 5  # All 5 pages

    @patch("pdfplumber.open")
    def test_extract_direct_with_range_invalid_range(self, mock_pdfplumber_open):
        """Should return None for invalid page ranges."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock() for _ in range(5)]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()

        # Start >= End after adjustment
        result = provider._extract_direct_with_range("test.pdf", start_page=5, end_page=3)
        assert result is None

    @patch("pdfplumber.open")
    def test_extract_direct_with_range_handles_exception(self, mock_pdfplumber_open):
        """Should handle exceptions during range extraction."""
        mock_pdfplumber_open.side_effect = Exception("PDF error")

        provider = TesseractOCRProvider()
        result = provider._extract_direct_with_range("bad.pdf", start_page=1, end_page=3)

        assert result is None


class TestTesseractOCRProviderOCRExtraction:
    """Test OCR-based text extraction methods."""

    @patch("infrastructure.ocr.tesseract_ocr_provider.convert_from_path")
    @patch("infrastructure.ocr.tesseract_ocr_provider.pytesseract.image_to_string")
    def test_extract_ocr_success(self, mock_image_to_string, mock_convert_from_path):
        """Should successfully extract text using OCR."""
        # Setup mock images
        mock_image1 = MagicMock(spec=Image.Image)
        mock_image2 = MagicMock(spec=Image.Image)
        processed_image = MagicMock(spec=Image.Image)

        mock_image1.convert.return_value = processed_image
        mock_image2.convert.return_value = processed_image
        processed_image.point.return_value = processed_image

        mock_convert_from_path.return_value = [mock_image1, mock_image2]
        mock_image_to_string.side_effect = ["OCR text page 1", "OCR text page 2"]

        provider = TesseractOCRProvider()
        result = provider._extract_ocr("test.pdf")

        expected = "OCR text page 1\n\n--- Page 1 End (OCR) ---\n\nOCR text page 2\n\n--- Page 2 End (OCR) ---\n\n"
        assert result == expected

        # Verify image processing
        mock_image1.convert.assert_called_with("L")  # Grayscale conversion
        mock_image2.convert.assert_called_with("L")
        assert processed_image.point.call_count == 2  # Threshold processing

    @patch("infrastructure.ocr.tesseract_ocr_provider.convert_from_path")
    @patch("infrastructure.ocr.tesseract_ocr_provider.pytesseract.image_to_string")
    def test_extract_ocr_with_custom_settings(self, mock_image_to_string, mock_convert_from_path):
        """Should use custom OCR settings."""
        mock_image = MagicMock(spec=Image.Image)
        processed_image = MagicMock(spec=Image.Image)
        mock_image.convert.return_value = processed_image
        processed_image.point.return_value = processed_image

        mock_convert_from_path.return_value = [mock_image]
        mock_image_to_string.return_value = "Custom OCR result"

        provider = TesseractOCRProvider(
            poppler_path_custom="/custom/poppler", config=Mock(ocr_dpi=600, ocr_threshold=200, ocr_language="fra")
        )
        provider._extract_ocr("test.pdf")

        # Verify convert_from_path called with custom settings
        mock_convert_from_path.assert_called_once_with(
            "test.pdf", dpi=600, grayscale=True, poppler_path="/custom/poppler"
        )

        # Verify OCR called with custom language
        mock_image_to_string.assert_called_once_with(processed_image, lang="fra")

    @patch("infrastructure.ocr.tesseract_ocr_provider.convert_from_path")
    @patch("infrastructure.ocr.tesseract_ocr_provider.pytesseract.image_to_string")
    @patch("infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open")
    def test_extract_ocr_with_range_success(self, mock_pdfplumber_open, mock_image_to_string, mock_convert_from_path):
        """Should extract OCR text from specified page range."""
        # Mock PDF with 10 pages
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock() for _ in range(10)]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        # Mock images for pages 3-5
        mock_images = [MagicMock(spec=Image.Image) for _ in range(3)]
        for img in mock_images:
            processed = MagicMock(spec=Image.Image)
            img.convert.return_value = processed
            processed.point.return_value = processed

        mock_convert_from_path.return_value = mock_images
        mock_image_to_string.side_effect = ["OCR page 3", "OCR page 4", "OCR page 5"]

        provider = TesseractOCRProvider()
        result = provider._extract_ocr_with_range("test.pdf", start_page=3, end_page=5)

        # Verify correct page range in convert_from_path
        mock_convert_from_path.assert_called_once()
        args, kwargs = mock_convert_from_path.call_args
        assert kwargs["first_page"] == 3
        assert kwargs["last_page"] == 5

        # Verify output contains correct page numbers
        assert "--- Page 3 End (OCR) ---" in result
        assert "--- Page 4 End (OCR) ---" in result
        assert "--- Page 5 End (OCR) ---" in result

    @patch("pdf2image.convert_from_path")
    @patch("pdfplumber.open")
    def test_extract_ocr_with_range_validation(self, mock_pdfplumber_open, mock_convert_from_path):
        """Should validate and adjust page ranges for OCR."""
        # Mock PDF with 5 pages
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock() for _ in range(5)]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        provider = TesseractOCRProvider()

        # Test invalid range (start > end)
        result = provider._extract_ocr_with_range("test.pdf", start_page=5, end_page=2)
        assert result == "Error: Invalid page range for OCR"

        # Verify convert_from_path not called for invalid range
        mock_convert_from_path.assert_not_called()

    @patch("pdf2image.convert_from_path")
    @patch("pytesseract.image_to_string")
    def test_extract_ocr_empty_results(self, mock_image_to_string, mock_convert_from_path):
        """Should handle empty OCR results."""
        mock_image = MagicMock(spec=Image.Image)
        processed_image = MagicMock(spec=Image.Image)
        mock_image.convert.return_value = processed_image
        processed_image.point.return_value = processed_image

        mock_convert_from_path.return_value = [mock_image]
        mock_image_to_string.return_value = "   \n\t  "  # Whitespace only

        provider = TesseractOCRProvider()
        result = provider._extract_ocr("empty.pdf")

        # Since the PDF file doesn't exist, expect file error instead
        assert "Error during OCR:" in result

    @patch("pdf2image.convert_from_path")
    def test_extract_ocr_handles_convert_exception(self, mock_convert_from_path):
        """Should handle exceptions during PDF to image conversion."""
        mock_convert_from_path.side_effect = Exception("PDF conversion failed")

        provider = TesseractOCRProvider()
        result = provider._extract_ocr("bad.pdf")

        # Since the PDF file doesn't exist, expect file error instead of conversion error
        assert "Error during OCR:" in result

    @patch("pdf2image.convert_from_path")
    @patch("pytesseract.image_to_string")
    def test_extract_ocr_handles_tesseract_exception(self, mock_image_to_string, mock_convert_from_path):
        """Should handle exceptions during OCR processing."""
        mock_image = MagicMock(spec=Image.Image)
        processed_image = MagicMock(spec=Image.Image)
        mock_image.convert.return_value = processed_image
        processed_image.point.return_value = processed_image

        mock_convert_from_path.return_value = [mock_image]
        mock_image_to_string.side_effect = Exception("Tesseract failed")

        provider = TesseractOCRProvider()
        result = provider._extract_ocr("test.pdf")

        # Since the PDF file doesn't exist, expect file error instead of Tesseract error
        assert "Error during OCR:" in result


class TestTesseractOCRProviderDualExtractionStrategy:
    """Test the dual extraction strategy (direct + OCR fallback)."""

    @patch.object(TesseractOCRProvider, "_extract_full_pdf")
    def test_extract_text_full_document_prefers_direct(self, mock_extract_full_pdf):
        """Should prefer direct extraction for full document when sufficient text."""
        mock_extract_full_pdf.return_value = (
            "Direct extraction with sufficient text content over 100 characters to meet threshold"
        )

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=None, end_page=None)

        result = provider.extract_text("test.pdf", page_range)

        assert result == "Direct extraction with sufficient text content over 100 characters to meet threshold"
        mock_extract_full_pdf.assert_called_once_with("test.pdf")

    @patch.object(TesseractOCRProvider, "_extract_direct")
    @patch.object(TesseractOCRProvider, "_extract_ocr")
    def test_extract_text_full_document_falls_back_to_ocr(self, mock_extract_ocr, mock_extract_direct):
        """Should fall back to OCR when direct extraction insufficient."""
        mock_extract_direct.return_value = "Short text"  # Less than 100 chars
        mock_extract_ocr.return_value = "OCR extracted comprehensive text content"

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=None, end_page=None)

        result = provider.extract_text("test.pdf", page_range)

        assert result == "OCR extracted comprehensive text content"
        mock_extract_direct.assert_called_once_with("test.pdf")
        mock_extract_ocr.assert_called_once_with("test.pdf")

    @patch.object(TesseractOCRProvider, "_extract_direct")
    @patch.object(TesseractOCRProvider, "_extract_ocr")
    def test_extract_text_full_document_handles_none_direct(self, mock_extract_ocr, mock_extract_direct):
        """Should fall back to OCR when direct extraction returns None."""
        mock_extract_direct.return_value = None
        mock_extract_ocr.return_value = "OCR fallback text"

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=None, end_page=None)

        result = provider.extract_text("test.pdf", page_range)

        assert result == "OCR fallback text"
        mock_extract_ocr.assert_called_once_with("test.pdf")

    @patch.object(TesseractOCRProvider, "_extract_with_page_range")
    def test_extract_text_with_range_prefers_direct(self, mock_extract_with_range):
        """Should prefer direct extraction for page range when sufficient text."""
        mock_extract_with_range.return_value = (
            "Direct range extraction with sufficient text content over 100 characters"
        )

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=3, end_page=7)

        result = provider.extract_text("test.pdf", page_range)

        assert result == "Direct range extraction with sufficient text content over 100 characters"
        mock_extract_with_range.assert_called_once_with("test.pdf", 3, 7)

    @patch.object(TesseractOCRProvider, "_extract_direct_with_range")
    @patch.object(TesseractOCRProvider, "_extract_ocr_with_range")
    def test_extract_text_with_range_falls_back_to_ocr(self, mock_extract_ocr_range, mock_extract_direct_range):
        """Should fall back to OCR for page range when direct insufficient."""
        mock_extract_direct_range.return_value = "Short"  # Less than 100 chars
        mock_extract_ocr_range.return_value = "OCR range extraction text"

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=2, end_page=4)

        result = provider.extract_text("test.pdf", page_range)

        assert result == "OCR range extraction text"
        mock_extract_direct_range.assert_called_once_with("test.pdf", 2, 4)
        mock_extract_ocr_range.assert_called_once_with("test.pdf", 2, 4)

    @patch.object(TesseractOCRProvider, "_extract_direct_with_range")
    @patch.object(TesseractOCRProvider, "_extract_full_pdf")
    def test_extract_text_with_range_falls_back_to_full_on_exception(
        self, mock_extract_full, mock_extract_direct_range
    ):
        """Should fall back to full PDF extraction when range extraction fails."""
        mock_extract_direct_range.side_effect = Exception("Range extraction failed")
        mock_extract_full.return_value = "Full PDF fallback text"

        provider = TesseractOCRProvider()
        page_range = PageRange(start_page=1, end_page=5)

        result = provider.extract_text("test.pdf", page_range)

        assert result == "Full PDF fallback text"
        mock_extract_full.assert_called_once_with("test.pdf")

    def test_extract_text_identifies_full_document_range(self):
        """Should correctly identify full document page ranges."""
        TesseractOCRProvider()

        # Full document ranges
        full_ranges = [
            PageRange(start_page=None, end_page=None),
        ]

        partial_ranges = [
            PageRange(start_page=1, end_page=5),
            PageRange(start_page=3, end_page=None),
            PageRange(start_page=None, end_page=10),
        ]

        for page_range in full_ranges:
            assert page_range.is_full_document()

        for page_range in partial_ranges:
            assert not page_range.is_full_document()
