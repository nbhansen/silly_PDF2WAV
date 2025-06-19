"""
Modern Text-to-Speech provider using Google Gemini 2.5 TTS API.
Uses the latest API features for high-quality speech generation.
"""

from typing import List, Tuple, Optional
import google.generativeai as genai
from google.genai import types

from domain.interfaces import ITTSEngine
from domain.models import TextSegment
from domain.services.text_cleaning_service import TextCleaningService

class GeminiTTSProvider(ITTSEngine):
    """
    Modern implementation using Gemini 2.5 TTS API with native audio output.
    Supports multiple voices, SSML, and natural language style control.
    """

    # Available voices in Gemini 2.5
    AVAILABLE_VOICES = {
        "Kore": "Balanced, natural voice (default)",
        "Puck": "Upbeat, energetic voice",  
        "Charon": "Deep, authoritative voice",
        "Fenrir": "Warm, friendly voice",
        "Aoede": "Clear, professional voice",
        "Leda": "Youthful, expressive voice"
    }

    def __init__(self, model_name: str, api_key: Optional[str] = None):
        if not api_key:
            raise ValueError("Google AI API key is required for GeminiTTSProvider.")
        
        # Configure API
        genai.configure(api_key=api_key)
        
        # Determine model and voice
        if model_name in self.AVAILABLE_VOICES:
            # If given a voice name, use it with default TTS model
            self.voice_name = model_name
            self.model_name = "gemini-2.5-flash-preview-tts"  # Cost-efficient
        else:
            # Use provided model name with default voice
            self.model_name = model_name
            self.voice_name = "Kore"
        
        # Initialize client
        self.client = genai.Client(api_key=api_key)
        self.text_cleaner = TextCleaningService()
        
        print(f"GeminiTTSProvider: Initialized with model '{self.model_name}' and voice '{self.voice_name}'")
        print(f"Voice description: {self.AVAILABLE_VOICES.get(self.voice_name, 'Custom voice')}")

    def generate_audio_data(self, text_to_speak: str) -> bytes:
        """
        Generate high-quality audio using Gemini 2.5 TTS.
        
        Args:
            text_to_speak: Text to convert to speech (supports SSML and natural language style)
            
        Returns:
            bytes: WAV audio data
        """
        if not text_to_speak or not text_to_speak.strip():
            return b""
        
        print(f"GeminiTTSProvider: Generating audio ({len(text_to_speak)} chars) with voice '{self.voice_name}'")
        
        try:
            # Use Gemini 2.5 TTS API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=text_to_speak,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.voice_name
                            )
                        )
                    )
                )
            )
            
            # Extract audio data
            if (response.candidates and 
                len(response.candidates) > 0 and
                response.candidates[0].content and
                response.candidates[0].content.parts and
                len(response.candidates[0].content.parts) > 0 and
                response.candidates[0].content.parts[0].inline_data):
                
                audio_data = response.candidates[0].content.parts[0].inline_data.data
                print(f"GeminiTTSProvider: Successfully generated {len(audio_data)} bytes of audio")
                return audio_data
            else:
                print("GeminiTTSProvider: No audio data in response")
                # Log response structure for debugging
                print(f"Response structure: candidates={len(response.candidates) if response.candidates else 0}")
                return b""
                
        except Exception as e:
            print(f"GeminiTTSProvider: Error generating audio: {e}")
            import traceback
            traceback.print_exc()
            raise

    def get_output_format(self) -> str:
        """Gemini TTS outputs WAV format"""
        return "wav"

    def prefers_sync_processing(self) -> bool:
        """Gemini is a cloud service, benefits from async processing"""
        return False

    def supports_ssml(self) -> bool:
        """Gemini 2.5 supports SSML and natural language style control"""
        return True

    def generate_audio_with_timestamps(self, text_to_speak: str) -> Tuple[bytes, List[TextSegment]]:
        """
        Generate audio with estimated timing information.
        
        Note: Gemini TTS doesn't yet provide precise word-level timestamps,
        so we estimate timing based on text analysis.
        
        Args:
            text_to_speak: Text to convert to speech
            
        Returns:
            Tuple of (audio_data, text_segments)
        """
        print(f"GeminiTTSProvider: Generating audio with estimated timestamps")
        
        try:
            # Generate audio
            audio_data = self.generate_audio_data(text_to_speak)
            
            if not audio_data:
                return b'', []
            
            # Create estimated timing segments
            text_segments = self._create_estimated_segments(text_to_speak)
            
            print(f"GeminiTTSProvider: Generated audio with {len(text_segments)} estimated segments")
            return audio_data, text_segments

        except Exception as e:
            print(f"GeminiTTSProvider: Error generating timestamped audio: {e}")
            return b'', []

    def _create_estimated_segments(self, text: str) -> List[TextSegment]:
        """
        Create estimated timing segments based on text analysis.
        
        This provides reasonable timing estimates until Gemini provides
        precise timestamp data in future API versions.
        """
        segments = []
        
        # Split into sentences
        sentences = self.text_cleaner.split_into_sentences(text)
        if not sentences:
            return segments
        
        cumulative_time = 0.0
        
        for i, sentence in enumerate(sentences):
            # Estimate duration based on text characteristics
            duration = self._estimate_sentence_duration(sentence)
            
            # Clean text for display (remove SSML tags)
            clean_text = self.text_cleaner.strip_ssml(sentence)
            
            segment = TextSegment(
                text=clean_text,
                start_time=cumulative_time,
                duration=duration,
                segment_type="sentence",
                chunk_index=0,  # Single chunk for Gemini
                sentence_index=i
            )
            
            segments.append(segment)
            cumulative_time += duration
        
        return segments

    def _estimate_sentence_duration(self, sentence: str) -> float:
        """
        Estimate speech duration for a sentence.
        
        Uses word count, punctuation, and text complexity to estimate
        how long the sentence will take to speak.
        """
        import re
        
        # Remove SSML tags for analysis
        clean_text = re.sub(r'<[^>]+>', '', sentence)
        
        # Count words
        words = clean_text.split()
        word_count = len(words)
        
        # Base speech rate: ~2.5 words per second (natural speech)
        base_duration = word_count / 2.5
        
        # Add pauses for punctuation
        pause_duration = 0.0
        pause_duration += sentence.count(',') * 0.2   # Comma pauses
        pause_duration += sentence.count(';') * 0.3   # Semicolon pauses  
        pause_duration += sentence.count('.') * 0.4   # Period pauses
        pause_duration += sentence.count('!') * 0.4   # Exclamation pauses
        pause_duration += sentence.count('?') * 0.4   # Question pauses
        pause_duration += sentence.count(':') * 0.3   # Colon pauses
        
        # Adjust for complex words (longer words take slightly more time)
        complex_word_bonus = sum(0.1 for word in words if len(word) > 8)
        
        # Calculate total duration with minimum
        total_duration = base_duration + pause_duration + complex_word_bonus
        
        # Ensure minimum duration
        return max(total_duration, 0.5)

    @classmethod
    def get_available_voices(cls) -> dict:
        """Get available voices with descriptions"""
        return cls.AVAILABLE_VOICES.copy()
    
    @classmethod
    def get_available_models(cls) -> List[str]:
        """Get available Gemini TTS models"""
        return [
            "gemini-2.5-pro-preview-tts",    # Highest quality
            "gemini-2.5-flash-preview-tts"   # Fast and cost-efficient
        ]
    
    def set_voice(self, voice_name: str) -> bool:
        """
        Change the voice for future audio generation.
        
        Args:
            voice_name: Name of the voice to use
            
        Returns:
            bool: True if voice was set successfully
        """
        if voice_name in self.AVAILABLE_VOICES:
            self.voice_name = voice_name
            print(f"GeminiTTSProvider: Voice changed to '{voice_name}'")
            return True
        else:
            print(f"GeminiTTSProvider: Voice '{voice_name}' not available")
            print(f"Available voices: {list(self.AVAILABLE_VOICES.keys())}")
            return False
    
    def enhance_with_style(self, text: str, style_instruction: str) -> str:
        """
        Enhance text with natural language style instructions.
        
        Gemini TTS supports natural language style control like:
        "Say cheerfully: Hello world!"
        "Say in a whisper: This is a secret"
        "Say dramatically: The results are in!"
        
        Args:
            text: Base text to speak
            style_instruction: Style instruction (e.g., "cheerfully", "dramatically")
            
        Returns:
            str: Enhanced text with style instruction
        """
        return f"Say {style_instruction}: {text}"