import pytest
from unittest.mock import MagicMock, patch, mock_open
from domain.models import GTTSConfig
import os

# Mock the GTTS_AVAILABLE flag to ensure GTTSProvider class is defined
with patch('infrastructure.tts.gtts_provider.GTTS_AVAILABLE', True):
    with patch('infrastructure.tts.gtts_provider.gTTS', MagicMock()):
        from infrastructure.tts.gtts_provider import GTTSProvider

@pytest.fixture
def mock_gtts():
    """Mock gTTS class."""
    with patch('infrastructure.tts.gtts_provider.gTTS') as mock_gtts_class:
        mock_instance = MagicMock()
        mock_gtts_class.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_os_remove():
    """Mock os.remove."""
    with patch('os.remove') as mock_or:
        yield mock_or

@pytest.fixture
def gtts_config_en():
    """Fixture for GTTSConfig with English language."""
    return GTTSConfig(lang="en", tld="com", slow=False)

# Tests for __init__
def test_gtts_provider_init_success(gtts_config_en):
    """Test successful initialization of GTTSProvider."""
    provider = GTTSProvider(gtts_config_en)
    assert provider.lang == "en"
    assert provider.tld == "com"
    assert provider.slow is False
    assert provider.output_format == "mp3"

# Tests for generate_audio_data
def test_generate_audio_data_success(mock_gtts, mock_os_remove, gtts_config_en):
    """Test successful audio generation."""
    provider = GTTSProvider(gtts_config_en)
    
    mock_gtts_instance = mock_gtts.return_value
    mock_gtts_instance.save.return_value = None # save method doesn't return anything

    mock_file_content = b"mock_mp3_data"
    with patch("builtins.open", mock_open(read_data=mock_file_content)) as mocked_file_open:
        text_to_speak = "Hello, gTTS!"
        audio_data = provider.generate_audio_data(text_to_speak)

        mock_gtts.assert_called_once_with(text=text_to_speak, lang="en", tld="com", slow=False)
        mock_gtts_instance.save.assert_called_once_with("temp_gtts_audio.mp3")
        mocked_file_open.assert_called_once_with("temp_gtts_audio.mp3", "rb")
        mock_os_remove.assert_called_once_with("temp_gtts_audio.mp3")
        assert audio_data == mock_file_content

def test_generate_audio_data_empty_text(mock_gtts, gtts_config_en):
    """Test audio generation with empty text."""
    provider = GTTSProvider(gtts_config_en)
    audio_data = provider.generate_audio_data("")
    mock_gtts.assert_not_called()
    assert audio_data == b""

def test_generate_audio_data_error_text(mock_gtts, gtts_config_en):
    """Test audio generation with error-like text."""
    provider = GTTSProvider(gtts_config_en)
    audio_data = provider.generate_audio_data("Error: API failed")
    mock_gtts.assert_not_called()
    assert audio_data == b""

def test_generate_audio_data_generation_failure(mock_gtts, gtts_config_en):
    """Test audio generation when gTTS raises an exception."""
    provider = GTTSProvider(gtts_config_en)
    mock_gtts.side_effect = Exception("gTTS generation failed")

    audio_data = provider.generate_audio_data("Test failure")
    mock_gtts.assert_called_once()
    assert audio_data == b""

# Tests for get_output_format
def test_get_output_format(gtts_config_en):
    """Test get_output_format method."""
    provider = GTTSProvider(gtts_config_en)
    assert provider.get_output_format() == "mp3"

# Test the fallback GTTSProvider when GTTS_AVAILABLE is False
def test_fallback_gtts_provider():
    """Test the fallback GTTSProvider when gTTS library is not available."""
    with patch('infrastructure.tts.gtts_provider.GTTS_AVAILABLE', False):
        # Reload the module to pick up the mocked GTTS_AVAILABLE
        import importlib
        import infrastructure.tts.gtts_provider
        importlib.reload(infrastructure.tts.gtts_provider)
        from infrastructure.tts.gtts_provider import GTTSProvider as FallbackGTTSProvider
        from domain.models import GTTSConfig

        provider = FallbackGTTSProvider(GTTSConfig(lang="en", tld="com", slow=False))
        assert provider.generate_audio_data("test") == b""
        assert provider.get_output_format() == "mp3"