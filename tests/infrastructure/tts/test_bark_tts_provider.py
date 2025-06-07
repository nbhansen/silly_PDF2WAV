import pytest
from unittest.mock import MagicMock, patch, mock_open
from domain.models import BarkConfig
import os

# Mock the BARK_AVAILABLE flag to ensure BarkTTSProvider class is defined
# This needs to be done before importing BarkTTSProvider if BARK_AVAILABLE is at module level
# For this test, we'll assume BARK_AVAILABLE is True for the main class definition.
# If it's False, the fallback class is used, which has simpler tests.

# Mock the bark and scipy.io.wavfile imports at the module level
with patch('infrastructure.tts.bark_tts_provider.BARK_AVAILABLE', True):
    with patch('infrastructure.tts.bark_tts_provider.preload_models', MagicMock()):
        with patch('infrastructure.tts.bark_tts_provider.generate_audio', MagicMock()):
            with patch('infrastructure.tts.bark_tts_provider.write_wav', MagicMock()):
                from infrastructure.tts.bark_tts_provider import BarkTTSProvider, BARK_SAMPLE_RATE

@pytest.fixture
def mock_preload_models():
    """Mock bark.preload_models."""
    with patch('infrastructure.tts.bark_tts_provider.preload_models') as mock_pm:
        yield mock_pm

@pytest.fixture
def mock_generate_audio():
    """Mock bark.generate_audio."""
    with patch('infrastructure.tts.bark_tts_provider.generate_audio') as mock_ga:
        yield mock_ga

@pytest.fixture
def mock_write_wav():
    """Mock scipy.io.wavfile.write."""
    with patch('infrastructure.tts.bark_tts_provider.write_wav') as mock_ww:
        yield mock_ww

@pytest.fixture
def mock_os_remove():
    """Mock os.remove."""
    with patch('os.remove') as mock_or:
        yield mock_or

@pytest.fixture
def mock_torch_cuda_is_available():
    """Mock torch.cuda.is_available."""
    with patch('torch.cuda.is_available') as mock_cuda:
        yield mock_cuda

@pytest.fixture
def bark_config_cpu():
    """Fixture for BarkConfig using CPU."""
    return BarkConfig(use_gpu=False, use_small_models=True, history_prompt=None)

@pytest.fixture
def bark_config_gpu():
    """Fixture for BarkConfig using GPU."""
    return BarkConfig(use_gpu=True, use_small_models=False, history_prompt="v2/en_speaker_6")

# Tests for __init__
def test_bark_tts_provider_init_cpu(mock_preload_models, mock_torch_cuda_is_available, bark_config_cpu):
    """Test initialization with CPU configuration."""
    mock_torch_cuda_is_available.return_value = False
    provider = BarkTTSProvider(bark_config_cpu)
    mock_preload_models.assert_called_once_with(
        text_use_gpu=False, text_use_small=True,
        coarse_use_gpu=False, coarse_use_small=True,
        fine_use_gpu=False, fine_use_small=True,
        codec_use_gpu=True
    )
    assert provider.models_loaded is True # Assuming preload_models doesn't raise
    assert provider.history_prompt is None
    assert provider.output_format == "wav"
    assert provider.sample_rate == BARK_SAMPLE_RATE

def test_bark_tts_provider_init_gpu_available(mock_preload_models, mock_torch_cuda_is_available, bark_config_gpu):
    """Test initialization with GPU configuration when CUDA is available."""
    mock_torch_cuda_is_available.return_value = True
    provider = BarkTTSProvider(bark_config_gpu)
    mock_preload_models.assert_called_once_with(
        text_use_gpu=True, text_use_small=False,
        coarse_use_gpu=True, coarse_use_small=False,
        fine_use_gpu=True, fine_use_small=False,
        codec_use_gpu=True
    )
    assert provider.models_loaded is True
    assert provider.history_prompt == "v2/en_speaker_6"

def test_bark_tts_provider_init_gpu_not_available(mock_preload_models, mock_torch_cuda_is_available, bark_config_gpu):
    """Test initialization with GPU configuration when CUDA is not available."""
    mock_torch_cuda_is_available.return_value = False
    provider = BarkTTSProvider(bark_config_gpu)
    mock_preload_models.assert_called_once_with(
        text_use_gpu=False, text_use_small=False, # Should fall back to CPU
        coarse_use_gpu=False, coarse_use_small=False,
        fine_use_gpu=False, fine_use_small=False,
        codec_use_gpu=True
    )
    assert provider.models_loaded is True

def test_bark_tts_provider_init_preload_failure(mock_preload_models, bark_config_cpu):
    """Test initialization when preload_models fails."""
    mock_preload_models.side_effect = Exception("Preload error")
    provider = BarkTTSProvider(bark_config_cpu)
    assert provider.models_loaded is False

# Tests for generate_audio_data
def test_generate_audio_data_success(mock_preload_models, mock_generate_audio, mock_write_wav, mock_os_remove, bark_config_cpu):
    """Test successful audio generation."""
    mock_preload_models.return_value = None # Ensure models are considered loaded
    provider = BarkTTSProvider(bark_config_cpu)
    provider.models_loaded = True # Explicitly set for testing generate_audio_data in isolation

    mock_audio_array = MagicMock()
    mock_generate_audio.return_value = mock_audio_array

    # Mock file operations for saving and reading WAV
    mock_file_content = b"mock_wav_data"
    with patch("builtins.open", mock_open(read_data=mock_file_content)) as mocked_file_open:
        audio_data = provider.generate_audio_data("Hello, world!")

        mock_generate_audio.assert_called_once_with("Hello, world!", history_prompt=None)
        mock_write_wav.assert_called_once_with("temp_bark_audio.wav", BARK_SAMPLE_RATE, mock_audio_array)
        mocked_file_open.assert_called_once_with("temp_bark_audio.wav", "rb")
        mock_os_remove.assert_called_once_with("temp_bark_audio.wav")
        assert audio_data == mock_file_content

def test_generate_audio_data_empty_text(mock_preload_models, mock_generate_audio, bark_config_cpu):
    """Test audio generation with empty text."""
    mock_preload_models.return_value = None
    provider = BarkTTSProvider(bark_config_cpu)
    provider.models_loaded = True

    audio_data = provider.generate_audio_data("")
    mock_generate_audio.assert_not_called()
    assert audio_data == b""

def test_generate_audio_data_error_text(mock_preload_models, mock_generate_audio, bark_config_cpu):
    """Test audio generation with error-like text."""
    mock_preload_models.return_value = None
    provider = BarkTTSProvider(bark_config_cpu)
    provider.models_loaded = True

    audio_data = provider.generate_audio_data("Error: Something went wrong")
    mock_generate_audio.assert_not_called()
    assert audio_data == b""

def test_generate_audio_data_models_not_loaded(mock_generate_audio, bark_config_cpu):
    """Test audio generation when models are not loaded."""
    provider = BarkTTSProvider(bark_config_cpu)
    provider.models_loaded = False # Ensure models are not loaded

    audio_data = provider.generate_audio_data("Hello")
    mock_generate_audio.assert_not_called()
    assert audio_data == b""

def test_generate_audio_data_generation_failure(mock_preload_models, mock_generate_audio, bark_config_cpu):
    """Test audio generation when bark.generate_audio raises an exception."""
    mock_preload_models.return_value = None
    provider = BarkTTSProvider(bark_config_cpu)
    provider.models_loaded = True

    mock_generate_audio.side_effect = Exception("Bark generation failed")

    audio_data = provider.generate_audio_data("Test failure")
    mock_generate_audio.assert_called_once_with("Test failure", history_prompt=None)
    assert audio_data == b""

# Tests for get_output_format
def test_get_output_format(bark_config_cpu):
    """Test get_output_format method."""
    provider = BarkTTSProvider(bark_config_cpu)
    assert provider.get_output_format() == "wav"

# Test the fallback BarkTTSProvider when BARK_AVAILABLE is False
def test_fallback_bark_tts_provider():
    """Test the fallback BarkTTSProvider when Bark library is not available."""
    with patch('infrastructure.tts.bark_tts_provider.BARK_AVAILABLE', False):
        # Reload the module to pick up the mocked BARK_AVAILABLE
        import importlib
        import infrastructure.tts.bark_tts_provider
        importlib.reload(infrastructure.tts.bark_tts_provider)
        from infrastructure.tts.bark_tts_provider import BarkTTSProvider as FallbackBarkTTSProvider
        from domain.models import BarkConfig

        provider = FallbackBarkTTSProvider(BarkConfig(use_gpu=False, use_small_models=True, history_prompt=None))
        assert provider.generate_audio_data("test") == b""
        assert provider.get_output_format() == "wav"