# infrastructure/tts/piper_tts_provider.py
import os
import subprocess
import tempfile
import json
from typing import Optional, Dict, Any
from domain.models import ITTSEngine, TTSConfig
from dataclasses import dataclass

@dataclass
class PiperConfig:
    """Configuration for Piper TTS"""
    model_name: str = "en_US-lessac-medium"  # Model identifier
    model_path: Optional[str] = None  # Path to .onnx model file
    config_path: Optional[str] = None  # Path to .onnx.json config file
    speaker_id: Optional[int] = None  # For multi-speaker models
    length_scale: float = 1.0  # Speed control (1.0 = normal, <1.0 = faster, >1.0 = slower)
    noise_scale: float = 0.667  # Variability in speech
    noise_w: float = 0.8  # Pronunciation variability
    sentence_silence: float = 0.2  # Silence between sentences (seconds)
    use_gpu: bool = False  # Currently Piper is CPU-optimized
    download_dir: str = "piper_models"  # Directory to store downloaded models

try:
    # Try to import piper_tts Python module first
    import piper_tts
    PIPER_AVAILABLE = True
    print("Piper TTS Python library found and available")
except ImportError:
    try:
        # Fallback: check if piper command is available
        result = subprocess.run(['piper', '--version'], capture_output=True, text=True, timeout=5)
        PIPER_AVAILABLE = result.returncode == 0
        if PIPER_AVAILABLE:
            print("Piper TTS command found and available")
        else:
            print("Piper TTS not found - install with: pip install piper-tts")
            PIPER_AVAILABLE = False
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        print("Piper TTS not found. Install with: pip install piper-tts")
        PIPER_AVAILABLE = False

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
            
            # Ensure models directory exists
            os.makedirs(self.models_dir, exist_ok=True)
            
            # Auto-download default model if no model specified
            if not self.model_path:
                self.model_path, self.config_path = self._ensure_default_model()
            
            print(f"PiperTTSProvider: Initialized with model {self.model_path}")
            print(f"PiperTTSProvider: Speed: {config.length_scale}, Noise: {config.noise_scale}")
        
        def _ensure_default_model(self) -> tuple[str, str]:
            """Download and return path to default English model"""
            # Default to high-quality English model
            model_name = self.config.model_name or "en_US-lessac-medium"
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
                "en_GB-alba-medium": "en/en_GB/alba/medium"
            }
            
            model_path_segment = model_paths.get(model_name, "en/en_US/lessac/medium")
            model_url = f"{base_url}/{model_path_segment}/{model_file}"
            config_url = f"{base_url}/{model_path_segment}/{config_file}"
            
            try:
                # Download model file
                self._download_file(model_url, model_path)
                # Download config file  
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
                    print(f"PiperTTSProvider: Using existing model {model_file}")
                    return model_path, config_path
                else:
                    raise Exception("No Piper TTS model available and download failed")
        
        def _download_file(self, url: str, filepath: str):
            """Download a file from URL"""
            import urllib.request
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
                return self._generate_with_piper(clean_text)
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
        
        def _generate_with_piper(self, text: str) -> bytes:
            """Generate audio using Piper Python library or command line"""
            
            try:
                # Try Python library first (more reliable)
                return self._generate_with_python_lib(text)
            except Exception as e:
                print(f"PiperTTSProvider: Python library failed: {e}")
                try:
                    # Fallback to command line
                    return self._generate_with_command_line(text)
                except Exception as e2:
                    print(f"PiperTTSProvider: Command line also failed: {e2}")
                    return b""
        
        def _generate_with_python_lib(self, text: str) -> bytes:
            """Generate audio using piper_tts Python library"""
            try:
                import piper_tts
                from io import BytesIO
                
                # Create a voice instance
                voice = piper_tts.PiperVoice.load(
                    self.model_path,
                    config_path=self.config_path,
                    use_cuda=False  # Piper is CPU optimized
                )
                
                # Generate audio
                audio_stream = BytesIO()
                voice.synthesize(
                    text, 
                    audio_stream,
                    speaker_id=self.config.speaker_id,
                    length_scale=self.config.length_scale,
                    noise_scale=self.config.noise_scale,
                    noise_w=self.config.noise_w,
                    sentence_silence=self.config.sentence_silence
                )
                
                audio_data = audio_stream.getvalue()
                print(f"PiperTTSProvider: Generated {len(audio_data)} bytes with Python lib")
                return audio_data
                
            except ImportError:
                raise Exception("piper_tts Python library not available")
            except Exception as e:
                raise Exception(f"Python library generation failed: {e}")
        
        def _generate_with_command_line(self, text: str) -> bytes:
            """Generate audio using Piper command line tool"""
            
            # Prepare command
            cmd = [
                'piper',
                '--model', self.model_path,
                '--config', self.config_path,
                '--length_scale', str(self.config.length_scale),
                '--noise_scale', str(self.config.noise_scale),
                '--noise_w', str(self.config.noise_w),
                '--sentence_silence', str(self.config.sentence_silence),
            ]
            
            # Add speaker ID if specified (for multi-speaker models)
            if self.config.speaker_id is not None:
                cmd.extend(['--speaker', str(self.config.speaker_id)])
            
            # Add output format
            cmd.extend(['--output_file', '-'])  # Output to stdout
            
            try:
                print(f"PiperTTSProvider: Generating audio for {len(text)} characters")
                
                # Run Piper with text input
                process = subprocess.run(
                    cmd,
                    input=text,
                    capture_output=True,
                    text=True,
                    timeout=30  # 30 second timeout
                )
                
                if process.returncode != 0:
                    raise Exception(f"Piper command failed: {process.stderr}")
                
                # Get audio data from stdout
                audio_data = process.stdout.encode('latin1')  # Binary data
                
                if len(audio_data) == 0:
                    raise Exception("No audio data generated")
                
                print(f"PiperTTSProvider: Generated {len(audio_data)} bytes with command line")
                return audio_data
                
            except subprocess.TimeoutExpired:
                raise Exception("Piper command timed out")
            except Exception as e:
                raise Exception(f"Command line generation failed: {e}")
        
        def get_output_format(self) -> str:
            return self.output_format
        
        def list_available_models(self) -> Dict[str, Any]:
            """List available Piper models (for future enhancement)"""
            # This could be expanded to dynamically list/download models
            return {
                "en_US-lessac-medium": "High-quality US English female voice",
                "en_US-ljspeech-medium": "US English female voice (LJSpeech dataset)",
                "en_GB-alba-medium": "British English female voice",
                "en_US-ryan-medium": "US English male voice",
                # Add more models as needed
            }

else:
    # Fallback class when Piper is not available
    class PiperTTSProvider(ITTSEngine):
        def __init__(self, config: PiperConfig):
            print("PiperTTSProvider: Piper TTS not available. Install with: pip install piper-tts")
            self.supports_ssml = False
        
        def generate_audio_data(self, text_to_speak: str) -> bytes:
            print("PiperTTSProvider: Piper TTS not available")
            return b""
        
        def get_output_format(self) -> str:
            return "wav"
        
        def _strip_ssml_tags(self, text: str) -> str:
            """Fallback SSML stripping method"""
            import re
            if not text.strip().startswith('<speak>'):
                return text
            
            # Basic SSML tag removal
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text