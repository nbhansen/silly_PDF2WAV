# domain/container/service_container.py - Simple Service Container
"""Clean, minimal service container that replaces the complex CompositionRoot.
Focuses on dependency injection without over-engineering.
Uses immutable MappingProxyType for true immutability.
"""

from abc import ABC, abstractmethod
import types
from typing import TYPE_CHECKING, Any, Callable, TypeVar, Union

if TYPE_CHECKING:
    from application.config.system_config import SystemConfig
else:
    from application.config.system_config import SystemConfig

T = TypeVar("T")


class IServiceContainer(ABC):
    """Simple service container interface."""

    @abstractmethod
    def get(self, interface: Union[type[T], str]) -> T:
        """Get a service instance."""

    @abstractmethod
    def has(self, interface: Union[type[T], str]) -> bool:
        """Check if service is registered."""


class ServiceContainer(IServiceContainer):
    """Immutable service container with lazy initialization.
    High cohesion: All dependency injection in one place.
    Low coupling: Uses factories to avoid tight dependencies.
    Thread-safe: Uses immutable MappingProxyType for factories.
    """

    def __init__(self, config: "SystemConfig"):
        self.config = config

        # Build all factories upfront (immutable)
        factories = self._build_core_services()
        self._factories: types.MappingProxyType[Union[type[Any], str], Callable[[], Any]] = types.MappingProxyType(
            factories
        )

        # Mutable singleton cache (internal implementation detail)
        # Note: This is the only mutable part, but it's thread-safe lazy loading
        self._singletons: dict[Union[type[Any], str], Any] = {}

    def get(self, interface: Union[type[T], str]) -> T:
        """Get service instance (singleton pattern)."""
        if interface in self._singletons:
            return self._singletons[interface]  # type: ignore[no-any-return]

        if interface not in self._factories:
            interface_name = getattr(interface, "__name__", str(interface))
            raise ValueError(f"Service {interface_name} not registered")

        # Create instance using factory
        instance = self._factories[interface]()
        self._singletons[interface] = instance
        return instance  # type: ignore[no-any-return]

    def has(self, interface: Union[type[T], str]) -> bool:
        """Check if service is registered."""
        return interface in self._factories

    def _build_core_services(self) -> dict[Union[type[Any], str], Callable[[], Any]]:
        """Build all core service factories upfront (immutable pattern)."""
        from domain.audio.audio_engine import AudioEngine, IAudioEngine
        from domain.audio.timing_engine import ITimingEngine, TimingEngine, TimingMode
        from domain.text.text_pipeline import ITextPipeline, TextPipeline
        from infrastructure.file.file_manager import FileManager
        from infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
        from infrastructure.ocr.tesseract_ocr_provider import TesseractOCRProvider

        # Build all factories in a single immutable dict
        factories: dict[Union[type[Any], str], Callable[[], Any]] = {
            # File Manager
            FileManager: lambda: FileManager(
                upload_folder=self.config.upload_folder, output_folder=self.config.audio_folder
            ),
            # TTS Engine (factory method)
            "tts_engine": lambda: self._create_tts_engine(),
            # Text Pipeline
            ITextPipeline: lambda: TextPipeline(
                llm_provider=self.get(GeminiLLMProvider) if self.config.gemini_api_key else None,
                enable_cleaning=self.config.enable_text_cleaning,
                enable_ssml=self.config.enable_ssml,
            ),
            # Timing Engine
            ITimingEngine: lambda: TimingEngine(
                tts_engine=self.get("tts_engine"),
                file_manager=self.get(FileManager),
                text_pipeline=self.get(ITextPipeline),
                mode=TimingMode.MEASUREMENT if self.config.gemini_use_measurement_mode else TimingMode.ESTIMATION,
                measurement_interval=self.config.gemini_measurement_mode_interval,
            ),
            # Audio Engine
            IAudioEngine: lambda: AudioEngine(
                tts_engine=self.get("tts_engine"),
                file_manager=self.get(FileManager),
                timing_engine=self.get(ITimingEngine),
                max_concurrent=self.config.max_concurrent_requests,
                audio_target_chunk_size=self.config.audio_target_chunk_size,
                audio_max_chunk_size=self.config.audio_max_chunk_size,
            ),
            # OCR Provider
            TesseractOCRProvider: lambda: TesseractOCRProvider(config=self.config),
        }

        # Add LLM Provider only if configured
        if self.config.gemini_api_key:
            api_key = self.config.gemini_api_key
            if api_key is not None:  # Type guard for mypy
                factories[GeminiLLMProvider] = lambda: GeminiLLMProvider(
                    model_name=self.config.gemini_model_name, api_key=api_key
                )

        return factories

    def _create_tts_engine(self) -> Any:
        """Factory for TTS engine based on configuration."""
        from infrastructure.tts.gemini_tts_provider import GeminiTTSProvider
        from infrastructure.tts.piper_tts_provider import PiperTTSProvider

        if self.config.tts_engine.value == "gemini":
            if not self.config.gemini_api_key:
                raise ValueError("Gemini API key is required for Gemini TTS engine")
            return GeminiTTSProvider(
                model_name=self.config.gemini_model_name,
                api_key=self.config.gemini_api_key,
                voice_name=self.config.gemini_voice_name,
                min_request_interval=self.config.gemini_min_request_interval,
                max_concurrent_requests=self.config.gemini_max_concurrent_requests,
                requests_per_minute=self.config.gemini_requests_per_minute,
            )
        else:
            piper_config = self.config.get_piper_config()
            # Ensure we have a proper PiperConfig object, not a dict fallback
            if isinstance(piper_config, dict):
                # Create PiperConfig from dict if needed
                from domain.config.tts_config import PiperConfig

                piper_config = PiperConfig(**piper_config)
            # Handle both the full PiperTTSProvider and the fallback version
            try:
                return PiperTTSProvider(config=piper_config, repository_url=self.config.piper_model_repository_url)
            except TypeError:
                # Fallback version only takes config parameter
                return PiperTTSProvider(config=piper_config)


class ImmutableServiceContainerBuilder:
    """Builder for creating immutable service containers with additional registrations."""

    def __init__(self, config: SystemConfig):
        self.config = config
        self._additional_factories: dict[Union[type[Any], str], Callable[[], Any]] = {}

    def register(self, interface: Union[type[T], str], factory: Callable[[], T]) -> "ImmutableServiceContainerBuilder":
        """Register additional service factory (builder pattern)."""
        self._additional_factories[interface] = factory
        return self

    def build(self) -> ServiceContainer:
        """Build the immutable service container."""
        # Create container with core services
        container = ServiceContainer(self.config)

        # Add additional factories if any (they'll be merged into the immutable proxy)
        if self._additional_factories:
            # Get existing factories and merge with additional ones
            all_factories = dict(container._factories)  # Convert proxy to dict
            all_factories.update(self._additional_factories)

            # Replace with new immutable proxy
            object.__setattr__(container, "_factories", types.MappingProxyType(all_factories))

        return container


def create_service_container(config: SystemConfig) -> ServiceContainer:
    """Factory function to create configured service container."""
    return ImmutableServiceContainerBuilder(config).build()


def create_service_container_builder(config: SystemConfig) -> ImmutableServiceContainerBuilder:
    """Factory function to create service container builder for additional registrations."""
    return ImmutableServiceContainerBuilder(config)
