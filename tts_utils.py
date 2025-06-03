# This module provides a unified interface for various TTS engines though should be refactored

import os
import torch # For checking CUDA availability and setting device
import numpy # For Bark's add_safe_globals fix

# --- Abstract Class for TTS Processors ---
class BaseTTSProcessor:
    """
  
    Specific TTS engine wrappers should inherit from this class
    and implement the generate_audio_file method.
    """
    def __init__(self, **kwargs):
        """
        Initializes the base processor.
        kwargs can be used to pass engine-specific configurations.
        """
        print(f"Initializing {self.__class__.__name__} with args: {kwargs}")
        pass

    def generate_audio_file(self, text_to_speak, output_filename_no_ext, audio_dir):
        """
        Generates an audio file from the given text.
        This method MUST be implemented by subclasses.

        Args:
            text_to_speak (str): The text to convert to speech.
            output_filename_no_ext (str): The base name for the output audio file (without extension).
            audio_dir (str): The directory where the audio file will be saved.

        Returns:
            str: The filename of the generated audio (e.g., "output.wav" or "output.mp3"), 
                 or None if generation fails.
        
        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement generate_audio_file.")

    def get_output_extension(self):
        """
        Returns the expected audio file extension (e.g., "wav", "mp3").
        This method SHOULD be implemented by subclasses.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement get_output_extension.")

# --- Coqui TTS Implementation ---
try:
    from TTS.api import TTS as CoquiTTS_API
    COQUI_TTS_AVAILABLE = True
    print("Coqui TTS library (TTS.api) found and imported successfully.")
except ImportError:
    print("TTS (Coqui TTS) library not found. CoquiTTSProcessor will not be available.")
    COQUI_TTS_AVAILABLE = False

if COQUI_TTS_AVAILABLE:
    class CoquiTTSProcessor(BaseTTSProcessor):
        """
        TTS Processor implementation using Coqui TTS.
        """
        def __init__(self, model_name="tts_models/en/vctk/vits", use_gpu_if_available=False, speaker_idx_to_use=None):
            super().__init__(model_name=model_name, use_gpu_if_available=use_gpu_if_available, speaker_idx_to_use=speaker_idx_to_use)
            self.model_name = model_name
            self.tts_model = None
            self.speaker_to_use = speaker_idx_to_use 
            self.is_multi_speaker = False
            self.output_extension = "wav"

            try:
                print(f"CoquiTTSProcessor: Initializing Coqui TTS model: {self.model_name}")
                self.tts_model = CoquiTTS_API(model_name=self.model_name) 
                
                if use_gpu_if_available:
                    if torch.cuda.is_available():
                        device = "cuda"
                        print("CoquiTTSProcessor: CUDA is available. Attempting to use GPU.")
                    else:
                        device = "cpu"
                        print("CoquiTTSProcessor: CUDA not available. Using CPU.")
                else:
                    device = "cpu"
                    print("CoquiTTSProcessor: GPU usage not requested. Using CPU.")
                
                self.tts_model.to(device) 
                print(f"CoquiTTSProcessor: Coqui TTS model initialized successfully on {device.upper()}.")

                if self.tts_model.is_multi_speaker:
                    self.is_multi_speaker = True
                    print("CoquiTTSProcessor: Model is multi-speaker.")
                    available_speakers_raw = self.tts_model.speakers
                    available_speakers_cleaned = [spk.strip() for spk in available_speakers_raw if isinstance(spk, str)]
                    
                    print("Available Coqui speakers (raw):", available_speakers_raw)
                    print("Available Coqui speakers (cleaned):", available_speakers_cleaned)

                    if not available_speakers_cleaned:
                        print("CoquiTTSProcessor: ERROR - No valid speaker IDs found after cleaning.")
                        self.is_multi_speaker = False 
                    elif self.speaker_to_use is None: 
                        self.speaker_to_use = available_speakers_cleaned[0] 
                        print(f"CoquiTTSProcessor: Defaulting to speaker: {self.speaker_to_use}")
                    elif self.speaker_to_use.strip() not in available_speakers_cleaned: 
                        requested_speaker_cleaned = self.speaker_to_use.strip()
                        print(f"CoquiTTSProcessor: WARNING - Specified speaker '{requested_speaker_cleaned}' not found. Defaulting to first available.")
                        self.speaker_to_use = available_speakers_cleaned[0] 
                        print(f"CoquiTTSProcessor: Now using speaker (fallback): {self.speaker_to_use}")
                    else: 
                        self.speaker_to_use = self.speaker_to_use.strip() 
                        print(f"CoquiTTSProcessor: Using specified speaker: {self.speaker_to_use}")
                else:
                    print(f"CoquiTTSProcessor: Model '{self.model_name}' is single-speaker.")
            except Exception as e:
                print(f"CoquiTTSProcessor: Error initializing Coqui TTS model: {e}")
                self.tts_model = None 

        def generate_audio_file(self, text_to_speak, output_filename_no_ext, audio_dir):
            if not self.tts_model:
                print("CoquiTTSProcessor: Coqui TTS model not available. Skipping audio generation.")
                return None
            print(f"CoquiTTSProcessor: Attempting Coqui TTS audio generation for {output_filename_no_ext}.{self.output_extension}")
            if not text_to_speak or text_to_speak.strip() == "" or \
               text_to_speak.startswith("LLM cleaning skipped") or text_to_speak.startswith("Error:") or \
               text_to_speak.startswith("Could not convert") or text_to_speak.startswith("No text could be extracted"):
                print("CoquiTTSProcessor: Skipping audio generation due to empty or error text from previous steps.")
                return None
            try:
                os.makedirs(audio_dir, exist_ok=True) 
                audio_filename = f"{output_filename_no_ext}.{self.output_extension}"
                audio_filepath = os.path.join(audio_dir, audio_filename)
                speaker_arg = None 
                if self.is_multi_speaker:
                    if self.speaker_to_use:
                        speaker_arg = self.speaker_to_use
                    else:
                        print("CoquiTTSProcessor: ERROR - Model is multi-speaker but no speaker is selected/available.")
                        return None
                self.tts_model.tts_to_file(text=text_to_speak, speaker=speaker_arg, file_path=audio_filepath)
                print(f"CoquiTTSProcessor: Audio file saved: {audio_filepath}")
                return audio_filename
            except Exception as e:
                print(f"CoquiTTSProcessor: Error generating audio file with Coqui TTS: {e}")
                return None
        
        def get_output_extension(self):
            return self.output_extension

# --- gTTS Implementation ---
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
    print("gTTS library found and imported successfully.")
except ImportError:
    print("gTTS library not found. GTTSProcessor will not be available.")
    GTTS_AVAILABLE = False

if GTTS_AVAILABLE:
    class GTTSProcessor(BaseTTSProcessor):
        def __init__(self, lang='en', tld='co.uk', slow=False):
            super().__init__(lang=lang, tld=tld, slow=slow)
            self.lang = lang
            self.tld = tld
            self.slow = slow
            self.output_extension = "mp3"
            print(f"GTTSProcessor: Initialized for lang='{lang}', tld='{tld}'.")

        def generate_audio_file(self, text_to_speak, output_filename_no_ext, audio_dir):
            print(f"GTTSProcessor: Attempting gTTS audio generation for {output_filename_no_ext}.{self.output_extension} ({self.lang}, {self.tld})")
            if not text_to_speak or text_to_speak.strip() == "" or \
               text_to_speak.startswith("LLM cleaning skipped") or text_to_speak.startswith("Error:") or \
               text_to_speak.startswith("Could not convert") or text_to_speak.startswith("No text could be extracted"):
                print("GTTSProcessor: Skipping audio generation due to empty or error text.")
                return None
            try:
                tts_object = gTTS(text=text_to_speak, lang=self.lang, tld=self.tld, slow=self.slow)
                os.makedirs(audio_dir, exist_ok=True) 
                audio_filename = f"{output_filename_no_ext}.{self.output_extension}"
                audio_filepath = os.path.join(audio_dir, audio_filename)
                tts_object.save(audio_filepath)
                print(f"GTTSProcessor: Audio file saved: {audio_filepath}")
                return audio_filename
            except Exception as e:
                print(f"GTTSProcessor: Error generating audio file with gTTS: {e}")
                return None

        def get_output_extension(self):
            return self.output_extension

# --- Bark TTS Implementation ---
try:
    from bark import SAMPLE_RATE as BARK_SAMPLE_RATE, generate_audio, preload_models
    from scipy.io.wavfile import write as write_wav
    BARK_AVAILABLE = True
    print("Bark library found and imported successfully.")
except ImportError:
    print("Bark library (suno-bark) or scipy.io.wavfile not found. BarkTTSProcessor will not be available.")
    BARK_AVAILABLE = False

if BARK_AVAILABLE:
    class BarkTTSProcessor(BaseTTSProcessor):
        def __init__(self, use_gpu_if_available=True, use_small_models=False, history_prompt=None):
            super().__init__(use_gpu_if_available=use_gpu_if_available, use_small_models=use_small_models)
            self.output_extension = "wav"
            self.sample_rate = BARK_SAMPLE_RATE
            self.history_prompt = history_prompt 
            self.models_loaded = False

            try:
                if hasattr(torch, 'serialization') and hasattr(torch.serialization, 'add_safe_globals'):
                    torch.serialization.add_safe_globals([numpy.core.multiarray.scalar])
                    print("BarkTTSProcessor: Added numpy.core.multiarray.scalar to PyTorch safe globals.")
            except Exception as e:
                print(f"BarkTTSProcessor: Error trying to add_safe_globals: {e}")

            text_use_gpu = False
            coarse_use_gpu = False
            fine_use_gpu = False
            codec_use_gpu = True 

            if use_gpu_if_available and torch.cuda.is_available():
                print("BarkTTSProcessor: CUDA available, enabling GPU for Bark components.")
                text_use_gpu = True
                coarse_use_gpu = True
                fine_use_gpu = True
            else:
                if use_gpu_if_available: 
                    print("BarkTTSProcessor: GPU requested but CUDA not available. Using CPU for Bark.")
                else: 
                    print("BarkTTSProcessor: GPU not requested. Using CPU for Bark.")
            
            try:
                print("BarkTTSProcessor: Preloading Bark models...")
                preload_models(
                    text_use_gpu=text_use_gpu,
                    text_use_small=use_small_models,
                    coarse_use_gpu=coarse_use_gpu,
                    coarse_use_small=use_small_models,
                    fine_use_gpu=fine_use_gpu,
                    fine_use_small=use_small_models,
                    codec_use_gpu=codec_use_gpu
                )
                print("BarkTTSProcessor: Bark models preloaded successfully.")
                self.models_loaded = True
            except Exception as e:
                print(f"BarkTTSProcessor: Error preloading Bark models: {e}")
                self.models_loaded = False

        def generate_audio_file(self, text_to_speak, output_filename_no_ext, audio_dir):
            if not self.models_loaded:
                print("BarkTTSProcessor: Bark models not loaded. Skipping audio generation.")
                return None
            print(f"BarkTTSProcessor: Attempting Bark audio generation for {output_filename_no_ext}.{self.output_extension}")
            if not text_to_speak or text_to_speak.strip() == "" or \
               text_to_speak.startswith("LLM cleaning skipped") or text_to_speak.startswith("Error:") or \
               text_to_speak.startswith("Could not convert") or text_to_speak.startswith("No text could be extracted"):
                print("BarkTTSProcessor: Skipping audio generation due to empty or error text.")
                return None
            try:
                print(f"BarkTTSProcessor: Generating audio for text: \"{text_to_speak[:100]}...\"")
                current_history_prompt = self.history_prompt if isinstance(self.history_prompt, str) else None
                audio_array = generate_audio(text_to_speak, history_prompt=current_history_prompt)
                os.makedirs(audio_dir, exist_ok=True)
                audio_filename = f"{output_filename_no_ext}.{self.output_extension}"
                audio_filepath = os.path.join(audio_dir, audio_filename)
                write_wav(audio_filepath, self.sample_rate, audio_array)
                print(f"BarkTTSProcessor: Audio file saved: {audio_filepath}")
                return audio_filename
            except Exception as e:
                print(f"BarkTTSProcessor: Error generating audio file with Bark: {e}")
                import traceback
                traceback.print_exc()
                return None

        def get_output_extension(self):
            return self.output_extension

# --- TTS Factory ---
def get_tts_processor(engine_name="coqui", **kwargs):
    """
    Factory function to get an instance of a TTS processor.
    """
    engine_name_lower = engine_name.lower()
    print(f"TTSFactory: Attempting to create processor for engine: '{engine_name_lower}' with kwargs: {kwargs}")

    if engine_name_lower == "coqui":
        if COQUI_TTS_AVAILABLE:
            print(f"TTSFactory: Creating CoquiTTSProcessor.")
            return CoquiTTSProcessor(**kwargs)
        else:
            print("TTSFactory: Coqui TTS selected but not available.")
    elif engine_name_lower == "gtts":
        if GTTS_AVAILABLE:
            print(f"TTSFactory: Creating GTTSProcessor.")
            return GTTSProcessor(**kwargs)
        else:
            print("TTSFactory: gTTS selected but not available.")
    elif engine_name_lower == "bark":
        if BARK_AVAILABLE:
            print(f"TTSFactory: Creating BarkTTSProcessor.")
            return BarkTTSProcessor(**kwargs)
        else:
            print("TTSFactory: Bark selected but not available.")
    
    # Fallback logic
    print(f"TTSFactory: Engine '{engine_name_lower}' not found or not available.")
    if GTTS_AVAILABLE: # Primary fallback
        print("TTSFactory: Defaulting to gTTS.")
        return GTTSProcessor() # Use gTTS default kwargs
    elif COQUI_TTS_AVAILABLE: # Secondary fallback
        print("TTSFactory: Defaulting to CoquiTTS (as gTTS not available).")
        return CoquiTTSProcessor() # Use CoquiTTS default kwargs
        
    print("TTSFactory: CRITICAL - No TTS engines available or specified engine not found and no fallback available.")
    return None
