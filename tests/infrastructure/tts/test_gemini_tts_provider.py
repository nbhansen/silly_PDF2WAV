"""Infrastructure tests for GeminiTTSProvider.

Tests the Gemini TTS provider implementation and interface compliance.
Currently tests the placeholder implementation, ready to be extended when
real Gemini TTS integration is implemented.
"""

import pytest

from domain.errors import ErrorCode
from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider


@pytest.fixture
def basic_gemini_provider() -> GeminiTTSProvider:
    """Basic GeminiTTSProvider for testing."""
    return GeminiTTSProvider(
        model_name="gemini-1.5-flash",
        api_key="test_api_key",
        voice_name="Kore",
    )


@pytest.fixture
def custom_gemini_provider() -> GeminiTTSProvider:
    """Custom GeminiTTSProvider with specific settings."""
    return GeminiTTSProvider(
        model_name="gemini-1.5-pro",
        api_key="custom_api_key",
        voice_name="Aria",
        min_request_interval=1.5,
        max_concurrent_requests=8,
        requests_per_minute=60,
    )


class TestGeminiTTSProviderInitialization:
    """Test GeminiTTSProvider initialization and configuration."""

    def test_init_with_basic_parameters(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should initialize with basic parameters."""
        provider = basic_gemini_provider

        assert provider.model_name == "gemini-1.5-flash"
        assert provider.api_key == "test_api_key"
        assert provider.voice_name == "Kore"
        assert provider.output_format == "mp3"

        # Default values
        assert provider.min_request_interval == 2.0
        assert provider.max_concurrent_requests == 4
        assert provider.requests_per_minute == 30

    def test_init_with_custom_parameters(self, custom_gemini_provider: GeminiTTSProvider) -> None:
        """Should initialize with custom parameters."""
        provider = custom_gemini_provider

        assert provider.model_name == "gemini-1.5-pro"
        assert provider.api_key == "custom_api_key"
        assert provider.voice_name == "Aria"
        assert provider.min_request_interval == 1.5
        assert provider.max_concurrent_requests == 8
        assert provider.requests_per_minute == 60

    def test_init_stores_rate_limiting_config(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should store rate limiting configuration."""
        provider = basic_gemini_provider

        # Rate limiting settings should be accessible
        assert hasattr(provider, "min_request_interval")
        assert hasattr(provider, "max_concurrent_requests")
        assert hasattr(provider, "requests_per_minute")

        assert isinstance(provider.min_request_interval, float)
        assert isinstance(provider.max_concurrent_requests, int)
        assert isinstance(provider.requests_per_minute, int)


class TestGeminiTTSProviderInterfaces:
    """Test ITTSEngine interface implementation."""

    def test_supports_ssml(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should support SSML markup."""
        provider = basic_gemini_provider

        assert provider.supports_ssml() is True


class TestGeminiTTSProviderTextValidation:
    """Test text input validation for TTS generation."""

    def test_generate_audio_data_rejects_empty_text(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should reject empty text input."""
        provider = basic_gemini_provider

        result = provider.generate_audio_data("")

        assert result.is_failure
        assert result.error is not None
        assert result.error.code == ErrorCode.TTS_ENGINE_ERROR
        assert "Empty text provided" in str(result.error.details)

    def test_generate_audio_data_rejects_whitespace_only(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should reject whitespace-only text."""
        provider = basic_gemini_provider

        result = provider.generate_audio_data("   \n\t  ")

        assert result.is_failure
        assert result.error is not None
        assert result.error.code == ErrorCode.TTS_ENGINE_ERROR
        assert "Empty text provided" in str(result.error.details)

    def test_generate_audio_data_accepts_valid_text(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should accept valid text input."""
        provider = basic_gemini_provider

        result = provider.generate_audio_data("Hello, this is a test.")

        # Placeholder implementation returns success with fake data
        assert result.is_success
        assert result.value == b"fake_audio_data"

    def test_generate_audio_data_handles_unicode(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should handle Unicode characters in text."""
        provider = basic_gemini_provider

        unicode_text = "Héllo wörld! 你好世界 🌍"
        result = provider.generate_audio_data(unicode_text)

        assert result.is_success
        assert result.value == b"fake_audio_data"

    def test_generate_audio_data_handles_ssml(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should handle SSML markup in text."""
        provider = basic_gemini_provider

        ssml_text = """
        <speak>
            <break time="1s"/>
            <emphasis level="strong">Important text</emphasis>
            <prosody rate="slow" pitch="low">Slow low voice</prosody>
        </speak>
        """

        result = provider.generate_audio_data(ssml_text)

        assert result.is_success
        assert result.value == b"fake_audio_data"


class TestGeminiTTSProviderAsyncGeneration:
    """Test async TTS generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_audio_data_async_success(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should generate audio asynchronously."""
        provider = basic_gemini_provider

        result = await provider.generate_audio_data_async("Test text for async generation")

        assert result.is_success
        assert result.value == b"fake_audio_data"

    @pytest.mark.asyncio
    async def test_generate_audio_data_async_rejects_empty_text(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should reject empty text in async generation."""
        provider = basic_gemini_provider

        result = await provider.generate_audio_data_async("")

        assert result.is_failure
        assert result.error is not None
        assert result.error.code == ErrorCode.TTS_ENGINE_ERROR
        assert "Empty text provided" in str(result.error.details)

    @pytest.mark.asyncio
    async def test_generate_audio_data_async_handles_long_text(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should handle long text in async generation."""
        provider = basic_gemini_provider

        long_text = "This is a very long text. " * 100  # 2700+ characters
        result = await provider.generate_audio_data_async(long_text)

        assert result.is_success
        assert result.value == b"fake_audio_data"


class TestGeminiTTSProviderConfiguration:
    """Test provider configuration and settings."""

    def test_voice_name_configuration(self) -> None:
        """Should accept different voice names."""
        voice_names = ["Kore", "Aria", "Nova", "Sage"]

        for voice_name in voice_names:
            provider = GeminiTTSProvider(
                model_name="gemini-1.5-flash",
                api_key="test_key",
                voice_name=voice_name,
            )

            assert provider.voice_name == voice_name

    def test_model_name_configuration(self) -> None:
        """Should accept different model names."""
        model_names = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]

        for model_name in model_names:
            provider = GeminiTTSProvider(
                model_name=model_name,
                api_key="test_key",
                voice_name="Kore",
            )

            assert provider.model_name == model_name

    def test_rate_limiting_configuration(self) -> None:
        """Should accept rate limiting configuration."""
        provider = GeminiTTSProvider(
            model_name="gemini-1.5-flash",
            api_key="test_key",
            voice_name="Kore",
            min_request_interval=0.5,
            max_concurrent_requests=10,
            requests_per_minute=120,
        )

        assert provider.min_request_interval == 0.5
        assert provider.max_concurrent_requests == 10
        assert provider.requests_per_minute == 120

    def test_api_key_storage(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should store API key securely."""
        provider = basic_gemini_provider

        # API key should be stored but not logged/exposed
        assert provider.api_key == "test_api_key"
        assert hasattr(provider, "api_key")


class TestGeminiTTSProviderPlaceholderBehavior:
    """Test current placeholder implementation behavior."""

    def test_placeholder_returns_consistent_data(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Placeholder should return consistent fake data."""
        provider = basic_gemini_provider

        # Multiple calls should return same fake data
        result1 = provider.generate_audio_data("Text 1")
        result2 = provider.generate_audio_data("Text 2")

        assert result1.is_success
        assert result2.is_success
        assert result1.value == result2.value == b"fake_audio_data"

    def test_placeholder_ignores_text_content(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Placeholder should ignore actual text content."""
        provider = basic_gemini_provider

        texts = [
            "Short text",
            "Very long text that would normally take longer to process",
            "Text with SSML <break time='1s'/> markup",
            "Unicode text: 你好世界",
        ]

        for text in texts:
            result = provider.generate_audio_data(text)
            assert result.is_success
            assert result.value == b"fake_audio_data"

    @pytest.mark.asyncio
    async def test_placeholder_async_matches_sync(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Placeholder async should match sync behavior."""
        provider = basic_gemini_provider

        sync_result = provider.generate_audio_data("Test text")
        async_result = await provider.generate_audio_data_async("Test text")

        assert sync_result.is_success == async_result.is_success
        assert sync_result.value == async_result.value


class TestGeminiTTSProviderErrorHandling:
    """Test error handling behavior."""

    def test_handles_edge_case_inputs(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should handle edge case text inputs."""
        provider = basic_gemini_provider

        edge_cases = [
            ".",  # Single punctuation
            "123",  # Numbers only
            "!@#$%^&*()",  # Special characters
            "A" * 10000,  # Very long text
        ]

        for text in edge_cases:
            result = provider.generate_audio_data(text)
            # Placeholder implementation should handle all cases
            assert result.is_success
            assert result.value == b"fake_audio_data"

    def test_empty_text_error_consistency(self, basic_gemini_provider: GeminiTTSProvider) -> None:
        """Should consistently reject empty text."""
        provider = basic_gemini_provider

        empty_inputs = ["", "   ", "\n\n", "\t\t", "  \n  \t  "]

        for empty_input in empty_inputs:
            result = provider.generate_audio_data(empty_input)
            assert result.is_failure
            assert result.error is not None
            assert result.error.code == ErrorCode.TTS_ENGINE_ERROR
            assert "Empty text provided" in str(result.error.details)


# TODO: When real Gemini TTS integration is implemented, add these test classes:
#
# class TestGeminiTTSProviderRealAPIIntegration:
#     """Test real Gemini API integration (when implemented)."""
#     pass
#
# class TestGeminiTTSProviderRateLimiting:
#     """Test rate limiting behavior with real API."""
#     pass
#
# class TestGeminiTTSProviderSSMLProcessing:
#     """Test SSML processing with real Gemini API."""
#     pass
#
# class TestGeminiTTSProviderNetworkErrorHandling:
#     """Test network error handling with real API calls."""
#     pass
