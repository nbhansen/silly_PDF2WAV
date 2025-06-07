# tests/domain/services/test_audio_generation_service.py - PATCHED VERSION

import pytest
import subprocess
from unittest.mock import MagicMock, patch, mock_open
from domain.services.audio_generation_service import AudioGenerationService
from domain.models import ITTSEngine

class MockTTSEngine(ITTSEngine):
    def __init__(self, output_format="wav", audio_data=b"mock_audio_data"):
        self._output_format = output_format
        self._audio_data = audio_data

    def generate_audio_data(self, text_to_speak: str) -> bytes:
        if "error" in text_to_speak:
            raise Exception("Mock TTS Error")
        return self._audio_data

    def get_output_format(self) -> str:
        return self._output_format

@pytest.fixture
def mock_tts_engine():
    return MockTTSEngine()

@pytest.fixture
def mock_tts_engine_mp3():
    return MockTTSEngine(output_format="mp3")

@pytest.fixture
def audio_service(mock_tts_engine):
    # Patch _check_ffmpeg to always return True for testing FFmpeg logic
    with patch('domain.services.audio_generation_service.AudioGenerationService._check_ffmpeg', return_value=True):
        service = AudioGenerationService(tts_engine=mock_tts_engine)
        yield service

@pytest.fixture
def audio_service_no_ffmpeg(mock_tts_engine):
    with patch('domain.services.audio_generation_service.AudioGenerationService._check_ffmpeg', return_value=False):
        service = AudioGenerationService(tts_engine=mock_tts_engine)
        yield service

class TestAudioGenerationService:

    @patch('os.makedirs')  # Convert to proper patch
    @patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=1024 * 1024)  # 1MB
    def test_generate_audio_single_chunk_wav(self, mock_getsize, mock_exists, mock_file_open, mock_path_join, mock_makedirs, audio_service):
        text_chunks = ["Hello, world!"]
        output_name = "test_output"
        output_dir = "/tmp/audio"

        individual_files, combined_mp3 = audio_service.generate_audio(text_chunks, output_name, output_dir)

        mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)
        mock_file_open.assert_called_once_with(f"{output_dir}/{output_name}_part01.wav", "wb")
        mock_file_open().write.assert_called_once_with(b"mock_audio_data")
        assert individual_files == [f"{output_name}_part01.wav"]
        assert combined_mp3 == f"{output_name}_combined.mp3" # Converted to MP3

    @patch('os.makedirs')
    @patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=1024 * 1024)
    def test_generate_audio_multiple_chunks_wav(self, mock_getsize, mock_exists, mock_file_open, mock_path_join, mock_makedirs, audio_service):
        text_chunks = ["Chunk 1.", "Chunk 2.", "Chunk 3."]
        output_name = "test_output"
        output_dir = "/tmp/audio"

        individual_files, combined_mp3 = audio_service.generate_audio(text_chunks, output_name, output_dir)

        mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)
        assert mock_file_open.call_count == 3
        assert mock_file_open().write.call_count == 3
        assert individual_files == [
            f"{output_name}_part01.wav",
            f"{output_name}_part02.wav",
            f"{output_name}_part03.wav"
        ]
        assert combined_mp3 == f"{output_name}_combined.mp3"

    @patch('os.makedirs')
    @patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=1024 * 1024)
    def test_generate_audio_empty_chunk_skipped(self, mock_getsize, mock_exists, mock_file_open, mock_path_join, mock_makedirs, audio_service):
        text_chunks = ["Chunk 1.", "", "Chunk 3."]
        output_name = "test_output"
        output_dir = "/tmp/audio"

        individual_files, combined_mp3 = audio_service.generate_audio(text_chunks, output_name, output_dir)

        assert mock_file_open.call_count == 2 # Only two non-empty chunks
        assert individual_files == [
            f"{output_name}_part01.wav",
            f"{output_name}_part03.wav"
        ]
        assert combined_mp3 == f"{output_name}_combined.mp3"

    @patch('os.makedirs')
    @patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=1024 * 1024)
    def test_generate_audio_error_chunk_skipped(self, mock_getsize, mock_exists, mock_file_open, mock_path_join, mock_makedirs, audio_service):
        text_chunks = ["Chunk 1.", "Error: TTS failed", "Chunk 3."]
        output_name = "test_output"
        output_dir = "/tmp/audio"

        individual_files, combined_mp3 = audio_service.generate_audio(text_chunks, output_name, output_dir)

        assert mock_file_open.call_count == 2 # Only two non-error chunks
        assert individual_files == [
            f"{output_name}_part01.wav",
            f"{output_name}_part03.wav"
        ]
        assert combined_mp3 == f"{output_name}_combined.mp3"

    @patch('os.makedirs')
    @patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=1024 * 1024)
    def test_generate_audio_tts_engine_failure(self, mock_getsize, mock_exists, mock_file_open, mock_path_join, mock_makedirs, audio_service):
        text_chunks = ["Valid chunk.", "Chunk with error."]
        output_name = "test_output"
        output_dir = "/tmp/audio"

        # Mock the generate_audio_data to raise an exception for the second chunk
        audio_service.tts_engine.generate_audio_data = MagicMock(side_effect=[
            b"mock_audio_data_1",
            Exception("TTS error for chunk 2")
        ])

        individual_files, combined_mp3 = audio_service.generate_audio(text_chunks, output_name, output_dir)

        assert mock_file_open.call_count == 1 # Only the first chunk should be written
        assert individual_files == [f"{output_name}_part01.wav"]
        assert combined_mp3 == f"{output_name}_combined.mp3"

    @patch('os.makedirs')
    @patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=1024 * 1024)
    def test_generate_audio_no_tts_engine(self, mock_getsize, mock_exists, mock_file_open, mock_path_join, mock_makedirs):
        service = AudioGenerationService(tts_engine=None)
        text_chunks = ["Hello, world!"]
        output_name = "test_output"
        output_dir = "/tmp/audio"

        individual_files, combined_mp3 = service.generate_audio(text_chunks, output_name, output_dir)

        mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)
        mock_file_open.assert_not_called()
        assert individual_files == []
        assert combined_mp3 is None

    @patch('subprocess.run')
    @patch('os.makedirs')
    @patch('os.path.join', side_effect=lambda *args: '/'.join(args))
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=1024 * 1024)
    def test_convert_single_to_mp3_success(self, mock_getsize, mock_exists, mock_file_open, mock_path_join, mock_makedirs, mock_subprocess_run, audio_service):
        mock_subprocess_run.return_value = MagicMock(returncode=0, stderr="")
        
        # Ensure os.path.exists returns True for the output MP3 path
        mock_exists.side_effect = [True, True] # Input file exists, then output MP3 exists

        combined_mp3 = audio_service._convert_single_to_mp3("test_file.wav", "test_output", "/tmp/audio")
        
        mock_subprocess_run.assert_called_once()
        assert "ffmpeg" in mock_subprocess_run.call_args[0][0]
        assert combined_mp3 == "test_output_combined.mp3"

    @patch('subprocess.run', side_effect=FileNotFoundError)
    def test_check_ffmpeg_not_available_filenotfound(self, mock_subprocess_run):
        service = AudioGenerationService(tts_engine=MockTTSEngine())
        assert service._check_ffmpeg() == False
        mock_subprocess_run.assert_called_once_with(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)

    @patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='ffmpeg', timeout=5))
    def test_check_ffmpeg_not_available_timeout(self, mock_subprocess_run):
        service = AudioGenerationService(tts_engine=MockTTSEngine())
        assert service._check_ffmpeg() == False
        mock_subprocess_run.assert_called_once_with(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)