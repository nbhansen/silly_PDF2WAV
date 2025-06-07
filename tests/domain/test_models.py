import pytest
from domain.models import PageRange, ProcessingRequest, PDFInfo, ProcessingResult, TTSConfig, CoquiConfig, GTTSConfig, BarkConfig, GeminiConfig

def test_page_range_full_document():
    """Test PageRange for a full document."""
    page_range = PageRange()
    assert page_range.is_full_document() == True
    page_range_start = PageRange(start_page=1)
    assert page_range_start.is_full_document() == False
    page_range_end = PageRange(end_page=10)
    assert page_range_end.is_full_document() == False
    page_range_partial = PageRange(start_page=1, end_page=5)
    assert page_range_partial.is_full_document() == False

def test_processing_request_instantiation():
    """Test ProcessingRequest instantiation."""
    page_range = PageRange(start_page=1, end_page=5)
    request = ProcessingRequest(
        pdf_path="test.pdf",
        output_name="test_audio",
        page_range=page_range
    )
    assert request.pdf_path == "test.pdf"
    assert request.output_name == "test_audio"
    assert request.page_range == page_range

def test_pdf_info_instantiation():
    """Test PDFInfo instantiation."""
    pdf_info = PDFInfo(
        total_pages=10,
        title="Test Title",
        author="Test Author"
    )
    assert pdf_info.total_pages == 10
    assert pdf_info.title == "Test Title"
    assert pdf_info.author == "Test Author"

def test_processing_result_success():
    """Test ProcessingResult for a successful outcome."""
    result = ProcessingResult(
        success=True,
        audio_files=["file1.mp3", "file2.mp3"],
        combined_mp3_file="combined.mp3"
    )
    assert result.success == True
    assert result.audio_files == ["file1.mp3", "file2.mp3"]
    assert result.combined_mp3_file == "combined.mp3"
    assert result.error is None
    assert result.debug_info is None

def test_processing_result_failure():
    """Test ProcessingResult for a failed outcome."""
    result = ProcessingResult(
        success=False,
        error="Conversion failed",
        debug_info={"step": "audio_gen"}
    )
    assert result.success == False
    assert result.audio_files is None
    assert result.combined_mp3_file is None
    assert result.error == "Conversion failed"
    assert result.debug_info == {"step": "audio_gen"}

def test_tts_config_instantiation():
    """Test TTSConfig instantiation with default and custom values."""
    config_default = TTSConfig()
    assert config_default.voice_quality == "medium"
    assert config_default.speaking_style == "neutral"
    assert config_default.speed == 1.0
    assert config_default.coqui is None
    assert config_default.gtts is None
    assert config_default.bark is None
    assert config_default.gemini is None

    config_custom = TTSConfig(
        voice_quality="high",
        speaking_style="professional",
        speed=1.2
    )
    assert config_custom.voice_quality == "high"
    assert config_custom.speaking_style == "professional"
    assert config_custom.speed == 1.2

def test_coqui_config_instantiation():
    """Test CoquiConfig instantiation."""
    config = CoquiConfig(model_name="test_model", speaker="test_speaker", use_gpu=True)
    assert config.model_name == "test_model"
    assert config.speaker == "test_speaker"
    assert config.use_gpu == True

def test_gtts_config_instantiation():
    """Test GTTSConfig instantiation."""
    config = GTTSConfig(lang="es", tld="com", slow=True)
    assert config.lang == "es"
    assert config.tld == "com"
    assert config.slow == True

def test_bark_config_instantiation():
    """Test BarkConfig instantiation."""
    config = BarkConfig(use_gpu=False, use_small_models=True, history_prompt="test_prompt")
    assert config.use_gpu == False
    assert config.use_small_models == True
    assert config.history_prompt == "test_prompt"

def test_gemini_config_instantiation():
    """Test GeminiConfig instantiation."""
    config = GeminiConfig(voice_name="Solar", style_prompt="friendly", api_key="test_key")
    assert config.voice_name == "Solar"
    assert config.style_prompt == "friendly"
    assert config.api_key == "test_key"

def test_tts_config_with_nested_configs():
    """Test TTSConfig with nested engine-specific configurations."""
    coqui_cfg = CoquiConfig(model_name="coqui_model")
    gtts_cfg = GTTSConfig(lang="fr")
    tts_config = TTSConfig(coqui=coqui_cfg, gtts=gtts_cfg)

    assert tts_config.coqui == coqui_cfg
    assert tts_config.gtts == gtts_cfg
    assert tts_config.bark is None
    assert tts_config.gemini is None