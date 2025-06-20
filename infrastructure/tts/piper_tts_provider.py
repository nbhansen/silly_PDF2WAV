# infrastructure/tts/piper_tts_provider.py - Fixed imports
import os
import subprocess
import tempfile
import urllib.request
import re
from typing import Optional, Dict, Any, List
from domain.interfaces import ITTSEngine, SSMLCapability  # FIXED: Removed ISSMLProcessor
from domain.config import PiperConfig
from domain.errors import Result, tts_engine_error

# Check for Piper availability
PIPER_AVAILABLE = False
PIPER_METHOD = None

try:
    # Try importing the Python library
    from piper.voice import PiperVoice
    PIPER_AVAILABLE = True
    PIPER_METHOD = "python_library"
    print("Piper TTS Python library found and available")
except ImportError:
    try:
        # Check if piper command is available
        result = subprocess.run(['piper', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            PIPER_AVAILABLE = True
            PIPER_METHOD = "command_line"
            print("Piper TTS command line tool found and available")
        else:
            print("Piper TTS not found - install with: pip install piper-tts")
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        print("Piper TTS not found. Install with: pip install piper-tts")

if PIPER_AVAILABLE:
    class PiperTTSProvider(ITTSEngine):  # FIXED: Only implement ITTSEngine
        """Piper TTS Provider with basic SSML support"""

        def __init__(self, config: PiperConfig, repository_url: str = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"):
            self.config = config
            self.output_format = "wav"
            self.model_path = config.model_path
            self.config_path = config.config_path
            self.models_dir = config.download_dir
            self.voice_instance = None
            self.repository_url = repository_url

            # Ensure models directory exists
            os.makedirs(self.models_dir, exist_ok=True)

            # Auto-download model if no path specified
            if not self.model_path:
                self.model_path, self.config_path = self._ensure_model()

            # Initialize Python library if available
            if PIPER_METHOD == "python_library":
                self._init_python_library()

            print(f"PiperTTSProvider: Using model {self.config.model_name}")

        # === ITTSEngine Implementation ===

        def generate_audio_data(self, text_to_speak: str) -> Result[bytes]:
            """Generate audio data using Piper TTS"""
            if not text_to_speak or text_to_speak.strip() == "":
                return Result.failure(tts_engine_error("Empty text provided"))

            # Skip error messages
            if (text_to_speak.startswith("LLM cleaning skipped")
                or text_to_speak.startswith("Error:")
                    or text_to_speak.startswith("Could not convert")):
                return Result.failure(tts_engine_error("Cannot generate audio from error message"))

            # Basic SSML processing for Piper
            processed_text = self._process_text_for_piper(text_to_speak)
            if not processed_text.strip():
                return Result.failure(tts_engine_error("Text processing resulted in empty content"))

            try:
                if PIPER_METHOD == "python_library" and self.voice_instance:
                    audio_data = self._generate_with_python_lib(processed_text)
                else:
                    audio_data = self._generate_with_command_line(processed_text)

                if not audio_data:
                    return Result.failure(tts_engine_error("TTS engine returned no audio data"))

                return Result.success(audio_data)
            except Exception as e:
                return Result.failure(tts_engine_error(f"Audio generation failed: {str(e)}"))

        def get_output_format(self) -> str:
            return self.output_format

        def prefers_sync_processing(self) -> bool:
            return True  # Local engine, works well with sync processing

        def supports_ssml(self) -> bool:
            return True  # Piper supports basic SSML

        # === SSML Processing ===

        def _process_text_for_piper(self, text: str) -> str:
            """Process text for Piper - keep basic SSML tags, strip others"""
            if not '<' in text:
                return text

            # Extract content from speak tags if present
            if text.strip().startswith('<speak>') and text.strip().endswith('</speak>'):
                text = text.strip()[7:-8]  # Remove <speak> and </speak>

            # Keep basic SSML tags that Piper supports
            # Remove unsupported tags but keep their content
            unsupported_tags = ['voice', 'audio', 'mark', 'sub', 'phoneme', 'lexicon']
            for tag in unsupported_tags:
                text = re.sub(f'<{tag}[^>]*>', '', text)
                text = re.sub(f'</{tag}>', '', text)

            # Clean up any malformed tags
            text = re.sub(r'<[^>]*$', '', text)  # Remove unclosed tags at end
            text = re.sub(r'^[^<]*>', '', text)  # Remove orphaned closing tags at start
            text = re.sub(r'\s+', ' ', text)     # Clean up multiple spaces

            return text.strip()

        # === Audio Generation Methods ===

        def _init_python_library(self):
            """Initialize the Python library version"""
            try:
                from piper.voice import PiperVoice
                self.voice_instance = PiperVoice.load(self.model_path, config_path=self.config_path)
                print("PiperTTSProvider: Python library voice loaded")
            except Exception as e:
                print(f"PiperTTSProvider: Failed to load voice with Python library: {e}")
                self.voice_instance = None

        def _generate_with_python_lib(self, text: str) -> bytes:
            """Generate using Python library"""
            try:
                import wave
                from io import BytesIO

                audio_buffer = BytesIO()
                wav_file = wave.open(audio_buffer, 'wb')

                # Piper's Python library can handle basic SSML
                self.voice_instance.synthesize(text, wav_file)
                audio_data = audio_buffer.getvalue()

                print(f"PiperTTSProvider: Generated {len(audio_data)} bytes with Python library")
                return audio_data

            except Exception as e:
                print(f"PiperTTSProvider: Python library failed: {e}")
                return self._generate_with_command_line(text)

        def _generate_with_command_line(self, text: str) -> bytes:
            """Generate using command line"""
            try:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_path = temp_file.name

                cmd = [
                    'piper',
                    '--model', self.model_path,
                    '--output_file', temp_path,
                    '--length_scale', str(self.config.length_scale),
                ]

                if self.config_path and os.path.exists(self.config_path):
                    cmd.extend(['--config', self.config_path])

                if self.config.speaker_id is not None:
                    cmd.extend(['--speaker', str(self.config.speaker_id)])

                # Piper command line can handle basic SSML
                process = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=60)

                if process.returncode != 0:
                    raise Exception(f"Piper command failed: {process.stderr}")

                if os.path.exists(temp_path):
                    with open(temp_path, 'rb') as f:
                        audio_data = f.read()

                    try:
                        os.unlink(temp_path)
                    except:
                        pass

                    if len(audio_data) > 0:
                        print(f"PiperTTSProvider: Generated {len(audio_data)} bytes with command line")
                        return audio_data
                    else:
                        raise Exception("No audio data generated")
                else:
                    raise Exception("Audio file was not created")

            except subprocess.TimeoutExpired:
                raise Exception("Piper command timed out")
            except Exception as e:
                raise Exception(f"Command line generation failed: {e}")

        # === Model Management ===

        def _ensure_model(self) -> tuple[str, str]:
            """Download model if needed"""
            model_name = self.config.model_name
            model_file = f"{model_name}.onnx"
            config_file = f"{model_name}.onnx.json"

            model_path = os.path.join(self.models_dir, model_file)
            config_path = os.path.join(self.models_dir, config_file)

            # Return existing model if found
            if os.path.exists(model_path) and os.path.exists(config_path):
                print(f"PiperTTSProvider: Using existing model {model_path}")
                return model_path, config_path

            # Download if needed
            print(f"PiperTTSProvider: Downloading model {model_name}...")
            base_url = self.repository_url

            # Simple model mapping
            model_paths = {
                # High quality models
                "en_US-lessac-high": "en/en_US/lessac/high",
                "en_US-ljspeech-high": "en/en_US/ljspeech/high",
                "en_US-ryan-high": "en/en_US/ryan/high",
                "en_GB-alba-high": "en/en_GB/alba/high",

                # Medium quality (existing)
                "en_US-lessac-medium": "en/en_US/lessac/medium",
                "en_US-ljspeech-medium": "en/en_US/ljspeech/medium",
                "en_US-ryan-medium": "en/en_US/ryan/medium",
                "en_GB-alba-medium": "en/en_GB/alba/medium",
                "en_US-arctic-medium": "en/en_US/arctic/medium",

                # Low quality (existing)
                "en_US-amy-low": "en/en_US/amy/low",
            }

            model_path_segment = model_paths.get(model_name, "en/en_US/lessac/medium")  # fallback

            try:
                # Download model and config
                model_url = f"{base_url}/{model_path_segment}/{model_file}"
                config_url = f"{base_url}/{model_path_segment}/{config_file}"

                urllib.request.urlretrieve(model_url, model_path)
                urllib.request.urlretrieve(config_url, config_path)

                print(f"PiperTTSProvider: Downloaded {model_name}")
                return model_path, config_path

            except Exception as e:
                print(f"PiperTTSProvider: Download failed: {e}")
                raise Exception("Model download failed")

else:
    # Fallback when Piper is not available
    class PiperTTSProvider(ITTSEngine):
        def __init__(self, config: PiperConfig):
            print("PiperTTSProvider: Piper TTS not available.")
            print("Install with: pip install piper-tts")

        def generate_audio_data(self, text_to_speak: str) -> Result[bytes]:
            return Result.failure(tts_engine_error("PiperTTSProvider: Piper TTS not available"))

        def get_output_format(self) -> str:
            return "wav"

        def prefers_sync_processing(self) -> bool:
            return True

        def supports_ssml(self) -> bool:
            return False
