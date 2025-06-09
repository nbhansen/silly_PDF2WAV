# infrastructure/tts/bark_tts_provider.py
import os
import torch
import numpy # For Bark's add_safe_globals fix
from domain.interfaces import ITTSEngine
from domain.config import BarkConfig


try:
    from bark import SAMPLE_RATE as BARK_SAMPLE_RATE, generate_audio, preload_models
    from scipy.io.wavfile import write as write_wav
    BARK_AVAILABLE = True
    print("Bark library found and imported successfully.")
except ImportError:
    print("Bark library (suno-bark) or scipy.io.wavfile not found. BarkTTSProvider will not be available.")
    BARK_AVAILABLE = False

if BARK_AVAILABLE:
    class BarkTTSProvider(ITTSEngine):
        def __init__(self, config: BarkConfig):
            self.output_format = "wav"
            self.sample_rate = BARK_SAMPLE_RATE
            self.history_prompt = config.history_prompt
            self.models_loaded = False

            try:
                if hasattr(torch, 'serialization') and hasattr(torch.serialization, 'add_safe_globals'):
                    torch.serialization.add_safe_globals([numpy.core.multiarray.scalar])
                    print("BarkTTSProvider: Added numpy.core.multiarray.scalar to PyTorch safe globals.")
            except Exception as e:
                print(f"BarkTTSProvider: Error trying to add_safe_globals: {e}")

            text_use_gpu = False
            coarse_use_gpu = False
            fine_use_gpu = False
            codec_use_gpu = True 

            if config.use_gpu is not None and config.use_gpu and torch.cuda.is_available():
                print("BarkTTSProvider: CUDA available, enabling GPU for Bark components.")
                text_use_gpu = True
                coarse_use_gpu = True
                fine_use_gpu = True
            else:
                if config.use_gpu: 
                    print("BarkTTSProvider: GPU requested but CUDA not available. Using CPU for Bark.")
                else: 
                    print("BarkTTSProvider: GPU not requested. Using CPU for Bark.")
            
            try:
                print("BarkTTSProvider: Preloading Bark models...")
                preload_models(
                    text_use_gpu=text_use_gpu,
                    text_use_small=config.use_small_models,
                    coarse_use_gpu=coarse_use_gpu,
                    coarse_use_small=config.use_small_models,
                    fine_use_gpu=fine_use_gpu,
                    fine_use_small=config.use_small_models,
                    codec_use_gpu=codec_use_gpu
                )
                print("BarkTTSProvider: Bark models preloaded successfully.")
                self.models_loaded = True
            except Exception as e:
                print(f"BarkTTSProvider: Error preloading Bark models: {e}")
                self.models_loaded = False

        def generate_audio_data(self, text_to_speak: str) -> bytes:
            if not self.models_loaded:
                print("BarkTTSProvider: Bark models not loaded. Skipping audio generation.")
                return b""
            print(f"BarkTTSProvider: Attempting Bark audio generation.")
            if not text_to_speak or text_to_speak.strip() == "" or \
               text_to_speak.startswith("LLM cleaning skipped") or text_to_speak.startswith("Error:") or \
               text_to_speak.startswith("Could not convert") or text_to_speak.startswith("No text could be extracted"):
                print("BarkTTSProvider: Skipping audio generation due to empty or error text.")
                return b""
            try:
                print(f"BarkTTSProvider: Generating audio for text: \"{text_to_speak[:100]}...\"")
                current_history_prompt = self.history_prompt if isinstance(self.history_prompt, str) else None
                audio_array = generate_audio(text_to_speak, history_prompt=current_history_prompt)
                
                # Bark generates numpy array, convert to bytes
                # Need to save to a temp file and read back to get bytes in WAV format
                temp_audio_filepath = "temp_bark_audio.wav"
                write_wav(temp_audio_filepath, self.sample_rate, audio_array)
                
                with open(temp_audio_filepath, "rb") as f:
                    audio_data = f.read()
                os.remove(temp_audio_filepath) # Clean up temp file
                
                print(f"BarkTTSProvider: Generated audio data ({len(audio_data)} bytes).")
                return audio_data
            except Exception as e:
                print(f"BarkTTSProvider: Error generating audio data with Bark: {e}")
                import traceback
                traceback.print_exc()
                return b""

        def get_output_format(self) -> str:
            return self.output_format
else:
    class BarkTTSProvider(ITTSEngine):
        def __init__(self, config: BarkConfig):
            print("BarkTTSProvider: Bark library not available. This provider will not function.")
        def generate_audio_data(self, text_to_speak: str) -> bytes:
            print("BarkTTSProvider: Bark library not available. Cannot generate audio.")
            return b""
        def get_output_format(self) -> str:
            return "wav"