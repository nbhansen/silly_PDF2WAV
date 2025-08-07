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
    if config.gemini and config.gemini.api_key:
        # IMPORTANT: This creates Gemini LLM for text cleaning/enhancement, NOT TTS
        # Uses language models like gemini-1.5-flash, NOT text-to-speech models
        llm_provider = GeminiLLMProvider(
            api_key=config.gemini.api_key,
            model_name=config.llm.model_name or "gemini-1.5-flash",  # Language model, not TTS model with fallback
            min_request_interval=config.llm.request_delay_seconds,
            max_concurrent_requests=config.llm.concurrent_requests,
            requests_per_minute=30,  # Default rate limit
        )

    return TextPipeline(
        llm_provider=llm_provider,  # This is for text processing, not audio generation
        enable_cleaning=config.text_processing.enable_cleaning,
        enable_natural_formatting=config.text_processing.enable_natural_formatting,
    )
