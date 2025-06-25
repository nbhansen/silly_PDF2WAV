# infrastructure/llm/gemini_llm_provider.py - Updated for unified google-genai SDK
from google import genai
from google.genai import types
from domain.interfaces import ILLMProvider
from domain.errors import Result, llm_provider_error


class GeminiLLMProvider(ILLMProvider):
    """Implementation of ILLMProvider using the unified Google Gen AI SDK"""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.client = self._init_client()

    def _init_client(self):
        """Initialize the unified Gemini client"""
        if not self.api_key or self.api_key == "YOUR_GOOGLE_AI_API_KEY":
            print("GeminiLLMProvider: No valid API key provided - LLM functionality will be limited.")
            return None

        try:
            client = genai.Client(api_key=self.api_key)
            print("GeminiLLMProvider: Unified Gemini client initialized successfully.")
            return client
        except Exception as e:
            print(f"GeminiLLMProvider: Failed to initialize unified client: {e}")
            return None

    def process_text(self, text: str) -> Result[str]:
        """Processes and enhances text - required by ILLMProvider interface"""
        return self.generate_content(text)

    def generate_content(self, prompt: str) -> Result[str]:
        """Generates content based on a prompt using the unified Gemini SDK"""
        if not self.client:
            return Result.failure(llm_provider_error("Client not available - missing API key or initialization error"))

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=8192,
                    temperature=0.3,
                )
            )

            if response and response.text:
                return Result.success(response.text)
            else:
                return Result.failure(llm_provider_error("LLM response was empty"))

        except Exception as e:
            return Result.failure(llm_provider_error(f"Content generation failed: {str(e)}"))
