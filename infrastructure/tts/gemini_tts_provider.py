# infrastructure/tts/gemini_tts_provider.py
import os
import wave
import time
import tempfile
import subprocess
from google import genai
from google.genai import types
from domain.interfaces import ITTSEngine
from domain.config import GeminiConfig

try:
    # Ensure genai is imported for Client and types
    from google import genai
    from google.genai import types
    GEMINI_TTS_AVAILABLE = True
    print("Google Gemini TTS library found and imported successfully.")
except ImportError as e:
    print(f"Google Gemini TTS library not found: {e}")
    print("Install with: pip install google-generativeai")
    GEMINI_TTS_AVAILABLE = False

if GEMINI_TTS_AVAILABLE:
    class GeminiTTSProvider(ITTSEngine):
        def __init__(self, config: GeminiConfig):
            self.voice_name = config.voice_name
            self.style_prompt = config.style_prompt
            self.api_key = config.api_key or os.getenv('GOOGLE_AI_API_KEY', '')
            self.output_format = "wav"  # We'll convert everything to WAV for consistency
            self.client = None
            
            # Rate limiting settings
            self.last_request_time = 0
            self.min_request_interval = 2.0  # Minimum 2 seconds between requests
            self.max_retries = 3
            self.base_retry_delay = 16  # Start with API suggested delay
            
            try:
                if not self.api_key:
                    print("GeminiTTSProvider: WARNING - No API key provided")
                    return
                    
                self.client = genai.Client(api_key=self.api_key)
                print(f"GeminiTTSProvider: Initialized with voice '{self.voice_name}' and rate limiting")
            except Exception as e:
                print(f"GeminiTTSProvider: Error initializing Gemini client: {e}")
                self.client = None

        def generate_audio_data(self, text_to_speak: str) -> bytes:
            if not self.client:
                print("GeminiTTSProvider: Client not available. Skipping audio generation.")
                return b""
                
            print(f"GeminiTTSProvider: Attempting Gemini TTS generation with rate limiting.")
            
            if not text_to_speak or text_to_speak.strip() == "" or \
               text_to_speak.startswith("LLM cleaning skipped") or text_to_speak.startswith("Error:") or \
               text_to_speak.startswith("Could not convert") or text_to_speak.startswith("No text could be extracted"):
                print("GeminiTTSProvider: Skipping audio generation due to empty or error text.")
                return b""
            
            # Apply rate limiting before making request
            self._apply_rate_limit()
            
            # Retry logic with exponential backoff
            for attempt in range(self.max_retries):
                try:
                    return self._make_tts_request(text_to_speak, attempt)
                except Exception as e:
                    if self._is_rate_limit_error(e):
                        retry_delay = self._calculate_retry_delay(e, attempt)
                        print(f"GeminiTTSProvider: Rate limit hit (attempt {attempt + 1}/{self.max_retries}). "
                              f"Waiting {retry_delay}s before retry...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        print(f"GeminiTTSProvider: Non-rate-limit error on attempt {attempt + 1}: {e}")
                        if attempt == self.max_retries - 1:
                            # Last attempt failed
                            return b""
                        time.sleep(2 ** attempt)  # Simple exponential backoff for other errors
                        continue
            
            print(f"GeminiTTSProvider: All {self.max_retries} attempts failed")
            return b""

        def _apply_rate_limit(self):
            """Ensure minimum time between requests"""
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last
                print(f"GeminiTTSProvider: Rate limiting - waiting {sleep_time:.1f}s")
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()

        def _make_tts_request(self, text_to_speak: str, attempt: int) -> bytes:
            """Make the actual TTS request"""
            # Prepare prompt with optional style guidance
            prompt = f"{self.style_prompt}: {text_to_speak}" if self.style_prompt else text_to_speak
            
            print(f"GeminiTTSProvider: Making TTS request (attempt {attempt + 1}) with voice '{self.voice_name}'")
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.voice_name,
                            )
                        )
                    ),
                )
            )
            
            # Extract audio data with error handling
            if not hasattr(response, 'candidates') or not response.candidates:
                print("GeminiTTSProvider: No candidates in response")
                return b""
                
            candidate = response.candidates[0]
            if not hasattr(candidate, 'content') or not candidate.content:
                print("GeminiTTSProvider: No content in candidate")
                return b""
                
            content = candidate.content
            if not hasattr(content, 'parts') or not content.parts:
                print("GeminiTTSProvider: No parts in content")
                return b""
                
            part = content.parts[0]
            if not hasattr(part, 'inline_data') or not part.inline_data:
                print("GeminiTTSProvider: No inline_data in part")
                return b""
                
            raw_audio_data = part.inline_data.data
            print(f"GeminiTTSProvider: Successfully extracted raw audio data ({len(raw_audio_data)} bytes)")
            
            # Detect and convert the audio format to WAV
            converted_wav_data = self._convert_to_wav(raw_audio_data)
            
            if converted_wav_data:
                print(f"GeminiTTSProvider: Successfully converted to WAV format ({len(converted_wav_data)} bytes)")
                return converted_wav_data
            else:
                print("GeminiTTSProvider: Failed to convert audio to WAV format")
                return b""

        def _is_rate_limit_error(self, error) -> bool:
            """Check if error is a rate limit error"""
            error_str = str(error)
            return "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower()

        def _calculate_retry_delay(self, error, attempt: int) -> float:
            """Calculate retry delay based on error and attempt number"""
            error_str = str(error)
            
            # Try to extract retry delay from API response
            if 'retryDelay' in error_str:
                try:
                    # Look for patterns like 'retryDelay': '16s'
                    import re
                    match = re.search(r"'retryDelay':\s*'(\d+)s'", error_str)
                    if match:
                        api_suggested_delay = int(match.group(1))
                        # Add some jitter and respect attempt number
                        return api_suggested_delay + (attempt * 2)
                except:
                    pass
            
            # Fallback to exponential backoff
            return self.base_retry_delay * (2 ** attempt)

        def _convert_to_wav(self, raw_audio_data: bytes) -> bytes:
            """Convert raw PCM audio data to proper WAV format"""
            try:
                # Gemini TTS returns raw PCM audio data - we need to add WAV headers
                if self._is_raw_pcm_data(raw_audio_data):
                    print("GeminiTTSProvider: Converting raw PCM data to WAV format")
                    return self._create_wav_from_pcm(raw_audio_data)
                
                # If it already has headers, try FFmpeg conversion
                detected_format = self._detect_audio_format(raw_audio_data)
                print(f"GeminiTTSProvider: Detected audio format: {detected_format}")
                
                if detected_format == "wav":
                    # Already a WAV file
                    return raw_audio_data
                
                # Use FFmpeg for other formats
                return self._convert_with_ffmpeg(raw_audio_data, detected_format)
                        
            except Exception as e:
                print(f"GeminiTTSProvider: Error during audio conversion: {e}")
                return raw_audio_data

        def _is_raw_pcm_data(self, audio_data: bytes) -> bool:
            """Check if this is raw PCM data (no file headers)"""
            # Raw PCM data doesn't start with known file format signatures
            known_signatures = [
                b'RIFF',  # WAV
                b'\xff\xfb', b'\xff\xfa', b'ID3',  # MP3
                b'\xff\xf1', b'\xff\xf9',  # AAC
                b'OggS',  # OGG
                b'fLaC',  # FLAC
            ]
            
            for sig in known_signatures:
                if audio_data.startswith(sig):
                    return False
            
            # If no known signature found, assume it's raw PCM
            return True

        def _create_wav_from_pcm(self, pcm_data: bytes) -> bytes:
            """Create a proper WAV file from raw PCM audio data"""
            # Gemini TTS typically returns 16-bit PCM at 24kHz, mono
            sample_rate = 24000  # Hz
            bits_per_sample = 16
            channels = 1
            
            # Calculate WAV header values
            byte_rate = sample_rate * channels * bits_per_sample // 8
            block_align = channels * bits_per_sample // 8
            data_size = len(pcm_data)
            file_size = 36 + data_size
            
            # Create WAV header
            wav_header = bytearray()
            
            # RIFF chunk descriptor
            wav_header += b'RIFF'                           # ChunkID
            wav_header += file_size.to_bytes(4, 'little')   # ChunkSize
            wav_header += b'WAVE'                           # Format
            
            # fmt sub-chunk
            wav_header += b'fmt '                           # Subchunk1ID
            wav_header += (16).to_bytes(4, 'little')        # Subchunk1Size (16 for PCM)
            wav_header += (1).to_bytes(2, 'little')         # AudioFormat (1 = PCM)
            wav_header += channels.to_bytes(2, 'little')    # NumChannels
            wav_header += sample_rate.to_bytes(4, 'little') # SampleRate
            wav_header += byte_rate.to_bytes(4, 'little')   # ByteRate
            wav_header += block_align.to_bytes(2, 'little') # BlockAlign
            wav_header += bits_per_sample.to_bytes(2, 'little') # BitsPerSample
            
            # data sub-chunk
            wav_header += b'data'                           # Subchunk2ID
            wav_header += data_size.to_bytes(4, 'little')   # Subchunk2Size
            
            # Combine header and PCM data
            wav_file = bytes(wav_header) + pcm_data
            
            print(f"GeminiTTSProvider: Created WAV file ({len(wav_file)} bytes) from PCM data ({len(pcm_data)} bytes)")
            return wav_file

        def _convert_with_ffmpeg(self, raw_audio_data: bytes, detected_format: str) -> bytes:
            """Convert non-WAV audio formats using FFmpeg"""
            try:
                # Check if FFmpeg is available
                if not self._check_ffmpeg():
                    print("GeminiTTSProvider: FFmpeg not available, returning raw audio data")
                    return raw_audio_data
                
                # Create temporary files for conversion
                with tempfile.NamedTemporaryFile(suffix=f".{detected_format}", delete=False) as input_file:
                    input_file.write(raw_audio_data)
                    input_path = input_file.name
                
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output_file:
                    output_path = output_file.name
                
                try:
                    # Convert to WAV using FFmpeg
                    cmd = [
                        'ffmpeg', '-y',  # -y to overwrite output
                        '-i', input_path,
                        '-acodec', 'pcm_s16le',  # Standard WAV codec
                        '-ar', '22050',          # 22.05 kHz sample rate (good for speech)
                        '-ac', '1',              # Mono audio
                        output_path
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        # Read the converted WAV data
                        with open(output_path, 'rb') as f:
                            wav_data = f.read()
                        
                        # Clean up temp files
                        try:
                            os.unlink(input_path)
                            os.unlink(output_path)
                        except:
                            pass
                        
                        return wav_data
                    else:
                        print(f"GeminiTTSProvider: FFmpeg conversion failed: {result.stderr}")
                        return raw_audio_data
                        
                except subprocess.TimeoutExpired:
                    print("GeminiTTSProvider: FFmpeg conversion timed out")
                    return raw_audio_data
                finally:
                    # Clean up temp files
                    try:
                        os.unlink(input_path)
                        os.unlink(output_path)
                    except:
                        pass
                        
            except Exception as e:
                print(f"GeminiTTSProvider: Error during FFmpeg conversion: {e}")
                return raw_audio_data

        def _detect_audio_format(self, audio_data: bytes) -> str:
            """Detect audio format from raw bytes"""
            # Check common audio format signatures
            if audio_data.startswith(b'RIFF') and b'WAVE' in audio_data[:12]:
                return "wav"
            elif audio_data.startswith(b'\xff\xfb') or audio_data.startswith(b'\xff\xfa') or audio_data.startswith(b'ID3'):
                return "mp3"
            elif audio_data.startswith(b'\xff\xf1') or audio_data.startswith(b'\xff\xf9'):
                return "aac"
            elif audio_data.startswith(b'OggS'):
                return "ogg"
            elif audio_data.startswith(b'fLaC'):
                return "flac"
            else:
                # Default to a common format that FFmpeg can usually handle
                print("GeminiTTSProvider: Unknown audio format, assuming MP3")
                return "mp3"

        def _check_ffmpeg(self) -> bool:
            """Check if FFmpeg is available"""
            try:
                result = subprocess.run(['ffmpeg', '-version'], 
                                      capture_output=True, text=True, timeout=5)
                return result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                return False

        def get_output_format(self) -> str:
            return self.output_format
else:
    class GeminiTTSProvider(ITTSEngine):
        def __init__(self, config: GeminiConfig):
            print("GeminiTTSProvider: Google Gemini TTS library not available. This provider will not function.")
        def generate_audio_data(self, text_to_speak: str) -> bytes:
            print("GeminiTTSProvider: Google Gemini TTS library not available. Cannot generate audio.")
            return b""
        def get_output_format(self) -> str:
            return "wav"