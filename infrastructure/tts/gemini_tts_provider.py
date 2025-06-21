# infrastructure/tts/gemini_tts_provider.py
"""
Enhanced Gemini TTS provider with audiobook-quality features
"""
from typing import List, Tuple, Optional, Dict
import re
import json
import os
import wave
import struct
from google import genai
from google.genai import types

from domain.interfaces import ITTSEngine, ITimestampedTTSEngine
from domain.models import TextSegment
from domain.errors import Result, tts_engine_error


class GeminiTTSProvider(ITimestampedTTSEngine):
    """
    Enhanced Gemini 2.5 TTS with audiobook features:
    - Multiple voice personas for different content types
    - Advanced timing estimation
    - Natural language style control
    """

    # Default voice personas (used if config file not found)
    DEFAULT_VOICE_PERSONAS = {
        "narrator": {
            "voice": "Charon",
            "style": "informative and clear",
            "rate": "medium"
        },
        "emphasis": {
            "voice": "Kore",
            "style": "engaged and emphatic",
            "rate": "slightly slower"
        }
    }

    def __init__(self, model_name: str = "gemini-2.0-flash-exp", api_key: Optional[str] = None, voice_personas_config: str = "config/voice_personas.json"):
        if not api_key:
            raise ValueError("API key required for Gemini TTS")

        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.voice_personas = self._load_voice_personas(voice_personas_config)
        self.current_voice = "Charon"  # Default narrator

        # Advanced timing estimation parameters
        self.base_wpm = 155  # Audiobook standard
        self.punctuation_pauses = {
            '.': 0.4, '!': 0.4, '?': 0.4,
            ',': 0.2, ';': 0.3, ':': 0.3,
            '—': 0.3, '...': 0.6
        }

    def _load_voice_personas(self, config_path: str) -> Dict:
        """Load voice personas from configuration file"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"Warning: Voice personas config not found at {config_path}, using defaults")
                return self.DEFAULT_VOICE_PERSONAS
        except Exception as e:
            print(f"Warning: Failed to load voice personas from {config_path}: {e}")
            return self.DEFAULT_VOICE_PERSONAS

    def generate_audio_data(self, text_to_speak: str) -> Result[bytes]:
        """Generate standard audio"""
        try:
            audio_data = self._generate_with_persona(text_to_speak, "narrator")
            if not audio_data:
                return Result.failure(tts_engine_error("No audio data generated"))
            return Result.success(audio_data)
        except Exception as e:
            return Result.failure(tts_engine_error(f"Audio generation failed: {str(e)}"))

    def generate_audio_with_timestamps(self, text_to_speak: str) -> Result[Tuple[bytes, List[TextSegment]]]:
        """
        Generate audio with intelligent content-aware processing
        """
        try:
            # Analyze content and split into segments with appropriate personas
            segments = self._analyze_and_segment_content(text_to_speak)

            # Generate audio for each segment with appropriate voice
            audio_chunks = []
            timing_segments = []
            current_time = 0.0

            for seg_data in segments:
                audio_data = self._generate_with_persona(
                    seg_data['text'],
                    seg_data['persona']
                )

                if not audio_data:
                    return Result.failure(tts_engine_error(f"Failed to generate audio for segment: {seg_data['text'][:50]}..."))

                duration = self._calculate_precise_duration(
                    seg_data['text'],
                    seg_data['persona']
                )

                audio_chunks.append(audio_data)

                timing_segments.append(TextSegment(
                    text=self._clean_for_display(seg_data['text']),
                    start_time=current_time,
                    duration=duration,
                    segment_type=seg_data['type'],
                    chunk_index=0,
                    sentence_index=len(timing_segments)
                ))

                current_time += duration

            # Combine audio chunks
            combined_audio = self._combine_audio_chunks(audio_chunks)

            if not combined_audio:
                return Result.failure(tts_engine_error("Failed to combine audio chunks"))

            return Result.success((combined_audio, timing_segments))

        except Exception as e:
            return Result.failure(tts_engine_error(f"Timestamped audio generation failed: {str(e)}"))

    def _generate_with_persona(self, text: str, persona: str) -> bytes:
        """Generate audio with specific voice persona"""
        voice_config = self.voice_personas.get(persona, self.voice_personas.get("narrator", self.DEFAULT_VOICE_PERSONAS["narrator"]))

        # Enhance text with natural language style
        styled_text = f"Say {voice_config['style']}: {text}"

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=styled_text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_config['voice']
                            )
                        )
                    )
                )
            )

            if response.candidates and response.candidates[0].content.parts:
                raw_audio_data = response.candidates[0].content.parts[0].inline_data.data
                # Convert raw audio to proper WAV format
                return self._convert_to_wav(raw_audio_data)

        except Exception as e:
            print(f"Error generating audio: {e}")

        return b""

    def _analyze_and_segment_content(self, text: str) -> List[Dict]:
        """
        Intelligently segment content and assign voice personas
        """
        segments = []

        # Split into sentences first
        sentences = self._split_into_sentences(text)

        for sentence in sentences:
            # Determine content type and appropriate persona
            if self._is_technical_content(sentence):
                persona = "technical"
                seg_type = "technical"
            elif self._is_emphasis_needed(sentence):
                persona = "emphasis"
                seg_type = "emphasis"
            elif self._is_dialogue(sentence):
                persona = "dialogue"
                seg_type = "dialogue"
            else:
                persona = "narrator"
                seg_type = "narrative"

            segments.append({
                'text': sentence,
                'persona': persona,
                'type': seg_type
            })

        return segments

    def _calculate_precise_duration(self, text: str, persona: str) -> float:
        """
        Calculate duration with persona-specific adjustments
        """
        # Clean text for word counting
        clean_text = re.sub(r'<[^>]+>', '', text)
        words = clean_text.split()
        word_count = len(words)

        # Get base rate for persona
        voice_config = self.voice_personas.get(persona, self.voice_personas.get("narrator", self.DEFAULT_VOICE_PERSONAS["narrator"]))
        rate_adjustment = {
            "medium": 1.0,
            "slightly slower": 1.1,
            "slower": 1.2,
            "natural": 1.0
        }.get(voice_config['rate'], 1.0)

        # Calculate base duration
        base_duration = (word_count / self.base_wpm) * 60 * rate_adjustment

        # Add punctuation pauses
        pause_time = 0.0
        for punct, pause in self.punctuation_pauses.items():
            pause_time += text.count(punct) * pause

        # Add complexity adjustments
        complexity_bonus = 0.0

        # Technical terms (words with numbers, capitals, long words)
        technical_pattern = r'\b(?:[A-Z]{2,}|\w*\d\w*|\w{10,})\b'
        technical_matches = re.findall(technical_pattern, clean_text)
        complexity_bonus += len(technical_matches) * 0.2

        # Parenthetical content
        paren_content = re.findall(r'\([^)]+\)', text)
        complexity_bonus += len(paren_content) * 0.3

        total_duration = base_duration + pause_time + complexity_bonus

        # Ensure minimum duration
        return max(total_duration, 0.5)

    def _is_technical_content(self, text: str) -> bool:
        """Detect technical content requiring slower, clearer delivery"""
        technical_indicators = [
            r'\b(?:equation|formula|algorithm|theorem|proof)\b',
            r'\b[A-Z]{3,}\b',  # Acronyms
            r'\b\d+\.?\d*\s*(?:percent|%|Hz|kHz|MHz|GB|MB)\b',
            r'(?:=|<|>|≤|≥|±)',  # Mathematical operators
            r'\bF\(\d+,\s*\d+\)',  # Statistics
        ]

        for pattern in technical_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _is_emphasis_needed(self, text: str) -> bool:
        """Detect content needing emphasis"""
        emphasis_indicators = [
            r'\b(?:significant|important|crucial|essential|key|primary)\b',
            r'\b(?:however|therefore|consequently|nevertheless)\b',
            r'\b(?:conclusion|summary|finding|result)\b',
        ]

        for pattern in emphasis_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _is_dialogue(self, text: str) -> bool:
        """Detect dialogue or quoted content"""
        return bool(re.search(r'[""].*[""]', text))

    def _split_into_sentences(self, text: str) -> List[str]:
        """Smart sentence splitting preserving context"""
        # Don't split on abbreviations
        text = re.sub(r'\b(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr)\.\s*', r'\g<0>@@@', text)

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        # Restore abbreviations
        sentences = [s.replace('@@@', '') for s in sentences]

        return [s.strip() for s in sentences if s.strip()]

    def _clean_for_display(self, text: str) -> str:
        """Clean text for display"""
        # Remove SSML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove style instructions
        text = re.sub(r'^Say \w+:\s*', '', text)
        return text.strip()

    def _convert_to_wav(self, raw_audio_data: bytes) -> bytes:
        """Convert raw audio data from Gemini to proper WAV format"""
        if not raw_audio_data:
            return b""
        
        try:
            # Gemini TTS typically returns PCM16 at 22050 Hz, mono
            # These are common parameters, but may need adjustment
            sample_rate = 22050
            channels = 1
            sample_width = 2  # 16-bit = 2 bytes per sample
            
            # Create WAV header manually
            # Calculate sizes
            data_size = len(raw_audio_data)
            file_size = data_size + 36  # 44 - 8 bytes for RIFF header
            
            # Create WAV header
            wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
                b'RIFF',           # Chunk ID
                file_size,         # Chunk size
                b'WAVE',           # Format
                b'fmt ',           # Subchunk1 ID
                16,                # Subchunk1 size (PCM)
                1,                 # Audio format (PCM)
                channels,          # Number of channels
                sample_rate,       # Sample rate
                sample_rate * channels * sample_width,  # Byte rate
                channels * sample_width,  # Block align
                sample_width * 8,  # Bits per sample
                b'data',           # Subchunk2 ID
                data_size          # Subchunk2 size
            )
            
            return wav_header + raw_audio_data
            
        except Exception as e:
            print(f"Warning: Failed to convert audio to WAV format: {e}")
            # Return raw data as fallback
            return raw_audio_data

    def _combine_audio_chunks(self, chunks: List[bytes]) -> bytes:
        """Properly combine WAV audio chunks by merging their data sections"""
        if not chunks:
            return b""
        
        if len(chunks) == 1:
            return chunks[0]
        
        try:
            import io
            import wave
            
            # Parse the first WAV file to get format info
            first_wav = io.BytesIO(chunks[0])
            with wave.open(first_wav, 'rb') as first_wave:
                # Get audio parameters from first file
                channels = first_wave.getnchannels()
                sampwidth = first_wave.getsampwidth()
                framerate = first_wave.getframerate()
                
                # Collect all audio data
                combined_data = b""
                total_frames = 0
                
                # Add data from first file
                first_wav.seek(0)
                with wave.open(first_wav, 'rb') as w:
                    combined_data += w.readframes(w.getnframes())
                    total_frames += w.getnframes()
                
                # Add data from remaining files
                for chunk in chunks[1:]:
                    chunk_io = io.BytesIO(chunk)
                    try:
                        with wave.open(chunk_io, 'rb') as w:
                            # Verify format compatibility
                            if (w.getnchannels() == channels and 
                                w.getsampwidth() == sampwidth and
                                w.getframerate() == framerate):
                                combined_data += w.readframes(w.getnframes())
                                total_frames += w.getnframes()
                            else:
                                print(f"Warning: Audio chunk format mismatch, skipping chunk")
                    except Exception as e:
                        print(f"Warning: Failed to read audio chunk: {e}")
                        continue
                
                # Create combined WAV file
                output_buffer = io.BytesIO()
                with wave.open(output_buffer, 'wb') as combined_wave:
                    combined_wave.setnchannels(channels)
                    combined_wave.setsampwidth(sampwidth)
                    combined_wave.setframerate(framerate)
                    combined_wave.writeframes(combined_data)
                
                return output_buffer.getvalue()
                
        except Exception as e:
            print(f"Error combining audio chunks: {e}")
            # Fallback: try simple concatenation for emergency cases
            print("Falling back to simple concatenation")
            return b''.join(chunks)

    def get_output_format(self) -> str:
        return "wav"

    def supports_ssml(self) -> bool:
        return True
