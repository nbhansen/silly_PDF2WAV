from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

@dataclass
class TTSConfig:
    voice_quality: str = "medium"  # low/medium/high
    speaking_style: str = "neutral"  # casual/professional/narrative  
    speed: float = 1.0
    
    # Engine-specific configs
    coqui: Optional['CoquiConfig'] = None
    gtts: Optional['GTTSConfig'] = None
    gemini: Optional['GeminiConfig'] = None

@dataclass
class CoquiConfig:
    model_name: Optional[str] = None
    speaker: Optional[str] = None
    use_gpu: Optional[bool] = None

@dataclass 
class GTTSConfig:
    lang: str = "en"
    tld: str = "co.uk"
    slow: bool = False

@dataclass
class GeminiConfig:
    voice_name: str = "Kore"
    style_prompt: Optional[str] = None

class ConfigAdapter(ABC):
    @abstractmethod
    def adapt(self, config: TTSConfig) -> Dict[str, Any]:
        pass

class CoquiConfigAdapter(ConfigAdapter):
    def adapt(self, config: TTSConfig) -> Dict[str, Any]:
        if config.coqui:
            return {
                "model_name": config.coqui.model_name or self._quality_to_model(config.voice_quality),
                "speaker_idx_to_use": config.coqui.speaker,
                "use_gpu_if_available": config.coqui.use_gpu or (config.voice_quality == "high")
            }
        return {
            "model_name": self._quality_to_model(config.voice_quality),
            "use_gpu_if_available": config.voice_quality == "high"
        }
    
    def _quality_to_model(self, quality: str) -> str:
        mapping = {
            "low": "tts_models/en/ljspeech/vits",
            "medium": "tts_models/en/ljspeech/vits", 
            "high": "tts_models/en/vctk/vits"
        }
        return mapping.get(quality, mapping["medium"])

class GTTSConfigAdapter(ConfigAdapter):
    def adapt(self, config: TTSConfig) -> Dict[str, Any]:
        if config.gtts:
            return {
                "lang": config.gtts.lang,
                "tld": config.gtts.tld,
                "slow": config.gtts.slow
            }
        return {"lang": "en", "tld": "co.uk", "slow": False}

class BarkConfigAdapter(ConfigAdapter):
    def adapt(self, config: TTSConfig) -> Dict[str, Any]:
        return {
            "use_gpu_if_available": config.voice_quality == "high",
            "use_small_models": config.voice_quality == "low"
        }