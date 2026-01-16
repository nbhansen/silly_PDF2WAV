
import asyncio
import os
import logging
import io
import wave
import yaml
from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_audio_generation():
    # Load key
    with open("config.yaml") as f:
        c = yaml.safe_load(f)
        key = c.get("secrets", {}).get("google_ai_api_key")
    
    if not key:
        print("No API Key found")
        return

    provider = GeminiTTSProvider(
        model_name="gemini-2.5-flash-preview-tts",
        api_key=key,
        voice_name="Kore"
    )

    text = "This is a test of the audio generation speed. If I sound like a chipmunk, the sample rate is wrong."
    
    print(f"Generating audio for: '{text}'")
    result = await provider.generate_audio_data_async(text)
    
    if result.is_success:
        audio_data = result.value
        filename = "debug_output.wav"
        
        with open(filename, "wb") as f:
            f.write(audio_data)
            
        print(f"Saved {len(audio_data)} bytes to {filename}")
        
        # Analyze with wave module
        try:
            with wave.open(io.BytesIO(audio_data), "rb") as wav_file:
                print(f"\nWAV Header Analysis:")
                print(f"  Channels: {wav_file.getnchannels()}")
                print(f"  Sample Width: {wav_file.getsampwidth()} bytes ({wav_file.getsampwidth()*8} bit)")
                print(f"  Frame Rate: {wav_file.getframerate()} Hz")
                print(f"  Frames: {wav_file.getnframes()}")
                duration = wav_file.getnframes() / wav_file.getframerate()
                print(f"  Duration: {duration:.2f} seconds")
        except Exception as e:
            print(f"Failed to parse WAV header: {e}")

    else:
        print(f"Generation failed: {result.error}")

if __name__ == "__main__":
    asyncio.run(test_audio_generation())
