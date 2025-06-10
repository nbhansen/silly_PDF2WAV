# infrastructure/tts/gemini_tts_provider.py - Enhanced with Full SSML Support
import os
import wave
import time
import tempfile
import subprocess
import re
from typing import List, Dict, Any
from google import genai
from google.genai import types
from domain.interfaces import ITTSEngine, ISSMLProcessor, SSMLCapability
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
    class GeminiTTSProvider(ITTSEngine, ISSMLProcessor):
        """Enhanced Gemini TTS Provider with full SSML support"""
        
        def __init__(self, config: GeminiConfig):
            self.voice_name = config.voice_name
            self.style_prompt = config.style_prompt
            self.api_key = config.api_key or os.getenv('GOOGLE_AI_API_KEY', '')
            self.output_format = "wav"  # We'll convert everything to WAV for consistency
            self.client = None
            
            # Rate limiting settings
            self.last_request_time = 0
            self.min_request_interval = config.min_request_interval
            self.max_retries = config.max_retries
            self.base_retry_delay = config.base_retry_delay
            
            # SSML configuration
            self.ssml_capability = SSMLCapability.FULL
            self.supported_ssml_tags = [
                'speak', 'break', 'emphasis', 'prosody', 'say-as', 'voice', 
                'audio', 'mark', 'p', 's', 'sub', 'phoneme', 'lexicon'
            ]
            
            try:
                if not self.api_key:
                    print("GeminiTTSProvider: WARNING - No API key provided")
                    return
                    
                self.client = genai.Client(api_key=self.api_key)
                print(f"GeminiTTSProvider: Initialized with voice '{self.voice_name}' and full SSML support")
            except Exception as e:
                print(f"GeminiTTSProvider: Error initializing Gemini client: {e}")
                self.client = None

        # === ITTSEngine Implementation ===

        def generate_audio_data(self, text_to_speak: str) -> bytes:
            """Generate audio with full SSML support"""
            if not self.client:
                print("GeminiTTSProvider: Client not available. Skipping audio generation.")
                return b""
                
            print(f"GeminiTTSProvider: Attempting Gemini TTS generation with SSML support.")
            
            if not text_to_speak or text_to_speak.strip() == "" or \
               text_to_speak.startswith("LLM cleaning skipped") or text_to_speak.startswith("Error:") or \
               text_to_speak.startswith("Could not convert") or text_to_speak.startswith("No text could be extracted"):
                print("GeminiTTSProvider: Skipping audio generation due to empty or error text.")
                return b""
            
            # Process text for Gemini (validate SSML)
            processed_text = self.process_text_for_engine(text_to_speak)
            
            # Apply rate limiting before making request
            self._apply_rate_limit()
            
            # Retry logic with exponential backoff
            for attempt in range(self.max_retries):
                try:
                    return self._make_tts_request(processed_text, attempt)
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
                            return b""
                        time.sleep(2 ** attempt)
                        continue
            
            print(f"GeminiTTSProvider: All {self.max_retries} attempts failed")
            return b""

        def get_output_format(self) -> str:
            return self.output_format

        # === ISSMLProcessor Implementation ===

        def get_ssml_capability(self) -> SSMLCapability:
            """Gemini supports full SSML specification"""
            return SSMLCapability.FULL

        def get_supported_tags(self) -> List[str]:
            """Gemini supports all standard SSML tags"""
            return self.supported_ssml_tags.copy()

        def process_ssml(self, ssml_text: str) -> str:
            """
            Process SSML for Gemini - validate and enhance
            Gemini supports full SSML, so we mainly validate and optimize
            """
            if not '<' in ssml_text:
                return ssml_text
                
            print(f"GeminiTTSProvider: Processing SSML input ({len(ssml_text)} chars)")
            
            # Step 1: Ensure proper SSML document structure
            processed_text = self._ensure_proper_ssml_structure(ssml_text)
            
            # Step 2: Validate and enhance SSML for Gemini
            processed_text = self._validate_and_enhance_ssml(processed_text)
            
            # Step 3: Optimize for Gemini's specific features
            processed_text = self._optimize_for_gemini(processed_text)
            
            print(f"GeminiTTSProvider: SSML processed and validated ({len(ssml_text)} -> {len(processed_text)} chars)")
            return processed_text

        def validate_ssml(self, ssml_text: str) -> Dict[str, Any]:
            """Comprehensive SSML validation for Gemini"""
            errors = []
            warnings = []
            suggestions = []
            
            if not '<' in ssml_text:
                return {'valid': True, 'errors': [], 'warnings': [], 'suggestions': []}
            
            # Check document structure
            if not ssml_text.strip().startswith('<speak>'):
                warnings.append("SSML should be wrapped in <speak> tags for best results")
            
            if '<speak>' in ssml_text and '</speak>' not in ssml_text:
                errors.append("Unclosed <speak> tag")
            
            # Validate specific tag formats
            self._validate_break_tags(ssml_text, errors, warnings)
            self._validate_prosody_tags(ssml_text, errors, warnings)
            self._validate_say_as_tags(ssml_text, errors, warnings)
            self._validate_voice_tags(ssml_text, errors, warnings, suggestions)
            
            # Check for nested structure issues
            self._validate_tag_nesting(ssml_text, errors)
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'suggestions': suggestions,
                'gemini_optimized': True
            }

        # === SSML Processing Helper Methods ===

        def _ensure_proper_ssml_structure(self, ssml_text: str) -> str:
            """Ensure proper SSML document structure"""
            text = ssml_text.strip()
            
            # Wrap in speak tags if not already wrapped
            if not text.startswith('<speak>'):
                if not text.endswith('</speak>'):
                    text = f'<speak>{text}</speak>'
                else:
                    text = f'<speak>{text}'
            elif not text.endswith('</speak>'):
                text = f'{text}</speak>'
            
            return text

        def _validate_and_enhance_ssml(self, ssml_text: str) -> str:
            """Validate and enhance SSML for Gemini compatibility"""
            text = ssml_text
            
            # Fix common SSML issues
            text = self._fix_break_tags(text)
            text = self._fix_emphasis_tags(text)
            text = self._fix_prosody_tags(text)
            text = self._fix_say_as_tags(text)
            text = self._fix_voice_tags(text)
            
            return text

        def _optimize_for_gemini(self, ssml_text: str) -> str:
            """Optimize SSML specifically for Gemini TTS"""
            text = ssml_text
            
            # Add Gemini-specific optimizations
            text = self._optimize_voice_selection(text)
            text = self._optimize_prosody_for_academic_content(text)
            text = self._add_gemini_specific_features(text)
            
            return text

        def _fix_break_tags(self, text: str) -> str:
            """Fix and validate break tags for Gemini"""
            def fix_break(match):
                time_value = match.group(1)
                
                # Gemini supports: Ns, Nms, weak, medium, strong, x-weak, x-strong
                if re.match(r'^\d+(\.\d+)?(s|ms)$', time_value):
                    return f'<break time="{time_value}"/>'
                elif time_value in ['weak', 'medium', 'strong', 'x-weak', 'x-strong']:
                    return f'<break strength="{time_value}"/>'
                else:
                    # Try to convert invalid formats
                    if time_value.isdigit():
                        return f'<break time="{time_value}ms"/>'
                    else:
                        return '<break strength="medium"/>'  # Default fallback
            
            text = re.sub(r'<break\s+(?:time|strength)="([^"]*)"[^>]*/?>', fix_break, text)
            return text

        def _fix_emphasis_tags(self, text: str) -> str:
            """Fix emphasis tags for Gemini"""
            def fix_emphasis(match):
                level = match.group(1) if match.group(1) else 'moderate'
                content = match.group(2)
                
                # Gemini supports: strong, moderate, reduced
                gemini_levels = ['strong', 'moderate', 'reduced']
                if level in gemini_levels:
                    return f'<emphasis level="{level}">{content}</emphasis>'
                else:
                    # Map other levels to Gemini-supported ones
                    level_map = {
                        'x-strong': 'strong',
                        'x-weak': 'reduced',
                        'none': 'moderate'
                    }
                    mapped_level = level_map.get(level, 'moderate')
                    return f'<emphasis level="{mapped_level}">{content}</emphasis>'
            
            text = re.sub(r'<emphasis(?:\s+level="([^"]*)")?>([^<]*)</emphasis>', fix_emphasis, text)
            return text

        def _fix_prosody_tags(self, text: str) -> str:
            """Fix prosody tags for Gemini (full support)"""
            def fix_prosody(match):
                attributes = match.group(1)
                content = match.group(2)
                
                # Gemini supports rate, pitch, volume with various formats
                fixed_attrs = []
                
                # Process rate attribute
                rate_match = re.search(r'rate="([^"]*)"', attributes)
                if rate_match:
                    rate = rate_match.group(1)
                    if rate in ['x-slow', 'slow', 'medium', 'fast', 'x-fast'] or \
                       re.match(r'^\d+(\.\d+)?%?$', rate):
                        fixed_attrs.append(f'rate="{rate}"')
                
                # Process pitch attribute
                pitch_match = re.search(r'pitch="([^"]*)"', attributes)
                if pitch_match:
                    pitch = pitch_match.group(1)
                    if pitch in ['x-low', 'low', 'medium', 'high', 'x-high'] or \
                       re.match(r'^[+-]?\d+(\.\d+)?(Hz|%)?$', pitch):
                        fixed_attrs.append(f'pitch="{pitch}"')
                
                # Process volume attribute
                volume_match = re.search(r'volume="([^"]*)"', attributes)
                if volume_match:
                    volume = volume_match.group(1)
                    if volume in ['silent', 'x-soft', 'soft', 'medium', 'loud', 'x-loud'] or \
                       re.match(r'^[+-]?\d+(\.\d+)?(dB)?$', volume):
                        fixed_attrs.append(f'volume="{volume}"')
                
                if fixed_attrs:
                    return f'<prosody {" ".join(fixed_attrs)}>{content}</prosody>'
                else:
                    return content  # No valid attributes, return content only
            
            text = re.sub(r'<prosody([^>]*)>([^<]*)</prosody>', fix_prosody, text)
            return text

        def _fix_say_as_tags(self, text: str) -> str:
            """Fix say-as tags for Gemini"""
            def fix_say_as(match):
                interpret_as = match.group(1)
                format_attr = match.group(2) if match.group(2) else ''
                content = match.group(3)
                
                # Gemini supports extensive say-as types
                supported_types = [
                    'characters', 'spell-out', 'cardinal', 'number', 'ordinal',
                    'digits', 'fraction', 'unit', 'date', 'time', 'telephone',
                    'address', 'interjection', 'expletive'
                ]
                
                if interpret_as in supported_types:
                    if format_attr:
                        return f'<say-as interpret-as="{interpret_as}" {format_attr}>{content}</say-as>'
                    else:
                        return f'<say-as interpret-as="{interpret_as}">{content}</say-as>'
                else:
                    # Try to map unsupported types
                    type_map = {
                        'verbatim': 'spell-out',
                        'alpha': 'characters',
                        'numeric': 'number'
                    }
                    mapped_type = type_map.get(interpret_as, 'characters')
                    return f'<say-as interpret-as="{mapped_type}">{content}</say-as>'
            
            text = re.sub(r'<say-as\s+interpret-as="([^"]*)"([^>]*)>([^<]*)</say-as>', fix_say_as, text)
            return text

        def _fix_voice_tags(self, text: str) -> str:
            """Fix voice tags for Gemini"""
            def fix_voice(match):
                attributes = match.group(1)
                content = match.group(2)
                
                # Extract name attribute (primary for Gemini)
                name_match = re.search(r'name="([^"]*)"', attributes)
                if name_match:
                    voice_name = name_match.group(1)
                    # Keep the voice tag as Gemini supports voice changes
                    return f'<voice name="{voice_name}">{content}</voice>'
                else:
                    # No name attribute, remove voice tag but keep content
                    return content
            
            text = re.sub(r'<voice([^>]*)>([^<]*)</voice>', fix_voice, text)
            return text

        def _optimize_voice_selection(self, text: str) -> str:
            """Optimize voice selection for Gemini"""
            # If no voice tags present and we have a preferred voice, we could add it
            # But generally, the main voice is set via the API call
            return text

        def _optimize_prosody_for_academic_content(self, text: str) -> str:
            """Add Gemini-specific prosody optimizations for academic content"""
            # Add subtle prosody enhancements for better academic narration
            
            # Slow down technical terms (simple heuristic)
            text = re.sub(r'\b([A-Z]{3,})\b', r'<prosody rate="90%">\1</prosody>', text)
            
            # Add slight emphasis to transition words if not already emphasized
            transition_words = ['however', 'therefore', 'furthermore', 'moreover', 'consequently']
            for word in transition_words:
                if f'<emphasis' not in text or word not in text:
                    pattern = f'\\b{word}\\b'
                    if re.search(pattern, text, re.IGNORECASE):
                        text = re.sub(pattern, f'<prosody pitch="+2%" rate="95%">{word}</prosody>', 
                                    text, flags=re.IGNORECASE)
            
            return text

        def _add_gemini_specific_features(self, text: str) -> str:
            """Add Gemini-specific SSML features"""
            # Could add audio effects, marks, or other Gemini-specific enhancements
            # For now, keep it simple and focus on compatibility
            return text

        def _validate_break_tags(self, text: str, errors: List[str], warnings: List[str]):
            """Validate break tags"""
            breaks = re.findall(r'<break\s+(?:time|strength)="([^"]*)"[^>]*/?>', text)
            for break_value in breaks:
                if not (re.match(r'^\d+(\.\d+)?(s|ms)$', break_value) or 
                       break_value in ['weak', 'medium', 'strong', 'x-weak', 'x-strong']):
                    errors.append(f"Invalid break value: {break_value}")

        def _validate_prosody_tags(self, text: str, errors: List[str], warnings: List[str]):
            """Validate prosody tags"""
            prosody_tags = re.findall(r'<prosody([^>]*)>', text)
            for attrs in prosody_tags:
                if not any(attr in attrs for attr in ['rate=', 'pitch=', 'volume=']):
                    warnings.append("Prosody tag without recognized attributes")

        def _validate_say_as_tags(self, text: str, errors: List[str], warnings: List[str]):
            """Validate say-as tags"""
            say_as_tags = re.findall(r'<say-as\s+interpret-as="([^"]*)"', text)
            supported_types = [
                'characters', 'spell-out', 'cardinal', 'number', 'ordinal',
                'digits', 'fraction', 'unit', 'date', 'time', 'telephone'
            ]
            for interpret_as in say_as_tags:
                if interpret_as not in supported_types:
                    warnings.append(f"Potentially unsupported say-as type: {interpret_as}")

        def _validate_voice_tags(self, text: str, errors: List[str], warnings: List[str], suggestions: List[str]):
            """Validate voice tags"""
            voice_tags = re.findall(r'<voice([^>]*)>', text)
            for attrs in voice_tags:
                if 'name=' not in attrs:
                    errors.append("Voice tag missing name attribute")
                else:
                    suggestions.append("Consider using Gemini's built-in voices for best quality")

        def _validate_tag_nesting(self, text: str, errors: List[str]):
            """Validate proper tag nesting"""
            # Simple validation for common nesting issues
            # This could be more sophisticated
            if '<emphasis>' in text and '</emphasis>' not in text:
                errors.append("Unclosed emphasis tag")
            if '<prosody>' in text and '</prosody>' not in text:
                errors.append("Unclosed prosody tag")

        # === Audio Generation Methods ===

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
            """Make the actual TTS request with SSML support"""
            # For SSML content, we may want to adjust the prompt
            if text_to_speak.strip().startswith('<speak>'):
                # This is SSML content
                prompt = text_to_speak
                if self.style_prompt:
                    # For SSML, style prompt might interfere, so be careful
                    print("GeminiTTSProvider: Using SSML content, style prompt may be ignored")
            else:
                # Plain text, apply style prompt
                prompt = f"{self.style_prompt}: {text_to_speak}" if self.style_prompt else text_to_speak
            
            print(f"GeminiTTSProvider: Making TTS request (attempt {attempt + 1}) with voice '{self.voice_name}' and SSML")
            
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

        # === Error Handling and Utilities ===

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
            
            return True

        def _create_wav_from_pcm(self, pcm_data: bytes) -> bytes:
            """Create a proper WAV file from raw PCM audio data"""
            # Gemini TTS typically returns 16-bit PCM at 24kHz, mono
            sample_rate = 24000
            bits_per_sample = 16
            channels = 1
            
            # Calculate WAV header values
            byte_rate = sample_rate * channels * bits_per_sample // 8
            block_align = channels * bits_per_sample // 8
            data_size = len(pcm_data)
            file_size = 36 + data_size
            
            # Create WAV header
            wav_header = bytearray()
            wav_header += b'RIFF'
            wav_header += file_size.to_bytes(4, 'little')
            wav_header += b'WAVE'
            wav_header += b'fmt '
            wav_header += (16).to_bytes(4, 'little')
            wav_header += (1).to_bytes(2, 'little')
            wav_header += channels.to_bytes(2, 'little')
            wav_header += sample_rate.to_bytes(4, 'little')
            wav_header += byte_rate.to_bytes(4, 'little')
            wav_header += block_align.to_bytes(2, 'little')
            wav_header += bits_per_sample.to_bytes(2, 'little')
            wav_header += b'data'
            wav_header += data_size.to_bytes(4, 'little')
            
            return bytes(wav_header) + pcm_data

        def _convert_with_ffmpeg(self, raw_audio_data: bytes, detected_format: str) -> bytes:
            """Convert non-WAV audio formats using FFmpeg"""
            try:
                if not self._check_ffmpeg():
                    print("GeminiTTSProvider: FFmpeg not available, returning raw audio data")
                    return raw_audio_data
                
                with tempfile.NamedTemporaryFile(suffix=f".{detected_format}", delete=False) as input_file:
                    input_file.write(raw_audio_data)
                    input_path = input_file.name
                
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output_file:
                    output_path = output_file.name
                
                try:
                    cmd = [
                        'ffmpeg', '-y',
                        '-i', input_path,
                        '-acodec', 'pcm_s16le',
                        '-ar', '22050',
                        '-ac', '1',
                        output_path
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        with open(output_path, 'rb') as f:
                            wav_data = f.read()
                        return wav_data
                    else:
                        print(f"GeminiTTSProvider: FFmpeg conversion failed: {result.stderr}")
                        return raw_audio_data
                        
                finally:
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
                return "mp3"  # Default assumption

        def _check_ffmpeg(self) -> bool:
            """Check if FFmpeg is available"""
            try:
                result = subprocess.run(['ffmpeg', '-version'], 
                                      capture_output=True, text=True, timeout=5)
                return result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                return False

else:
    # Fallback when Gemini TTS is not available
    class GeminiTTSProvider(ITTSEngine, ISSMLProcessor):
        def __init__(self, config: GeminiConfig):
            print("GeminiTTSProvider: Google Gemini TTS library not available.")
        
        def generate_audio_data(self, text_to_speak: str) -> bytes:
            print("GeminiTTSProvider: Google Gemini TTS library not available.")
            return b""
        
        def get_output_format(self) -> str:
            return "wav"
        
        def get_ssml_capability(self) -> SSMLCapability:
            return SSMLCapability.NONE
        
        def get_supported_tags(self) -> List[str]:
            return []
        
        def process_ssml(self, ssml_text: str) -> str:
            return ssml_text