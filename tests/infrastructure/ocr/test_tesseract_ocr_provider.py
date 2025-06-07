import pytest
from unittest.mock import patch, MagicMock
from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider
from domain.models import PDFInfo, PageRange

@pytest.fixture
def ocr_provider(mocker):
    """Fixture for TesseractOCRProvider instance."""
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pytesseract.image_to_string', new_callable=MagicMock)
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', new_callable=MagicMock)
    provider = TesseractOCRProvider()
    yield provider

# Tests for get_pdf_info
def test_get_pdf_info_success(ocr_provider, mocker):
    """Test successful retrieval of PDF information."""
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock(), MagicMock()]
    mock_pdf.metadata = {'Title': 'Test Document', 'Author': 'Test Author'}
    mock_pdfplumber = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    pdf_info = ocr_provider.get_pdf_info("dummy.pdf")

    assert pdf_info.total_pages == 2
    assert pdf_info.title == "Test Document"
    assert pdf_info.author == "Test Author"
    mock_pdfplumber.assert_called_once_with("dummy.pdf")

def test_get_pdf_info_no_metadata(ocr_provider, mocker):
    """Test retrieval of PDF information when metadata is missing."""
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock()]
    mock_pdf.metadata = None
    mock_pdfplumber = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    pdf_info = ocr_provider.get_pdf_info("dummy.pdf")

    assert pdf_info.total_pages == 1
    assert pdf_info.title == "Unknown"
    assert pdf_info.author == "Unknown"

def test_get_pdf_info_error_handling(ocr_provider, mocker):
    """Test error handling during PDF information retrieval."""
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', side_effect=Exception("File not found"))

    pdf_info = ocr_provider.get_pdf_info("nonexistent.pdf")

    assert pdf_info.total_pages == 0
    assert pdf_info.title == "Unknown"
    assert pdf_info.author == "Unknown"
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open').assert_called_once_with("nonexistent.pdf")

# Tests for extract_text (formerly extract_text_from_pdf)
def test_extract_text_full_pdf_direct_success(ocr_provider, mocker):
    """Test successful direct text extraction for full PDF."""
    mock_pdf = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Text from page 1."
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Text from page 2."
    mock_pdf.pages = [mock_page1, mock_page2]
    mock_pdfplumber = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    page_range = PageRange(start_page=None, end_page=None)
    extracted_text = ocr_provider.extract_text("dummy.pdf", page_range)

    assert "Text from page 1." in extracted_text
    assert "Text from page 2." in extracted_text
    assert "--- Page 1 End ---" in extracted_text
    assert "--- Page 2 End ---" in extracted_text
    mock_pdfplumber.assert_called_once_with("dummy.pdf")
    mock_page1.extract_text.assert_called_once()
    mock_page2.extract_text.assert_called_once()

def test_extract_text_full_pdf_ocr_fallback(ocr_provider, mocker):
    """Test OCR fallback for full PDF when direct extraction fails."""
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock()]
    mock_pdf.pages[0].extract_text.return_value = None # Simulate no direct text
    mock_pdfplumber = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    mock_image = MagicMock()
    mock_pdf2image = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdf2image.convert_from_path', return_value=[mock_image])
    mock_image.convert.return_value.point.return_value = mock_image # Chain calls
    mock_pytesseract = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pytesseract.image_to_string', return_value="OCR Text from page 1.")

    page_range = PageRange(start_page=None, end_page=None)
    extracted_text = ocr_provider.extract_text("dummy.pdf", page_range)

    assert "OCR Text from page 1." in extracted_text
    assert "--- Page 1 End (OCR) ---" in extracted_text
    mock_pdfplumber.assert_called_once_with("dummy.pdf") # Called for direct attempt
    mock_pdf2image.assert_called_once_with("dummy.pdf", dpi=300, grayscale=True, poppler_path=None)
    mock_pytesseract.assert_called_once_with(mock_image, lang='eng')

def test_extract_text_page_range_direct_success(ocr_provider, mocker):
    """Test successful direct text extraction for a specific page range."""
    mock_pdf = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Text from page 1."
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Text from page 2."
    mock_page3 = MagicMock()
    mock_page3.extract_text.return_value = "Text from page 3."
    mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
    mock_pdf.metadata = {'Title': 'Test Document', 'Author': 'Test Author'} # Ensure metadata is present
    mock_pdfplumber = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    page_range = PageRange(start_page=2, end_page=2)
    extracted_text = ocr_provider.extract_text("dummy.pdf", page_range)

    assert "Text from page 2." in extracted_text
    assert "--- Page 2 End ---" in extracted_text
    assert "Text from page 1." not in extracted_text
    assert "Text from page 3." not in extracted_text
    mock_pdfplumber.assert_called_once_with("dummy.pdf")
    mock_page2.extract_text.assert_called_once()

def test_extract_text_page_range_ocr_fallback(ocr_provider, mocker):
    """Test OCR fallback for page range when direct extraction fails."""
    mock_pdf = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = None # Simulate no direct text
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = None # Simulate no direct text
    mock_pdf.pages = [mock_page1, mock_page2]
    mock_pdf.metadata = {'Title': 'Test Document', 'Author': 'Test Author'} # Ensure metadata is present
    mock_pdfplumber = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    mock_image = MagicMock()
    mock_pdf2image = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdf2image.convert_from_path', return_value=[mock_image])
    mock_image.convert.return_value.point.return_value = mock_image
    mock_pytesseract = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pytesseract.image_to_string', return_value="OCR Text from page 1.")

    page_range = PageRange(start_page=1, end_page=1)
    extracted_text = ocr_provider.extract_text("dummy.pdf", page_range)

    assert "OCR Text from page 1." in extracted_text
    assert "--- Page 1 End (OCR) ---" in extracted_text
    mock_pdfplumber.assert_called_once_with("dummy.pdf") # Called for direct attempt
    mock_pdf2image.assert_called_once_with(
        "dummy.pdf", dpi=300, grayscale=True, first_page=1, last_page=1, poppler_path=None
    )
    mock_pytesseract.assert_called_once_with(mock_image, lang='eng')

def test_extract_text_invalid_pdf_path(ocr_provider, mocker):
    """Test extract_text with an invalid PDF path."""
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', side_effect=Exception("File not found"))
    page_range = PageRange(start_page=1, end_page=1)
    extracted_text = ocr_provider.extract_text("nonexistent.pdf", page_range)
    assert "Error during OCR" in extracted_text or "OCR process yielded no text." in extracted_text # Depending on exact fallback behavior
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open').assert_called_once_with("nonexistent.pdf")

def test_extract_text_empty_pdf(ocr_provider, mocker):
    """Test extract_text with an empty PDF (no pages)."""
    mock_pdf = MagicMock()
    mock_pdf.pages = []
    mock_pdf.metadata = {'Title': 'Test Document', 'Author': 'Test Author'} # Ensure metadata is present
    mock_pdfplumber = mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    # Ensure OCR fallback also returns no text
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdf2image.convert_from_path', return_value=[])
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pytesseract.image_to_string', return_value="")

    page_range = PageRange(start_page=1, end_page=1)
    extracted_text = ocr_provider.extract_text("empty.pdf", page_range)
    assert "OCR process yielded no text." in extracted_text
    mock_pdfplumber.assert_called_once_with("empty.pdf")

# Tests for validate_page_range
def test_validate_page_range_valid_full_document(ocr_provider, mocker):
    """Test valid full document page range."""
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock(), MagicMock(), MagicMock()] # 3 pages
    mock_pdf.metadata = {'Title': 'Test Document', 'Author': 'Test Author'}
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    page_range = PageRange(start_page=None, end_page=None)
    result = ocr_provider.validate_range("dummy.pdf", page_range)

    assert result['valid'] is True
    assert result['total_pages'] == 3
    assert result['actual_start'] == 1
    assert result['actual_end'] == 3
    assert result['pages_to_process'] == 3
    assert result['percentage_of_document'] == 100.0

def test_validate_page_range_valid_partial_document(ocr_provider, mocker):
    """Test valid partial document page range."""
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()] # 5 pages
    mock_pdf.metadata = {'Title': 'Test Document', 'Author': 'Test Author'}
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    page_range = PageRange(start_page=2, end_page=4)
    result = ocr_provider.validate_range("dummy.pdf", page_range)

    assert result['valid'] is True
    assert result['total_pages'] == 5
    assert result['actual_start'] == 2
    assert result['actual_end'] == 4
    assert result['pages_to_process'] == 3
    assert result['percentage_of_document'] == 60.0

def test_validate_page_range_start_page_less_than_1(ocr_provider, mocker):
    """Test validation with start page less than 1."""
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock()]
    mock_pdf.metadata = {'Title': 'Test Document', 'Author': 'Test Author'}
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    page_range = PageRange(start_page=0, end_page=1)
    result = ocr_provider.validate_range("dummy.pdf", page_range)

    assert result['valid'] is False
    assert "Start page must be 1 or greater" in result['error']
    assert result['total_pages'] == 1

def test_validate_page_range_start_page_exceeds_total(ocr_provider, mocker):
    """Test validation with start page exceeding total pages."""
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock()] # 1 page
    mock_pdf.metadata = {'Title': 'Test Document', 'Author': 'Test Author'}
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    page_range = PageRange(start_page=2, end_page=None)
    result = ocr_provider.validate_range("dummy.pdf", page_range)

    assert result['valid'] is False
    assert "Start page 2 exceeds total pages (1)" in result['error']
    assert result['total_pages'] == 1

def test_validate_page_range_end_page_less_than_1(ocr_provider, mocker):
    """Test validation with end page less than 1."""
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock()]
    mock_pdf.metadata = {'Title': 'Test Document', 'Author': 'Test Author'}
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    page_range = PageRange(start_page=1, end_page=0)
    result = ocr_provider.validate_range("dummy.pdf", page_range)

    assert result['valid'] is False
    assert "End page must be 1 or greater" in result['error']
    assert result['total_pages'] == 1

def test_validate_page_range_end_page_exceeds_total(ocr_provider, mocker):
    """Test validation with end page exceeding total pages."""
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock(), MagicMock()] # 2 pages
    mock_pdf.metadata = {'Title': 'Test Document', 'Author': 'Test Author'}
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    page_range = PageRange(start_page=1, end_page=3)
    result = ocr_provider.validate_range("dummy.pdf", page_range)

    assert result['valid'] is False
    assert "End page 3 exceeds total pages (2)" in result['error']
    assert result['total_pages'] == 2

def test_validate_page_range_start_greater_than_end(ocr_provider, mocker):
    """Test validation with start page greater than end page."""
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock(), MagicMock(), MagicMock()] # 3 pages
    mock_pdf.metadata = {'Title': 'Test Document', 'Author': 'Test Author'}
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', return_value=mock_pdf)

    page_range = PageRange(start_page=3, end_page=1)
    result = ocr_provider.validate_range("dummy.pdf", page_range)

    assert result['valid'] is False
    assert "Start page (3) cannot be greater than end page (1)" in result['error']
    assert result['total_pages'] == 3

def test_validate_page_range_pdf_info_failure(ocr_provider, mocker):
    """Test validation when get_pdf_info fails."""
    mocker.patch('infrastructure.ocr.tesseract_ocr_provider.pdfplumber.open', side_effect=Exception("PDF corrupted"))

    page_range = PageRange(start_page=1, end_page=1)
    result = ocr_provider.validate_range("corrupted.pdf", page_range)

    assert result['valid'] is False
    assert "Could not determine PDF page count" in result['error']
    assert result['total_pages'] == 0