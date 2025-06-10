# infrastructure/tts/coqui_tts_provider.py - Enhanced with Basic SSML Support
import os
import torch
import re
from typing import Optional, Dict, Any, List
from domain.interfaces import ITTSEngine, ISSMLProcessor, SSMLCapability
from domain.config import CoquiConfig

try:
    from TTS.api import TTS as CoquiTTS_API
    COQUI_TTS_AVAILABLE = True
    print("Coqui TTS library (TTS.api) found and imported successfully.")
except ImportError:
    print("TTS (Coqui TTS) library not found. CoquiTTSProvider will not be available.")
    COQUI_TTS_AVAILABLE = False

if COQUI_TTS_AVAILABLE:
    class CoquiTTSProvider(ITTSEngine, ISSMLProcessor):
        """Enhanced Coqui TTS Provider with basic SSML support"""
        
        def __init__(self, config: CoquiConfig):
            self.model_name = config.model_name or self._quality_to_model("medium")
            self.speaker_to_use = config.speaker
            self.use_gpu_if_available = config.use_gpu if config.use_gpu is not None else False
            self.tts_model = None
            self.is_multi_speaker = False
            self.output_format = "wav"

            # SSML configuration for Coqui
            self.ssml_capability = SSMLCapability.BASIC  # Some models support basic SSML
            self.supported_ssml_tags = [
                'speak', 'break', 'emphasis', 'prosody', 'p', 's'
            ]
            self.model_supports_ssml = False  # Will be determined after model loading

            try:
                print(f"CoquiTTSProvider: Initializing Coqui TTS model: {self.model_name}")
                self.tts_model = CoquiTTS_API(model_name=self.model_name) 
                
                # Determine device
                if self.use_gpu_if_available:
                    if torch.cuda.is_available():
                        device = "cuda"
                        print("CoquiTTSProvider: CUDA is available. Attempting to use GPU.")
                    else:
                        device = "cpu"
                        print("CoquiTTSProvider: CUDA not available. Using CPU.")
                else:
                    device = "cpu"
                    print("CoquiTTSProvider: GPU usage not requested. Using CPU.")
                
                self.tts_model.to(device) 
                print(f"CoquiTTSProvider: Coqui TTS model initialized successfully on {device.upper()}.")

                # Check for multi-speaker support
                if self.tts_model.is_multi_speaker:
                    self.is_multi_speaker = True
                    print("CoquiTTSProvider: Model is multi-speaker.")
                    self._setup_speaker_selection()
                else:
                    print(f"CoquiTTSProvider: Model '{self.model_name}' is single-speaker.")

                # Detect SSML support
                self._detect_ssml_support()
                
            except Exception as e:
                print(f"CoquiTTSProvider: Error initializing Coqui TTS model: {e}")
                self.tts_model = None 

        # === ITTSEngine Implementation ===

        def generate_audio_data(self, text_to_speak: str) -> bytes:
            """Generates raw audio data from text using Coqui TTS with SSML support"""
            if not self.tts_model:
                print("CoquiTTSProvider: Coqui TTS model not available. Skipping audio generation.")
                return b""
            
            print(f"CoquiTTSProvider: Attempting Coqui TTS audio generation with SSML support.")
            
            if not text_to_speak or text_to_speak.strip() == "" or \
               text_to_speak.startswith("LLM cleaning skipped") or text_to_speak.startswith("Error:") or \
               text_to_speak.startswith("Could not convert") or text_to_speak.startswith("No text could be extracted"):
                print("CoquiTTSProvider: Skipping audio generation due to empty or error text from previous steps.")
                return b""
            
            # Process text for Coqui (handle SSML)
            processed_text = self.process_text_for_engine(text_to_speak)
            
            try:
                # Coqui's tts_to_file saves directly, so we need a temp file to get bytes
                temp_audio_filepath = "temp_coqui_audio.wav"
                speaker_arg = None 
                
                if self.is_multi_speaker:
                    if self.speaker_to_use:
                        speaker_arg = self.speaker_to_use
                    else:
                        print("CoquiTTSProvider: ERROR - Model is multi-speaker but no speaker is selected/available.")
                        return b""
                
                # Generate audio with processed text
                self.tts_model.tts_to_file(text=processed_text, speaker=speaker_arg, file_path=temp_audio_filepath)
                
                with open(temp_audio_filepath, "rb") as f:
                    audio_data = f.read()
                os.remove(temp_audio_filepath)  # Clean up temp file
                
                print(f"CoquiTTSProvider: Generated audio data ({len(audio_data)} bytes) with SSML processing.")
                return audio_data
                
            except Exception as e:
                print(f"CoquiTTSProvider: Error generating audio data with Coqui TTS: {e}")
                return b""
        
        def get_output_format(self) -> str:
            return self.output_format

        # === ISSMLProcessor Implementation ===

        def get_ssml_capability(self) -> SSMLCapability:
            """Coqui supports basic SSML features on some models"""
            return SSMLCapability.BASIC if self.model_supports_ssml else SSMLCapability.NONE

        def get_supported_tags(self) -> List[str]:
            """Get list of SSML tags supported by this Coqui model"""
            if self.model_supports_ssml:
                return self.supported_ssml_tags.copy()
            else:
                return []

        def process_ssml(self, ssml_text: str) -> str:
            """Process SSML for Coqui - basic support with fallback to text"""
            if not '<' in ssml_text:
                return ssml_text
            
            print(f"CoquiTTSProvider: Processing SSML input ({len(ssml_text)} chars)")
            
            if self.model_supports_ssml:
                # Model supports SSML, process it
                processed_text = self._process_ssml_for_coqui(ssml_text)
            else:
                # Model doesn't support SSML, strip tags but preserve natural flow
                processed_text = self._strip_ssml_with_natural_conversion(ssml_text)
            
            print(f"CoquiTTSProvider: SSML processed ({len(ssml_text)} -> {len(processed_text)} chars)")
            return processed_text

        def validate_ssml(self, ssml_text: str) -> Dict[str, Any]:
            """Validate SSML for Coqui compatibility"""
            errors = []
            warnings = []
            
            if not '<' in ssml_text:
                return {'valid': True, 'errors': [], 'warnings': []}
            
            if not self.model_supports_ssml:
                warnings.append("Current Coqui model doesn't support SSML - tags will be stripped")
                return {'valid': True, 'errors': [], 'warnings': warnings}
            
            # Validate basic SSML structure
            if '<speak>' in ssml_text and '</speak>' not in ssml_text:
                errors.append("Unclosed <speak> tag")
            
            # Check for unsupported tags
            unsupported_tags = self._find_unsupported_tags(ssml_text)
            if unsupported_tags:
                warnings.extend([f"Tag not supported by Coqui model: <{tag}>" for tag in unsupported_tags])
            
            # Validate break tags
            break_tags = re.findall(r'<break\s+time="([^"]*)"[^>]*/?>', ssml_text)
            for break_time in break_tags:
                if not re.match(r'^\d+(\.\d+)?(ms|s)$', break_time):
                    errors.append(f"Invalid break time format: {break_time}")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'model_supports_ssml': self.model_supports_ssml
            }

        # === SSML Processing Helper Methods ===

        def _detect_ssml_support(self):
            """Detect if the current Coqui model supports SSML"""
            # This is a heuristic - some Coqui models support SSML, others don't
            # VITS models generally have better SSML support
            ssml_supporting_models = [
                'tts_models/en/ljspeech/vits',
                'tts_models/en/vctk/vits',
                'tts_models/multilingual/multi-dataset/xtts_v2'
            ]
            
            if any(model in self.model_name for model in ssml_supporting_models):
                self.model_supports_ssml = True
                print(f"CoquiTTSProvider: Model {self.model_name} detected as SSML-capable")
            else:
                self.model_supports_ssml = False
                print(f"CoquiTTSProvider: Model {self.model_name} detected as non-SSML, will strip tags")

        def _process_ssml_for_coqui(self, ssml_text: str) -> str:
            """Process SSML for SSML-capable Coqui models"""
            text = ssml_text
            
            # Extract from speak tags if present
            if text.strip().startswith('<speak>') and text.strip().endswith('</speak>'):
                text = text.strip()[7:-8].strip()  # Remove <speak> wrapper
            
            # Process supported tags
            text = self._process_coqui_break_tags(text)
            text = self._process_coqui_emphasis_tags(text)
            text = self._process_coqui_prosody_tags(text)
            text = self._process_coqui_structural_tags(text)
            
            # Remove unsupported tags but keep content
            text = self._remove_unsupported_coqui_tags(text)
            
            # Wrap in speak tags for Coqui
            if not text.startswith('<speak>'):
                text = f'<speak>{text}</speak>'
            
            return text

        def _strip_ssml_with_natural_conversion(self, ssml_text: str) -> str:
            """Strip SSML but convert to natural text with pauses for non-SSML models"""
            text = ssml_text
            
            # Convert break tags to natural pauses
            text = re.sub(r'<break\s+time="(\d+)ms"\s*/>', lambda m: self._convert_break_to_pause(int(m.group(1)), 'ms'), text)
            text = re.sub(r'<break\s+time="(\d+(?:\.\d+)?)s"\s*/>', lambda m: self._convert_break_to_pause(float(m.group(1)), 's'), text)
            text = re.sub(r'<break\s+strength="([^"]*)"[^>]*/?>', lambda m: self._convert_strength_to_pause(m.group(1)), text)
            
            # Remove emphasis tags but add text cues for important terms
            text = re.sub(r'<emphasis[^>]*>([^<]*)</emphasis>', r'\1', text)
            
            # Remove prosody tags but keep content
            text = re.sub(r'<prosody[^>]*>([^<]*)</prosody>', r'\1', text)
            
            # Remove all other SSML tags but preserve content
            text = re.sub(r'<[^>]+>', '', text)
            
            # Clean up spacing
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\.{3,}', '...', text)
            
            return text.strip()

        def _convert_break_to_pause(self, duration, unit):
            """Convert SSML break to natural pause text"""
            if unit == 'ms':
                if duration < 300:
                    return ' '
                elif duration < 800:
                    return '... '
                else:
                    return '... ... '
            else:  # seconds
                if duration < 0.5:
                    return '... '
                elif duration < 1.5:
                    return '... ... '
                else:
                    return '... ... ... '

        def _convert_strength_to_pause(self, strength):
            """Convert SSML break strength to natural pause"""
            strength_map = {
                'x-weak': ' ',
                'weak': '... ',
                'medium': '... ... ',
                'strong': '... ... ... ',
                'x-strong': '... ... ... ... '
            }
            return strength_map.get(strength, '... ')

        def _process_coqui_break_tags(self, text: str) -> str:
            """Process break tags for Coqui SSML models"""
            # Coqui supports break tags, validate format
            def fix_break(match):
                time_value = match.group(1)
                if re.match(r'^\d+ms$', time_value) or re.match(r'^\d+(\.\d+)?s$', time_value):
                    return f'<break time="{time_value}"/>'
                else:
                    # Convert invalid format
                    try:
                        if time_value.isdigit():
                            return f'<break time="{time_value}ms"/>'
                    except:
                        pass
                    return '... '  # Fallback to text pause
            
            text = re.sub(r'<break\s+time="([^"]*)"[^>]*/?>', fix_break, text)
            return text

        def _process_coqui_emphasis_tags(self, text: str) -> str:
            """Process emphasis tags for Coqui"""
            # Coqui has limited emphasis support, simplify levels
            def fix_emphasis(match):
                level = match.group(1) if match.group(1) else 'moderate'
                content = match.group(2)
                
                # Coqui supports emphasis but with limited levels
                if level in ['strong', 'moderate']:
                    return f'<emphasis level="{level}">{content}</emphasis>'
                else:
                    # Map to supported levels
                    if level in ['x-strong']:
                        return f'<emphasis level="strong">{content}</emphasis>'
                    else:
                        return f'<emphasis level="moderate">{content}</emphasis>'
            
            text = re.sub(r'<emphasis(?:\s+level="([^"]*)")?>([^<]*)</emphasis>', fix_emphasis, text)
            return text

        def _process_coqui_prosody_tags(self, text: str) -> str:
            """Process prosody tags for Coqui (limited support)"""
            def process_prosody(match):
                attributes = match.group(1)
                content = match.group(2)
                
                # Coqui has very limited prosody support
                # For most models, it's better to remove prosody and keep content
                rate_match = re.search(r'rate="([^"]*)"', attributes)
                if rate_match and rate_match.group(1) in ['slow', 'fast']:
                    # Keep very basic rate changes
                    return f'<prosody rate="{rate_match.group(1)}">{content}</prosody>'
                else:
                    # Remove prosody but keep content
                    return content
            
            text = re.sub(r'<prosody([^>]*)>([^<]*)</prosody>', process_prosody, text)
            return text

        def _process_coqui_structural_tags(self, text: str) -> str:
            """Process paragraph and sentence tags"""
            # Coqui supports basic structural tags
            return text  # Keep <p> and <s> tags as they help with pacing

        def _remove_unsupported_coqui_tags(self, text: str) -> str:
            """Remove tags not supported by Coqui"""
            unsupported_tags = ['voice', 'audio', 'mark', 'say-as', 'sub', 'phoneme']
            
            for tag in unsupported_tags:
                # Remove tags but preserve content
                text = re.sub(f'<{tag}[^>]*>', '', text)
                text = re.sub(f'</{tag}>', '', text)
            
            return text

        def _find_unsupported_tags(self, text: str) -> List[str]:
            """Find SSML tags not supported by current Coqui model"""
            all_tags = re.findall(r'<([^/\s>]+)', text)
            unsupported = []
            
            for tag in set(all_tags):
                if tag not in self.supported_ssml_tags:
                    unsupported.append(tag)
            
            return unsupported

        # === Speaker Management ===

        def _setup_speaker_selection(self):
            """Setup speaker selection for multi-speaker models"""
            available_speakers_raw = self.tts_model.speakers
            available_speakers_cleaned = [spk.strip() for spk in available_speakers_raw if isinstance(spk, str)]
            
            print("Available Coqui speakers (raw):", available_speakers_raw)
            print("Available Coqui speakers (cleaned):", available_speakers_cleaned)

            if not available_speakers_cleaned:
                print("CoquiTTSProvider: ERROR - No valid speaker IDs found after cleaning.")
                self.is_multi_speaker = False 
            elif self.speaker_to_use is None: 
                self.speaker_to_use = available_speakers_cleaned[0] 
                print(f"CoquiTTSProvider: Defaulting to speaker: {self.speaker_to_use}")
            elif self.speaker_to_use.strip() not in available_speakers_cleaned: 
                requested_speaker_cleaned = self.speaker_to_use.strip()
                print(f"CoquiTTSProvider: WARNING - Specified speaker '{requested_speaker_cleaned}' not found. Defaulting to first available.")
                self.speaker_to_use = available_speakers_cleaned[0] 
                print(f"CoquiTTSProvider: Now using speaker (fallback): {self.speaker_to_use}")
            else: 
                self.speaker_to_use = self.speaker_to_use.strip() 
                print(f"CoquiTTSProvider: Using specified speaker: {self.speaker_to_use}")

        # === Model Quality Mapping ===

        def _quality_to_model(self, quality: str) -> str:
            """Map quality setting to Coqui model"""
            mapping = {
                "low": "tts_models/en/ljspeech/tacotron2-DDC",
                "medium": "tts_models/en/ljspeech/vits", 
                "high": "tts_models/en/vctk/vits"
            }
            return mapping.get(quality, mapping["medium"])

else:
    # Fallback when Coqui TTS is not available
    class CoquiTTSProvider(ITTSEngine, ISSMLProcessor):
        def __init__(self, config: CoquiConfig):
            print("CoquiTTSProvider: Coqui TTS library not available. This provider will not function.")
        
        def generate_audio_data(self, text_to_speak: str) -> bytes:
            print("CoquiTTSProvider: Coqui TTS library not available. Cannot generate audio.")
            return b""
        
        def get_output_format(self) -> str:
            return "wav"
        
        def get_ssml_capability(self) -> SSMLCapability:
            return SSMLCapability.NONE
        
        def get_supported_tags(self) -> List[str]:
            return []
        
        def process_ssml(self, ssml_text: str) -> str:
            return ssml_text