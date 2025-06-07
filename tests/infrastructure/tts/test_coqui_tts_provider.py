import pytest
from unittest.mock import MagicMock, patch, mock_open
from domain.models import CoquiConfig
import os

# Mock the COQUI_TTS_AVAILABLE flag to ensure CoquiTTSProvider class is defined
with patch('infrastructure.tts.coqui_tts_provider.COQUI_TTS_AVAILABLE', True):
    with patch('infrastructure.tts.coqui_tts_provider.CoquiTTS_API', MagicMock()): # Mock the TTS.api.TTS class
        from infrastructure.tts.coqui_tts_provider import CoquiTTSProvider

@pytest.fixture
def mock_coqui_tts_api():
    """Mock TTS.api.TTS class."""
    with patch('infrastructure.tts.coqui_tts_provider.CoquiTTS_API') as mock_tts_api_class:
        mock_instance = MagicMock()
        mock_tts_api_class.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_torch_cuda_is_available():
    """Mock torch.cuda.is_available."""
    with patch('torch.cuda.is_available') as mock_cuda:
        yield mock_cuda

@pytest.fixture
def mock_os_remove():
    """Mock os.remove."""
    with patch('os.remove') as mock_or:
        yield mock_or

@pytest.fixture
def coqui_config_cpu():
    """Fixture for CoquiConfig using CPU."""
    return CoquiConfig(model_name="tts_models/en/ljspeech/vits", speaker=None, use_gpu=False)

@pytest.fixture
def coqui_config_gpu():
    """Fixture for CoquiConfig using GPU."""
    return CoquiConfig(model_name="tts_models/en/vctk/vits", speaker="p225", use_gpu=True)

# Tests for __init__
def test_coqui_tts_provider_init_cpu(mock_coqui_tts_api, mock_torch_cuda_is_available, coqui_config_cpu):
    """Test initialization with CPU configuration."""
    mock_torch_cuda_is_available.return_value = False
    provider = CoquiTTSProvider(coqui_config_cpu)

    mock_coqui_tts_api.assert_called_once_with(model_name="tts_models/en/ljspeech/vits")
    mock_coqui_tts_api.return_value.to.assert_called_once_with("cpu")
    assert provider.tts_model is not None
    assert provider.is_multi_speaker is False # Default mock behavior
    assert provider.speaker_to_use is None
    assert provider.output_format == "wav"

def test_coqui_tts_provider_init_gpu_available(mock_coqui_tts_api, mock_torch_cuda_is_available, coqui_config_gpu):
    """Test initialization with GPU configuration when CUDA is available."""
    mock_torch_cuda_is_available.return_value = True
    provider = CoquiTTSProvider(coqui_config_gpu)

    mock_coqui_tts_api.assert_called_once_with(model_name="tts_models/en/vctk/vits")
    mock_coqui_tts_api.return_value.to.assert_called_once_with("cuda")
    assert provider.tts_model is not None
    assert provider.speaker_to_use == "p225"

def test_coqui_tts_provider_init_gpu_not_available(mock_coqui_tts_api, mock_torch_cuda_is_available, coqui_config_gpu):
    """Test initialization with GPU configuration when CUDA is not available."""
    mock_torch_cuda_is_available.return_value = False
    provider = CoquiTTSProvider(coqui_config_gpu)

    mock_coqui_tts_api.assert_called_once_with(model_name="tts_models/en/vctk/vits")
    mock_coqui_tts_api.return_value.to.assert_called_once_with("cpu") # Falls back to CPU
    assert provider.tts_model is not None
    assert provider.speaker_to_use == "p225"

def test_coqui_tts_provider_init_model_failure(mock_coqui_tts_api, coqui_config_cpu):
    """Test initialization when CoquiTTS_API raises an exception."""
    mock_coqui_tts_api.side_effect = Exception("Model load error")
    provider = CoquiTTSProvider(coqui_config_cpu)
    assert provider.tts_model is None

def test_coqui_tts_provider_init_multi_speaker_no_speaker_specified(mock_coqui_tts_api, coqui_config_cpu):
    """Test multi-speaker model initialization when no speaker is specified."""
    mock_coqui_tts_api.return_value.is_multi_speaker = True
    mock_coqui_tts_api.return_value.speakers = ["speaker1", "speaker2"]
    config = CoquiConfig(model_name="multi_speaker_model", speaker=None, use_gpu=False)
    provider = CoquiTTSProvider(config)
    assert provider.is_multi_speaker is True
    assert provider.speaker_to_use == "speaker1" # Should default to first available

def test_coqui_tts_provider_init_multi_speaker_invalid_speaker(mock_coqui_tts_api, coqui_config_cpu):
    """Test multi-speaker model initialization with an invalid speaker."""
    mock_coqui_tts_api.return_value.is_multi_speaker = True
    mock_coqui_tts_api.return_value.speakers = ["speaker1", "speaker2"]
    config = CoquiConfig(model_name="multi_speaker_model", speaker="invalid_speaker", use_gpu=False)
    provider = CoquiTTSProvider(config)
    assert provider.is_multi_speaker is True
    assert provider.speaker_to_use == "speaker1" # Should fall back to first available

def test_coqui_tts_provider_init_multi_speaker_valid_speaker(mock_coqui_tts_api, coqui_config_gpu):
    """Test multi-speaker model initialization with a valid speaker."""
    mock_coqui_tts_api.return_value.is_multi_speaker = True
    mock_coqui_tts_api.return_value.speakers = ["p225", "p226"]
    provider = CoquiTTSProvider(coqui_config_gpu)
    assert provider.is_multi_speaker is True
    assert provider.speaker_to_use == "p225"

# Tests for generate_audio_data
def test_generate_audio_data_success_single_speaker(mock_coqui_tts_api, mock_os_remove, coqui_config_cpu):
    """Test successful audio generation for a single-speaker model."""
    provider = CoquiTTSProvider(coqui_config_cpu)
    provider.tts_model = mock_coqui_tts_api.return_value # Ensure model is set
    provider.tts_model.is_multi_speaker = False # Ensure single speaker mode

    mock_file_content = b"mock_coqui_wav_data"
    with patch("builtins.open", mock_open(read_data=mock_file_content)) as mocked_file_open:
        audio_data = provider.generate_audio_data("Hello from Coqui!")

        provider.tts_model.tts_to_file.assert_called_once_with(
            text="Hello from Coqui!", speaker=None, file_path="temp_coqui_audio.wav"
        )
        mocked_file_open.assert_called_once_with("temp_coqui_audio.wav", "rb")
        mock_os_remove.assert_called_once_with("temp_coqui_audio.wav")
        assert audio_data == mock_file_content

def test_generate_audio_data_success_multi_speaker(mock_coqui_tts_api, mock_os_remove, coqui_config_gpu):
    """Test successful audio generation for a multi-speaker model."""
    provider = CoquiTTSProvider(coqui_config_gpu)
    provider.tts_model = mock_coqui_tts_api.return_value
    provider.tts_model.is_multi_speaker = True
    provider.tts_model.speakers = ["p225", "p226"] # Ensure speakers are available
    provider.speaker_to_use = "p225" # Set selected speaker

    mock_file_content = b"mock_coqui_wav_data_multi"
    with patch("builtins.open", mock_open(read_data=mock_file_content)) as mocked_file_open:
        audio_data = provider.generate_audio_data("Hello from multi-speaker Coqui!")

        provider.tts_model.tts_to_file.assert_called_once_with(
            text="Hello from multi-speaker Coqui!", speaker="p225", file_path="temp_coqui_audio.wav"
        )
        mocked_file_open.assert_called_once_with("temp_coqui_audio.wav", "rb")
        mock_os_remove.assert_called_once_with("temp_coqui_audio.wav")
        assert audio_data == mock_file_content

def test_generate_audio_data_empty_text(mock_coqui_tts_api, coqui_config_cpu):
    """Test audio generation with empty text."""
    provider = CoquiTTSProvider(coqui_config_cpu)
    provider.tts_model = mock_coqui_tts_api.return_value

    audio_data = provider.generate_audio_data("")
    provider.tts_model.tts_to_file.assert_not_called()
    assert audio_data == b""

def test_generate_audio_data_error_text(mock_coqui_tts_api, coqui_config_cpu):
    """Test audio generation with error-like text."""
    provider = CoquiTTSProvider(coqui_config_cpu)
    provider.tts_model = mock_coqui_tts_api.return_value

    audio_data = provider.generate_audio_data("Error: Something went wrong")
    provider.tts_model.tts_to_file.assert_not_called()
    assert audio_data == b""

def test_generate_audio_data_model_not_available(coqui_config_cpu):
    """Test audio generation when the TTS model is not available."""
    provider = CoquiTTSProvider(coqui_config_cpu)
    provider.tts_model = None # Explicitly set to None

    audio_data = provider.generate_audio_data("Test text")
    assert audio_data == b""

def test_generate_audio_data_generation_failure(mock_coqui_tts_api, coqui_config_cpu):
    """Test audio generation when tts_to_file raises an exception."""
    provider = CoquiTTSProvider(coqui_config_cpu)
    provider.tts_model = mock_coqui_tts_api.return_value
    provider.tts_model.tts_to_file.side_effect = Exception("Coqui TTS generation failed")

    audio_data = provider.generate_audio_data("Test failure")
    provider.tts_model.tts_to_file.assert_called_once()
    assert audio_data == b""

def test_generate_audio_data_multi_speaker_no_speaker_selected(mock_coqui_tts_api, coqui_config_cpu):
    """Test multi-speaker generation when no speaker is selected."""
    provider = CoquiTTSProvider(coqui_config_cpu)
    provider.tts_model = mock_coqui_tts_api.return_value
    provider.tts_model.is_multi_speaker = True
    provider.speaker_to_use = None # Simulate no speaker selected

    audio_data = provider.generate_audio_data("Multi-speaker text")
    provider.tts_model.tts_to_file.assert_not_called()
    assert audio_data == b""

# Tests for get_output_format
def test_get_output_format(coqui_config_cpu):
    """Test get_output_format method."""
    provider = CoquiTTSProvider(coqui_config_cpu)
    assert provider.get_output_format() == "wav"

# Test the fallback CoquiTTSProvider when COQUI_TTS_AVAILABLE is False
def test_fallback_coqui_tts_provider():
    """Test the fallback CoquiTTSProvider when Coqui TTS library is not available."""
    with patch('infrastructure.tts.coqui_tts_provider.COQUI_TTS_AVAILABLE', False):
        # Reload the module to pick up the mocked COQUI_TTS_AVAILABLE
        import importlib
        import infrastructure.tts.coqui_tts_provider
        importlib.reload(infrastructure.tts.coqui_tts_provider)
        from infrastructure.tts.coqui_tts_provider import CoquiTTSProvider as FallbackCoquiTTSProvider
        from domain.models import CoquiConfig

        provider = FallbackCoquiTTSProvider(CoquiConfig(model_name="any", speaker=None, use_gpu=False))
        assert provider.generate_audio_data("test") == b""
        assert provider.get_output_format() == "wav"