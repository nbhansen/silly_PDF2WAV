# tests/domain/test_models.py
from domain.models import (
    PageRange, ProcessingRequest, PDFInfo, ProcessingResult, 
    TTSConfig, CoquiConfig, GTTSConfig, BarkConfig, GeminiConfig
)

def test_page_range_full_document():
    page_range = PageRange()
    assert page_range.is_full_document() == True
    
    page_range_partial = PageRange(start_page=1, end_page=5)
    assert page_range_partial.is_full_document() == False

def test_processing_request():
    page_range = PageRange(start_page=1, end_page=5)
    request = ProcessingRequest(
        pdf_path="test.pdf",
        output_name="test_audio",
        page_range=page_range
    )
    assert request.pdf_path == "test.pdf"
    assert request.output_name == "test_audio"
    assert request.page_range == page_range

def test_pdf_info():
    pdf_info = PDFInfo(total_pages=10, title="Test Title", author="Test Author")
    assert pdf_info.total_pages == 10
    assert pdf_info.title == "Test Title"
    assert pdf_info.author == "Test Author"

def test_processing_result_success():
    result = ProcessingResult(
        success=True,
        audio_files=["file1.mp3", "file2.mp3"],
        combined_mp3_file="combined.mp3"
    )
    assert result.success == True
    assert result.audio_files == ["file1.mp3", "file2.mp3"]
    assert result.combined_mp3_file == "combined.mp3"
    assert result.error is None

def test_processing_result_failure():
    result = ProcessingResult(
        success=False,
        error="Conversion failed"
    )
    assert result.success == False
    assert result.error == "Conversion failed"
    assert result.audio_files is None

def test_tts_config_defaults():
    config = TTSConfig()
    assert config.voice_quality == "medium"
    assert config.speaking_style == "neutral"
    assert config.speed == 1.0

def test_tts_config_with_engines():
    coqui_cfg = CoquiConfig(model_name="test_model", use_gpu=True)
    gtts_cfg = GTTSConfig(lang="en", tld="com")
    
    config = TTSConfig(
        voice_quality="high",
        coqui=coqui_cfg,
        gtts=gtts_cfg
    )
    
    assert config.voice_quality == "high"
    assert config.coqui.model_name == "test_model"
    assert config.coqui.use_gpu == True
    assert config.gtts.lang == "en"
    assert config.gtts.tld == "com"