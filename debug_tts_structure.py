
import asyncio
import os
import logging
from google import genai
from google.genai import types
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_audio_structure():
    # Load key from config
    with open("config.yaml") as f:
        c = yaml.safe_load(f)
        key = c.get("secrets", {}).get("google_ai_api_key")
        
    if not key:
        print("No API Key found")
        return

    client = genai.Client(api_key=key)
    model_name = "gemini-2.5-flash-preview-tts"
    
    print(f"\nTesting model: {model_name}")
    try:
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore"
                    )
                )
            )
        )
        
        # Simple text, no wrapper
        text = "Hello, this is a test of the audio structure."
        
        print("Sending request...")
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=text,
            config=config
        )
        
        print("\nResponse received!")
        print(f"Response type: {type(response)}")
        
        if hasattr(response, "candidates"):
            print(f"Candidates count: {len(response.candidates)}")
            if response.candidates:
                cand = response.candidates[0]
                print(f"Candidate 0: {cand}")
                if hasattr(cand, "content") and cand.content:
                    print(f"Content: {cand.content}")
                    if hasattr(cand.content, "parts"):
                        for i, part in enumerate(cand.content.parts):
                            print(f"\nPart {i}:")
                            print(f"  Types available: {dir(part)}")
                            if hasattr(part, "inline_data"):
                                print(f"  Inline Data: {part.inline_data}")
                            if hasattr(part, "file_data"):
                                print(f"  File Data: {part.file_data}")
                            if hasattr(part, "text"):
                                print(f"  Text: {part.text}")
                            # Check for other fields potentially holding audio
                            if hasattr(part, "audio_data"): # Hypothetical
                                print(f"  Audio Data: {part.audio_data}")
                            if hasattr(part, "binary_data"): # Hypothetical
                                print(f"  Binary Data: {part.binary_data}")

    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_audio_structure())
