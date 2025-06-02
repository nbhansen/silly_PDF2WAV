import pytest
from pathlib import Path
from pdf_to_audio.processors import PDFProcessor
from pdf_to_audio.text_processing import OCRProcessor, TextCleaner
from pdf_to_audio.audio_generation import TTSGenerator

@pytest.fixture
def sample_pdf_path(tmp_path):
    # Create a dummy PDF file for testing
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%Test PDF content")
    return pdf_path

@pytest.fixture
def pdf_processor():
    return PDFProcessor()

def test_pdf_processor_initialization(pdf_processor):
    assert isinstance(pdf_processor, PDFProcessor)
    assert hasattr(pdf_processor, 'ocr_processor')
    assert hasattr(pdf_processor, 'text_cleaner')
    assert hasattr(pdf_processor, 'tts_generator')

def test_process_pdf_invalid_file(pdf_processor, tmp_path):
    invalid_path = tmp_path / "nonexistent.pdf"
    with pytest.raises(FileNotFoundError):
        pdf_processor.process_pdf(str(invalid_path))

def test_process_pdf_empty_file(pdf_processor, tmp_path):
    empty_pdf = tmp_path / "empty.pdf"
    empty_pdf.write_bytes(b"%PDF-1.4\n")
    with pytest.raises(ValueError):
        pdf_processor.process_pdf(str(empty_pdf))

@pytest.mark.skipif(not Path("/usr/bin/tesseract").exists(),
                   reason="Tesseract not installed")
def test_ocr_processor():
    processor = OCRProcessor()
    assert processor is not None
    # Add more OCR-specific tests here

def test_text_cleaner():
    cleaner = TextCleaner()
    assert cleaner is not None
    # Add more text cleaning tests here

def test_tts_generator():
    generator = TTSGenerator()
    assert generator is not None
    # Add more TTS-specific tests here 