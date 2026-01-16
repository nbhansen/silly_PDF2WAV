# infrastructure/tts/gemini_tts_provider.py
"""Gemini TTS Provider implementation using Google Gen AI SDK."""

import logging
import io
import wave
from typing import Optional

from google import genai
from google.genai import types

from domain.errors import Result, tts_engine_error
from domain.interfaces import ITTSEngine

logger = logging.getLogger(__name__)


class GeminiTTSProvider(ITTSEngine):
    """Gemini TTS Provider using Google Gen AI SDK."""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        voice_name: str = "Kore",
        min_request_interval: float = 2.0,
        max_concurrent_requests: int = 4,
        requests_per_minute: int = 30,
    ):
        """Initialize Gemini TTS Provider.
        
        Args:
            model_name: Gemini model (e.g. gemini-2.0-flash-exp)
            api_key: Google AI API Key
            voice_name: Voice to use (e.g. "Kore", "Puck", "Charon", "Fenrir", "Aoede")
        """
        self.model_name = model_name
        self.api_key = api_key
        self.voice_name = voice_name
        self.min_request_interval = min_request_interval
        self.max_concurrent_requests = max_concurrent_requests
        self.requests_per_minute = requests_per_minute
        self.output_format = "mp3"  # Gemini audio is typically MP3

        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"Gemini TTS initialized with model={model_name}, voice={voice_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            self.client = None

    def generate_audio_data(self, text: str) -> Result[bytes]:
        """Generate audio data from text using Gemini."""
        if not self.client:
            return Result.failure(tts_engine_error("Gemini Client not initialized"))

        if not text.strip():
            return Result.failure(tts_engine_error("Empty text provided"))

        try:
            # Configure for audio generation
            config = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self.voice_name
                        )
                    )
                )
            )

            # Direct text input for TTS models
            prompt = text

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            return self._extract_audio_from_response(response)

        except Exception as e:
            logger.exception("Gemini TTS generation failed")
            return Result.failure(tts_engine_error(f"Gemini TTS failed: {e}"))

    async def generate_audio_data_async(self, text: str) -> Result[bytes]:
        """Generate audio data asynchronously."""
        if not self.client:
            return Result.failure(tts_engine_error("Gemini Client not initialized"))

        try:
            config = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self.voice_name
                        )
                    )
                )
            )

            # Direct text input for TTS models
            prompt = text

            # Use async client
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            return self._extract_audio_from_response(response)

        except Exception as e:
            logger.exception("Gemini Async TTS generation failed")
            return Result.failure(tts_engine_error(f"Gemini Async TTS failed: {e}"))

    def _extract_audio_from_response(self, response: types.GenerateContentResponse) -> Result[bytes]:
        """Extract audio bytes from Gemini response."""
        if not response.candidates:
            return Result.failure(tts_engine_error("No candidates returned from Gemini"))

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return Result.failure(tts_engine_error("Empty content in Gemini response"))

        for part in candidate.content.parts:
            # Check for inline_data with audio mime type
            if part.inline_data and part.inline_data.mime_type and part.inline_data.mime_type.startswith("audio"):
                if part.inline_data.data:
                    audio_data = part.inline_data.data
                    # If PCM, add WAV header
                    if "pcm" in part.inline_data.mime_type:
                        # Extract sample rate if possible, otherwise default to 24000
                        sample_rate = 24000
                        if "rate=" in part.inline_data.mime_type:
                            try:
                                rate_str = part.inline_data.mime_type.split("rate=")[1]
                                sample_rate = int(rate_str.split(";")[0])
                            except (IndexError, ValueError):
                                pass
                        
                        return Result.success(self._add_wav_header(audio_data, sample_rate))
                    
                    return Result.success(audio_data)
        
        return Result.failure(tts_engine_error("No audio data found in Gemini response"))

    def _add_wav_header(self, pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, bit_depth: int = 16) -> bytes:
        """Add WAV header to raw PCM data."""
        with io.BytesIO() as wav_io:
            with wave.open(wav_io, "wb") as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(bit_depth // 8)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_data)
            return wav_io.getvalue()

    def get_output_format(self) -> str:
        """Get the output format for generated audio."""
        return self.output_format

    def prefers_sync_processing(self) -> bool:
        """Whether this engine prefers synchronous processing."""
        return False  # Gemini is API-based, async preferred

    def supports_ssml(self) -> bool:
        """Whether this engine supports SSML."""
        return False  # Gemini Audio model takes text prompt, not SSML (prompt engineering used instead)