
import asyncio
import os
from google import genai

async def list_models():
    api_key = os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        import yaml
        with open("config.yaml") as f:
            c = yaml.safe_load(f)
            key = c.get("secrets", {}).get("google_ai_api_key")
            if key:
                os.environ["GOOGLE_AI_API_KEY"] = key
                api_key = key
            else:
                print("No API Key found")
                return

    client = genai.Client(api_key=api_key)
    
    print("Listing available models...")
    try:
        # Pager object, iterate to get models
        pager = client.models.list() 
        for model in pager:
            # Check for audio capability or just print name
            print(f"Name: {model.name}, Display Name: {model.display_name}")
            if hasattr(model, 'supported_generation_methods'):
                 print(f"  Methods: {model.supported_generation_methods}")
            if hasattr(model, 'output_modalities'): # Assuming this might exist
                 print(f"  Output Modalities: {model.output_modalities}")

    except Exception as e:
        print(f"Failed to list models: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
