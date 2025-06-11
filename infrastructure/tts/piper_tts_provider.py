# infrastructure/tts/piper_tts_provider.py - Enhanced with SSML Support
import os
import subprocess
import tempfile
import urllib.request
import re
from typing import Optional, Dict, Any, List
from domain.interfaces import ITTSEngine, ISSMLProcessor, SSMLCapability
from domain.config import PiperConfig

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
    class PiperTTSProvider(ITTSEngine, ISSMLProcessor):
        """Enhanced Piper TTS Provider with SSML support"""
        
        def __init__(self, config: PiperConfig):
            self.config = config
            self.output_format = "wav"
            self.model_path = config.model_path
            self.config_path = config.config_path
            self.models_dir = config.download_dir
            self.voice_instance = None
            
            # SSML configuration
            self.ssml_capability = SSMLCapability.BASIC
            self.supported_ssml_tags = [
                'speak', 'break', 'emphasis', 'prosody', 'say-as', 'p', 's'
            ]
            
            # Ensure models directory exists
            os.makedirs(self.models_dir, exist_ok=True)
            
            # Auto-download model if no path specified
            if not self.model_path:
                self.model_path, self.config_path = self._ensure_model()
            
            # Initialize Python library if available
            if PIPER_METHOD == "python_library":
                self._init_python_library()
            
            print(f"PiperTTSProvider: Using model {self.config.model_name} with SSML support")
        
        # === ITTSEngine Implementation ===
        
        def generate_audio_data(self, text_to_speak: str) -> bytes:
            """Generate audio data using Piper TTS with SSML support"""
            if not text_to_speak or text_to_speak.strip() == "":
                return b""
            
            # Skip error messages
            if (text_to_speak.startswith("LLM cleaning skipped") or 
                text_to_speak.startswith("Error:") or 
                text_to_speak.startswith("Could not convert")):
                return b""
            
            # Process text for Piper (handle SSML)
            processed_text = self.process_text_for_engine(text_to_speak)
            if not processed_text.strip():
                return b""
            
            try:
                if PIPER_METHOD == "python_library" and self.voice_instance:
                    return self._generate_with_python_lib(processed_text)
                else:
                    return self._generate_with_command_line(processed_text)
            except Exception as e:
                print(f"PiperTTSProvider: Error generating audio: {e}")
                return b""
        
        def get_output_format(self) -> str:
            return self.output_format
        
        # === ISSMLProcessor Implementation ===
        
        def get_ssml_capability(self) -> SSMLCapability:
            """Piper supports basic SSML features"""
            return SSMLCapability.BASIC
        
        def get_supported_tags(self) -> List[str]:
            """Get list of SSML tags supported by Piper"""
            return self.supported_ssml_tags.copy()
        
        def process_ssml(self, ssml_text: str) -> str:
            """Process SSML for Piper - keep supported tags, convert or strip others"""
            if not '<' in ssml_text:
                return ssml_text
            
            # If it's plain text, return as-is
            if not self._contains_ssml_tags(ssml_text):
                return ssml_text
            
            print(f"PiperTTSProvider: Processing SSML input ({len(ssml_text)} chars)")
            
            # Step 1: Extract content from speak tags
            processed_text = self._extract_speak_content(ssml_text)
            
            # Step 2: Process supported SSML tags
            processed_text = self._process_supported_ssml_tags(processed_text)
            
            # Step 3: Remove unsupported tags but preserve content
            processed_text = self._remove_unsupported_tags(processed_text)
            
            # Step 4: Validate and clean up
            processed_text = self._validate_and_cleanup(processed_text)
            
            print(f"PiperTTSProvider: SSML processed ({len(ssml_text)} -> {len(processed_text)} chars)")
            return processed_text
        
        def validate_ssml(self, ssml_text: str) -> Dict[str, Any]:
            """Validate SSML for Piper compatibility"""
            errors = []
            warnings = []
            
            if not '<' in ssml_text:
                return {'valid': True, 'errors': [], 'warnings': []}
            
            # Check for unsupported tags
            unsupported_tags = self._find_unsupported_tags(ssml_text)
            if unsupported_tags:
                warnings.extend([f"Unsupported tag will be stripped: <{tag}>" for tag in unsupported_tags])
            
            # Check for malformed SSML
            if '<speak>' in ssml_text and '</speak>' not in ssml_text:
                errors.append("Unclosed <speak> tag")
            
            # Check break tag format
            invalid_breaks = re.findall(r'<break[^>]*time="([^"]*)"[^>]*>', ssml_text)
            for break_time in invalid_breaks:
                if not re.match(r'^\d+(\.\d+)?(ms|s)$', break_time):
                    errors.append(f"Invalid break time format: {break_time}")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'unsupported_tags': unsupported_tags
            }
        
        # === SSML Processing Helper Methods ===
        
        def _contains_ssml_tags(self, text: str) -> bool:
            """Check if text contains SSML markup"""
            return bool(re.search(r'<[^>]+>', text))
        
        def _extract_speak_content(self, ssml_text: str) -> str:
            """Extract content from <speak> tags"""
            # Remove speak wrapper if present
            if ssml_text.strip().startswith('<speak>') and ssml_text.strip().endswith('</speak>'):
                content = ssml_text.strip()[7:-8]  # Remove <speak> and </speak>
                return content.strip()
            return ssml_text
        
        def _process_supported_ssml_tags(self, text: str) -> str:
            """Process SSML tags that Piper supports"""
            # Process break tags - Piper supports these natively
            text = self._process_break_tags(text)
            
            # Process emphasis tags - convert to Piper format if needed
            text = self._process_emphasis_tags(text)
            
            # Process prosody tags - keep basic rate control
            text = self._process_prosody_tags(text)
            
            # Process say-as tags - Piper has some support
            text = self._process_say_as_tags(text)
            
            # Process paragraph and sentence tags
            text = self._process_structural_tags(text)
            
            return text
        
        def _process_break_tags(self, text: str) -> str:
            """Process break tags for Piper"""
            # Piper supports break tags, but validate format
            def fix_break_time(match):
                time_attr = match.group(1)
                # Ensure proper format
                if re.match(r'^\d+ms$', time_attr):
                    return f'<break time="{time_attr}"/>'
                elif re.match(r'^\d+(\.\d+)?s$', time_attr):
                    return f'<break time="{time_attr}"/>'
                else:
                    # Invalid format, convert to valid one or remove
                    try:
                        # Try to extract number and assume milliseconds
                        num = re.search(r'(\d+)', time_attr)
                        if num:
                            return f'<break time="{num.group(1)}ms"/>'
                    except:
                        pass
                    return ''  # Remove invalid break
            
            text = re.sub(r'<break\s+time="([^"]*)"[^>]*/?>', fix_break_time, text)
            return text
        
        def _process_emphasis_tags(self, text: str) -> str:
            """Process emphasis tags for Piper"""
            # Piper supports emphasis, ensure correct levels
            def fix_emphasis(match):
                level = match.group(1) if match.group(1) else 'moderate'
                content = match.group(2)
                
                # Piper supports: strong, moderate, reduced
                if level in ['strong', 'moderate', 'reduced']:
                    return f'<emphasis level="{level}">{content}</emphasis>'
                else:
                    # Convert other levels to supported ones
                    level_map = {
                        'x-strong': 'strong',
                        'x-weak': 'reduced', 
                        'none': 'moderate'
                    }
                    mapped_level = level_map.get(level, 'moderate')
                    return f'<emphasis level="{mapped_level}">{content}</emphasis>'
            
            text = re.sub(r'<emphasis(?:\s+level="([^"]*)")?>([^<]*)</emphasis>', fix_emphasis, text)
            return text
        
        def _process_prosody_tags(self, text: str) -> str:
            """Process prosody tags for Piper (basic support)"""
            def fix_prosody(match):
                attributes = match.group(1)
                content = match.group(2)
                
                # Extract rate attribute (Piper's main prosody support)
                rate_match = re.search(r'rate="([^"]*)"', attributes)
                if rate_match:
                    rate = rate_match.group(1)
                    # Piper supports: x-slow, slow, medium, fast, x-fast
                    if rate in ['x-slow', 'slow', 'medium', 'fast', 'x-fast']:
                        return f'<prosody rate="{rate}">{content}</prosody>'
                    else:
                        # Try to map percentage or other values
                        if rate.endswith('%'):
                            try:
                                percent = int(rate[:-1])
                                if percent < 75:
                                    return f'<prosody rate="slow">{content}</prosody>'
                                elif percent > 125:
                                    return f'<prosody rate="fast">{content}</prosody>'
                                else:
                                    return f'<prosody rate="medium">{content}</prosody>'
                            except ValueError:
                                pass
                
                # If no supported prosody attributes, just return content
                return content
            
            text = re.sub(r'<prosody([^>]*)>([^<]*)</prosody>', fix_prosody, text)
            return text
        
        def _process_say_as_tags(self, text: str) -> str:
            """Process say-as tags for Piper"""
            def process_say_as(match):
                interpret_as = match.group(1)
                content = match.group(2)
                
                # Piper has limited say-as support
                if interpret_as in ['number', 'ordinal', 'digits']:
                    return f'<say-as interpret-as="{interpret_as}">{content}</say-as>'
                elif interpret_as == 'date':
                    # Piper supports basic date interpretation
                    return f'<say-as interpret-as="date">{content}</say-as>'
                else:
                    # Unsupported say-as type, just return content
                    return content
            
            text = re.sub(r'<say-as\s+interpret-as="([^"]*)"[^>]*>([^<]*)</say-as>', process_say_as, text)
            return text
        
        def _process_structural_tags(self, text: str) -> str:
            """Process paragraph and sentence tags"""
            # Piper supports <p> and <s> tags
            # These are kept as-is since they help with natural pauses
            return text
        
        def _remove_unsupported_tags(self, text: str) -> str:
            """Remove unsupported SSML tags but preserve their content"""
            unsupported_tags = [
                'voice', 'audio', 'mark', 'sub', 'phoneme', 'lexicon', 'meta'
            ]
            
            for tag in unsupported_tags:
                # Remove opening and closing tags but keep content
                text = re.sub(f'<{tag}[^>]*>', '', text)
                text = re.sub(f'</{tag}>', '', text)
            
            return text
        
        def _find_unsupported_tags(self, text: str) -> List[str]:
            """Find unsupported SSML tags in text"""
            all_tags = re.findall(r'<([^/\s>]+)', text)
            unsupported = []
            
            for tag in set(all_tags):
                if tag not in self.supported_ssml_tags:
                    unsupported.append(tag)
            
            return unsupported
        
        def _validate_and_cleanup(self, text: str) -> str:
            """Final validation and cleanup of processed text"""
            # Remove any remaining malformed tags
            text = re.sub(r'<[^>]*$', '', text)  # Remove unclosed tags at end
            text = re.sub(r'^[^<]*>', '', text)  # Remove orphaned closing tags at start
            
            # Clean up multiple spaces and line breaks
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n', text)
            
            # Ensure proper spacing around tags
            text = re.sub(r'>\s*<', '> <', text)
            
            return text.strip()
        
        # === Audio Generation Methods (Enhanced) ===
        
        def _init_python_library(self):
            """Initialize the Python library version"""
            try:
                from piper.voice import PiperVoice
                self.voice_instance = PiperVoice.load(self.model_path, config_path=self.config_path)
                print("PiperTTSProvider: Python library voice loaded with SSML support")
            except Exception as e:
                print(f"PiperTTSProvider: Failed to load voice with Python library: {e}")
                self.voice_instance = None
        
        def _generate_with_python_lib(self, text: str) -> bytes:
            """Generate using Python library with SSML support"""
            try:
                import wave
                from io import BytesIO
                
                audio_buffer = BytesIO()
                wav_file = wave.open(audio_buffer, 'wb')
                
                # Piper's Python library can handle SSML directly
                self.voice_instance.synthesize(text, wav_file)
                audio_data = audio_buffer.getvalue()
                
                print(f"PiperTTSProvider: Generated {len(audio_data)} bytes with SSML processing")
                return audio_data
                
            except Exception as e:
                print(f"PiperTTSProvider: Python library failed: {e}")
                return self._generate_with_command_line(text)
        
        def _generate_with_command_line(self, text: str) -> bytes:
            """Generate using command line with SSML support"""
            try:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                cmd = [
                    'piper',
                    '--model', self.model_path,
                    '--output_file', temp_path,
                    '--length_scale', str(self.config.length_scale),
                    '--noise_scale', str(self.config.noise_scale),
                    '--noise_w', str(self.config.noise_w),
                    '--sentence_silence', str(self.config.sentence_silence),
                ]
                
                if self.config_path and os.path.exists(self.config_path):
                    cmd.extend(['--config', self.config_path])
                
                if self.config.speaker_id is not None:
                    cmd.extend(['--speaker', str(self.config.speaker_id)])
                
                # Piper command line can handle SSML input directly
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
        
        # === Model Management (Unchanged) ===
        
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
            base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
            
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
    class PiperTTSProvider(ITTSEngine, ISSMLProcessor):
        def __init__(self, config: PiperConfig):
            print("PiperTTSProvider: Piper TTS not available.")
            print("Install with: pip install piper-tts")
        
        def generate_audio_data(self, text_to_speak: str) -> bytes:
            print("PiperTTSProvider: Piper TTS not available")
            return b""
        
        def get_output_format(self) -> str:
            return "wav"
        
        def get_ssml_capability(self) -> SSMLCapability:
            return SSMLCapability.NONE
        
        def get_supported_tags(self) -> List[str]:
            return []
        
        def process_ssml(self, ssml_text: str) -> str:
            return ssml_text
        def prefers_sync_processing(self) -> bool:
            return True  # Local engine, subprocess-based
