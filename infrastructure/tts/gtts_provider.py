# infrastructure/tts/gtts_provider.py
import os
from domain.interfaces import ITTSEngine
from domain.config import GTTSConfig

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
    print("gTTS library found and imported successfully.")
except ImportError:
    print("gTTS library not found. GTTSProvider will not be available.")
    GTTS_AVAILABLE = False

if GTTS_AVAILABLE:
    class GTTSProvider(ITTSEngine):
        def __init__(self, config: GTTSConfig):
            self.lang = config.lang
            self.tld = config.tld
            self.slow = config.slow
            self.output_format = "mp3"
            print(f"GTTSProvider: Initialized for lang='{self.lang}', tld='{self.tld}'.")

        def generate_audio_data(self, text_to_speak: str) -> bytes:
            print(f"GTTSProvider: Attempting gTTS audio generation ({self.lang}, {self.tld})")
            if not text_to_speak or text_to_speak.strip() == "" or \
               text_to_speak.startswith("LLM cleaning skipped") or text_to_speak.startswith("Error:") or \
               text_to_speak.startswith("Could not convert") or text_to_speak.startswith("No text could be extracted"):
                print("GTTSProvider: Skipping audio generation due to empty or error text.")
                return b""
            try:
                tts_object = gTTS(text=text_to_speak, lang=self.lang, tld=self.tld, slow=self.slow)
                # gTTS saves to file, so we need a temp file to get bytes
                temp_audio_filepath = "temp_gtts_audio.mp3"
                tts_object.save(temp_audio_filepath)
                
                with open(temp_audio_filepath, "rb") as f:
                    audio_data = f.read()
                os.remove(temp_audio_filepath) # Clean up temp file
                
                print(f"GTTSProvider: Generated audio data ({len(audio_data)} bytes).")
                return audio_data
            except Exception as e:
                print(f"GTTSProvider: Error generating audio data with gTTS: {e}")
                return b""

        def get_output_format(self) -> str:
            return self.output_format
else:
    class GTTSProvider(ITTSEngine):
        def __init__(self, config: GTTSConfig):
            print("GTTSProvider: gTTS library not available. This provider will not function.")
        def generate_audio_data(self, text_to_speak: str) -> bytes:
            print("GTTSProvider: gTTS library not available. Cannot generate audio.")
            return b""
        def get_output_format(self) -> str:
            return "mp3"