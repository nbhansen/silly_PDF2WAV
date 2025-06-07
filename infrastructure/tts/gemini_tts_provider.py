# infrastructure/tts/gemini_tts_provider.py
import os
import wave
from google import genai
from google.genai import types
from domain.models import ITTSEngine, GeminiConfig

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
            self.output_format = "wav"
            self.client = None
            
            try:
                if not self.api_key:
                    print("GeminiTTSProvider: WARNING - No API key provided")
                    return
                    
                self.client = genai.Client(api_key=self.api_key)
                print(f"GeminiTTSProvider: Initialized with voice '{self.voice_name}'")
            except Exception as e:
                print(f"GeminiTTSProvider: Error initializing Gemini client: {e}")
                self.client = None

        def generate_audio_data(self, text_to_speak: str) -> bytes:
            if not self.client:
                print("GeminiTTSProvider: Client not available. Skipping audio generation.")
                return b""
                
            print(f"GeminiTTSProvider: Attempting Gemini TTS generation.")
            
            if not text_to_speak or text_to_speak.strip() == "" or \
               text_to_speak.startswith("LLM cleaning skipped") or text_to_speak.startswith("Error:") or \
               text_to_speak.startswith("Could not convert") or text_to_speak.startswith("No text could be extracted"):
                print("GeminiTTSProvider: Skipping audio generation due to empty or error text.")
                return b""
                
            try:
                # Prepare prompt with optional style guidance
                prompt = f"{self.style_prompt}: {text_to_speak}" if self.style_prompt else text_to_speak
                
                print(f"GeminiTTSProvider: Generating audio with voice '{self.voice_name}'")
                
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
                    
                audio_data = part.inline_data.data
                print(f"GeminiTTSProvider: Successfully extracted audio data ({len(audio_data)} bytes)")
                
                return audio_data
                
            except Exception as e:
                print(f"GeminiTTSProvider: Error generating audio data with Gemini TTS: {e}")
                return b""

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