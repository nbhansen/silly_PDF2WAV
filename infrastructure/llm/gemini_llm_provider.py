# infrastructure/llm/gemini_llm_provider.py
"""Gemini LLM provider implementation for text processing and content generation.
Uses the unified Google Gen AI SDK for language model operations.
"""

import asyncio
import concurrent.futures
from typing import Optional

from google import genai
from google.genai import types

from domain.errors import Result, llm_provider_error
from domain.interfaces import ILLMProvider


class GeminiLLMProvider(ILLMProvider):
    """Gemini LLM provider for text processing and content generation."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        min_request_interval: float = 0.5,
        max_concurrent_requests: int = 3,
        requests_per_minute: int = 120,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.client = self._init_client()

        # Rate limiting configuration
        self.min_request_interval = min_request_interval
        self.max_concurrent_requests = max_concurrent_requests
        self.requests_per_minute = requests_per_minute
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)

    def _init_client(self) -> Optional[genai.Client]:
        """Initialize the Gemini client with API key validation."""
        if not self.api_key or self.api_key == "YOUR_GOOGLE_AI_API_KEY":
            return None

        try:
            return genai.Client(api_key=self.api_key)
        except Exception:
            return None

    def process_text(self, text: str) -> Result[str]:
        """Process and enhance text using the language model."""
        return self.generate_content(text)

    def generate_content(self, prompt: str) -> Result[str]:
        """Generate content based on a prompt."""
        if not self.client:
            return Result.failure(llm_provider_error("Client not available"))

        prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
        print(f"🔬 LLM API Call: Model={self.model_name}, prompt='{prompt_preview}' ({len(prompt)} chars)")

        try:
            import time

            start_time = time.time()

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=30000,  # Increased from 8192 to avoid empty response bug
                    temperature=0.3,
                ),
            )

            api_time = time.time() - start_time
            print(f"✅ LLM API Success: {api_time:.2f}s for '{prompt_preview}'")

            # Inspect response structure for debugging
            if response:
                try:
                    # Check if response has candidates
                    if hasattr(response, "candidates") and response.candidates:
                        candidate = response.candidates[0]
                        finish_reason = getattr(candidate, "finish_reason", "UNKNOWN")
                        print(f"📊 Response finish_reason: {finish_reason}")

                        # Try to get text content
                        if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                            parts = candidate.content.parts
                            if parts and hasattr(parts[0], "text"):
                                text_content = parts[0].text
                                if text_content:
                                    print(f"📝 LLM Response: {len(text_content)} chars returned")
                                    return Result.success(text_content)
                except Exception as e:
                    print(f"⚠️ Error inspecting response structure: {e}")

            # Try the simple .text accessor as fallback
            if response and hasattr(response, "text") and response.text:
                print(f"📝 LLM Response: {len(response.text)} chars returned (via .text accessor)")
                return Result.success(response.text)
            else:
                print(f"❌ LLM API: No text in response for '{prompt_preview}'")
                if response:
                    print(f"🔍 Response object type: {type(response)}")
                    print(f"🔍 Response attributes: {dir(response)[:10]}...")  # First 10 attributes
                return Result.failure(llm_provider_error("Empty response from LLM"))

        except Exception as e:
            api_time = time.time() - start_time
            error_str = str(e)
            print(f"💥 LLM API Error ({api_time:.2f}s): {error_str[:200]} for '{prompt_preview}'")
            return Result.failure(llm_provider_error(f"Content generation failed: {e!s}"))

    async def generate_content_async(self, prompt: str) -> Result[str]:
        """Generate content asynchronously with rate limiting."""
        if not self.client:
            return Result.failure(llm_provider_error("Client not available"))

        try:
            async with self.request_semaphore:
                # Execute in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(executor, self.generate_content, prompt)

                # Rate limiting delay
                await asyncio.sleep(self.min_request_interval)
                return result

        except Exception as e:
            return Result.failure(llm_provider_error(f"Async content generation failed: {e!s}"))
