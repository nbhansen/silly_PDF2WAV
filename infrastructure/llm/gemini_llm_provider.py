# infrastructure/llm/gemini_llm_provider.py - Updated imports
import os
import google.generativeai as genai
from google.generativeai import types
from domain.interfaces import ILLMProvider

class GeminiLLMProvider(ILLMProvider):
    """Direct implementation of ILLMProvider for Google Gemini"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = self._init_model()
    
    def _init_model(self):
        """Initialize the Gemini model"""
        if not self.api_key or self.api_key == "YOUR_GOOGLE_AI_API_KEY" or self.api_key == "crawling in my skin":
            print("GeminiLLMProvider: No valid API key provided - LLM functionality will be limited.")
            return None
            
        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            print("GeminiLLMProvider: Gemini initialized successfully.")
            return model
        except Exception as e:
            print(f"GeminiLLMProvider: Failed to initialize Gemini: {e}")
            return None
    def process_text(self, text: str) -> str:
        """Processes and enhances text - required by ILLMProvider interface"""
        return self.generate_content(text)

    def generate_content(self, prompt: str) -> str:
        """Generates content based on a prompt using Gemini"""
        if not self.model:
            print("GeminiLLMProvider: LLM model not available, cannot generate content.")
            return "LLM content generation skipped due to missing API key or initialization error."
        
        try:
            response = self.model.generate_content(prompt)
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            else:
                print("GeminiLLMProvider: LLM response was empty.")
                return "LLM content generation yielded no response."
        except Exception as e:
            print(f"GeminiLLMProvider: Error during content generation: {e}")
            return f"Error during LLM content generation: {str(e)}"