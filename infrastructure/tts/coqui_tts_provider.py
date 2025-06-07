# infrastructure/tts/coqui_tts_provider.py
import os
import torch
from typing import Optional, Dict, Any
from domain.models import ITTSEngine, CoquiConfig

try:
    from TTS.api import TTS as CoquiTTS_API
    COQUI_TTS_AVAILABLE = True
    print("Coqui TTS library (TTS.api) found and imported successfully.")
except ImportError:
    print("TTS (Coqui TTS) library not found. CoquiTTSProvider will not be available.")
    COQUI_TTS_AVAILABLE = False

if COQUI_TTS_AVAILABLE:
    class CoquiTTSProvider(ITTSEngine):
        """
        Direct implementation of ITTSEngine using Coqui TTS.
        """
        def __init__(self, config: CoquiConfig):
            self.model_name = config.model_name or self._quality_to_model("medium") # Default if not specified
            self.speaker_to_use = config.speaker
            self.use_gpu_if_available = config.use_gpu if config.use_gpu is not None else False # Default to False
            self.tts_model = None
            self.is_multi_speaker = False
            self.output_format = "wav"

            try:
                print(f"CoquiTTSProvider: Initializing Coqui TTS model: {self.model_name}")
                self.tts_model = CoquiTTS_API(model_name=self.model_name) 
                
                if self.use_gpu_if_available:
                    if torch.cuda.is_available():
                        device = "cuda"
                        print("CoquiTTSProvider: CUDA is available. Attempting to use GPU.")
                    else:
                        device = "cpu"
                        print("CoquiTTSProvider: CUDA not available. Using CPU.")
                else:
                    device = "cpu"
                    print("CoquiTTSProvider: GPU usage not requested. Using CPU.")
                
                self.tts_model.to(device) 
                print(f"CoquiTTSProvider: Coqui TTS model initialized successfully on {device.upper()}.")

                if self.tts_model.is_multi_speaker:
                    self.is_multi_speaker = True
                    print("CoquiTTSProvider: Model is multi-speaker.")
                    available_speakers_raw = self.tts_model.speakers
                    available_speakers_cleaned = [spk.strip() for spk in available_speakers_raw if isinstance(spk, str)]
                    
                    print("Available Coqui speakers (raw):", available_speakers_raw)
                    print("Available Coqui speakers (cleaned):", available_speakers_cleaned)

                    if not available_speakers_cleaned:
                        print("CoquiTTSProvider: ERROR - No valid speaker IDs found after cleaning.")
                        self.is_multi_speaker = False 
                    elif self.speaker_to_use is None: 
                        self.speaker_to_use = available_speakers_cleaned[0] 
                        print(f"CoquiTTSProvider: Defaulting to speaker: {self.speaker_to_use}")
                    elif self.speaker_to_use.strip() not in available_speakers_cleaned: 
                        requested_speaker_cleaned = self.speaker_to_use.strip()
                        print(f"CoquiTTSProvider: WARNING - Specified speaker '{requested_speaker_cleaned}' not found. Defaulting to first available.")
                        self.speaker_to_use = available_speakers_cleaned[0] 
                        print(f"CoquiTTSProvider: Now using speaker (fallback): {self.speaker_to_use}")
                    else: 
                        self.speaker_to_use = self.speaker_to_use.strip() 
                        print(f"CoquiTTSProvider: Using specified speaker: {self.speaker_to_use}")
                else:
                    print(f"CoquiTTSProvider: Model '{self.model_name}' is single-speaker.")
            except Exception as e:
                print(f"CoquiTTSProvider: Error initializing Coqui TTS model: {e}")
                self.tts_model = None 

        def generate_audio_data(self, text_to_speak: str) -> bytes:
            """Generates raw audio data from text using Coqui TTS."""
            if not self.tts_model:
                print("CoquiTTSProvider: Coqui TTS model not available. Skipping audio generation.")
                return b""
            print(f"CoquiTTSProvider: Attempting Coqui TTS audio generation.")
            if not text_to_speak or text_to_speak.strip() == "" or \
               text_to_speak.startswith("LLM cleaning skipped") or text_to_speak.startswith("Error:") or \
               text_to_speak.startswith("Could not convert") or text_to_speak.startswith("No text could be extracted"):
                print("CoquiTTSProvider: Skipping audio generation due to empty or error text from previous steps.")
                return b""
            try:
                # Coqui's tts_to_file saves directly, so we need a temp file to get bytes
                temp_audio_filepath = "temp_coqui_audio.wav"
                speaker_arg = None 
                if self.is_multi_speaker:
                    if self.speaker_to_use:
                        speaker_arg = self.speaker_to_use
                    else:
                        print("CoquiTTSProvider: ERROR - Model is multi-speaker but no speaker is selected/available.")
                        return b""
                
                self.tts_model.tts_to_file(text=text_to_speak, speaker=speaker_arg, file_path=temp_audio_filepath)
                
                with open(temp_audio_filepath, "rb") as f:
                    audio_data = f.read()
                os.remove(temp_audio_filepath) # Clean up temp file
                
                print(f"CoquiTTSProvider: Generated audio data ({len(audio_data)} bytes).")
                return audio_data
            except Exception as e:
                print(f"CoquiTTSProvider: Error generating audio data with Coqui TTS: {e}")
                return b""
        
        def get_output_format(self) -> str:
            return self.output_format

        def _quality_to_model(self, quality: str) -> str:
            mapping = {
                "low": "tts_models/en/ljspeech/vits",
                "medium": "tts_models/en/ljspeech/vits", 
                "high": "tts_models/en/vctk/vits"
            }
            return mapping.get(quality, mapping["medium"])
else:
    class CoquiTTSProvider(ITTSEngine):
        def __init__(self, config: CoquiConfig):
            print("CoquiTTSProvider: Coqui TTS library not available. This provider will not function.")
        def generate_audio_data(self, text_to_speak: str) -> bytes:
            print("CoquiTTSProvider: Coqui TTS library not available. Cannot generate audio.")
            return b""
        def get_output_format(self) -> str:
            return "wav"