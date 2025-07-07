# domain/factories/audio_factory.py - Audio Service Factory
"""Focused factory for audio-related services.
Separated from the monolithic service_factory.py for better maintainability.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.config.system_config import SystemConfig
    from domain.audio.audio_engine import IAudioEngine
    from domain.audio.timing_engine import ITimingEngine
    from domain.interfaces import ITTSEngine
    from domain.text.text_pipeline import ITextPipeline
    from infrastructure.file.file_manager import FileManager


def create_audio_engine(
    config: "SystemConfig", tts_engine: "ITTSEngine", file_manager: "FileManager", timing_engine: "ITimingEngine"
) -> "IAudioEngine":
    """Create audio engine with chunking service."""
    from domain.audio.audio_engine import AudioEngine
    from domain.text.chunking_strategy import ChunkingMode, create_chunking_service

    # Create chunking service based on configuration
    chunking_mode = ChunkingMode.SENTENCE_BASED  # Could be configurable
    chunking_service = create_chunking_service(chunking_mode)

    print("🔍 AudioFactory: Creating AudioEngine with chunk sizes:")
    print(f"  - audio_target_chunk_size: {config.audio_target_chunk_size}")
    print(f"  - audio_max_chunk_size: {config.audio_max_chunk_size}")

    return AudioEngine(
        tts_engine=tts_engine,
        file_manager=file_manager,
        timing_engine=timing_engine,
        max_concurrent=config.audio_concurrent_chunks,
        audio_target_chunk_size=config.audio_target_chunk_size,
        audio_max_chunk_size=config.audio_max_chunk_size,
        chunking_service=chunking_service,
    )


def create_timing_engine(
    config: "SystemConfig", tts_engine: "ITTSEngine", file_manager: "FileManager", text_pipeline: "ITextPipeline"
) -> "ITimingEngine":
    """Create timing engine with appropriate mode."""
    from domain.audio.timing_engine import TimingEngine, TimingMode

    # IMPORTANT: This uses TTS engine timing capabilities, NOT LLM models
    # gemini_use_measurement_mode refers to TTS timing measurement, not text processing
    mode = TimingMode.MEASUREMENT if config.gemini_use_measurement_mode else TimingMode.ESTIMATION

    return TimingEngine(
        tts_engine=tts_engine,  # This is Gemini TTS, not Gemini LLM
        file_manager=file_manager,
        text_pipeline=text_pipeline,
        mode=mode,
        measurement_interval=config.gemini_measurement_mode_interval,
    )
