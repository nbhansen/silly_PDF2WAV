# infrastructure/tts/piper_tts_provider.py - Fixed imports
from contextlib import suppress
import os
from pathlib import Path
import re
import ssl
import subprocess
import tempfile
from typing import Optional
import urllib.error
from urllib.parse import urlparse
import urllib.request

from domain.config import PiperConfig
from domain.errors import Result, tts_engine_error
from domain.interfaces import ITTSEngine  # FIXED: Removed ISSMLProcessor

# Optional imports - handle gracefully at runtime
try:
    from piper.voice import PiperVoice

    PIPER_VOICE_AVAILABLE = True
except ImportError:
    PiperVoice = None
    PIPER_VOICE_AVAILABLE = False


class PiperTTSProvider(ITTSEngine):  # FIXED: Only implement ITTSEngine
    """Piper TTS Provider with basic SSML support."""

    def __init__(
        self,
        config: PiperConfig,
        repository_url: str = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0",
        project_root: Optional[str] = None,
    ):
        """Initialize Piper TTS Provider.

        Args:
            config: Piper configuration
            repository_url: URL for downloading Piper models
            project_root: Secure project root path (for binary lookup)
        """
        self.config = config
        self.output_format = "wav"
        self.model_path = config.model_path
        self.config_path = config.config_path
        self.project_root = project_root or str(Path.cwd())  # Secure default
        self.models_dir = config.download_dir
        self.voice_instance = None
        self.repository_url = repository_url

        # Check what's available
        self._check_piper_availability()

        # Only proceed with setup if we have some form of Piper
        if not self.piper_method:
            # Will fail at generation time with helpful error
            return

        # Ensure models directory exists
        Path(self.models_dir).mkdir(parents=True, exist_ok=True)

        # Auto-download model if no path specified
        if not self.model_path:
            self.model_path, self.config_path = self._ensure_model()

        # Make paths absolute
        if self.model_path and not Path(self.model_path).is_absolute():
            self.model_path = str(Path(self.model_path).resolve())
        if self.config_path and not Path(self.config_path).is_absolute():
            self.config_path = str(Path(self.config_path).resolve())

        # Verify files exist
        if self.model_path and not Path(self.model_path).exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        if self.config_path and not Path(self.config_path).exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        # Initialize Python library if available
        if self.piper_method == "python_library":
            self._init_python_library()

    # === ITTSEngine Implementation ===

    def generate_audio_data(self, text_to_speak: str) -> Result[bytes]:
        """Generate audio data using Piper TTS."""
        if not text_to_speak or text_to_speak.strip() == "":
            return Result.failure(tts_engine_error("Empty text provided"))

        # Skip error messages
        if text_to_speak.startswith(("LLM cleaning skipped", "Error:", "Could not convert")):
            return Result.failure(tts_engine_error("Cannot generate audio from error message"))

        # Strip ALL SSML tags for Piper (it doesn't support any SSML)
        processed_text = self._process_text_for_piper(text_to_speak)
        if not processed_text.strip():
            return Result.failure(tts_engine_error("Text processing resulted in empty content"))

        # Check if Piper is available at all
        if not hasattr(self, "piper_method") or not self.piper_method:
            return Result.failure(
                tts_engine_error(
                    "Piper TTS not available. Install with: pip install piper-tts or install piper command"
                )
            )

        try:
            if self.piper_method == "python_library" and self.voice_instance is not None:
                audio_data = self._generate_with_python_lib(processed_text)  # type: ignore[unreachable]
            else:
                audio_data = self._generate_with_command_line(processed_text)

            if not audio_data:
                return Result.failure(tts_engine_error("TTS engine returned no audio data"))

            return Result.success(audio_data)
        except subprocess.TimeoutExpired as timeout_ex:
            timeout_duration = getattr(timeout_ex, "timeout", 30)
            cmd_info = "piper command"
            print(f"🔍 PIPER TIMEOUT: Command timed out after {timeout_duration} seconds")
            print(f"🔍 PIPER TIMEOUT CMD: {cmd_info}")
            return Result.failure(tts_engine_error(f"Piper command timed out after {timeout_duration} seconds"))
        except Exception as e:
            print(f"🔍 PIPER EXCEPTION: {type(e).__name__}: {e}")
            return Result.failure(tts_engine_error(f"Audio generation failed: {e!s}"))

    async def generate_audio_data_async(self, text_to_speak: str) -> Result[bytes]:
        """Async wrapper for Piper TTS - calls sync method in thread pool.

        Piper is a local engine and doesn't have native async support.
        """
        import asyncio
        import concurrent.futures

        # Run the sync method in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, self.generate_audio_data, text_to_speak)
        return result

    def get_output_format(self) -> str:
        """Return the output audio format."""
        return self.output_format

    def prefers_sync_processing(self) -> bool:
        """Return True if this engine prefers synchronous processing."""
        return True  # Local engine, works well with sync processing

    def supports_ssml(self) -> bool:
        """Return True if this engine supports SSML markup."""
        return False  # Piper does NOT support SSML - all tags must be stripped

    def _secure_download(self, url: str, destination: str, timeout: int = 30) -> None:
        """Securely download a file with SSL verification and URL validation."""
        # Validate URL structure
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL format: {url}")

        # Only allow HTTPS for security
        if parsed_url.scheme != "https":
            raise ValueError(f"Only HTTPS URLs are allowed: {url}")

        # Create SSL context with certificate verification
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        try:
            # Create request with timeout and proper headers
            request = urllib.request.Request(url, headers={"User-Agent": "PiperTTS/1.0"})

            # Download with SSL context and timeout
            with urllib.request.urlopen(request, context=ssl_context, timeout=timeout) as response:
                if response.status != 200:
                    raise urllib.error.HTTPError(url, response.status, "Download failed", None, None)

                # Write to destination file
                with Path(destination).open("wb") as f:
                    while True:
                        chunk = response.read(8192)  # Read in 8KB chunks
                        if not chunk:
                            break
                        f.write(chunk)

        except urllib.error.URLError as e:
            raise Exception(f"Network error downloading {url}: {e}") from e
        except ssl.SSLError as e:
            raise Exception(f"SSL verification failed for {url}: {e}") from e
        except Exception as e:
            raise Exception(f"Download failed for {url}: {e}") from e

    # === SSML Processing ===

    def _process_text_for_piper(self, text: str) -> str:
        """Process text for Piper - strip ALL SSML tags since Piper doesn't support SSML."""
        if "<" not in text:
            return text

        # Remove ALL SSML tags - Piper doesn't support any SSML processing
        # This includes <break>, <emphasis>, <prosody>, etc.
        clean_text = re.sub(r"<[^>]+>", "", text)

        # Clean up any extra whitespace left after tag removal
        clean_text = re.sub(r"\s+", " ", clean_text)
        clean_text = re.sub(r"\s+([.,;!?])", r"\1", clean_text)  # Fix space before punctuation

        return clean_text.strip()

    # === Setup Methods ===

    def _check_piper_availability(self) -> None:
        """Check what Piper options are available."""
        self.piper_method = None

        # Try Python library first
        if PIPER_VOICE_AVAILABLE:
            self.piper_method = "python_library"
            return

        # Try command line - use secure project root
        piper_cmd = str(Path(self.project_root) / "piper")
        try:
            env = os.environ.copy()
            env["LD_LIBRARY_PATH"] = self.project_root + (
                (":" + env.get("LD_LIBRARY_PATH", "")) if env.get("LD_LIBRARY_PATH") else ""
            )
            result = subprocess.run([piper_cmd, "--help"], capture_output=True, text=True, timeout=5, env=env)
            if result.returncode == 0:
                self.piper_command = piper_cmd
                self.piper_method = "command_line"
                return
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass

        # Nothing available
        self.piper_method = None

    def _init_python_library(self) -> None:
        """Initialize the Python library version."""
        try:
            if PiperVoice is None:
                raise ImportError("PiperVoice not available")
            self.voice_instance = PiperVoice.load(self.model_path, config_path=self.config_path)
        except Exception:
            self.voice_instance = None

    def _generate_with_python_lib(self, text: str) -> bytes:
        """Generate using Python library."""
        try:
            from io import BytesIO
            import wave

            if self.voice_instance is None:
                raise Exception("Voice instance not initialized")

            audio_buffer = BytesIO()
            with wave.open(audio_buffer, "wb") as wav_file:
                # Piper's Python library can handle basic SSML
                self.voice_instance.synthesize(text, wav_file)

            audio_data = audio_buffer.getvalue()

            return audio_data

        except Exception:
            return self._generate_with_command_line(text)

    def _generate_with_command_line(self, text: str) -> bytes:
        """Generate using command line."""
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name

            # Ensure all paths are valid strings
            if not self.model_path:
                raise Exception("Model path not configured")

            cmd = [
                getattr(self, "piper_command", "piper"),
                "--model",
                self.model_path,
                "--output_file",
                temp_path,
                "--length_scale",
                str(self.config.length_scale),
            ]

            if self.config_path and Path(self.config_path).exists():
                cmd.extend(["--config", self.config_path])

            if self.config.speaker_id is not None:
                cmd.extend(["--speaker", str(self.config.speaker_id)])

            # Piper command line can handle basic SSML
            # Use dynamic timeout based on text length (minimum 30 seconds)
            timeout = max(30, len(text) // 50)  # ~1 second per 50 chars

            # Set up environment for local piper binary with libraries
            env = os.environ.copy()
            env["LD_LIBRARY_PATH"] = self.project_root + (
                (":" + env.get("LD_LIBRARY_PATH", "")) if env.get("LD_LIBRARY_PATH") else ""
            )

            print(f"🔍 PIPER COMMAND: {' '.join(cmd)}")
            print(f"🔍 PIPER ENV LD_LIBRARY_PATH: {env.get('LD_LIBRARY_PATH')}")
            print(f"🔍 PIPER INPUT LENGTH: {len(text)} chars")
            process = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=timeout, env=env)

            if process.returncode != 0:
                error_msg = (
                    f"Piper command failed with code {process.returncode}\n"
                    f"Command: {' '.join(cmd)}\nStderr: {process.stderr}\n"
                    f"Stdout: {process.stdout}\n"
                    f"Env LD_LIBRARY_PATH: {env.get('LD_LIBRARY_PATH', 'not set')}\n"
                    f"Input text length: {len(text)}\nFirst 200 chars: {text[:200]!r}"
                )
                print(f"🔍 PIPER DEBUG: {error_msg}")
                raise Exception(error_msg)

            if Path(temp_path).exists():
                # Verify file was created with content
                file_size = Path(temp_path).stat().st_size
                if file_size == 0:
                    raise Exception("Output file exists but contains no audio data")

                with Path(temp_path).open("rb") as f:
                    audio_data = f.read()

                if len(audio_data) > 0:
                    return audio_data
                else:
                    raise Exception("Output file exists but contains no audio data")
            else:
                raise Exception(f"Audio file was not created at {temp_path}")

        except subprocess.TimeoutExpired as e:
            raise Exception(f"Piper command timed out after {timeout} seconds") from e
        except Exception as e:
            raise Exception(f"Command line generation failed: {e}") from e
        finally:
            # Always try to clean up temp file
            if temp_path and Path(temp_path).exists():
                # Ignore cleanup errors
                with suppress(Exception):
                    Path(temp_path).unlink()

    # === Model Management ===

    def _ensure_model(self) -> tuple[str, str]:
        """Download model if needed."""
        model_name = self.config.model_name
        model_file = f"{model_name}.onnx"
        config_file = f"{model_name}.onnx.json"

        model_path = str(Path(self.models_dir) / model_file)
        config_path = str(Path(self.models_dir) / config_file)

        # Return existing model if found
        if Path(model_path).exists() and Path(config_path).exists():
            return model_path, config_path

        # Download if needed
        base_url = self.repository_url

        # Simple model mapping
        model_paths = {
            # US Male voices
            "en_US-ryan-high": "en/en_US/ryan/high",
            "en_US-ryan-medium": "en/en_US/ryan/medium",
            # GB voices
            "en_GB-cori-high": "en/en_GB/cori/high",
            "en_GB-alba-medium": "en/en_GB/alba/medium",
        }

        model_path_segment = model_paths.get(model_name, "en/en_US/lessac/medium")  # fallback

        try:
            # Download model and config securely
            model_url = f"{base_url}/{model_path_segment}/{model_file}"
            config_url = f"{base_url}/{model_path_segment}/{config_file}"

            self._secure_download(model_url, model_path)
            self._secure_download(config_url, config_path)

            return model_path, config_path

        except Exception as e:
            raise Exception(f"Model download failed: {e}") from e
