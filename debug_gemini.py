
import asyncio
import os
from google import genai
from google.genai import types

async def test_audio_gen():
    api_key = os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        print("No API Key found")
        return

    client = genai.Client(api_key=api_key)
    
    # Try different model names
    models_to_test = [
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
    ]

    for model_name in models_to_test:
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
            
            response = await client.aio.models.generate_content(
                model=model_name,
                contents="Hello, this is a test.",
                config=config
            )
            print("Success!")
            # print(response)
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    # Load env vars from .env if needed, or just rely on system env
    # For now, I'll assume the user has the key in the environment or config.
    # I need to read the key from config.yaml actually since I can't see the user's env vars directly in this script easily without dotenv
    
    # Hack to get key from config.yaml
    import yaml
    with open("config.yaml") as f:
        c = yaml.safe_load(f)
        key = c.get("secrets", {}).get("google_ai_api_key")
        if key:
            os.environ["GOOGLE_AI_API_KEY"] = key

    asyncio.run(test_audio_gen())
