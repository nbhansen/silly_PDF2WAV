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

            print(f"PiperTTSProvider: Initializing with config:")
            print(f"  - Model name: {config.model_name}")
            print(f"  - Model path: {config.model_path}")
            print(f"  - Config path: {config.config_path}")
            print(f"  - Models dir: {config.download_dir}")
            print(f"  - PIPER_METHOD: {PIPER_METHOD}")

            # Ensure models directory exists
            os.makedirs(self.models_dir, exist_ok=True)

            # Auto-download model if no path specified
            if not self.model_path:
                print("PiperTTSProvider: No model path specified, ensuring model...")
                self.model_path, self.config_path = self._ensure_model()
            
            # Make paths absolute
            if self.model_path and not os.path.isabs(self.model_path):
                self.model_path = os.path.abspath(self.model_path)
            if self.config_path and not os.path.isabs(self.config_path):
                self.config_path = os.path.abspath(self.config_path)
            
            print(f"PiperTTSProvider: Using absolute paths:")
            print(f"  - Model: {self.model_path}")
            print(f"  - Config: {self.config_path}")
            
            # Verify files exist
            if self.model_path and not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model file not found: {self.model_path}")
            if self.config_path and not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Config file not found: {self.config_path}")

            # Initialize Python library if available
            if PIPER_METHOD == "python_library":
                self._init_python_library()

            print(f"PiperTTSProvider: Initialization complete")

        # === ITTSEngine Implementation ===

        def generate_audio_data(self, text_to_speak: str) -> Result[bytes]:
            """Generate audio data using Piper TTS"""
            print(f"PiperTTSProvider: generate_audio_data called with {len(text_to_speak)} chars")
            print(f"PiperTTSProvider: Using method: {PIPER_METHOD}")
            
            if not text_to_speak or text_to_speak.strip() == "":
                return Result.failure(tts_engine_error("Empty text provided"))

            # Skip error messages
            if (text_to_speak.startswith("LLM cleaning skipped")
                or text_to_speak.startswith("Error:")
                    or text_to_speak.startswith("Could not convert")):
                return Result.failure(tts_engine_error("Cannot generate audio from error message"))

            # Strip ALL SSML tags for Piper (it doesn't support any SSML)
            processed_text = self._process_text_for_piper(text_to_speak)
            if not processed_text.strip():
                return Result.failure(tts_engine_error("Text processing resulted in empty content"))
            
            # Debug: Check if SSML was present and stripped
            if '<' in text_to_speak and '>' in text_to_speak:
                print(f"🔍 PiperTTSProvider: Stripped SSML tags from text")
                print(f"🔍 PiperTTSProvider: Original had {text_to_speak.count('<')} tags")
            
            print(f"PiperTTSProvider: Processed text length: {len(processed_text)} chars")

            # Log warning if text is unusually large (should be chunked upstream)
            if len(processed_text) > 3000:
                print(f"🚨 PiperTTSProvider: WARNING - Received large text chunk ({len(processed_text)} chars)")
                print("🚨 PiperTTSProvider: This exceeds the expected chunk size limit (2000-3000 chars)")
                print(f"🚨 PiperTTSProvider: First 100 chars: {processed_text[:100]}...")
            elif len(processed_text) > 2000:
                print(f"⚠️  PiperTTSProvider: Received chunk at upper limit ({len(processed_text)} chars)")

            try:
                if PIPER_METHOD == "python_library" and self.voice_instance:
                    print("PiperTTSProvider: Using Python library method")
                    audio_data = self._generate_with_python_lib(processed_text)
                else:
                    print("PiperTTSProvider: Using command line method")
                    audio_data = self._generate_with_command_line(processed_text)

                if not audio_data:
                    return Result.failure(tts_engine_error("TTS engine returned no audio data"))

                print(f"PiperTTSProvider: Successfully generated {len(audio_data)} bytes of audio")
                return Result.success(audio_data)
            except Exception as e:
                import traceback
                error_msg = f"Audio generation failed: {str(e)}\nTraceback: {traceback.format_exc()}"
                print(f"PiperTTSProvider ERROR: {error_msg}")
                return Result.failure(tts_engine_error(error_msg))

        def get_output_format(self) -> str:
            return self.output_format

        def prefers_sync_processing(self) -> bool:
            return True  # Local engine, works well with sync processing

        def supports_ssml(self) -> bool:
            return False  # Piper does NOT support SSML - all tags must be stripped

        # === SSML Processing ===

        def _process_text_for_piper(self, text: str) -> str:
            """Process text for Piper - strip ALL SSML tags since Piper doesn't support SSML"""
            if not '<' in text:
                return text

            # Remove ALL SSML tags - Piper doesn't support any SSML processing
            # This includes <break>, <emphasis>, <prosody>, etc.
            clean_text = re.sub(r'<[^>]+>', '', text)
            
            # Clean up any extra whitespace left after tag removal
            clean_text = re.sub(r'\s+', ' ', clean_text)
            clean_text = re.sub(r'\s+([.,;!?])', r'\1', clean_text)  # Fix space before punctuation
            
            return clean_text.strip()

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
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                print(f"PiperTTSProvider: Created temp file: {temp_path}")

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

                print(f"PiperTTSProvider: Running command: {' '.join(cmd)}")
                print(f"PiperTTSProvider: Input text length: {len(text)} chars")
                print(f"PiperTTSProvider: First 100 chars: {text[:100]}...")

                # Piper command line can handle basic SSML
                # Use dynamic timeout based on text length (minimum 60 seconds)
                timeout = max(60, len(text) // 100)  # ~1 second per 100 chars
                print(f"PiperTTSProvider: Using timeout of {timeout} seconds for {len(text)} chars")
                process = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=timeout)

                print(f"PiperTTSProvider: Command completed with return code: {process.returncode}")
                if process.stdout:
                    print(f"PiperTTSProvider: Stdout: {process.stdout}")
                if process.stderr:
                    print(f"PiperTTSProvider: Stderr: {process.stderr}")

                if process.returncode != 0:
                    raise Exception(f"Piper command failed with code {process.returncode}: {process.stderr}")

                if os.path.exists(temp_path):
                    file_size = os.path.getsize(temp_path)
                    print(f"PiperTTSProvider: Output file size: {file_size} bytes")
                    
                    with open(temp_path, 'rb') as f:
                        audio_data = f.read()

                    if len(audio_data) > 0:
                        print(f"PiperTTSProvider: Successfully read {len(audio_data)} bytes from output file")
                        return audio_data
                    else:
                        raise Exception("Output file exists but contains no audio data")
                else:
                    raise Exception(f"Audio file was not created at {temp_path}")

            except subprocess.TimeoutExpired:
                raise Exception(f"Piper command timed out after {timeout} seconds")
            except Exception as e:
                raise Exception(f"Command line generation failed: {e}")
            finally:
                # Always try to clean up temp file
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                        print(f"PiperTTSProvider: Cleaned up temp file: {temp_path}")
                    except Exception as e:
                        print(f"PiperTTSProvider: Failed to clean up temp file: {e}")

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
