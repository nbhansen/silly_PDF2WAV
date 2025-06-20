# domain/services/engine_capability_detector.py
from typing import Dict, Set

from domain.interfaces import IEngineCapabilityDetector, ITTSEngine, SSMLCapability


class EngineCapabilityDetector(IEngineCapabilityDetector):
    """Concrete implementation for detecting TTS engine capabilities"""
    
    def __init__(self):
        # Engine capability mappings
        self.engine_ssml_capabilities = {
            'GeminiTTSProvider': SSMLCapability.FULL,
            'OpenAITTSProvider': SSMLCapability.BASIC,
            'ElevenLabsTTSProvider': SSMLCapability.ADVANCED,
            'AzureTTSProvider': SSMLCapability.FULL,
            'AWSTTSProvider': SSMLCapability.FULL,
            'PiperTTSProvider': SSMLCapability.BASIC,
            'CoquiTTSProvider': SSMLCapability.NONE,
            'BarkTTSProvider': SSMLCapability.NONE,
            'ESpeakTTSProvider': SSMLCapability.NONE,
        }
        
        # Engines that support native timestamps
        self.timestamp_capable_engines: Set[str] = {
            'GeminiTTSProvider',
            'AzureTTSProvider',
            'AWSTTSProvider'
        }
        
        # Engine rate limiting recommendations (seconds)
        self.rate_limits = {
            'GeminiTTSProvider': 2.0,
            'OpenAITTSProvider': 1.0,
            'ElevenLabsTTSProvider': 1.5,
            'AzureTTSProvider': 0.5,
            'AWSTTSProvider': 0.3,
            'PiperTTSProvider': 0.1,
            'CoquiTTSProvider': 0.1,
            'BarkTTSProvider': 0.1,
            'ESpeakTTSProvider': 0.05,
        }
        
        # Engines that require async processing (cloud-based)
        self.async_engines: Set[str] = {
            'GeminiTTSProvider',
            'OpenAITTSProvider', 
            'ElevenLabsTTSProvider',
            'AzureTTSProvider',
            'AWSTTSProvider'
        }
    
    def detect_ssml_capability(self, engine: ITTSEngine) -> SSMLCapability:
        """Detect SSML capability level of an engine."""
        engine_name = engine.__class__.__name__
        
        # Check predefined capabilities
        if engine_name in self.engine_ssml_capabilities:
            return self.engine_ssml_capabilities[engine_name]
        
        # Try to detect capabilities dynamically
        if hasattr(engine, 'supports_ssml'):
            try:
                if engine.supports_ssml():
                    # Try to determine level based on methods/attributes
                    if hasattr(engine, 'ssml_capability'):
                        return engine.ssml_capability
                    elif hasattr(engine, 'supports_prosody') and engine.supports_prosody():
                        return SSMLCapability.ADVANCED
                    else:
                        return SSMLCapability.BASIC
                else:
                    return SSMLCapability.NONE
            except Exception:
                pass
        
        # Default assumption for unknown engines
        return SSMLCapability.NONE
    
    def supports_timestamps(self, engine: ITTSEngine) -> bool:
        """Check if engine supports native timestamp generation."""
        engine_name = engine.__class__.__name__
        
        # Check predefined capabilities
        if engine_name in self.timestamp_capable_engines:
            return True
        
        # Try to detect dynamically
        if hasattr(engine, 'generate_audio_with_timestamps'):
            return True
        
        if hasattr(engine, 'supports_timestamps'):
            try:
                return engine.supports_timestamps()
            except Exception:
                pass
        
        return False
    
    def get_recommended_rate_limit(self, engine: ITTSEngine) -> float:
        """Get recommended rate limiting delay for engine."""
        engine_name = engine.__class__.__name__
        
        # Check predefined rate limits
        if engine_name in self.rate_limits:
            return self.rate_limits[engine_name]
        
        # Try to get from engine itself
        if hasattr(engine, 'recommended_rate_limit'):
            try:
                return float(engine.recommended_rate_limit)
            except (ValueError, TypeError):
                pass
        
        # Heuristic based on engine type
        if self.requires_async_processing(engine):
            return 1.0  # Conservative for cloud services
        else:
            return 0.1  # Liberal for local engines
    
    def requires_async_processing(self, engine: ITTSEngine) -> bool:
        """Determine if engine should use async processing."""
        engine_name = engine.__class__.__name__
        
        # Check predefined async engines
        if engine_name in self.async_engines:
            return True
        
        # Try to detect based on engine attributes
        if hasattr(engine, 'is_cloud_service'):
            try:
                return engine.is_cloud_service
            except Exception:
                pass
        
        # Heuristic based on naming patterns
        cloud_indicators = ['gemini', 'openai', 'elevenlabs', 'azure', 'aws', 'google', 'microsoft']
        engine_lower = engine_name.lower()
        
        for indicator in cloud_indicators:
            if indicator in engine_lower:
                return True
        
        # Local engines (usually don't require async)
        local_indicators = ['piper', 'coqui', 'bark', 'espeak', 'festival', 'flite']
        for indicator in local_indicators:
            if indicator in engine_lower:
                return False
        
        # Default to async for unknown engines (safer)
        return True
    
    def get_engine_characteristics(self, engine: ITTSEngine) -> Dict[str, any]:
        """Get comprehensive characteristics of an engine"""
        return {
            'name': engine.__class__.__name__,
            'ssml_capability': self.detect_ssml_capability(engine),
            'supports_timestamps': self.supports_timestamps(engine),
            'recommended_rate_limit': self.get_recommended_rate_limit(engine),
            'requires_async': self.requires_async_processing(engine),
            'is_cloud_service': self.requires_async_processing(engine),
            'output_format': getattr(engine, 'get_output_format', lambda: 'wav')()
        }
    
    def register_engine_capabilities(self, engine_name: str, capabilities: Dict[str, any]) -> None:
        """Register capabilities for a custom engine"""
        if 'ssml_capability' in capabilities:
            self.engine_ssml_capabilities[engine_name] = capabilities['ssml_capability']
        
        if 'supports_timestamps' in capabilities and capabilities['supports_timestamps']:
            self.timestamp_capable_engines.add(engine_name)
        
        if 'rate_limit' in capabilities:
            self.rate_limits[engine_name] = capabilities['rate_limit']
        
        if 'requires_async' in capabilities and capabilities['requires_async']:
            self.async_engines.add(engine_name)