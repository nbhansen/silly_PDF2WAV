# domain/factories/text_factory.py - Text Processing Factory
"""Focused factory for text processing services."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.config.system_config import SystemConfig
    from domain.text.text_pipeline import ITextPipeline


def create_text_pipeline(config: "SystemConfig") -> "ITextPipeline":
    """Create text pipeline with optional LLM provider and natural formatting."""
    from domain.text.text_pipeline import TextPipeline
    from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider

    llm_provider = None
    if config.gemini_api_key:
        # IMPORTANT: This creates Gemini LLM for text cleaning/enhancement, NOT TTS
        # Uses language models like gemini-1.5-flash, NOT text-to-speech models
        llm_provider = GeminiLLMProvider(
            api_key=config.gemini_api_key,
            model_name=config.llm_model_name,  # Language model, not TTS model
            min_request_interval=config.llm_request_delay_seconds,
            max_concurrent_requests=config.llm_concurrent_requests,
            requests_per_minute=30,  # Default rate limit
        )

    return TextPipeline(
        llm_provider=llm_provider,  # This is for text processing, not audio generation
        enable_cleaning=config.enable_text_cleaning,
        enable_natural_formatting=config.enable_natural_formatting,
    )
