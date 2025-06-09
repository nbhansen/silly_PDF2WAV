# infrastructure/tts/piper_tts_provider.py - Updated imports
import os
import subprocess
import tempfile
import json
import urllib.request
from typing import Optional, Dict, Any
from domain.interfaces import ITTSEngine
from domain.config import PiperConfig

# Check for Piper availability with correct import paths
PIPER_AVAILABLE = False
PIPER_METHOD = None

try:
    # Method 1: Try importing the Python library (correct import path)
    from piper.voice import PiperVoice
    PIPER_AVAILABLE = True
    PIPER_METHOD = "python_library"
    print("Piper TTS Python library found and available (from piper.voice import PiperVoice)")
except ImportError:
    try:
        # Method 2: Check if piper command is available
        result = subprocess.run(['piper', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            PIPER_AVAILABLE = True
            PIPER_METHOD = "command_line"
            print("Piper TTS command line tool found and available")
        else:
            print("Piper TTS not found - install with: pip install piper-tts")
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        print("Piper TTS not found. Install with: pip install piper-tts")
        print("or download binary from: https://github.com/rhasspy/piper/releases")

if PIPER_AVAILABLE:
    class PiperTTSProvider(ITTSEngine):
        """
        Piper TTS Provider - Fast, local neural text-to-speech
        Optimized for Raspberry Pi 4 but runs well on any system
        """
        
        def __init__(self, config: PiperConfig):
            self.config = config
            self.output_format = "wav"
            self.supports_ssml = False  # Piper doesn't support SSML natively
            self.model_path = config.model_path
            self.config_path = config.config_path
            self.models_dir = config.download_dir
            self.voice_instance = None
            
            # Ensure models directory exists
            os.makedirs(self.models_dir, exist_ok=True)
            
            # Auto-download default model if no model specified
            if not self.model_path:
                self.model_path, self.config_path = self._ensure_default_model()
            
            # Initialize based on available method
            if PIPER_METHOD == "python_library":
                self._init_python_library()
            
            print(f"PiperTTSProvider: Initialized with model {self.config.model_name}")
            print(f"PiperTTSProvider: Method: {PIPER_METHOD}")
            print(f"PiperTTSProvider: Speed: {config.length_scale}, Noise: {config.noise_scale}")
        
        def _init_python_library(self):
            """Initialize the Python library version"""
            try:
                from piper.voice import PiperVoice
                self.voice_instance = PiperVoice.load(
                    self.model_path, 
                    config_path=self.config_path
                )
                print("PiperTTSProvider: Python library voice loaded successfully")
            except Exception as e:
                print(f"PiperTTSProvider: Failed to load voice with Python library: {e}")
                self.voice_instance = None
        
        def _ensure_default_model(self) -> tuple[str, str]:
            """Download and return path to default English model"""
            # Use model name from config
            model_name = self.config.model_name
            model_file = f"{model_name}.onnx"
            config_file = f"{model_name}.onnx.json"
            
            model_path = os.path.join(self.models_dir, model_file)
            config_path = os.path.join(self.models_dir, config_file)
            
            # Check if model already exists
            if os.path.exists(model_path) and os.path.exists(config_path):
                print(f"PiperTTSProvider: Using existing model {model_path}")
                return model_path, config_path
            
            print(f"PiperTTSProvider: Downloading model {model_name}...")
            
            # Download URLs for the model
            base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
            
            # Map model names to their paths
            model_paths = {
                "en_US-lessac-medium": "en/en_US/lessac/medium",
                "en_US-ljspeech-medium": "en/en_US/ljspeech/medium", 
                "en_US-ryan-medium": "en/en_US/ryan/medium",
                "en_GB-alba-medium": "en/en_GB/alba/medium",
                "en_US-amy-low": "en/en_US/amy/low",
                "en_US-arctic-medium": "en/en_US/arctic/medium"
            }
            
            model_path_segment = model_paths.get(model_name, "en/en_US/lessac/medium")
            model_url = f"{base_url}/{model_path_segment}/{model_file}"
            config_url = f"{base_url}/{model_path_segment}/{config_file}"
            
            try:
                # Download model file
                print(f"PiperTTSProvider: Downloading {model_file}...")
                self._download_file(model_url, model_path)
                # Download config file  
                print(f"PiperTTSProvider: Downloading {config_file}...")
                self._download_file(config_url, config_path)
                
                print(f"PiperTTSProvider: Successfully downloaded {model_name}")
                return model_path, config_path
                
            except Exception as e:
                print(f"PiperTTSProvider: Failed to download model: {e}")
                # Try to find any existing model in the directory
                existing_models = [f for f in os.listdir(self.models_dir) if f.endswith('.onnx')]
                if existing_models:
                    model_file = existing_models[0]
                    model_path = os.path.join(self.models_dir, model_file)
                    config_path = model_path + '.json'
                    if os.path.exists(config_path):
                        print(f"PiperTTSProvider: Using existing model {model_file}")
                        return model_path, config_path
                
                raise Exception("No Piper TTS model available and download failed")
        
        def _download_file(self, url: str, filepath: str):
            """Download a file from URL"""
            try:
                print(f"PiperTTSProvider: Downloading {os.path.basename(filepath)}...")
                urllib.request.urlretrieve(url, filepath)
            except Exception as e:
                raise Exception(f"Failed to download {url}: {e}")
        
        def generate_audio_data(self, text_to_speak: str) -> bytes:
            """Generate audio data using Piper TTS"""
            if not text_to_speak or text_to_speak.strip() == "":
                print("PiperTTSProvider: Skipping empty text")
                return b""
            
            # Skip error messages
            if (text_to_speak.startswith("LLM cleaning skipped") or 
                text_to_speak.startswith("Error:") or 
                text_to_speak.startswith("Could not convert")):
                print("PiperTTSProvider: Skipping error text")
                return b""
            
            # Strip SSML tags if present (Piper doesn't support SSML)
            clean_text = self._strip_ssml_tags(text_to_speak)
            
            if not clean_text.strip():
                return b""
            
            try:
                if PIPER_METHOD == "python_library" and self.voice_instance:
                    return self._generate_with_python_lib(clean_text)
                else:
                    return self._generate_with_command_line(clean_text)
            except Exception as e:
                print(f"PiperTTSProvider: Error generating audio: {e}")
                return b""
        
        def _strip_ssml_tags(self, text: str) -> str:
            """Remove SSML tags and convert to natural pauses for Piper"""
            if not text.strip().startswith('<speak>'):
                return text
            
            import re
            
            print("PiperTTSProvider: Converting SSML to natural text")
            
            # Convert SSML breaks to natural pauses
            text = re.sub(r'<break\s+time=["\'](\d+(?:\.\d+)?)s["\'][^>]*/?>', 
                         lambda m: '... ' * max(1, int(float(m.group(1)))), text)
            text = re.sub(r'<break\s+time=["\'](\d+)ms["\'][^>]*/?>', 
                         lambda m: '... ' if int(m.group(1)) > 300 else ' ', text)
            text = re.sub(r'<break\s+strength=["\']strong["\'][^>]*/?>', '... ... ', text)
            text = re.sub(r'<break\s+strength=["\']medium["\'][^>]*/?>', '... ', text)
            text = re.sub(r'<break\s+strength=["\']weak["\'][^>]*/?>', ' ', text)
            text = re.sub(r'<break[^>]*/?>', '... ', text)
            
            # Convert paragraph and sentence tags
            text = re.sub(r'<p[^>]*>', '\n\n', text)
            text = re.sub(r'</p>', '', text)
            text = re.sub(r'<s[^>]*>', '', text)
            text = re.sub(r'</s>', '. ', text)
            
            # Remove emphasis but keep the text
            text = re.sub(r'<emphasis[^>]*>', '', text)
            text = re.sub(r'</emphasis>', '', text)
            
            # Remove prosody tags
            text = re.sub(r'<prosody[^>]*>', '', text)
            text = re.sub(r'</prosody>', '', text)
            
            # Remove say-as tags but keep content
            text = re.sub(r'<say-as[^>]*>', '', text)
            text = re.sub(r'</say-as>', '', text)
            
            # Remove speak tags
            text = re.sub(r'<speak[^>]*>', '', text)
            text = re.sub(r'</speak>', '', text)
            
            # Clean up multiple spaces and normalize punctuation
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\.{4,}', '...', text)  # Limit multiple dots
            text = text.strip()
            
            return text
        
        def _generate_with_python_lib(self, text: str) -> bytes:
            """Generate audio using piper.voice Python library"""
            try:
                import wave
                from io import BytesIO
                
                # Create a BytesIO buffer to capture the audio
                audio_buffer = BytesIO()
                wav_file = wave.open(audio_buffer, 'wb')
                
                # Generate audio using the voice instance
                self.voice_instance.synthesize(text, wav_file)
                
                # Get the audio data
                audio_data = audio_buffer.getvalue()
                
                print(f"PiperTTSProvider: Generated {len(audio_data)} bytes with Python lib")
                return audio_data
                
            except Exception as e:
                print(f"PiperTTSProvider: Python library generation failed: {e}")
                # Fallback to command line
                return self._generate_with_command_line(text)
        
        def _generate_with_command_line(self, text: str) -> bytes:
            """Generate audio using Piper command line tool"""
            
            try:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                # Prepare command
                cmd = [
                    'piper',
                    '--model', self.model_path,
                    '--output_file', temp_path,
                ]
                
                # Add optional parameters
                if self.config_path and os.path.exists(self.config_path):
                    cmd.extend(['--config', self.config_path])
                
                cmd.extend([
                    '--length_scale', str(self.config.length_scale),
                    '--noise_scale', str(self.config.noise_scale),
                    '--noise_w', str(self.config.noise_w),
                    '--sentence_silence', str(self.config.sentence_silence),
                ])
                
                # Add speaker ID if specified (for multi-speaker models)
                if self.config.speaker_id is not None:
                    cmd.extend(['--speaker', str(self.config.speaker_id)])
                
                print(f"PiperTTSProvider: Generating audio for {len(text)} characters")
                
                # Run Piper with text input
                process = subprocess.run(
                    cmd,
                    input=text,
                    capture_output=True,
                    text=True,
                    timeout=60  # 60 second timeout
                )
                
                if process.returncode != 0:
                    raise Exception(f"Piper command failed: {process.stderr}")
                
                # Read the generated audio file
                if os.path.exists(temp_path):
                    with open(temp_path, 'rb') as f:
                        audio_data = f.read()
                    
                    # Clean up temp file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    
                    if len(audio_data) == 0:
                        raise Exception("No audio data generated")
                    
                    print(f"PiperTTSProvider: Generated {len(audio_data)} bytes with command line")
                    return audio_data
                else:
                    raise Exception("Audio file was not created")
                    
            except subprocess.TimeoutExpired:
                raise Exception("Piper command timed out")
            except Exception as e:
                raise Exception(f"Command line generation failed: {e}")
        
        def get_output_format(self) -> str:
            return self.output_format
        
        def list_available_models(self) -> Dict[str, Any]:
            """List available Piper models (for future enhancement)"""
            return {
                "en_US-lessac-medium": "High-quality US English female voice",
                "en_US-ljspeech-medium": "US English female voice (LJSpeech dataset)",
                "en_GB-alba-medium": "British English female voice",
                "en_US-ryan-medium": "US English male voice",
                "en_US-amy-low": "US English female voice (low quality, faster)",
                "en_US-arctic-medium": "US English male voice (Arctic dataset)"
            }

else:
    # Fallback class when Piper is not available
    class PiperTTSProvider(ITTSEngine):
        def __init__(self, config: PiperConfig):
            print("PiperTTSProvider: Piper TTS not available.")
            print("Install with: pip install piper-tts")
            print("Or download binary from: https://github.com/rhasspy/piper/releases")
            self.supports_ssml = False
        
        def generate_audio_data(self, text_to_speak: str) -> bytes:
            print("PiperTTSProvider: Piper TTS not available")
            return b""
        
        def get_output_format(self) -> str:
            return "wav"