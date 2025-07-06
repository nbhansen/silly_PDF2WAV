# tests/unit/test_new_architecture.py - Tests for Consolidated Architecture
"""Tests for the new consolidated domain aggregates.
Focuses on testing the high-cohesion, low-coupling design.
"""

from unittest.mock import MagicMock

from application.config.system_config import SystemConfig, TTSEngine
from domain.audio.audio_engine import AudioEngine, IAudioEngine
from domain.audio.timing_engine import ITimingEngine, TimingEngine, TimingMode
from domain.container.service_container import ServiceContainer, create_service_container_builder
from domain.errors import Result
from domain.models import TextSegment, TimedAudioResult
from domain.text.text_pipeline import ITextPipeline, TextPipeline


def create_test_config(tts_engine: str = "piper") -> SystemConfig:
    """Create a minimal SystemConfig for testing."""
    return SystemConfig(
        tts_engine=TTSEngine(tts_engine), llm_model_name="test-llm-model", gemini_model_name="test-gemini-model"
    )


class TestAudioEngine:
    """Test the consolidated AudioEngine."""

    def test_audio_engine_creation(self):
        """AudioEngine should be creatable with minimal dependencies."""
        mock_tts = MagicMock()
        mock_file_manager = MagicMock()
        mock_timing_engine = MagicMock()

        engine = AudioEngine(tts_engine=mock_tts, file_manager=mock_file_manager, timing_engine=mock_timing_engine)

        assert isinstance(engine, IAudioEngine)
        assert engine.tts_engine == mock_tts
        assert engine.file_manager == mock_file_manager
        assert engine.timing_engine == mock_timing_engine

    def test_audio_engine_delegates_to_timing_engine(self):
        """AudioEngine should delegate timing generation to TimingEngine."""
        mock_tts = MagicMock()
        mock_file_manager = MagicMock()
        mock_timing_engine = MagicMock()

        # Setup timing engine to return a result
        expected_result = TimedAudioResult(audio_files=["test.mp3"], combined_mp3="test.mp3", timing_data=None)
        mock_timing_engine.generate_with_timing.return_value = expected_result

        engine = AudioEngine(tts_engine=mock_tts, file_manager=mock_file_manager, timing_engine=mock_timing_engine)

        result = engine.generate_with_timing(["test text"], "output")

        # Verify delegation
        mock_timing_engine.generate_with_timing.assert_called_once_with(["test text"], "output")
        assert result == expected_result

    def test_audio_engine_process_audio_file_success(self):
        """AudioEngine should process audio files and return duration."""
        import os
        import tempfile

        mock_tts = MagicMock()
        mock_file_manager = MagicMock()
        mock_timing_engine = MagicMock()

        engine = AudioEngine(tts_engine=mock_tts, file_manager=mock_file_manager, timing_engine=mock_timing_engine)

        # Create a temporary file to test with
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"fake audio data" * 1000)  # Make it a reasonable size
            temp_path = f.name

        try:
            result = engine.process_audio_file(temp_path)
            assert result.is_success
            assert isinstance(result.value, float)
            assert result.value > 0
        finally:
            os.unlink(temp_path)


class TestTimingEngine:
    """Test the consolidated TimingEngine."""

    def test_timing_engine_creation(self):
        """TimingEngine should be creatable with minimal dependencies."""
        mock_tts = MagicMock()
        mock_file_manager = MagicMock()

        engine = TimingEngine(tts_engine=mock_tts, file_manager=mock_file_manager, mode=TimingMode.ESTIMATION)

        assert isinstance(engine, ITimingEngine)
        assert engine.tts_engine == mock_tts
        assert engine.file_manager == mock_file_manager
        assert engine.mode == TimingMode.ESTIMATION

    def test_timing_engine_mode_selection(self):
        """TimingEngine should use appropriate mode based on TTS engine capabilities."""
        # Mock TTS with timestamp support
        mock_timestamped_tts = MagicMock()
        mock_timestamped_tts.generate_audio_with_timestamps = MagicMock()
        mock_file_manager = MagicMock()

        engine = TimingEngine(
            tts_engine=mock_timestamped_tts, file_manager=mock_file_manager, mode=TimingMode.ESTIMATION
        )

        assert engine.mode == TimingMode.ESTIMATION

        # Mock TTS without timestamp support
        mock_basic_tts = MagicMock()
        # Remove the method to simulate lack of support
        if hasattr(mock_basic_tts, "generate_audio_with_timestamps"):
            delattr(mock_basic_tts, "generate_audio_with_timestamps")

        engine2 = TimingEngine(tts_engine=mock_basic_tts, file_manager=mock_file_manager, mode=TimingMode.ESTIMATION)

        # Should fall back to measurement mode
        assert engine2.mode == TimingMode.MEASUREMENT

    def test_timing_engine_estimation_mode(self):
        """TimingEngine should use estimation mode when TTS supports timestamps."""
        mock_tts = MagicMock()
        mock_file_manager = MagicMock()

        # Mock successful timestamp generation
        mock_segments = [
            TextSegment(
                text="Test", start_time=0.0, duration=1.0, segment_type="sentence", chunk_index=0, sentence_index=0
            )
        ]
        mock_tts.generate_audio_with_timestamps.return_value = Result.success((b"fake_audio", mock_segments))
        mock_file_manager.save_output_file.return_value = "test.mp3"

        engine = TimingEngine(tts_engine=mock_tts, file_manager=mock_file_manager, mode=TimingMode.ESTIMATION)

        result = engine.generate_with_timing(["test text"], "output")

        assert isinstance(result, TimedAudioResult)
        mock_tts.generate_audio_with_timestamps.assert_called_once()


class TestTextPipeline:
    """Test the consolidated TextPipeline."""

    def test_text_pipeline_creation(self):
        """TextPipeline should be creatable with minimal configuration."""
        pipeline = TextPipeline(enable_cleaning=True, enable_ssml=True)

        assert isinstance(pipeline, ITextPipeline)
        assert pipeline.enable_cleaning is True
        assert pipeline.enable_ssml is True

    def test_text_pipeline_basic_cleaning(self):
        """TextPipeline should perform basic text cleanup."""
        pipeline = TextPipeline(enable_cleaning=False)  # Force basic cleanup

        dirty_text = "This   has    extra   spaces\nand\tsome\tother\fissues."
        cleaned = pipeline.clean_text(dirty_text)

        assert "  " not in cleaned  # No double spaces
        assert "\n" not in cleaned
        assert "\t" not in cleaned
        assert "\f" not in cleaned

    def test_text_pipeline_sentence_splitting(self):
        """TextPipeline should split text into sentences correctly."""
        pipeline = TextPipeline()

        text = "This is sentence one. This is sentence two! Is this sentence three? This is a longer sentence."
        sentences = pipeline.split_into_sentences(text)

        assert len(sentences) == 4
        assert sentences[0] == "This is sentence one."
        assert sentences[1] == "This is sentence two!"
        assert sentences[2] == "Is this sentence three?"
        assert sentences[3] == "This is a longer sentence."

    def test_text_pipeline_ssml_stripping(self):
        """TextPipeline should remove SSML tags correctly."""
        pipeline = TextPipeline()

        ssml_text = 'This is <emphasis level="moderate">emphasized</emphasis> text with <break time="1s"/> pauses.'
        clean_text = pipeline.strip_ssml(ssml_text)

        assert "<emphasis" not in clean_text
        assert "</emphasis>" not in clean_text
        assert "<break" not in clean_text
        assert "emphasized" in clean_text
        assert "pauses" in clean_text

    def test_text_pipeline_ssml_enhancement(self):
        """TextPipeline should add SSML enhancements when enabled."""
        pipeline = TextPipeline(enable_ssml=True)

        text = "Abstract This is important research. The algorithm performs well."
        enhanced = pipeline.enhance_with_ssml(text)

        # Should contain SSML enhancements
        assert "<break" in enhanced or "<emphasis" in enhanced
        assert len(enhanced) >= len(text)  # Should be longer with SSML


class TestServiceContainer:
    """Test the simplified ServiceContainer."""

    def test_service_container_creation(self):
        """ServiceContainer should be creatable with SystemConfig."""
        config = create_test_config("piper")
        container = ServiceContainer(config)

        assert container.config == config
        assert len(container._factories) > 0  # Should have registered services

    def test_service_container_registration_and_retrieval(self):
        """ServiceContainer should register and retrieve services correctly."""
        config = create_test_config("piper")

        # Register a test service using builder pattern
        test_service = "test_instance"
        container = create_service_container_builder(config).register(str, lambda: test_service).build()

        # Retrieve the service
        retrieved = container.get(str)
        assert retrieved == test_service

    def test_service_container_singleton_behavior(self):
        """ServiceContainer should return same instance for repeated calls."""
        config = create_test_config("piper")

        # Register a service that creates new instances using builder pattern
        call_count = 0

        def factory() -> str:
            nonlocal call_count
            call_count += 1
            return f"instance_{call_count}"

        container = create_service_container_builder(config).register(str, factory).build()

        # Get the service twice
        first = container.get(str)
        second = container.get(str)

        assert first == second  # Should be same instance
        assert call_count == 1  # Factory should only be called once

    def test_service_container_text_pipeline_registration(self):
        """ServiceContainer should register TextPipeline correctly."""
        config = create_test_config("piper")
        container = ServiceContainer(config)

        # Should be able to get text pipeline
        text_pipeline = container.get(ITextPipeline)
        assert isinstance(text_pipeline, TextPipeline)
        assert isinstance(text_pipeline, ITextPipeline)


class TestArchitectureIntegration:
    """Test integration between the new architectural components."""

    def test_audio_and_timing_engine_integration(self):
        """AudioEngine and TimingEngine should work together."""
        mock_tts = MagicMock()
        mock_file_manager = MagicMock()

        # Create timing engine
        timing_engine = TimingEngine(tts_engine=mock_tts, file_manager=mock_file_manager, mode=TimingMode.ESTIMATION)

        # Create audio engine with timing engine
        audio_engine = AudioEngine(tts_engine=mock_tts, file_manager=mock_file_manager, timing_engine=timing_engine)

        # Mock successful operation
        mock_segments = [
            TextSegment(
                text="Test", start_time=0.0, duration=1.0, segment_type="sentence", chunk_index=0, sentence_index=0
            )
        ]
        mock_tts.generate_audio_with_timestamps.return_value = Result.success((b"audio", mock_segments))
        mock_file_manager.save_output_file.return_value = "test.mp3"

        result = audio_engine.generate_with_timing(["test"], "output")

        assert isinstance(result, TimedAudioResult)
        # The audio engine now processes in chunks, so we expect chunk-based naming
        assert len(result.audio_files) > 0
        assert result.audio_files[0].startswith("output_chunk_")

    def test_text_pipeline_integration(self):
        """TextPipeline should integrate with other components."""
        # Mock LLM provider
        mock_llm = MagicMock()
        mock_llm.generate_text.return_value = Result.success("Cleaned text content.")

        pipeline = TextPipeline(llm_provider=mock_llm, enable_cleaning=True, enable_ssml=True)

        raw_text = "This is raw text that needs cleaning and enhancement."

        # Test the full pipeline
        cleaned = pipeline.clean_text(raw_text)
        enhanced = pipeline.enhance_with_ssml(cleaned)
        sentences = pipeline.split_into_sentences(enhanced)

        assert isinstance(cleaned, str)
        assert isinstance(enhanced, str)
        assert isinstance(sentences, list)
        assert len(sentences) > 0
