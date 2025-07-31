# infrastructure/tts/gemini_tts_provider.py
"""Gemini TTS Provider - placeholder implementation for testing compatibility."""


from domain.errors import Result, tts_engine_error
from domain.interfaces import ITTSEngine


class GeminiTTSProvider(ITTSEngine):
    """Placeholder Gemini TTS Provider for testing compatibility."""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        voice_name: str = "Kore",
        min_request_interval: float = 2.0,
        max_concurrent_requests: int = 4,
        requests_per_minute: int = 30,
    ):
        """Initialize Gemini TTS Provider."""
        self.model_name = model_name
        self.api_key = api_key
        self.voice_name = voice_name
        self.min_request_interval = min_request_interval
        self.max_concurrent_requests = max_concurrent_requests
        self.requests_per_minute = requests_per_minute
        self.output_format = "mp3"

    def generate_audio_data(self, text: str) -> Result[bytes]:
        """Generate audio data from text (placeholder implementation)."""
        if not text.strip():
            return Result.failure(tts_engine_error("Empty text provided"))

        # Placeholder - return empty audio data for testing
        return Result.success(b"fake_audio_data")

    async def generate_audio_data_async(self, text: str) -> Result[bytes]:
        """Generate audio data asynchronously (placeholder implementation)."""
        return self.generate_audio_data(text)

    def get_output_format(self) -> str:
        """Get the output format for generated audio."""
        return self.output_format

    def prefers_sync_processing(self) -> bool:
        """Whether this engine prefers synchronous processing."""
        return False  # Gemini is API-based, async preferred

    def supports_ssml(self) -> bool:
        """Whether this engine supports SSML."""
        return True  # Gemini typically supports SSML
