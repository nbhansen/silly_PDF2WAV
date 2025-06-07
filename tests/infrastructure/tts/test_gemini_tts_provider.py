import pytest
from unittest.mock import MagicMock, patch, mock_open
from domain.models import GeminiConfig, ITTSEngine
import os
import tempfile
import subprocess

# Mock the GEMINI_TTS_AVAILABLE flag to ensure GeminiTTSProvider class is defined
with patch('infrastructure.tts.gemini_tts_provider.GEMINI_TTS_AVAILABLE', True):
    # Mock google.genai and its submodules
    with patch('google.genai.Client', MagicMock()) as MockClient:
        with patch('google.genai.types', MagicMock()) as MockTypes:
            from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider

@pytest.fixture
def mock_genai_client():
    """Mock google.genai.Client."""
    with patch('google.genai.Client') as mock_client_class:
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_os_getenv():
    """Mock os.getenv."""
    with patch('os.getenv') as mock_getenv:
        yield mock_getenv

@pytest.fixture
def mock_tempfile_namedtemporaryfile():
    """Mock tempfile.NamedTemporaryFile."""
    with patch('tempfile.NamedTemporaryFile') as mock_ntf:
        mock_file_obj = MagicMock()
        mock_file_obj.name = "/tmp/mock_temp_file.wav"
        mock_ntf.return_value.__enter__.return_value = mock_file_obj
        yield mock_ntf

@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run."""
    with patch('subprocess.run') as mock_run:
        yield mock_run

@pytest.fixture
def mock_os_remove(mocker):
    """Mock os.remove."""
    return mocker.patch("os.remove")

@pytest.fixture
def gemini_config_valid():
    """Fixture for a valid GeminiConfig."""
    return GeminiConfig(api_key="test_api_key", voice_name="en-US-Neural2-D", style_prompt="friendly")

@pytest.fixture
def gemini_config_no_api_key():
    """Fixture for GeminiConfig with no API key."""
    return GeminiConfig(api_key="", voice_name="en-US-Neural2-D", style_prompt=None)

# Tests for __init__
def test_gemini_tts_provider_init_success(mock_genai_client, mock_os_getenv, gemini_config_valid):
    """Test successful initialization of GeminiTTSProvider."""
    mock_os_getenv.return_value = "env_api_key" # Ensure env var is checked
    provider = GeminiTTSProvider(gemini_config_valid)
    mock_genai_client.assert_called_once_with(api_key="test_api_key")
    assert provider.client is not None
    assert provider.voice_name == "en-US-Neural2-D"
    assert provider.style_prompt == "friendly"
    assert provider.output_format == "wav"

def test_gemini_tts_provider_init_no_api_key_in_config(mock_genai_client, mock_os_getenv):
    """Test initialization when no API key is provided in config or env."""
    mock_os_getenv.return_value = ""
    config = GeminiConfig(api_key="", voice_name="en-US-Neural2-D", style_prompt=None)
    provider = GeminiTTSProvider(config)
    mock_genai_client.assert_not_called()
    assert provider.client is None

def test_gemini_tts_provider_init_api_key_from_env(mock_genai_client, mock_os_getenv):
    """Test initialization when API key is provided via environment variable."""
    mock_os_getenv.return_value = "env_api_key"
    config = GeminiConfig(api_key=None, voice_name="en-US-Neural2-D", style_prompt=None)
    provider = GeminiTTSProvider(config)
    mock_genai_client.assert_called_once_with(api_key="env_api_key")
    assert provider.client is not None

def test_gemini_tts_provider_init_client_error(mock_genai_client, gemini_config_valid):
    """Test initialization when genai.Client raises an exception."""
    mock_genai_client.side_effect = Exception("Client init error")
    provider = GeminiTTSProvider(gemini_config_valid)
    assert provider.client is None

# Tests for generate_audio_data
def test_generate_audio_data_success(mock_genai_client, mock_tempfile_namedtemporaryfile, mock_subprocess_run, gemini_config_valid):
    """Test successful audio generation with mock conversion."""
    provider = GeminiTTSProvider(gemini_config_valid)
    provider.client = mock_genai_client.return_value # Ensure client is set

    # Mock the generate_content response
    mock_response = MagicMock()
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content = MagicMock()
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].inline_data = MagicMock()
    mock_response.candidates[0].content.parts[0].inline_data.data = b"raw_audio_data"
    provider.client.models.generate_content.return_value = mock_response

    # Mock the internal conversion methods
    with patch.object(provider, '_convert_to_wav', return_value=b"converted_wav_data") as mock_convert:
        text_to_speak = "Hello, Gemini TTS!"
        audio_data = provider.generate_audio_data(text_to_speak)

        expected_prompt = f"{gemini_config_valid.style_prompt}: {text_to_speak}"
        provider.client.models.generate_content.assert_called_once()
        # Check arguments to generate_content more precisely
        args, kwargs = provider.client.models.generate_content.call_args
        assert kwargs['model'] == "gemini-2.5-flash-preview-tts"
        assert kwargs['contents'] == expected_prompt
        assert 'config' in kwargs
        assert audio_data == b"converted_wav_data"
        mock_convert.assert_called_once_with(b"raw_audio_data")

def test_generate_audio_data_empty_text(mock_genai_client, gemini_config_valid):
    """Test audio generation with empty text."""
    provider = GeminiTTSProvider(gemini_config_valid)
    provider.client = mock_genai_client.return_value

    audio_data = provider.generate_audio_data("")
    provider.client.models.generate_content.assert_not_called()
    assert audio_data == b""

def test_generate_audio_data_error_text(mock_genai_client, gemini_config_valid):
    """Test audio generation with error-like text."""
    provider = GeminiTTSProvider(gemini_config_valid)
    provider.client = mock_genai_client.return_value

    audio_data = provider.generate_audio_data("Error: API failed")
    provider.client.models.generate_content.assert_not_called()
    assert audio_data == b""

def test_generate_audio_data_client_not_available(gemini_config_no_api_key):
    """Test audio generation when client is not available."""
    provider = GeminiTTSProvider(gemini_config_no_api_key) # This config makes client None
    assert provider.client is None
    audio_data = provider.generate_audio_data("Test text")
    assert audio_data == b""

def test_generate_audio_data_api_error(mock_genai_client, gemini_config_valid):
    """Test audio generation when generate_content raises an exception."""
    provider = GeminiTTSProvider(gemini_config_valid)
    provider.client = mock_genai_client.return_value
    provider.client.models.generate_content.side_effect = Exception("API error")

    audio_data = provider.generate_audio_data("Test failure")
    assert audio_data == b""

def test_generate_audio_data_empty_response_from_api(mock_genai_client, gemini_config_valid):
    """Test audio generation when API returns an empty response."""
    provider = GeminiTTSProvider(gemini_config_valid)
    provider.client = mock_genai_client.return_value
    
    mock_response = MagicMock()
    mock_response.candidates = [] # No candidates
    provider.client.models.generate_content.return_value = mock_response

    audio_data = provider.generate_audio_data("Test empty response")
    assert audio_data == b""

def test_generate_audio_data_no_inline_data(mock_genai_client, gemini_config_valid):
    """Test audio generation when API response lacks inline_data."""
    provider = GeminiTTSProvider(gemini_config_valid)
    provider.client = mock_genai_client.return_value
    
    mock_response = MagicMock()
    mock_response.candidates = [MagicMock()]
    mock_response.candidates[0].content = MagicMock()
    mock_response.candidates[0].content.parts = [MagicMock()]
    mock_response.candidates[0].content.parts[0].inline_data = None # Missing inline_data
    provider.client.models.generate_content.return_value = mock_response

    audio_data = provider.generate_audio_data("Test no inline data")
    assert audio_data == b""

# Tests for _convert_to_wav and its helpers
def test_is_raw_pcm_data_true(gemini_config_valid):
    """Test _is_raw_pcm_data for raw PCM."""
    provider = GeminiTTSProvider(gemini_config_valid)
    # A simple byte string that doesn't start with known headers
    raw_data = b'\x00\x01\x02\x03\x04\x05\x06\x07'
    assert provider._is_raw_pcm_data(raw_data) is True

def test_is_raw_pcm_data_false_wav(gemini_config_valid):
    """Test _is_raw_pcm_data for WAV data."""
    provider = GeminiTTSProvider(gemini_config_valid)
    wav_header = b'RIFF\x00\x00\x00\x00WAVE'
    assert provider._is_raw_pcm_data(wav_header + b'data') is False

def test_is_raw_pcm_data_false_mp3(gemini_config_valid):
    """Test _is_raw_pcm_data for MP3 data."""
    provider = GeminiTTSProvider(gemini_config_valid)
    mp3_header = b'\xff\xfb'
    assert provider._is_raw_pcm_data(mp3_header + b'data') is False

def test_create_wav_from_pcm(gemini_config_valid):
    """Test _create_wav_from_pcm creates a valid WAV header."""
    provider = GeminiTTSProvider(gemini_config_valid)
    pcm_data = b'\x00\x01\x02\x03' * 100 # 400 bytes of PCM data
    wav_data = provider._create_wav_from_pcm(pcm_data)

    assert wav_data.startswith(b'RIFF')
    assert wav_data[8:12] == b'WAVE'
    # Check fmt chunk
    assert wav_data[12:16] == b'fmt '
    assert int.from_bytes(wav_data[16:20], 'little') == 16 # Subchunk1Size
    assert int.from_bytes(wav_data[20:22], 'little') == 1 # AudioFormat (PCM)
    assert int.from_bytes(wav_data[22:24], 'little') == 1 # Channels
    assert int.from_bytes(wav_data[24:28], 'little') == 24000 # SampleRate
    assert int.from_bytes(wav_data[34:36], 'little') == 16 # BitsPerSample
    # Check data chunk
    assert wav_data[36:40] == b'data'
    assert int.from_bytes(wav_data[40:44], 'little') == len(pcm_data)
    assert wav_data[44:] == pcm_data
    assert len(wav_data) == 44 + len(pcm_data)

def test_detect_audio_format_wav(gemini_config_valid):
    """Test _detect_audio_format for WAV."""
    provider = GeminiTTSProvider(gemini_config_valid)
    wav_data = b'RIFF\x00\x00\x00\x00WAVEfmt ' + b'\x00'*36
    assert provider._detect_audio_format(wav_data) == "wav"

def test_detect_audio_format_mp3(gemini_config_valid):
    """Test _detect_audio_format for MP3."""
    provider = GeminiTTSProvider(gemini_config_valid)
    mp3_data = b'\xff\xfb' + b'\x00'*100
    assert provider._detect_audio_format(mp3_data) == "mp3"

def test_detect_audio_format_unknown_defaults_to_mp3(gemini_config_valid):
    """Test _detect_audio_format for unknown format defaults to mp3."""
    provider = GeminiTTSProvider(gemini_config_valid)
    unknown_data = b'RANDOMBYTES'
    assert provider._detect_audio_format(unknown_data) == "mp3"

def test_convert_with_ffmpeg_success(mock_subprocess_run, mock_tempfile_namedtemporaryfile, mock_os_remove, gemini_config_valid):
    """Test _convert_with_ffmpeg successful conversion."""
    provider = GeminiTTSProvider(gemini_config_valid)
    
    # Mock _check_ffmpeg to return True
    with patch.object(provider, '_check_ffmpeg', return_value=True):
        mock_subprocess_run.return_value = MagicMock(returncode=0, stderr="")
        
        # Mock reading the output file
        mock_file_content = b"ffmpeg_converted_wav"
        with patch("builtins.open", mock_open(read_data=mock_file_content)) as mocked_file_open:
            converted_data = provider._convert_with_ffmpeg(b"input_mp3_data", "mp3")
            
            mock_subprocess_run.assert_called_once()
            assert "ffmpeg" in mock_subprocess_run.call_args[0][0]
            assert "-i" in mock_subprocess_run.call_args[0][0]
            assert "input_mp3_data" not in str(mock_subprocess_run.call_args[0][0]) # Should use temp file path
            assert converted_data == mock_file_content
            mock_os_remove.assert_called() # Called twice for input and output temp files

def test_convert_with_ffmpeg_ffmpeg_not_available(mock_subprocess_run, gemini_config_valid):
    """Test _convert_with_ffmpeg when FFmpeg is not available."""
    provider = GeminiTTSProvider(gemini_config_valid)
    with patch.object(provider, '_check_ffmpeg', return_value=False):
        raw_data = b"some_audio_data"
        converted_data = provider._convert_with_ffmpeg(raw_data, "mp3")
        mock_subprocess_run.assert_not_called()
        assert converted_data == raw_data # Should return original data

def test_convert_with_ffmpeg_ffmpeg_failure(mock_subprocess_run, mock_tempfile_namedtemporaryfile, gemini_config_valid):
    """Test _convert_with_ffmpeg when FFmpeg command fails."""
    provider = GeminiTTSProvider(gemini_config_valid)
    with patch.object(provider, '_check_ffmpeg', return_value=True):
        mock_subprocess_run.return_value = MagicMock(returncode=1, stderr="FFmpeg error")
        raw_data = b"input_mp3_data"
        converted_data = provider._convert_with_ffmpeg(raw_data, "mp3")
        assert converted_data == raw_data # Should return original data on failure

def test_convert_with_ffmpeg_timeout(mock_subprocess_run, mock_tempfile_namedtemporaryfile, gemini_config_valid):
    """Test _convert_with_ffmpeg when FFmpeg command times out."""
    provider = GeminiTTSProvider(gemini_config_valid)
    with patch.object(provider, '_check_ffmpeg', return_value=True):
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=30)
        raw_data = b"input_mp3_data"
        converted_data = provider._convert_with_ffmpeg(raw_data, "mp3")
        assert converted_data == raw_data # Should return original data on timeout

def test_check_ffmpeg_available(mock_subprocess_run, gemini_config_valid):
    """Test _check_ffmpeg when FFmpeg is available."""
    provider = GeminiTTSProvider(gemini_config_valid)
    mock_subprocess_run.return_value = MagicMock(returncode=0)
    assert provider._check_ffmpeg() is True
    mock_subprocess_run.assert_called_once_with(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)

def test_check_ffmpeg_not_available(mock_subprocess_run, gemini_config_valid):
    """Test _check_ffmpeg when FFmpeg is not available."""
    provider = GeminiTTSProvider(gemini_config_valid)
    mock_subprocess_run.side_effect = FileNotFoundError
    assert provider._check_ffmpeg() is False

def test_get_output_format(gemini_config_valid):
    """Test get_output_format method."""
    provider = GeminiTTSProvider(gemini_config_valid)
    assert provider.get_output_format() == "wav"

# Test the fallback GeminiTTSProvider when GEMINI_TTS_AVAILABLE is False
def test_fallback_gemini_tts_provider():
    """Test the fallback GeminiTTSProvider when Gemini TTS library is not available."""
    with patch('infrastructure.tts.gemini_tts_provider.GEMINI_TTS_AVAILABLE', False):
        # Reload the module to pick up the mocked GEMINI_TTS_AVAILABLE
        import importlib
        import infrastructure.tts.gemini_tts_provider
        importlib.reload(infrastructure.tts.gemini_tts_provider)
        from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider as FallbackGeminiTTSProvider
        from domain.models import GeminiConfig

        provider = FallbackGeminiTTSProvider(GeminiConfig(api_key="any", voice_name="any", style_prompt=None))
        assert provider.generate_audio_data("test") == b""
        assert provider.get_output_format() == "wav"