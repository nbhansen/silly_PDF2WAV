# application/config/processing_configs.py
"""Text processing, OCR, and performance configuration classes."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TextProcessingConfig:
    """Text processing configuration."""

    enable_cleaning: bool = True
    enable_natural_formatting: bool = True
    enable_plain_english: bool = False
    llm_chunk_size: int = 50000  # Large chunks for LLM text cleaning
    audio_target_chunk_size: int = 3000
    audio_max_chunk_size: int = 5000


@dataclass(frozen=True)
class LLMConfig:
    """LLM configuration for text cleaning."""

    model_name: Optional[str] = None
    concurrent_requests: int = 3
    request_delay_seconds: float = 0.5
    api_key: Optional[str] = None


@dataclass(frozen=True)
class OCRConfig:
    """OCR configuration."""

    dpi: int = 300
    threshold: int = 180
    language: str = "eng"


@dataclass(frozen=True)
class PerformanceConfig:
    """Performance and resource management configuration."""

    enable_async_audio: bool = True
    audio_concurrent_chunks: int = 4
